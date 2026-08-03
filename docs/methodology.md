# Methodology

How the Ojo Crítico pipeline is framed as a method: problem, units of analysis, procedure, outputs, and limits. System wiring lives in [Architecture](architecture.md); engineering rationale in [Design decisions](design-decisions.md).

## Problem

Dominican news events are covered by many outlets with overlapping facts, different framing, and uneven reliability. A single-source summary hides disagreement; an unreviewed LLM rewrite can invent facts. This project treats multi-outlet coverage as the unit of work: gather related articles, audit claims and rhetoric across them, then publish a synthesized verified article with explicit confidence signals.

## Pipeline as protocol

| Stage | Module | Role in the method |
|---|---|---|
| **Ingest** | `ingestion/ingestor.py` | Collect raw articles from configured outlets; quality-gate and deduplicate |
| **Cluster** | `preprocessing/runner.py` | Group same-day coverage into story clusters via embedding similarity |
| **Audit** | `audit/story_audit.py` | Multi-agent verification and synthesis over each cluster |
| **Publish** | `verified_articles` | Persist the product record for API, MCP, and admin review |

Scheduler cadence (America/Santo_Domingo): ingest every 3 hours; preprocess and story audit every 3 days. See [Architecture → Scheduler](architecture.md#scheduler).

## Units of analysis

- **Article** — one scraped piece in `raw_articles` (source, URL, headline, body, date).
- **Cluster / story** — a set of related articles (`clusters` + `topic_clusters`) representing one event/topic window.
- **Claim** — an extractable factual assertion from the cluster, produced for external checking.
- **Verified article** — the synthesized output (1:1 with `cluster_id`) with status, confidence, sources, and body.

## Audit procedure

For each eligible unprocessed cluster, a LangGraph graph runs specialized agents in order:

```text
claim_extractor → fact_checker ↘
rhetorical_auditor ─────────────→ judger → analyzer → synthesizer
```

1. **Claim extraction** — pull checkable claims from the cluster text.
2. **Fact check** — search trusted external sources for local/national/regional/international claims; budgeted search with trusted-domain filtering. Missing evidence yields `insufficient evidence`, not an ungrounded contradiction.
3. **Rhetorical audit** — assess framing, loaded language, and cross-outlet tone in parallel with fact-checking.
4. **Judge** — reconcile claim and rhetoric findings.
5. **Analyze** — score trustworthiness / source-level signals for the cluster.
6. **Synthesize** — write the verified article body and metadata for upsert.

Default batch mode prefers fresher, larger clusters (`STORY_AUDIT_MAX_AGE_DAYS`, `STORY_AUDIT_BATCH_SIZE`). Agents use DeepSeek via `audit.llm.get_llm`.

## Outputs and quality signals

- Rows in `verified_articles` (title, body, sources, status, confidence, slug, `cluster_id`).
- Semantic index in Chroma `verified_index` for MCP search.
- Editorial path through `admin/` for full-table review and correction.
- Public consumption via `api/` → Next.js website and MCP tools.

## Limitations

- **Clustering errors** — average-linkage can merge unrelated stories or split one event across clusters.
- **LLM risk** — extraction, judgment, and synthesis can hallucinate; fact-check is a guardrail, not a proof.
- **Evidence gaps** — search budget, missing API keys, and empty trusted results stop at `insufficient evidence`.
- **Latency** — preprocess and audit run every 3 days, so verified output lags behind raw ingest.
- **Coverage bias** — only configured Dominican outlets are ingested; absences are invisible to the cluster.

## Further reading

Topic keywords (not a bibliography): news story clustering / event detection; claim detection in journalism; automated fact-checking and evidence retrieval; multi-agent LLM pipelines; media framing and rhetorical analysis.
