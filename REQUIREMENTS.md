# News Extraction Pipeline — Requirements & Gap Analysis

This document captures the current state of the project, known inconsistencies, and the work required to reach a complete, production-ready system. It is derived from a full review of the repository as of July 2026.

---

## 1. Executive summary

The pipeline **works end-to-end in development** for scraping → clustering → story audit → MCP search, but several major pieces are **disconnected or incomplete**:

| Area | Current state | Target state |
|------|---------------|--------------|
| Database | Single SQLite file, raw `sqlite3` + SQLAlchemy dual access | PostgreSQL (recommended), unified data layer |
| Public website | Mock articles in TypeScript | Live data + **SEO** + **mobile-first** UX |
| Story audit graph | 5 agents; judger output is free text only; fact checker is LLM-only | 6 agents; **Analyzer** scores; fact checker uses **domain-filtered web search** |
| MCP | Raw/cluster stories only | Includes **verified (synthesized) articles** and scores |
| Documentation | Single README | Per-component docs + architecture reference |
| Tests | MCP, clustering, indexing | Agents, DB layer, website API, migration |
| Security | MCP bearer token + admin login only | Secrets hygiene, TLS, rate limits, API hardening |
| Observability | Print logs + basic Docker healthchecks | Structured logs, metrics, job tracing, alerts |
| Prompt quality | Ad-hoc manual runs | **DeepEval** + pytest: golden evals, schema validation, CI gates |

---

## 2. System architecture (as-is)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         pipeline-data volume                            │
│  dominican_news_repository.db (SQLite)  +  chroma_db/ (vectors)       │
└─────────────────────────────────────────────────────────────────────────┘
         ▲              ▲              ▲              ▲
         │              │              │              │
   ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
   │ scheduler │  │    mcp    │  │   admin   │  │  website  │
   │ (cron)    │  │  (HTTP)   │  │ (SQLAdmin)│  │ (Next.js) │
   └─────┬─────┘  └───────────┘  └───────────┘  └───────────┘
         │
    ingestor ──► preprocessing ──► story_audit (LangGraph)
    (6 sources)    (cluster+describe)   (5 agents → verified_articles)
```

### Components

| Path | Role | Entry point |
|------|------|-------------|
| `common/` | Config, SQLite CRUD, Chroma indexing, reindex | `common/db.py`, `common/indexing.py` |
| `ingestion/` | Crawl4AI scrapers for 6 Dominican outlets | `python -m ingestion.ingestor` |
| `preprocessing/` | Embedding AHC clustering + Groq descriptions | `python -m preprocessing.runner` |
| `agents/` | LangGraph story-audit workflow (DeepSeek) | `python -m agents.story_audit` |
| `mcp_app/` | MCP server: search/list/get stories & articles | `python -m mcp_app.server` |
| `admin/` | SQLAdmin UI over SQLite tables | `uvicorn admin.app:app` |
| `website/` | Next.js front page (“Ojo Crítico”) | **mock data only** |
| `deploy/` | Supercronic schedule (ingest 4×/day, preprocess + audit every 15 min) | `deploy/crontab` |

### Data model (SQLite)

| Table | Purpose |
|-------|---------|
| `raw_articles` | Scraped articles; `processed` flag for clustering |
| `topic_clusters` | Many-to-many: cluster ↔ article |
| `clusters` | Cluster metadata + Groq description; `processed` flag for audit |
| `verified_articles` | Synthesized article per cluster; `status` always `draft` |

**Chroma collections:** `news_index_v2` (article chunks), `story_index` (cluster descriptions).

---

## 3. Inconsistencies & missing pieces

### 3.1 Database layer

- **SQLite everywhere** — `common/db.py` uses raw `sqlite3`; `admin/app.py` uses SQLAlchemy against the same file; `mcp_app/utils.py` opens a separate read-only SQLite connection. Three access patterns, no connection pooling, no transaction coordination.
- **Concurrency risk** — Scheduler runs preprocess and story-audit every 15 minutes against the same SQLite file while MCP and admin may read/write concurrently. SQLite is a poor fit for multi-container writes.
- **Ad-hoc migrations only** — Schema changes live in `init_db()` as inline `PRAGMA` / `ALTER TABLE` helpers. No Alembic (or equivalent), no version tracking, no rollback.
- **Dual ORM vs raw SQL** — Admin models in `admin/models.py` mirror `common/db.py` DDL but can drift (e.g. new columns added in one place only).
- **`verified_articles` schema is incomplete for the product** — Missing: `slug`, `confidence`, per-source scores, audit trail (claims, judgment, analyzer output), `published_at`, structured `sources` JSON.

### 3.2 Website vs backend

- **`website/lib/articles.ts` is entirely mock data** — Hardcoded Spanish articles with fake confidence levels. Comment in `docker-compose.yml`: *“static-rendered, mock data for now”*.
- **`website/lib/api.ts` is a no-op wrapper** — Re-exports mock data; no HTTP call to admin, MCP, or a future REST API.
- **Confidence UI exists without backend support** — `ConfidenceBadge` expects `alta | media | baja | en_revision`; nothing in the pipeline produces or stores these values.
- **No publish workflow** — `insert_verified_article(..., status="draft")` always writes `draft`; website has no concept of draft vs published.
- **`docker-compose.local.yml` omits the website service** — Local dev stack is MCP + scheduler + admin only.
- **Slug mismatch** — Website uses slugs like `reforma-presupuesto`; DB uses `cluster_id` hashes. No mapping layer.

**SEO gaps (Next.js `website/`):**

| Gap | Detail |
|-----|--------|
| No `sitemap.xml` / `robots.txt` | Crawlers cannot discover article URLs systematically |
| Minimal per-page metadata | Article pages have title + description only; no Open Graph, Twitter cards, or canonical URLs |
| No structured data | Missing `NewsArticle` / `Organization` JSON-LD for rich results |
| `generator: 'v0.app'` in root metadata | Noise in HTML; should be removed |
| Images `unoptimized: true` | No responsive `srcset`, hurts LCP and mobile bandwidth |
| No `generateStaticParams` / ISR | Article routes not pre-rendered for crawlers once live API exists |
| Section nav uses `href="#"` | Dead links; no category landing pages for SEO silos |
| No hreflang (if ever multi-locale) | Spanish-only is fine; document `lang="es"` as intentional |

**Mobile & accessibility gaps:**

| Gap | Detail |
|-----|--------|
| Partial responsive layout | Header has mobile menu (`md:hidden` / `md:block`) but not audited end-to-end |
| Viewport incomplete | `viewport` export lacks explicit `width=device-width, initial-scale=1` |
| Touch targets / tap spacing | Not verified against 44×44px minimum on donate, nav, article links |
| No Lighthouse / Core Web Vitals gate | No CI budget for mobile performance or accessibility score |
| `ignoreBuildErrors: true` | Type errors can ship; risky for production quality |
| Client-heavy header | `SiteHeader` is `'use client'`; acceptable but limits static SEO shell optimization |

### 3.3 Agent pipeline

Current graph (`agents/story_audit.py`):

```
START ──► claim_extractor ──► fact_checker ──► judger (defer) ──► synthesizer ──► END
START ──► rhetorical_auditor ──────────────────► judger
```

**Missing: Analyzer node** between `judger` and `synthesizer`.

| Gap | Detail |
|-----|--------|
| No quantitative output | Judger returns prose buckets (`absolutely_false`, `not_verifiable`, `narrative_to_keep`); no numeric scores |
| No source reliability | Outlets are listed as comma-separated strings; no per-source weight or track record |
| No confidence enum | Website expects 4 levels; pipeline never sets them |
| Intermediate outputs not persisted | Audit reports go to `agents/output/<cluster_id>_audit.txt` only; not queryable |
| Fact checker has no tools | `fact_checker.py` relies on LLM parametric knowledge; no domain-filtered search API |
| State schema minimal | `StoryAuditState` has no fields for scores, structured judgment, or analyzer output |

### 3.4 MCP server

**Exposed today:** `search_articles`, `search_story`, `list_stories`, `get_story`, resources `news://sources`, `news://{source_id}/frontpage`, prompt `get_last_week`.

