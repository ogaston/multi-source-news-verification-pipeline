"""LangGraph story-audit workflow (DeepSeek-backed agents).

Default: batch-audit unprocessed clusters until none remain.
Optional: single cluster file via --story.

Usage:
  python -m agents.story_audit
  python -m agents.story_audit --batch-size 10
  python -m agents.story_audit --story path/to/cluster.txt
  python -m agents.story_audit --story path/to/cluster.txt --no-save
"""

from __future__ import annotations

import argparse
import os
import re
import traceback
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agents.analyzer import parse_analysis
from agents.analyzer import run as analyzer
from agents.claim_extractor import run as claim_extractor
from agents.fact_checker import run as fact_checker
from agents.judger import run as judger
from agents.rhetorical_auditor import run as rhetorical_auditor
from agents.state import StoryAuditState
from agents.synthesizer import run as synthesizer
from common.db import (
    fetch_cluster,
    fetch_cluster_articles,
    fetch_unprocessed_clusters,
    init_db,
    insert_verified_article,
    mark_cluster_processed,
)
from mcp_app.utils import format_story_detail

DEFAULT_STORY_PATH = Path(__file__).parent / "examples" / "luis_pie_cluster.txt"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_BATCH_SIZE = int(os.environ.get("STORY_AUDIT_BATCH_SIZE", "5"))

_STORY_ID_RE = re.compile(r"^STORY_ID:\s*(.+)$", re.MULTILINE)
_SOURCES_RE = re.compile(r"^SOURCES:\s*(.+)$", re.MULTILINE)

# Pipeline order for the written report (not parallel completion order).
REPORT_SECTIONS: tuple[tuple[str, str], ...] = (
    ("claim_extractor", "claims"),
    ("rhetorical_auditor", "rhetorical_audit"),
    ("fact_checker", "fact_check"),
    ("judger", "judgment"),
    ("analyzer", "analysis"),
    ("synthesizer", "article"),
)

# Map LangGraph node names to state fields for live terminal output.
NODE_FIELDS: dict[str, str] = dict(REPORT_SECTIONS)


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


