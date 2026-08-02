"""LangGraph story-audit workflow (DeepSeek-backed agents).

Default: audit the top STORY_AUDIT_BATCH_SIZE unprocessed clusters
(by member count, source diversity, then recency; newest member within
STORY_AUDIT_MAX_AGE_DAYS), generate images for the first
ARTICLE_IMAGE_MAX_PER_BATCH, then stop.
Optional: single cluster file via --story.

Usage:
  python -m audit.story_audit
  python -m audit.story_audit --story path/to/cluster.txt
  python -m audit.story_audit --story path/to/cluster.txt --no-save
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from audit.agents.analyzer import run as analyzer
from audit.agents.claim_extractor import run as claim_extractor
from audit.agents.fact_checker import run as fact_checker
from audit.agents.judger import run as judger
from audit.persist import (
    attach_cover_image,
    ensure_cluster,
    parse_sources_from_text,
    parse_story_id_from_text,
    persist_verified,
    split_article,
)
from audit.reporting import (
    REPORT_SECTIONS,
    default_output_path,
    print_agent_response,
    write_audit_report,
)
from audit.agents.rhetorical_auditor import run as rhetorical_auditor
from audit.state import StoryAuditState
from audit.agents.synthesizer import run as synthesizer
from common.config import ARTICLE_IMAGE_MAX_PER_BATCH, STORY_AUDIT_BATCH_SIZE
from common.db import fetch_cluster_articles, fetch_unprocessed_clusters, init_db
from mcp_app.utils import format_story_detail

DEFAULT_BATCH_SIZE = STORY_AUDIT_BATCH_SIZE

def load_story(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Story file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_graph():
    graph = StateGraph(StoryAuditState)
    graph.add_node("claim_extractor", claim_extractor)
    graph.add_node("fact_checker", fact_checker)
    graph.add_node("rhetorical_auditor", rhetorical_auditor)
    # defer so judger waits for both branches (fact_checker + rhetorical_auditor)
    graph.add_node("judger", judger, defer=True)
    graph.add_node("analyzer", analyzer)
    graph.add_node("synthesizer", synthesizer)

    graph.add_edge(START, "claim_extractor")
    graph.add_edge(START, "rhetorical_auditor")
    graph.add_edge("claim_extractor", "fact_checker")
    graph.add_edge("fact_checker", "judger")
    graph.add_edge("rhetorical_auditor", "judger")
    graph.add_edge("judger", "analyzer")
    graph.add_edge("analyzer", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()


def run_audit(app, story: str) -> dict:
    """Stream the graph and print each agent response as it completes."""
    result: dict = {"story": story}
    for event in app.stream({"story": story}, stream_mode="updates"):
        for node, update in event.items():
            result.update(update)
            field = dict(REPORT_SECTIONS).get(node)
            if field:
                print_agent_response(node, result.get(field))
    return result


def cluster_to_story_text(cluster: dict, articles: list[dict]) -> str:
    return format_story_detail(
        cluster["cluster_id"],
        cluster.get("description") or "",
        cluster.get("created_at") or "",
        articles,
    ).strip()


def finalize_audit(
    *,
    result: dict,
    output_path: Path,
    save: bool,
    cluster_id: str | None,
    articles: list[dict] | None = None,
    sources: str | None = None,
    category: str | None = None,
    place: str | None = None,
    generate_image: bool = False,
    story_file: bool = False,
) -> bool:
    write_audit_report(output_path, result)
    prefix = "\n" if story_file else ""
    print(f"{prefix}Wrote audit report to {output_path}", flush=True)
    if not save:
        return False
    if story_file:
        init_db()
    if not cluster_id:
        raise SystemExit(
            "Cannot save: pass --cluster-id or include STORY_ID: in the story file"
        )

    cluster = ensure_cluster(cluster_id) if story_file else {}
    category = category if category is not None else cluster.get("category")
    place = place if place is not None else cluster.get("place")
    members = articles if articles is not None else fetch_cluster_articles(cluster_id)
    article_id = persist_verified(
        cluster_id=cluster_id,
        result=result,
        articles=members,
        sources=sources,
        category=category,
        place=place,
    )
    print(
        f"Saved verified_articles id={article_id} cluster_id={cluster_id}",
        flush=True,
    )
    if generate_image:
        title, _ = split_article(result.get("article") or "")
        image_url = attach_cover_image(
            article_id=article_id,
            title=title,
            category=category,
            place=place,
        )
        if image_url:
            print(f"Attached cover image for {article_id}: {image_url}", flush=True)
        else:
            print(f"No cover image for {article_id}", flush=True)
    return True


def audit_cluster(
    app,
    cluster: dict,
    *,
    save: bool,
    generate_image: bool = False,
) -> bool:
    """Audit one cluster. Return whether a verified article was saved."""
    cluster_id = cluster["cluster_id"]
    articles = fetch_cluster_articles(cluster_id)
    if not articles:
        print(f"[skip] {cluster_id}: no member articles", flush=True)
        return False
    story = cluster_to_story_text(cluster, articles)
    print(f"\n>>> Auditing cluster {cluster_id} ({len(articles)} articles)", flush=True)
    result = run_audit(app, story)
    return finalize_audit(
        result=result,
        output_path=default_output_path(cluster_id),
        save=save,
        cluster_id=cluster_id,
        articles=articles,
        category=cluster.get("category"),
        place=cluster.get("place"),
        generate_image=generate_image,
    )


def run_batch(*, batch_size: int, save: bool) -> None:
    init_db()
    app = build_graph()
    total_ok = 0
    total_fail = 0
    images_generated = 0
    image_budget = max(0, ARTICLE_IMAGE_MAX_PER_BATCH)
    batch = fetch_unprocessed_clusters(batch_size)
    if not batch:
        print("No unprocessed clusters to audit.", flush=True)
        return
    print(
        f"\n=== Batch: {len(batch)} largest recent unprocessed cluster(s) "
        f"(batch_size={batch_size}, image_budget={image_budget}) ===",
        flush=True,
    )
    for cluster in batch:
        cluster_id = cluster["cluster_id"]
        try:
            generate_image = save and images_generated < image_budget
            saved = audit_cluster(
                app, cluster, save=save, generate_image=generate_image
            )
            total_ok += 1
            if saved and generate_image:
                # Count the slot even if generation soft-failed so we do not
                # retry endlessly within the same batch.
                images_generated += 1
        except Exception as exc:
            total_fail += 1
            print(
                f"[error] cluster {cluster_id} failed: {exc}",
                flush=True,
            )
            traceback.print_exc()
    print(
        f"\nBatch complete: {total_ok} succeeded, {total_fail} failed, "
        f"{images_generated} image slot(s) used.",
        flush=True,
    )


def run_story_file(
    *,
    story_path: Path,
    output: Path | None,
    cluster_id: str | None,
    save: bool,
) -> None:
    story = load_story(story_path)
    app = build_graph()
    result = run_audit(app, story)

    resolved_id = cluster_id or parse_story_id_from_text(story)
    finalize_audit(
        result=result,
        output_path=output or default_output_path(story_path.stem),
        save=save,
        cluster_id=resolved_id,
        sources=parse_sources_from_text(story),
        generate_image=True,
        story_file=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-audit unprocessed clusters (or a single story file)."
    )
    parser.add_argument(
        "--story",
        type=Path,
        default=None,
        help="Optional single cluster text file (skips DB batch mode)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write agent messages for --story runs "
        "(default: audit/output/<stem>_audit.txt)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Unprocessed clusters per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--cluster-id",
        type=str,
        default=None,
        help="Cluster id when using --story (default: STORY_ID: in file)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write verified_articles / mark cluster processed",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    save = not args.no_save
    if args.story is not None:
        run_story_file(
            story_path=args.story,
            output=args.output,
            cluster_id=args.cluster_id,
            save=save,
        )
        return
    run_batch(batch_size=max(1, args.batch_size), save=save)


if __name__ == "__main__":
    main()
