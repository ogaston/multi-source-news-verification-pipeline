# News extraction pipeline

Scrapes Dominican news outlets into **SQLite + Chroma**, then exposes semantic search over MCP (`query_topic`).

**Sources:** Somos Pueblo, El Nuevo Diario, Listín Diario, Diario Libre, Hoy, Acento.

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

## Deploy

Daily cron on a small VPS (Docker):

- [DigitalOcean](deploy/digitalocean.md) (recommended)
- [Oracle Always Free](deploy/oracle-cloud.md)

```bash
docker compose build
docker compose run --rm ingest python ingestor.py --limit 2
```

Data lives in the `pipeline-data` volume (`DB_NAME` / `CHROMA_PATH` under `/data`).

## Layout

| Path | Role |
|------|------|
| `ingestor.py` | Discover + scrape + save |
| `pipeline.py` | Date normalize + quality gates |
| `db.py` | SQLite + Chroma upsert |
| `mcp.py` | MCP server |
| `providers/` | Per-outlet scrapers |
| `config.py` | Paths, limits, embed model (env-overridable) |