def default_output_path(stem: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{stem}_audit.txt"


def _section_text(text: str | None) -> str:
    value = (text or "").strip()
    return value if value else "(empty response)"


def print_agent_response(agent: str, text: str | None) -> None:
    print(f"\n{'=' * 60}", flush=True)
    print(f"[{agent}]", flush=True)
    print("=" * 60, flush=True)
    print(_section_text(text), flush=True)


def format_audit_report(result: dict) -> str:
    lines: list[str] = []
    for agent, field in REPORT_SECTIONS:
        lines.append(f"[{agent}]\n{_section_text(result.get(field))}\n")
    return "\n".join(lines).rstrip() + "\n"


def write_audit_report(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_audit_report(result), encoding="utf-8")


def run_audit(app, story: str) -> dict:
    """Stream the graph and print each agent response as it completes."""
    result: dict = {"messages": [], "story": story}
    for event in app.stream({"messages": [], "story": story}, stream_mode="updates"):
        for node, update in event.items():
            result.update(update)
            field = NODE_FIELDS.get(node)
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


def split_article(article: str) -> tuple[str, str]:
    """Split synthesizer output into title (first non-empty line) and body."""
    lines = [line.strip() for line in (article or "").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ("(sin título)", "")
    title = lines[0].lstrip("#").strip() or "(sin título)"
    # Drop markdown bold markers often used in headlines.
    if title.startswith("**") and title.endswith("**") and len(title) > 4:
        title = title[2:-2].strip()
    body = "\n\n".join(lines[1:]).strip()
    return title, body


def article_sources(articles: list[dict]) -> str | None:
    sources = sorted(
        {
            (article.get("source") or "").strip()
            for article in articles
            if (article.get("source") or "").strip()
        }
    )
    return ", ".join(sources) if sources else None


def article_date(articles: list[dict]) -> str | None:
    dates = [
        (article.get("date") or "").strip()
        for article in articles
        if (article.get("date") or "").strip()
    ]
    return max(dates) if dates else None


def parse_story_id_from_text(story: str) -> str | None:
    match = _STORY_ID_RE.search(story)
    if not match:
        return None
    return match.group(1).strip() or None


def parse_sources_from_text(story: str) -> str | None:
    match = _SOURCES_RE.search(story)
    if not match:
        return None
    return match.group(1).strip() or None


def article_category(articles: list[dict]) -> str | None:
    for article in articles:
        category = (article.get("category") or "").strip()
        if category:
            return category
    return None


def persist_verified(
    *,
    cluster_id: str,
    result: dict,
    articles: list[dict] | None = None,
    sources: str | None = None,
) -> str:
    title, body = split_article(result.get("article") or "")
    if not body:
        body = title
    members = articles or []
    analysis = parse_analysis(result.get("analysis"))
    article_id = insert_verified_article(
        cluster_id=cluster_id,
        title=title,
        content=body,
        image_url=None,
        date=article_date(members),
        sources=sources if sources is not None else article_sources(members),
        category=article_category(members),
        status="published",
        confidence=analysis["confidence"],
        confidence_score=analysis["confidence_score"],
        source_scores=analysis["source_scores"],
        audit_json=analysis["audit_json"],
    )
    mark_cluster_processed(cluster_id)
    return article_id


def audit_cluster(app, cluster: dict, *, save: bool) -> None:
    cluster_id = cluster["cluster_id"]
    articles = fetch_cluster_articles(cluster_id)
    if not articles:
        print(f"[skip] {cluster_id}: no member articles", flush=True)
        return
    story = cluster_to_story_text(cluster, articles)
    print(f"\n>>> Auditing cluster {cluster_id} ({len(articles)} articles)", flush=True)
    result = run_audit(app, story)
    output_path = default_output_path(cluster_id)
    write_audit_report(output_path, result)
    print(f"Wrote audit report to {output_path}", flush=True)
    if save:
        article_id = persist_verified(
            cluster_id=cluster_id,
            result=result,
            articles=articles,
        )
        print(
            f"Saved verified_articles id={article_id} cluster_id={cluster_id}",
            flush=True,
        )


def run_batch(*, batch_size: int, save: bool) -> None:
    init_db()
    app = build_graph()
    total_ok = 0
    total_fail = 0
    while True:
        batch = fetch_unprocessed_clusters(batch_size)
        if not batch:
            break
        print(
            f"\n=== Batch: {len(batch)} unprocessed cluster(s) "
            f"(batch_size={batch_size}) ===",
            flush=True,
        )
        progress = False
        for cluster in batch:
            cluster_id = cluster["cluster_id"]
            try:
                audit_cluster(app, cluster, save=save)
                total_ok += 1
                progress = True
            except Exception as exc:
                total_fail += 1
                print(
                    f"[error] cluster {cluster_id} failed: {exc}",
                    flush=True,
                )
                traceback.print_exc()
        if not save:
            # Dry run does not mark processed; stop after one batch.
            break
        if not progress:
            print(
                "Stopping batch run: no clusters in this batch succeeded "
                "(will retry on next schedule).",
                flush=True,
            )
            break
    print(
        f"\nBatch complete: {total_ok} succeeded, {total_fail} failed.",
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

    output_path = output or default_output_path(story_path.stem)
    write_audit_report(output_path, result)
    print(f"\nWrote audit report to {output_path}", flush=True)

    if not save:
        return

    init_db()
    resolved_id = cluster_id or parse_story_id_from_text(story)
    if not resolved_id:
        raise SystemExit(
            "Cannot save: pass --cluster-id or include STORY_ID: in the story file"
        )
    # Ensure cluster row exists so processed can be set (example files may not
    # be in DB yet).
    if fetch_cluster(resolved_id) is None:
        from datetime import datetime

        from common.db import insert_clusters

        insert_clusters(
            [(resolved_id, "Example / file-based audit", datetime.now().isoformat())]
        )

    article_id = persist_verified(
        cluster_id=resolved_id,
        result=result,
        articles=[],
        sources=parse_sources_from_text(story),
    )
    print(
        f"Saved verified_articles id={article_id} cluster_id={resolved_id}",
        flush=True,
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
        "(default: agents/output/<stem>_audit.txt)",
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
