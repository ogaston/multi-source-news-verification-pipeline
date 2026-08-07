"""Shared configuration for ingest, storage, and MCP."""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://news:news@localhost:5432/news",
)
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")
# v2 = chunked LlamaIndex nodes (not whole-article vectors).
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "news_index_v2")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "64"))

MIN_CONTENT_CHARS = 50
DEFAULT_URL_LIMIT = int(os.environ.get("DEFAULT_URL_LIMIT", "100"))
DEFAULT_QUERY_LIMIT = 5
DEFAULT_DAYS_BACK = 7
DEFAULT_LIST_DAYS_BACK = 1
DEFAULT_LIST_STORIES_LIMIT = 20

MAX_QUERY_LIMIT = int(os.environ.get("MAX_QUERY_LIMIT", "50"))
MAX_DAYS_BACK = int(os.environ.get("MAX_DAYS_BACK", "365"))
MAX_TOPIC_LENGTH = int(os.environ.get("MAX_TOPIC_LENGTH", "500"))

# Fetch extra Chroma hits so post-filters (date/source) still fill `limit`.
QUERY_CANDIDATE_MULTIPLIER = 5
QUERY_CANDIDATE_MIN = 25

DATA_DIR = os.environ.get("DATA_DIR", "data")

PREPROCESS_BATCH_SIZE = int(os.environ.get("PREPROCESS_BATCH_SIZE", "650"))
# Pipeline calendar timezone (ingest timestamps + daily preprocess day window).
PIPELINE_TZ = os.environ.get("PIPELINE_TZ", "America/Santo_Domingo")
# Daily preprocess selects this many local days before "today" (1 = previous day).
PREPROCESS_DAY_OFFSET = int(os.environ.get("PREPROCESS_DAY_OFFSET", "1"))
# Deprecated rolling-hour filter for manual backfill only (0 = off).
# Daily cron uses the previous local calendar day, not this knob.
PREPROCESS_LOOKBACK_HOURS = int(os.environ.get("PREPROCESS_LOOKBACK_HOURS", "0"))
# Max clusters to describe/index per preprocess run (0 = no limit).
# Largest clusters are preferred; undescribed ones can be backfilled via reindex.
PREPROCESS_CLUSTER_LIMIT = int(os.environ.get("PREPROCESS_CLUSTER_LIMIT", "30"))
# Cosine distance threshold for AHC (≈ 1 - similarity); 0.25 ≈ similarity 0.75.
CLUSTER_DISTANCE_THRESHOLD = float(os.environ.get("CLUSTER_DISTANCE_THRESHOLD", "0.27"))
# Only audit clusters whose newest member article is within this many days.
STORY_AUDIT_MAX_AGE_DAYS = int(os.environ.get("STORY_AUDIT_MAX_AGE_DAYS", "1"))
# Top unprocessed clusters to audit per batch run.
STORY_AUDIT_BATCH_SIZE = int(os.environ.get("STORY_AUDIT_BATCH_SIZE", "30"))
# Homepage layout: lead + secondary (imaged) + list.
HOMEPAGE_SECONDARY_COUNT = int(os.environ.get("HOMEPAGE_SECONDARY_COUNT", "8"))
HOMEPAGE_LIST_COUNT = int(os.environ.get("HOMEPAGE_LIST_COUNT", "8"))
# Articles newer than this many days are ranked by cluster importance;
# older published articles append below by recency.
HOMEPAGE_RANK_MAX_AGE_DAYS = int(os.environ.get("HOMEPAGE_RANK_MAX_AGE_DAYS", "3"))


def get_deepseek_config() -> tuple[str, str, str, int, int, float]:
    return (
        os.environ.get("DEEPSEEK_API_KEY", ""),
        os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        int(os.environ.get("DEEPSEEK_MAX_TOKENS", "4096")),
        int(os.environ.get("DEEPSEEK_MAX_RETRIES", "5")),
        float(os.environ.get("DEEPSEEK_RETRY_WAIT", "8")),
    )


