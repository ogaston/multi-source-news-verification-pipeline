"""Shared configuration for ingest, storage, and MCP."""

import os

DB_NAME = os.environ.get("DB_NAME", "dominican_news_repository.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "news_index")
EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)

MIN_CONTENT_CHARS = 200
DEFAULT_URL_LIMIT = 5
DEFAULT_QUERY_LIMIT = 5
DEFAULT_DAYS_BACK = 7
# Fetch extra Chroma hits so post-filters (date/source) still fill `limit`.
QUERY_CANDIDATE_MULTIPLIER = 5
QUERY_CANDIDATE_MIN = 25

DATA_DIR = os.environ.get("DATA_DIR", "data")
