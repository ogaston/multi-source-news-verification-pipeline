"""Shared configuration for ingest, storage, and MCP."""

import os

DB_NAME = os.environ.get("DB_NAME", "dominican_news_repository.db")
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
# Cosine distance threshold for AHC (≈ 1 - similarity); 0.25 ≈ similarity 0.75.
CLUSTER_DISTANCE_THRESHOLD = float(os.environ.get("CLUSTER_DISTANCE_THRESHOLD", "0.30"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
CLUSTER_DESC_MAX_CHARS = int(os.environ.get("CLUSTER_DESC_MAX_CHARS", "800"))
STORY_CHROMA_COLLECTION = os.environ.get("STORY_CHROMA_COLLECTION", "story_index")
