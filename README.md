# News extraction pipeline

Scrapes Dominican news outlets into **SQLite + Chroma**, then exposes semantic search over MCP (`query_topic`).

**Sources:** 
    - Somos Pueblo
    - El Nuevo Diario
    - Listín Diario
    - Diario Libre
    - Hoy
    - Acento

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# crawl4ai / Playwright browser deps as needed for your OS
```

## Ingest

```bash
python ingestor.py                  # all sources, default --limit 5
python ingestor.py --source Acento --limit 10
python ingestor.py --write-json     # also dump debug JSON under data/
```

Incremental: URLs already in SQLite are skipped.

## MCP (RAG query)

```bash
mcp dev mcp.py
```

Tool: `query_topic(topic, limit=5, days_back=7, source=None)`.

## Reindex

After changing `EMBED_MODEL` in `config.py`:

```bash
python reindex.py
```