def get_final_article_max_chars() -> int:
    return int(os.environ.get("FINAL_ARTICLE_MAX_CHARS", "1500"))


DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY", "")
DEEPINFRA_MODEL = os.environ.get(
    "DEEPINFRA_MODEL", "Qwen/Qwen3.6-35B-A3B"
)
DEEPINFRA_BASE_URL = os.environ.get(
    "DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1/openai"
).rstrip("/")
DEEPINFRA_IMAGE_MODEL = os.environ.get(
    "DEEPINFRA_IMAGE_MODEL", "black-forest-labs/FLUX-2-klein-4b"
)
# 4:3 landscape (multiples of 32) for editorial covers; 3:2 e.g. 1152x768 also fine.
DEEPINFRA_IMAGE_SIZE = os.environ.get("DEEPINFRA_IMAGE_SIZE", "1024x768")
ARTICLE_IMAGE_MAX_PER_BATCH = int(os.environ.get("ARTICLE_IMAGE_MAX_PER_BATCH", "9"))
ARTICLE_IMAGES_DIR = os.environ.get(
    "ARTICLE_IMAGES_DIR", os.path.join(DATA_DIR, "article_images")
)
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "http://localhost:7002").rstrip("/")
CLUSTER_DESC_MAX_CHARS = int(os.environ.get("CLUSTER_DESC_MAX_CHARS", "800"))
STORY_CHROMA_COLLECTION = os.environ.get("STORY_CHROMA_COLLECTION", "story_index")
VERIFIED_CHROMA_COLLECTION = os.environ.get(
    "VERIFIED_CHROMA_COLLECTION", "verified_index"
)

# Serper-backed fact checking.  Every result is post-filtered against this
# allowlist; `gob.do` also permits its subdomains (for example, one.gob.do).
DEFAULT_FACT_CHECK_TRUSTED_DOMAINS = (
    "gob.do",
    "armando.info",
    "ojo-publico.com",
    "connectas.org",
    "chequeado.com",
    "aosfatos.org",
    "agencialupa.com.br",
    "verificado.mx",
    "un.org",
    "unicef.org",
    "who.int",
    "paho.org",
    "oas.org",
    "worldbank.org",
    "imf.org",
    "iadb.org",
    "ilo.org",
    "unesco.org",
)
FACT_CHECK_SEARCH_API_KEY = os.environ.get(
    "FACT_CHECK_SEARCH_API_KEY", os.environ.get("SERPER_API_KEY", "")
)
FACT_CHECK_TRUSTED_DOMAINS = tuple(
    domain.strip().lower().rstrip(".")
    for domain in os.environ.get(
        "FACT_CHECK_TRUSTED_DOMAINS",
        ",".join(DEFAULT_FACT_CHECK_TRUSTED_DOMAINS),
    ).split(",")
    if domain.strip()
)
FACT_CHECK_MAX_SEARCHES_PER_CLUSTER = int(
    os.environ.get("FACT_CHECK_MAX_SEARCHES_PER_CLUSTER", "10")
)
FACT_CHECK_RESULTS_PER_QUERY = int(
    os.environ.get("FACT_CHECK_RESULTS_PER_QUERY", "3")
)
FACT_CHECK_SEARCH_GEO = os.environ.get("FACT_CHECK_SEARCH_GEO", "do")
FACT_CHECK_SEARCH_LANG = os.environ.get("FACT_CHECK_SEARCH_LANG", "es")
FACT_CHECK_SEARCH_TIMEOUT_SECONDS = float(
    os.environ.get("FACT_CHECK_SEARCH_TIMEOUT_SECONDS", "15")
)
FACT_CHECK_SEARCH_CACHE_TTL_SECONDS = int(
    os.environ.get("FACT_CHECK_SEARCH_CACHE_TTL_SECONDS", "86400")
)
