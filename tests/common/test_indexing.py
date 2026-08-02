"""Unit tests for chunk node building (no embedding model required)."""

from __future__ import annotations

import common.indexing as indexing
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


def test_public_store_and_index_caches_are_isolated_by_collection(monkeypatch):
    collections = {}
    created_stores = []
    created_indexes = []

    class FakeVectorStore:
        def __init__(self, *, chroma_collection):
            self.collection = chroma_collection
            created_stores.append(self)

    class FakeStorageContext:
        @staticmethod
        def from_defaults(*, vector_store):
            return {"vector_store": vector_store}

    class FakeIndex:
        @staticmethod
        def from_vector_store(vector_store, *, storage_context, embed_model):
            index = (vector_store, storage_context, embed_model)
            created_indexes.append(index)
            return index

    monkeypatch.setattr(indexing, "_vector_stores", {})
    monkeypatch.setattr(indexing, "_indexes", {})
    monkeypatch.setattr(
        indexing,
        "_get_chroma_collection",
        lambda name=indexing.CHROMA_COLLECTION: collections.setdefault(name, object()),
    )
    monkeypatch.setattr(indexing, "ChromaVectorStore", FakeVectorStore)
    monkeypatch.setattr(indexing, "StorageContext", FakeStorageContext)
    monkeypatch.setattr(indexing, "VectorStoreIndex", FakeIndex)
    monkeypatch.setattr(indexing, "_get_embed_model", lambda: "embed-model")

    stores = [
        indexing.get_vector_store(),
        indexing.get_story_vector_store(),
        indexing.get_verified_vector_store(),
    ]
    indexes = [
        indexing.get_index(),
        indexing.get_story_index(),
        indexing.get_verified_index(),
    ]

    assert len({id(store) for store in stores}) == 3
    assert len(created_stores) == 3
    assert len(created_indexes) == 3
    assert indexing.get_vector_store() is stores[0]
    assert indexing.get_story_index() is indexes[1]
    assert indexing.get_verified_index() is indexes[2]


def test_deleting_story_invalidates_only_story_cache(monkeypatch):
    stores = {
        indexing.CHROMA_COLLECTION: object(),
        indexing.STORY_CHROMA_COLLECTION: object(),
        indexing.VERIFIED_CHROMA_COLLECTION: object(),
    }
    indexes = {name: object() for name in stores}
    deleted = []

    class FakeClient:
        def delete_collection(self, name):
            deleted.append(name)

    monkeypatch.setattr(indexing, "_vector_stores", stores)
    monkeypatch.setattr(indexing, "_indexes", indexes)
    monkeypatch.setattr(indexing, "_chroma_client", FakeClient)

    assert indexing.delete_story_index() is True
    assert deleted == [indexing.STORY_CHROMA_COLLECTION]
    assert set(stores) == {
        indexing.CHROMA_COLLECTION,
        indexing.VERIFIED_CHROMA_COLLECTION,
    }
    assert set(indexes) == {
        indexing.CHROMA_COLLECTION,
        indexing.VERIFIED_CHROMA_COLLECTION,
    }


def test_story_and_verified_upserts_preserve_public_document_behavior(monkeypatch):
    deleted = []
    inserted = []

    class FakeCollection:
        def __init__(self, name):
            self.name = name

        def delete(self, *, ids):
            deleted.append((self.name, ids))

    class FakeIndex:
        def __init__(self, name):
            self.name = name

        def insert_nodes(self, nodes):
            inserted.append((self.name, nodes[0]))

    monkeypatch.setattr(indexing, "_get_chroma_collection", FakeCollection)
    monkeypatch.setattr(indexing, "_get_index", FakeIndex)

    indexing.index_story("story-1", "  Story description  ", "2026-08-01")
    indexing.index_verified_article(
        cluster_id="verified-1",
        title="  Headline  ",
        content="  Body copy  ",
        date=None,
        status="",
    )

    assert deleted == [
        (indexing.STORY_CHROMA_COLLECTION, ["story-1"]),
        (indexing.VERIFIED_CHROMA_COLLECTION, ["verified-1"]),
    ]
    story_node = inserted[0][1]
    assert inserted[0][0] == indexing.STORY_CHROMA_COLLECTION
    assert story_node.id_ == "story-1"
    assert story_node.text == "Story description"
    assert story_node.metadata == {
        "cluster_id": "story-1",
        "created_at": "2026-08-01",
    }
    verified_node = inserted[1][1]
    assert inserted[1][0] == indexing.VERIFIED_CHROMA_COLLECTION
    assert verified_node.id_ == "verified-1"
    assert verified_node.text == "Headline\n\nBody copy"
    assert verified_node.metadata == {
        "cluster_id": "verified-1",
        "title": "Headline",
        "date": "",
        "status": "draft",
    }
