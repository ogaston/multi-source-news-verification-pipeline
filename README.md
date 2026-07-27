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

Local stdio (dev):

```bash
mcp dev mcp_server.py
# or: MCP_TRANSPORT=stdio python mcp_server.py
```

Tool: `query_topic(topic, limit=5, days_back=7, source=None)`.

## Security (HTTP transports)

When `MCP_TRANSPORT` is `streamable-http` or `sse`, clients must send:

```http
Authorization: Bearer 5cfb757b93c423b4bd8fcc6c65a5139304978503d5a1be38
```

The token is intentionally hardcoded so the MCP endpoint stays free to use without a private key exchange. Override `MCP_API_KEY` in `.env` if you want a private deployment.

## Deploy (My personal VPS)

Two always-on containers share a volume: 
- **mcp** (HTTP MCP behind Traefik)
- **ingest-scheduler** (daily cron via supercronic at **06:00 America/Santo_Domingo**)

Prerequisites: Docker Compose, Traefik already running on the external `proxy` network.

```bash
# once, if missing
docker network create proxy

cp .env.example .env
# set MCP_DOMAIN and MCP_API_KEY (required for HTTP MCP)

docker compose up -d --build
```

- MCP URL: `http://${MCP_DOMAIN}/mcp` (streamable HTTP). Clients must send `Authorization: Bearer <MCP_API_KEY>`.
- Switch Traefik entrypoint to `websecure` in compose labels if you terminate TLS there.
- Manual one-shot ingest: `docker compose run --rm ingest-scheduler python ingestor.py`
- First image build is heavy (Playwright Chromium + embedding model bake-in).

## Reindex

After changing `EMBED_MODEL` in `config.py`:

```bash
python reindex.py
```