**Not exposed:**

- Verified / synthesized articles (`verified_articles` table)
- Confidence or source-quality scores
- Audit metadata (claims, fact-check, judgment)
- `fetch_verified_article()` exists in `common/db.py` but is **unused** outside that module

Clients cannot discover or consume the final “Ojo Crítico” product through MCP.

### 3.5 Operations & configuration

- **README embeds a default MCP API key** — Documented as intentional but risky for copy-paste deployments.
- **`.env.example` lacks DB URL** — No placeholder for PostgreSQL or future connection string.
- **Scheduler depends on API keys via `env_file` only** — `GROQ_API_KEY`, `DEEPSEEK_API_KEY` not validated at container start; silent failures in cron jobs.
- **No health check on scheduler** — Failed ingest/audit runs are only visible in logs.
- **Reindex is manual** — Documented but not wired into deploy on embedding config changes.

### 3.6 Tests & quality

Existing tests cover MCP tools, auth, clustering, indexing, describe (mocked Groq). **No tests for:**

- `agents/story_audit` graph or individual agents
- `common/db.py` migrations and CRUD
- `ingestion.ingestor` integration
- Website data layer (once real API exists)
- Database migration scripts

### 3.7 Security & secrets

**What exists today:**

- MCP HTTP transports: single shared Bearer token (`MCP_API_KEY`) via `StaticTokenVerifier` in `mcp_app/auth.py` — constant-time compare, scoped `news:read`.
- Admin: username/password session auth via SQLAdmin (`admin/auth.py`); `ADMIN_SECRET_KEY` for session signing.
- Traefik terminates routing; compose labels use `web` entrypoint (TLS optional, not enforced in repo).

**Gaps:**

| Gap | Risk |
|-----|------|
| Default MCP API key in README and `docker-compose.yml` | Credential leak on public deployments |
| No rate limiting on MCP or future public API | Abuse, cost spikes, DoS |
| Admin has no CSRF hardening beyond SQLAdmin defaults | Session fixation / CSRF if exposed broadly |
| Website will be public with no auth plan documented | Accidental exposure of draft articles via API |
| Secrets only in `.env`; no rotation or validation at startup | Silent misconfiguration (empty `DEEPSEEK_API_KEY`) |
| No security headers (CSP, HSTS) on MCP landing or website | Baseline web hardening missing |
| PostgreSQL credentials not yet modeled | Future risk of default passwords in compose |
| LLM prompts include full article text; no PII/redaction policy | Data handling unclear for logs and eval artifacts |
| No audit log for admin publish/edit actions | No accountability for content changes |
| Scheduler/MCP/admin share one DB volume | Lateral movement if one service compromised |

### 3.8 Observability & operability

**What exists today:**

