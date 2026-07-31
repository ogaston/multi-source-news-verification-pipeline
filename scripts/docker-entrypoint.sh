#!/bin/sh
set -eu

mkdir -p "${CHROMA_PATH:-/data/chroma_db}" "${DATA_DIR:-/data/debug_json}" "${HF_HOME:-/data/hf_cache}"

exec "$@"
