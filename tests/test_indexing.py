"""Unit tests for chunk node building (no embedding model required)."""

from __future__ import annotations

from common.config import CHUNK_OVERLAP, CHUNK_SIZE
from common.indexing import build_nodes_for_article


def test_build_nodes_sets_ids_and_metadata():
    article = {
        "id": "abc123",
        "url": "https://example.com/story",
        "source": "Acento",
        "title": "Reforma fiscal",
        "date": "2026-07-21T12:00:00+00:00",
        "content": "Primera oración sobre la reforma. " * 40
        + "Segunda parte del artículo con más detalle. " * 40,
    }
    nodes = build_nodes_for_article(article)
    assert len(nodes) >= 1
    for i, node in enumerate(nodes):
        assert node.id_ == f"abc123:{i}"
        assert node.metadata["article_id"] == "abc123"
        assert node.metadata["url"] == "https://example.com/story"
        assert node.metadata["source"] == "Acento"
        assert node.metadata["title"] == "Reforma fiscal"
        assert node.metadata["date"] == "2026-07-21T12:00:00+00:00"
        assert node.metadata["chunk_index"] == i
        assert node.get_content()
        # Title is metadata only — not prepended into chunk text.
        assert not node.get_content().startswith("Reforma fiscal\n\n")


def test_build_nodes_empty_content():
    assert build_nodes_for_article({"id": "x", "content": ""}) == []
    assert build_nodes_for_article({"id": "x", "content": "   "}) == []


def test_chunk_config_positive():
    assert CHUNK_SIZE > 0
    assert CHUNK_OVERLAP >= 0
    assert CHUNK_OVERLAP < CHUNK_SIZE
