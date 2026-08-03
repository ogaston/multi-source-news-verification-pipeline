# Multi-Source News Verification Pipeline (Ojo Crítico)

Ingests Dominican news from multiple outlets, clusters related coverage, runs AI verification/synthesis, and publishes verified articles.

**Sources:** Somos Pueblo, El Nuevo Diario, Listín Diario, Diario Libre, Hoy, Acento, Remolacha, El Caribe, El Nacional, El Día.

**Layout:** `common/` (config, db, sources), `ingestion/`, `preprocessing/`, `audit/`, `mcp_app/`, `api/`, `admin/`, `website/`.

## Docs

- [Architecture](docs/architecture.md) — data flow, storage, surfaces, deploy
- [Methodology](docs/methodology.md) — problem framing and pipeline as method
- [Design decisions](docs/design-decisions.md) — why key technical choices exist

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# crawl4ai / Playwright browser deps as needed for your OS

cp .env.example .env
# set DEEPINFRA_API_KEY, DEEPSEEK_API_KEY, FACT_CHECK_SEARCH_API_KEY (or SERPER_API_KEY)
# for deploy also set MCP_*/ADMIN_*/API_*/WEBSITE_* domain and auth keys

docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

| Service | Local URL |
|---------|-----------|
| MCP | `http://localhost:7000/mcp` |
| Admin | `http://localhost:7001/admin` |
| API | `http://localhost:7002/api/articles` |
| Website | `http://localhost:7003` |
| Postgres | `localhost:5432` (`news`; pytest uses `news_test`) |

Production (VPS + Traefik): see [Architecture → Deploy](docs/architecture.md#deploy).

## Pipeline commands

```bash
python -m ingestion.ingestor
python -m preprocessing.runner
python -m audit.story_audit
python -m common.reindex
```

## Tests

DB-backed pytest needs `TEST_DATABASE_URL` pointing at `news_test` (never the app `news` DB — the fixture runs `drop_all`).

```bash
export TEST_DATABASE_URL=postgresql+psycopg://news:news@localhost:5432/news_test
pytest -q
```
