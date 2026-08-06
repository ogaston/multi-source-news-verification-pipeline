# Multi-Source News Verification Pipeline

Ingests news from multiple outlets, clusters related coverage, runs AI verification/synthesis, and publishes verified articles. 

> [!NOTE]
> For this project (**Ojo Crítico**), we are using the Dominican Republic as a case study but the pipeline is designed to be agnostic to the country. See [Case Study](docs/case-study.md) for more details.

## Docs

For more details, see the following docs:

- [Architecture](docs/architecture.md)
- [Methodology](docs/methodology.md)
- [Design decisions](docs/design-decisions.md)

**Layout:**
- `common/` (config, db, sources, utils)
- `ingestion/` (ingests news from multiple outlets)
- `preprocessing/` (preprocesses and clusters news)
- `audit/` (runs fact checks and verifies news)
- `mcp_app/` (MCP server)
- `api/` (API)
- `admin/` (admin UI)
- `website/` (website)

## Quickstart

To get started quickly using docker, follow these steps:


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


## Pipeline commands

These are the commands to run the pipeline locally.

```bash
python -m ingestion.ingestor
python -m preprocessing.runner
python -m audit.story_audit
python -m common.reindex
```

## Tests

We use pytest to run against the test database. To run the tests, we need to set the `TEST_DATABASE_URL` environment variable to point at the test database.

> ⚠️ Never the app `news` DB — the fixture runs `drop_all`).

```bash
export TEST_DATABASE_URL=postgresql+psycopg://news:news@localhost:5432/news_test
pytest -q
```