- `print()` / `traceback` in agents and ingest; `logging` only in `preprocessing/describe.py`.
- Docker healthchecks: TCP socket open on MCP, admin, website — not application-level.
- Cron via supercronic; failures visible only in container stdout.
- DeepSeek retries logged to stdout in `agents/llm.py`.

**Gaps:**

| Gap | Impact |
|-----|--------|
| No structured JSON logging | Hard to search/aggregate in production |
| No metrics (Prometheus/OpenTelemetry) | Cannot dashboard ingest lag, audit throughput, LLM latency |
| No distributed trace IDs across graph nodes | Cannot debug slow/failed cluster audits end-to-end |
| No alerting on cron failure | Missed ingest or audit runs |
| No SLOs defined | No objective “healthy pipeline” signal |
| LLM token/cost usage not tracked | Budget surprises from Groq/DeepSeek |
| Chroma/SQLite disk usage not monitored | Volume fill silently breaks pipeline |
| No `/health` or `/ready` semantics beyond socket checks | False-positive “healthy” containers |

### 3.9 Prompt validation & harness engineering (DeepEval)

**Decision:** Use **[DeepEval](https://github.com/confident-ai/deepeval)** as the eval harness (pytest-native, CI-friendly). Domain-specific metrics live in custom `BaseMetric` subclasses; do not build a bespoke `run_eval.py` CLI.

**What exists today:**

- Agent prompts live inline in each module (`claim_extractor.py`, `judger.py`, etc.).
- One example cluster file: `agents/examples/luis_pie_cluster.txt`.
- `agents/story_audit --no-save` for dry runs; audit output as plain text files.
- Unit tests mock Groq for cluster descriptions; **no DeepEval suite for story-audit agents**.
- Analyzer (planned) will need structured JSON — no schema validation layer yet.

**Gaps:**

| Gap | Impact |
|-----|--------|
| No golden dataset of clusters + expected outputs | Prompt edits can regress quality silently |
| No automated eval CI job | Bad prompt deploys reach production scheduler |
| Judger/analyzer outputs are free text | Downstream synthesizer fragile; hard to assert correctness |
| No prompt versioning | Cannot A/B or roll back prompt changes |
| No output validators (length, language, forbidden patterns) | Synthesizer can drift off-topic (known issue in prompts) |
| No regression metrics (claim recall, confidence calibration) | Eval loop not closed |
| Fact-checker search not grounded against fixtures | Cannot verify domain-filtered search without VCR cassettes |

### 3.10 Likely removable / consolidatable code (verify before delete)

| Item | Verdict |
|------|---------|
| `website/lib/articles.ts` mock articles | **Remove after** website reads from API/DB |
| `mcp_app/utils.py` → `query_db()` duplicate SQLite access | **Consolidate** into `common/db` read-only helpers |
| `agents/output/` audit text files | **Keep optional** for debugging; add `.gitignore` entry if not already |
| `agents/requirements.txt` | **Merge** into root `requirements.txt` or document why separate (Docker uses root only) |
| `fetch_verified_article()` | **Keep** — wire into MCP + website, not dead code |
| `website/lib/api.ts` passthrough | **Replace** with real fetch client, not delete prematurely |

---

## 4. Requirements

### REQ-DB-001 — Replace SQLite with PostgreSQL

**Recommendation:** PostgreSQL over MySQL or MongoDB.

- Relational schema already fits (articles, clusters, memberships, verified articles).
- SQLAlchemy is already used in admin; extend to the whole stack.
- JSONB columns suit analyzer scores and structured audit payloads.
- Better concurrent access for scheduler + MCP + admin + future website API.

**Tasks:**

1. Add `DATABASE_URL` to `common/config.py` and `.env.example` (e.g. `postgresql+psycopg://user:pass@postgres:5432/news`).
2. Introduce SQLAlchemy models in `common/` (or shared `models/`) as single source of truth; admin imports from there.
3. Add Alembic for migrations; initial migration reproduces current SQLite schema.
4. Add `postgres` service to `docker-compose.yml` / `docker-compose.local.yml` with persistent volume.
5. Replace all `sqlite3.connect()` calls in `common/db.py` and `mcp_app/utils.py`.
6. Update SQLAdmin engine in `admin/app.py` to use `DATABASE_URL`.
7. Remove SQLite-specific logic (`PRAGMA`, `INSERT OR IGNORE` → `ON CONFLICT`, URI read-only mode).

**Acceptance:** All existing CLI commands and cron jobs run against PostgreSQL with no SQLite file on the volume.

---

### REQ-DB-002 — Migrate existing data

**Tasks:**

1. Write `scripts/migrate_sqlite_to_postgres.py`:
   - Read from `dominican_news_repository.db` (configurable path).
   - Insert in dependency order: `raw_articles` → `clusters` → `topic_clusters` → `verified_articles`.
   - Preserve primary keys (`id`, `cluster_id`, `article_key` uniqueness).
   - Log row counts and conflicts; support dry-run.
2. Document Chroma handling: vectors are keyed by article/cluster IDs — **IDs must stay stable** during SQL migration (they will if PKs are copied verbatim).
3. Provide rollback note: keep SQLite backup until PostgreSQL is validated in production.
4. Add one-shot Compose task: `docker compose run --rm scheduler python -m scripts.migrate_sqlite_to_postgres`.

**Acceptance:** Row counts match between SQLite source and PostgreSQL target; MCP search and admin UI show the same data.

---

### REQ-AGENT-001 — Add Analyzer agent node

Insert **Analyzer** after `judger`, before `synthesizer`.

**Responsibilities:**

1. Consume: original story cluster, claims, fact-check, rhetorical audit, **judgment**.
2. Produce structured quantitative output, e.g.:

```json
{
  "overall_confidence": "alta | media | baja | en_revision",
  "confidence_score": 0.0,
  "source_scores": [
    { "source": "Listín Diario", "reliability": 0.85, "corroboration": 0.7 }
  ],
  "metrics": {
    "claims_total": 12,
    "claims_supported": 8,
    "claims_contradicted": 1,
    "claims_unverifiable": 3,
    "rhetoric_risk": 0.2
  },
  "rationale": "Brief Spanish summary for editors"
}
```

3. Extend `StoryAuditState` with `analysis: str` (or typed dict serialized to JSON).
4. Persist analyzer output:
   - New table `audit_results` (`cluster_id`, JSON payload, `created_at`), **or**
   - Columns on `verified_articles`: `confidence`, `confidence_score`, `source_scores` (JSONB), `audit_json` (JSONB).
5. Pass analyzer summary into `synthesizer` prompt (optional: only pass judgment + narrative_to_keep as today).
6. Map `overall_confidence` to website `ConfidenceLevel` enum.

**Graph (target):**

```
judger ──► analyzer ──► synthesizer
```

**Acceptance:** Batch audit writes confidence fields; website badge can be driven from DB; analyzer output appears in audit report file.

---

### REQ-AGENT-002 — Fact checker with domain-filtered search

The fact checker **must not** rely on LLM parametric knowledge alone for world-fact claims. It must call a **cheap web search API** that supports **filtering by specific domains** (native `include_domains` / `site:` scoping — not unconstrained open web search).

**Why domain filtering**

- Reduces hallucinated “contradictions” from random blogs.
- Keeps verification grounded in official and high-trust sources (government, courts, international bodies, primary data).
- Lowers cost vs full-web search by narrowing result sets.

**Recommended providers** (pick one; all support domain scoping and have low-cost tiers):

| Provider | Domain filter mechanism | Notes |
|----------|-------------------------|-------|
| **Tavily** | `include_domains` parameter | Simple API; good for agents; pay-per-search |
| **Serper** (Google) | `site:domain.com` in query | Very cheap; high recall for Spanish/Latin America |
| **Brave Search API** | `site:` operator or Goggles | Competitive pricing |
| **Exa** | `includeDomains` | Neural search; slightly pricier |

**Not sufficient alone:** MCP `search_articles` (internal corpus only) — use as **supplement** for corroboration within scraped outlets, not replacement for external official sources.

**Implementation**

1. Add `agents/search.py` (or `common/search.py`):
   - `search_domains(query: str, domains: list[str], *, limit: int) -> list[SearchResult]`
   - Normalize snippets + URLs for LLM context.
2. Configure via env (`.env.example`):
   - `FACT_CHECK_SEARCH_PROVIDER` — e.g. `tavily`, `serper`, `brave`
   - `FACT_CHECK_SEARCH_API_KEY`
   - `FACT_CHECK_TRUSTED_DOMAINS` — comma-separated allowlist, e.g. `presidencia.gob.do,contraloria.gob.do,one.gob.do,datos.gob.do,who.int,un.org,reuters.com,apnews.com`
   - `FACT_CHECK_MAX_SEARCHES_PER_CLUSTER` — default `10` (cost cap)
   - `FACT_CHECK_RESULTS_PER_QUERY` — default `3`
3. Refactor `fact_checker.py` into tool-using agent (LangChain tool or explicit pre-search step):
   - For each **world-fact** claim (not reported-speech), build query + select domain subset.
   - Call search API with domain filter; attach snippets to LLM prompt.
   - LLM synthesizes verdict from search evidence + cluster text.
4. Domain selection strategy:
   - **Official DR gov** domains for policy/legal/statistics claims.
   - **International orgs** for health, climate, sports sanction bodies as relevant.
   - **Outlet domains** from cluster (`diariolibre.com`, etc.) only for cross-outlet corroboration via `site:` — separate from gov allowlist.
5. Log every search: query, domains, result count, latency, provider (for cost/observability metrics).
6. Handle failures gracefully: API error → verdict `insufficient evidence`, never `contradicted`.
7. Add VCR cassettes under `tests/evals/cassettes/` so CI does not hit live search API on every run.

**Prompt update**

- Instruct fact checker to cite **URL + domain** for each external verification.
- Reinforce: reported speech in cluster → `supported as reported`; external search only for world facts.

**Cost controls**

- Batch claims where possible (one query per topic, not per atomic claim).
- Cache search results by `(query, domains)` hash for 24h within a cluster audit run.
- Enforce `FACT_CHECK_MAX_SEARCHES_PER_CLUSTER`; overflow claims → `insufficient evidence`.

**Acceptance:** Running audit on a cluster with a verifiable gov statistic triggers domain-scoped search calls; fact-check output cites filtered URLs; DeepEval + VCR tests pass; monthly search spend predictable via configured caps.

---

### REQ-MCP-001 — Expose verified articles in MCP

**New tools (minimum):**

| Tool | Description |
|------|-------------|
| `list_verified_articles` | Recent synthesized articles (`status`, `confidence`, title, date, cluster_id/slug) |
| `get_verified_article` | Full body + sources + confidence + optional audit summary |
| `search_verified_articles` | Semantic search over verified content (new Chroma collection or reuse story index) |

**Optional resources:**

- `news://verified/{cluster_id}` — JSON or markdown document

**Tasks:**

1. Implement tool handlers in `mcp_app/tools.py`; register in `mcp_app/server.py`.
2. Add DB helpers: `fetch_verified_articles(...)`, list by date/status/confidence.
3. Update README MCP section and `mcp_app/static/index.html` landing page.
4. Add tests in `tests/test_tools.py`.

**Acceptance:** MCP client can list and retrieve verified articles with confidence metadata without reading raw clusters.

---

### REQ-WEB-001 — Connect website to backend

**Tasks:**

1. Add public read API (FastAPI route on admin app or separate `api/` service):
   - `GET /api/articles` — published verified articles for homepage
   - `GET /api/articles/{slug}` — single article with sources and confidence
2. Add `slug` to `verified_articles` (generated from title + cluster_id hash).
3. Replace `website/lib/articles.ts` mock exports with fetch to API (`WEBSITE_API_URL` env).
4. Map DB `confidence` → `ConfidenceLevel`; map `sources` JSON → `ArticleSource[]`.
5. Add `status = 'published'` workflow (manual in admin or auto when confidence ≥ threshold).
6. Include website in `docker-compose.local.yml`; wire Traefik host in production compose.

**Acceptance:** Homepage and article pages render live verified content; confidence badge reflects analyzer output.

---

### REQ-WEB-002 — SEO and mobile-friendly website

Make **Ojo Crítico** discoverable by search engines and usable on phones/tablets. Target: **Lighthouse mobile ≥ 90** (Performance, SEO, Accessibility) on homepage and a representative article page.

**SEO — technical**

1. **`metadataBase`** in root layout from `WEBSITE_URL` env (canonical origin for all pages).
2. **Per-route metadata** (homepage + `/articulo/[slug]`):
   - `title`, `description` (unique, ≤ 160 chars)
   - `openGraph`: title, description, `type: article`, `locale: es_DO`, image, `publishedTime`, `authors`
   - `twitter`: `summary_large_image`
   - `alternates.canonical` per slug
3. **`app/sitemap.ts`** — dynamic sitemap of published articles + static routes; ping on publish (optional).
4. **`app/robots.ts`** — allow `/`, disallow `/api/` and admin paths; link sitemap URL.
5. **JSON-LD** on article pages (`NewsArticle` + `Organization` publisher); optional `BreadcrumbList`.
6. **Semantic HTML** — one `<h1>` per page, `<article>`, `<time datetime>`, proper heading hierarchy in `ArticleDetail`.
7. Remove `generator: 'v0.app'` and other non-brand metadata noise.
8. **`generateStaticParams`** + ISR/revalidate for article slugs from API (SSG/ISR so crawlers get full HTML without JS).
9. Category/section landing pages (replace `href="#"` nav) — e.g. `/seccion/politica` with indexable headlines list.

**SEO — content**

10. Human-readable slugs from verified article titles (Spanish, ASCII-folded).
11. Meta descriptions from article summary or first paragraph (not duplicated titles).
12. `rel="noopener noreferrer"` on external source links; descriptive link text where possible.

**Images & performance (mobile LCP)**

13. Enable Next.js **Image** optimization (`images.unoptimized: false`); configure remote patterns if images are external.
14. Responsive images with `sizes` for lead/hero and article body figures.
15. Font strategy: keep `display: 'swap'` (already set); preload critical fonts only.
16. Fix `typescript.ignoreBuildErrors: true` before production launch.

**Mobile UX**

17. Explicit viewport: `width=device-width, initial-scale=1, viewport-fit=cover`.
18. Audit all pages at **320px, 375px, 768px** breakpoints — no horizontal scroll, readable body text (16px+ base), adequate line length.
19. Touch targets ≥ **44×44px** for menu, donate, footer links, source chips.
20. Mobile nav: focus trap, `aria-expanded`, close on route change, keyboard accessible.
21. Sticky/fixed elements must not obscure article text or CTAs on small screens.
22. Test donate dialog and article source list on mobile.

**Verification**

23. Add **Lighthouse CI** (or manual checklist in CI) on PRs touching `website/`:
    - Mobile performance, SEO, accessibility thresholds documented in `docs/website.md`
24. Optional: Google Search Console setup documented in ops runbook (`WEBSITE_URL` verification).

**Acceptance:** Valid sitemap and robots; article pages pass Rich Results Test (NewsArticle); Lighthouse mobile SEO ≥ 90; no horizontal overflow on 375px viewport; Core Web Vitals in “good” range on 4G throttling.

---

### REQ-CLEAN-001 — Remove unnecessary code

After REQ-WEB-001 and REQ-DB-001:

1. Delete mock article definitions from `website/lib/articles.ts` (keep types only).
2. Remove duplicate SQLite helper in `mcp_app/utils.py`; use `common/db` read-only functions.
3. Collapse `agents/requirements.txt` into root if Docker never installs it separately.
4. Audit `common/db.py` for unused exports (`fetch_all_news` is used by reindex — keep).
5. Run test suite; remove any dead imports flagged by linters.

**Do not remove without replacement:** audit text output, example cluster file, reindex module.

---

### REQ-DOC-001 — Document project and each component

Create and maintain:

| Document | Contents |
|----------|----------|
| `README.md` (update) | High-level diagram, quick start, link to component docs |
| `docs/architecture.md` | Data flow, containers, schedules, external APIs (Groq, DeepSeek) |
| `docs/ingestion.md` | Providers, quality gates, dedup keys, adding a source |
| `docs/preprocessing.md` | Clustering params, Groq descriptions, Chroma story index |
| `docs/agents.md` | Graph diagram, agent prompts, analyzer schema, fact-check search config, env vars |
| `docs/mcp.md` | All tools/resources, auth, example client calls |
| `docs/database.md` | ER diagram, migrations, backup/restore |
| `docs/website.md` | API contract, SEO checklist, mobile/Lighthouse targets, env vars, deploy |
| `docs/operations.md` | Cron schedule, monitoring, reindex, migration runbook |
| `docs/security.md` | Secrets, TLS, rate limits, auth matrix, rotation |
| `docs/observability.md` | Logs, metrics, dashboards, alerts, trace IDs |
| `docs/harness.md` | DeepEval setup, datasets, custom metrics, CI, prompt versioning |

Each component README snippet at top of major packages is optional if `docs/` is complete.

**Acceptance:** New developer can run full stack locally and understand where to change scrape vs audit vs publish behavior.

---

### REQ-SEC-001 — Basic security baseline

Establish a practical security layer suitable for a VPS deployment (not enterprise SOC2, but production-safe defaults).

**Secrets & configuration**

1. Remove hardcoded MCP API key from README; document generation via `openssl rand -hex 24`.
2. Add startup validation (`common/startup.py` or entrypoint): fail fast if required secrets missing in production (`MCP_API_KEY`, `ADMIN_*`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`).
3. Never log secrets, full Bearer tokens, or admin passwords; redact in structured logs.
4. Document secret rotation in `docs/operations.md`.

**Transport & network**

5. Document Traefik `websecure` + TLS (Let's Encrypt) as the production default; keep `web` for local only.
6. Restrict admin and PostgreSQL ports to internal Docker network — not published on host in production compose.
7. Public website API: read-only endpoints only; drafts excluded unless authenticated.

**Authentication & authorization**

8. Keep MCP Bearer token for HTTP transports; require `MCP_API_KEY` in production (no anonymous HTTP).
9. Admin: strong password policy documented; optional IP allowlist at Traefik middleware.
10. Future publish API: separate admin-only write scope (session or API key), distinct from public read.
11. Add admin audit log table: `who`, `action`, `entity`, `timestamp` for publish/unpublish/edit.

**Input validation & abuse prevention**

12. MCP tools already cap `limit`, `days_back`, query length — extend validation to new verified-article tools.
13. Add rate limiting on MCP HTTP and public website API (e.g. Traefik middleware or SlowAPI): configurable per IP.
14. Sanitize/validate `story_id`, `slug`, and cluster IDs (length, charset) on all entry points.

**Web hardening**

15. Security headers on MCP landing, admin, website: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; HSTS when TLS enabled.
16. CORS: explicit allowlist for website → API origin only.

**Acceptance:** Production checklist passes; default compose does not expose DB; no secrets in git; rate limit returns 429 under abuse test.

---

### REQ-OBS-001 — Observability & operability

Make pipeline behavior visible without SSH-ing into containers for every incident.

**Structured logging**

1. Introduce `common/logging.py`: JSON logs in production (`LOG_FORMAT=json`), human-readable in local dev.
2. Standard fields: `timestamp`, `level`, `service`, `trace_id`, `cluster_id`, `job`, `duration_ms`, `error`.
3. Replace bare `print()` in ingest, preprocess, and agents with logger calls (keep user-facing audit prints optional via `VERBOSE=1`).

**Health & readiness**

4. Add HTTP endpoints:
   - MCP: `GET /health` (process up), `GET /ready` (DB + Chroma reachable).
   - Admin/API: same pattern.
   - Scheduler: lightweight sidecar or periodic self-check script writing heartbeat file/metric.
5. Upgrade Docker healthchecks to hit `/ready`, not just TCP.

**Metrics**

6. Expose Prometheus metrics (or OpenTelemetry → Prometheus/Grafana Cloud):
   - `ingest_articles_total`, `ingest_errors_total`
   - `clusters_processed_total`, `audits_completed_total`, `audits_failed_total`
   - `llm_requests_total`, `llm_latency_seconds`, `llm_tokens_total` (by provider/model)
   - `mcp_tool_calls_total`, `mcp_tool_latency_seconds`
   - `db_pool_in_use`, `chroma_collection_size` (gauge, periodic)
7. Optional: Grafana dashboard JSON in `deploy/grafana/`.

**Tracing**

8. Propagate `trace_id` (UUID) through LangGraph run: set at `story_audit` batch start, attach to every agent log line.
9. Optional OpenTelemetry spans per agent node for latency breakdown.

**Alerting & runbooks**

10. Define alert rules (even if manual at first):
    - No successful ingest in 8h
    - Audit failure rate > 20% over 1h
    - Disk usage on `pipeline-data` > 85%
11. Document response steps in `docs/operations.md`.

**Cron visibility**

12. Wrap supercronic jobs with exit-code logging; non-zero exit increments `job_failures_total{job="ingestor"}`.
13. Optional: post summary to webhook (Slack/Discord/email) on batch complete or failure.

**Acceptance:** Operator can answer “did last night’s audit run?” and “why is cluster X stuck?” from logs/metrics alone.

---

### REQ-HARNESS-001 — Prompt validation with DeepEval

Implement **harness engineering** using **[DeepEval](https://deepeval.com/docs/introduction)** — pytest-style LLM evals with CI gates. Treat agent prompts like code: versioned fixtures, custom metrics, and `deepeval test run` before merge.

**Dependencies**

- Add `deepeval` to root `requirements.txt` (and dev/CI).
- Optional: [Confident AI](https://www.confident-ai.com/) cloud for dataset sync and eval history (not required for local/CI).

**Layout**

```
tests/evals/
  datasets/
    clusters/              # golden inputs (.txt); symlink or copy from agents/examples/
    goldens.json           # DeepEval Golden records (input, expected_output, metadata)
  metrics/
    __init__.py
    schema_validator.py    # Custom BaseMetric — analyzer JSON Schema
    topic_preservation.py
    claims_extracted.py
    fact_check_grounded.py
    spanish_language.py
    non_empty.py
  cassettes/               # VCR.py recordings for fact-checker search (--no-llm CI)
  schemas/
    analyzer_v1.json       # JSON Schema for analyzer output
  conftest.py              # Shared fixtures: mock graph, cassette mode, prompt versions
  test_story_audit_e2e.py  # End-to-end graph evals
  test_agents_unit.py      # Per-agent evals with mocked upstream state
agents/prompts/            # Extract prompts from inline strings; version: field
```

**Golden dataset**

1. Expand beyond `luis_pie_cluster.txt`: at least **5–10 curated clusters** (politics, sports, crime, economy, low-source-count edge cases).
2. Load via DeepEval `EvaluationDataset`:

```python
from deepeval.dataset import EvaluationDataset, Golden

dataset = EvaluationDataset()
dataset.add_goldens_from_json_file("tests/evals/datasets/goldens.json")
```

3. Each golden includes:
   - `input` — cluster story text (or path reference)
   - `expected_output` — optional reference synthesizer headline/topics
   - `metadata` — `topic`, `expected_confidence_band`, `min_claims`, `fixture_id`

**Custom metrics** (DeepEval `BaseMetric` subclasses)

| Metric | Agent | Pass criteria |
|--------|-------|---------------|
| `SchemaValidatorMetric` | analyzer | Valid JSON matching `schemas/analyzer_v1.json` |
| `NonEmptyMetric` | all | Response length > N chars |
| `SpanishLanguageMetric` | synthesizer | Language detection or heuristic |
| `TopicPreservationMetric` | synthesizer | Keyword overlap with cluster description |
| `NoHallucinationMetric` | synthesizer | No ages/dates absent from judgment |
| `ClaimsExtractedMetric` | claim_extractor | ≥ N numbered claims for multi-article clusters |
| `FactCheckGroundedMetric` | fact_checker | Cited URL from allowlisted domain when world-fact marked supported/contradicted |
| `RegressionDiffMetric` | any | Optional snapshot compare with tolerance |

Use built-in DeepEval metrics where useful (e.g. `GEval` for rubric-based checks); prefer deterministic custom metrics for schema and URL grounding.

**Test patterns**

End-to-end (full LangGraph):

```python
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

@pytest.mark.parametrize("golden", dataset.goldens)
def test_story_audit_e2e(golden):
    result = run_story_audit(golden.input)  # wraps build_graph().invoke
    test_case = LLMTestCase(
        input=golden.input,
        actual_output=result["article"],
        expected_output=golden.expected_output,
        context=[result.get("judgment", ""), result.get("analysis", "")],
    )
    assert_test(test_case, metrics=E2E_METRICS)
```

Per-agent (mocked upstream):

```python
@pytest.mark.parametrize("golden", dataset.goldens)
def test_judger(golden, judger_upstream_state):
    output = judger.run(judger_upstream_state(golden))
    assert_test(LLMTestCase(input=golden.input, actual_output=output["judgment"]), JUDGER_METRICS)
```

**CLI** — use DeepEval, not a custom module:

```bash
# Full eval suite (preferred for CI)
deepeval test run tests/evals/

# Single file or test
deepeval test run tests/evals/test_story_audit_e2e.py
deepeval test run tests/evals/ -k luis_pie

# Validate fixtures/schemas only (pytest, no LLM)
pytest tests/evals/ --collect-only
python -c "import jsonschema; ..."  # schema smoke test in conftest or small script
```

**Cassettes / cheap CI (`--no-llm`)**

- Use **VCR.py** (or `pytest-recording`) for fact-checker search API calls in `tests/evals/cassettes/`.
- For LLM calls on PR CI: either
  - **Recorded responses** — commit cassettes/fixtures refreshed via `VCR_RECORD=1` or manual snapshot update when prompts change intentionally, or
  - **Skip live LLM on PR** — run schema + deterministic metrics only; nightly workflow runs full live eval.
- Do **not** use plain `pytest` for DeepEval tests — always `deepeval test run` ([docs](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)).

**CI integration**

```yaml
# .github/workflows/eval.yml (sketch)
- run: deepeval test run tests/evals/ --skip-live-llm   # if using env flag / marker
  env:
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}   # nightly / manual only
    FACT_CHECK_SEARCH_API_KEY: ${{ secrets.FACT_CHECK_SEARCH_API_KEY }}
```

1. **PR:** `deepeval test run tests/evals/` with VCR cassettes + deterministic metrics; fail on non-zero exit.
2. **Nightly / manual:** full live LLM + search eval; upload results artifact (DeepEval CLI report or Confident AI).
3. Fail CI if pass rate drops below threshold (configure per-metric `threshold` on custom metrics).

**Prompt lifecycle**

1. Extract prompts to `agents/prompts/*.yaml` with `version:` field; load in agent modules.
2. Log prompt version in audit results and structured logs.
3. Document workflow in `docs/harness.md`: edit prompt → `deepeval test run` → review → deploy.

**Integration with Analyzer (REQ-AGENT-001)**

- JSON Schema in `tests/evals/schemas/analyzer_v1.json`.
- `SchemaValidatorMetric` validates analyzer output before synthesizer in e2e tests.

**Integration with production**

- Optional **shadow mode:** run same custom metrics on live audit output; log warnings without blocking publish.
- Store eval scores in `audit_results` JSONB for calibration review.

**Acceptance:** Prompt changes to `agents/` require `deepeval test run tests/evals/` before merge; CI blocks schema/regression failures; golden dataset ≥ 5 fixtures; eval report available per run.

---

## 5. Proposed target architecture

```
                    ┌──────────────┐
                    │  PostgreSQL  │
                    └──────┬───────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
┌────┴────┐          ┌─────┴─────┐         ┌─────┴─────┐
│scheduler│          │    MCP    │         │ admin/API │
│         │          │ +verified │         │ +publish  │
└────┬────┘          └───────────┘         └─────┬─────┘
     │                                            │
     │         ┌──────────────┐                   │
     └────────►│ Chroma (RAG) │◄──────────────────┘
               └──────────────┘
                           ▲
                    ┌──────┴───────┐
                    │   website    │
                    │ (Next.js)    │
                    └──────────────┘

LangGraph: claim_extractor → fact_checker (+ domain search) ↘
           rhetorical_auditor ──────────────────► judger → analyzer → synthesizer
                                                      │
                                                      ▼
                                            verified_articles + scores

Observability:  services ──► structured logs ──► (Loki / journald)
                      └──► Prometheus metrics ──► Grafana + alerts

Harness:  goldens.json ──► deepeval test run ──► CI gate ──► prompt version in audit JSON
```

---

## 6. Implementation phases (suggested priority)

| Phase | Scope | Depends on |
|-------|--------|------------|
| **P0** | PostgreSQL + Alembic + migration script | — |
| **P0b** | Security baseline (secrets, startup validation, rate limits, TLS docs) | — |
| **P0c** | Structured logging + `/health`/`/ready` + cron exit metrics | — |
| **P1** | Analyzer agent + DB fields + JSON Schema | P0 |
| **P1b** | DeepEval suite: `tests/evals/`, goldens, custom metrics, VCR cassettes | P1 |
| **P1c** | Fact checker domain-filtered search + VCR cassettes in `tests/evals/cassettes/` | P0 |
| **P2** | MCP verified-article tools | P0, P1 |
| **P3** | Website API + remove mock data | P0, P1 |
| **P3b** | SEO (sitemap, OG, JSON-LD, ISR) + mobile audit + Lighthouse CI | P3 |
| **P4** | Documentation + test coverage | Parallel with P1–P3 |
| **P5** | Code cleanup + publish workflow | P3 |
| **P6** | Full observability (Prometheus dashboard, alerting, OTel optional) | P0c |
| **P7** | DeepEval expansion: nightly live eval, shadow mode, Confident AI sync (optional) | P1b |

---

## 7. Open decisions

1. **Auto-publish rules** — Publish all synthesized articles, or only when `confidence_score >= X`?
2. **Search provider** — Tavily vs Serper vs Brave for fact checker (all must support domain filtering)?
3. **Trusted domain list** — Curated static list vs config file vs admin-editable allowlist?
4. **Verified article search** — Index synthesized body in new Chroma collection vs SQL full-text only?
5. **MongoDB** — Not recommended unless requirements shift to document-first storage with no relational joins.
6. **Observability stack** — Self-hosted Prometheus/Grafana vs managed (Grafana Cloud, Datadog)?
7. **DeepEval in CI** — VCR cassettes + deterministic metrics on PR; live LLM on nightly (recommended).
8. **Rate limit defaults** — Requests/min per IP for MCP and public API?
9. **Shadow eval in production** — Log-only warnings vs block publish on eval failure?
10. **Analyzer model** — Same DeepSeek instance as judger, or cheaper/faster model for structured JSON?
11. **Confident AI cloud** — Use for dataset/eval history or keep everything in-repo only?
12. **Image hosting** — Self-hosted vs CDN for article/OG images (affects LCP and SEO)?

---

## 8. Acceptance checklist (project complete)

- [ ] PostgreSQL is the only OLTP database; SQLite removed from compose and docs
- [ ] Production data migrated with verified row counts and stable IDs
- [ ] Analyzer node in graph; confidence and source scores persisted
- [ ] Fact checker uses domain-filtered search API; citations include allowlisted URLs
- [ ] MCP exposes verified articles and confidence metadata
- [ ] Website renders live published articles (no mock TS data)
- [ ] Website passes mobile Lighthouse SEO ≥ 90; sitemap + robots + NewsArticle JSON-LD live
- [ ] Mobile layout verified at 375px; touch targets and nav accessibility OK
- [ ] Admin can view/edit/publish verified articles
- [ ] Component documentation under `docs/` is accurate
- [ ] Tests cover DB layer, analyzer persistence, MCP verified tools, and website API contract
- [ ] Dead code and duplicate DB access paths removed
- [ ] Security baseline: no default secrets in docs, rate limits, TLS documented, admin audit log
- [ ] Structured logging with trace IDs across agent runs; `/ready` healthchecks
- [ ] Metrics exported for ingest, audit, LLM, and MCP tool latency
- [ ] DeepEval CI runs on `agents/` changes; `deepeval test run tests/evals/` passes
- [ ] Golden dataset ≥ 5 fixtures in `tests/evals/datasets/goldens.json`
- [ ] Custom metrics cover analyzer schema, claims, topic preservation, fact-check URL grounding

---

*Generated from repository analysis. Update this file as requirements are implemented or decisions change.*
