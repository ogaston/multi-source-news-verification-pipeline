# News extraction pipeline

Scrapes Dominican news outlets into **SQLite + Chroma +  LlamaIndex chunked index**, then exposes semantic search over MCP (`query_topic`).

**Sources:** 
- Somos Pueblo
- El Nuevo Diario
- Listín Diario
- Diario Libre
- Hoy
- Acento

**Layout:** `common/` (config, db, sources), `ingestion/` (scrape + quality gates), `mcp_app/` (MCP server), `preprocessing/` (data clustering).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# crawl4ai / Playwright browser deps as needed for your OS
```

## Ingest

```bash
python -m ingestion.ingestor                  # all sources, default --limit 5
python -m ingestion.ingestor --source Acento --limit 10
python -m ingestion.ingestor --write-json     # also dump debug JSON under data/
```

Incremental: URLs already in SQLite are skipped.

## MCP (RAG query)

Local stdio (dev):

```bash
mcp dev mcp_app/server.py
# or: MCP_TRANSPORT=stdio python -m mcp_app.server
```

Tool: `query_topic(topic, limit=5, days_back=7, source=None)`.

Returns the best matching **chunk** per article (plus source, date, headline, URL). Articles are split with LlamaIndex `SentenceSplitter` (`CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`) into Chroma collection `news_index_v2`.

## Security (HTTP transports)

When `MCP_TRANSPORT` is `streamable-http` or `sse`, clients must send:

```http
Authorization: Bearer 5cfb757b93c423b4bd8fcc6c65a5139304978503d5a1be38
```

The token is intentionally hardcoded so the MCP endpoint stays free to use without a private key exchange. Override `MCP_API_KEY` in `.env` if you want a private deployment.

## Deploy (My personal VPS)

Two always-on containers share a volume: 
- **mcp** (HTTP MCP behind Traefik)
- **scheduler** (supercronic: daily ingest at **06:00 America/Santo_Domingo**, preprocess/clustering every **15 minutes**)

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
- Manual one-shot ingest: `docker compose run --rm scheduler python -m ingestion.ingestor`
- Manual one-shot preprocess: `docker compose run --rm scheduler python -m preprocessing.runner`
- First image build is heavy (Playwright Chromium + embedding model bake-in).

## Reindex

Required after changing `EMBED_MODEL`, `CHUNK_SIZE` / `CHUNK_OVERLAP`, or upgrading to the chunked `news_index_v2` collection (old whole-article vectors are incompatible):

```bash
python -m common.reindex
```
