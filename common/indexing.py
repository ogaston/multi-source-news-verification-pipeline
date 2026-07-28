"""LlamaIndex + Chroma chunk indexing and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from common.config import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBED_MODEL,
)

_embed_model: HuggingFaceEmbedding | None = None
_vector_store: ChromaVectorStore | None = None
_index: VectorStoreIndex | None = None
_splitter: SentenceSplitter | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    article_id: str
    text: str
    score: float
    url: str
    source: str
    title: str
    date: str
    chunk_index: int


def _get_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    return _embed_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the shared HuggingFace model."""
    if not texts:
        return []
    model = _get_embed_model()
    return [list(model.get_text_embedding(text)) for text in texts]


def _get_splitter() -> SentenceSplitter:
    global _splitter
    if _splitter is None:
        _splitter = SentenceSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
    return _splitter


def _chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)


def _get_chroma_collection():
    return _chroma_client().get_or_create_collection(name=CHROMA_COLLECTION)


def get_vector_store() -> ChromaVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore(chroma_collection=_get_chroma_collection())
    return _vector_store


def get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        storage_context = StorageContext.from_defaults(
            vector_store=get_vector_store()
        )
        _index = VectorStoreIndex.from_vector_store(
            get_vector_store(),
            storage_context=storage_context,
            embed_model=_get_embed_model(),
        )
    return _index


def reset_index_cache() -> None:
    """Clear cached store/index (e.g. after deleting the collection)."""
    global _vector_store, _index
    _vector_store = None
    _index = None


def delete_collection() -> bool:
    """Delete the Chroma collection if it exists. Returns True if deleted."""
    client = _chroma_client()
    try:
        client.delete_collection(CHROMA_COLLECTION)
        reset_index_cache()
        return True
    except Exception:
        reset_index_cache()
        return False


def delete_article_chunks(article_id: str) -> None:
    collection = _get_chroma_collection()
    try:
        collection.delete(where={"article_id": article_id})
    except Exception:
        pass
    # Also clear LlamaIndex document_id refs if present.
    try:
        get_vector_store().delete(ref_doc_id=article_id)
    except Exception:
        pass


def build_nodes_for_article(article: dict[str, Any]) -> list:
    """Split article content into TextNodes (no embedding). Used by tests."""
    article_id = article["id"]
    content = (article.get("content") or "").strip()
    if not content:
        return []

    doc = Document(
        text=content,
        id_=article_id,
        metadata={
            "article_id": article_id,
            "url": article.get("url") or "",
            "source": article.get("source") or "",
            "title": article.get("title") or "",
            "date": article.get("date") or "",
        },
    )
    nodes = _get_splitter().get_nodes_from_documents([doc])
    for i, node in enumerate(nodes):
        node.id_ = f"{article_id}:{i}"
        node.metadata["chunk_index"] = i
        # Keep article_id as a plain string for Chroma where-filters.
        node.metadata["article_id"] = article_id
    return nodes


def index_article(article: dict[str, Any]) -> int:
    """
    Delete prior chunks for this article and upsert fresh chunk nodes.
    Returns number of chunks indexed.
    """
    article_id = article["id"]
    nodes = build_nodes_for_article(article)
    delete_article_chunks(article_id)
    if not nodes:
        return 0
    get_index().insert_nodes(nodes)
    return len(nodes)


def retrieve_chunks(topic: str, n_results: int) -> list[RetrievedChunk]:
    """Semantic retrieve of chunk nodes (ranked)."""
    if n_results < 1:
        return []
    retriever = get_index().as_retriever(similarity_top_k=n_results)
    results = retriever.retrieve(topic)
    chunks: list[RetrievedChunk] = []
    for node_with_score in results:
        node = node_with_score.node
        meta = node.metadata or {}
        article_id = str(meta.get("article_id") or "")
        if not article_id:
            # Fallback: parse from node id "{article_id}:{chunk_index}"
            node_id = node.node_id or ""
            article_id = node_id.rsplit(":", 1)[0] if ":" in node_id else node_id
        try:
            chunk_index = int(meta.get("chunk_index", 0))
        except (TypeError, ValueError):
            chunk_index = 0
        chunks.append(
            RetrievedChunk(
                article_id=article_id,
                text=node.get_content() or "",
                score=float(node_with_score.score or 0.0),
                url=str(meta.get("url") or ""),
                source=str(meta.get("source") or ""),
                title=str(meta.get("title") or ""),
                date=str(meta.get("date") or ""),
                chunk_index=chunk_index,
            )
        )
    return chunks
