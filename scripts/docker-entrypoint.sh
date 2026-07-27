#!/bin/sh
set -eu

mkdir -p "$(dirname "$DB_NAME")" "$CHROMA_PATH" "$DATA_DIR" "${HF_HOME:-/data/hf_cache}"

exec "$@"
