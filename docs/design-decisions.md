# Design decisions

Why the current technical choices exist. System map: [Architecture](architecture.md). Method framing: [Methodology](methodology.md).

## PostgreSQL as source of truth, Chroma for vectors

Relational tables own articles, clusters, membership, and verified output (`common/models.py`, `common/db.py`). Chroma holds three semantic collections via `common/indexing.py`: chunked raw news, story descriptions, and verified articles. That split keeps transactional integrity and admin CRUD on Postgres while MCP/RAG queries stay vector-first without denormalizing full text into the search store.

## Chunked article index (`news_index_v2`)

Whole-article embeddings bury mid-piece claims. Articles are split with LlamaIndex `SentenceSplitter` (`CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`) into `news_index_v2` so retrieval returns the best matching span per article. Changing embed model or chunk settings invalidates vectors; rebuild with `python -m common.reindex`.

## Average-linkage clustering on cosine distance

Preprocess embeds same-day unprocessed articles and clusters them with average-linkage on cosine distance (`preprocessing/runner.py`). Average linkage is a stable default for news: less chain-prone than single linkage, less rigid than complete linkage, and cosine matches the embedding space used elsewhere. Clusters then get LLM descriptions (DeepInfra/Qwen) and land in `story_index`.

## LangGraph multi-agent audit vs a single prompt

Story audit is a graph of focused agents (`audit/agents/*`) rather than one megaprompt: extract claims, fact-check and rhetorical audit in parallel, then judge, analyze, and synthesize (`audit/story_audit.py`). Separation makes each step inspectable, budgetable (especially search), and easier to tune without rewriting the entire verification path.

## External search + trusted-domain filter for fact-check

The fact checker uses Serper (`FACT_CHECK_SEARCH_API_KEY` / `SERPER_API_KEY`) with `site:` scoping and post-filters against `FACT_CHECK_TRUSTED_DOMAINS` (e.g. `*.gob.do`, selected fact-checkers, major IOs). Caps (`FACT_CHECK_MAX_SEARCHES_PER_CLUSTER`, `FACT_CHECK_RESULTS_PER_QUERY`) and a short cache bound cost. Failures and empty trusted hits yield `insufficient evidence` — never an ungrounded contradiction.

## Separate API, MCP, and admin surfaces

- **API** (`api/`) — read-only published verified articles for the website.
- **MCP** (`mcp_app/`) — semantic search and story tools for external AI clients.
- **Admin** (`admin/`) — full SQLAdmin CRUD for editorial operations.

Splitting audiences avoids exposing admin power on the public API and keeps MCP free to join Chroma + Postgres without coupling to Next.js SSR.

## Cron cadence: frequent ingest, sparse audit

`deploy/crontab` (`TZ=America/Santo_Domingo`) runs ingest every 3 hours so the raw corpus stays fresh, while preprocess and story audit run every 3 days. Clustering and multi-agent audit are LLM- and search-heavy; batching them reduces cost and load while still producing verified articles on a predictable cycle.
