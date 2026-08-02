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
    STORY_CHROMA_COLLECTION,
    VERIFIED_CHROMA_COLLECTION,
)

_embed_model: HuggingFaceEmbedding | None = None
_vector_stores: dict[str, ChromaVectorStore] = {}
_indexes: dict[str, VectorStoreIndex] = {}
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


@dataclass(frozen=True)
class RetrievedStory:
    cluster_id: str
    description: str
    score: float
    created_at: str


@dataclass(frozen=True)
class RetrievedVerified:
    cluster_id: str
    title: str
    score: float
    date: str
    status: str


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


def _get_chroma_collection(collection_name: str = CHROMA_COLLECTION):
    return _chroma_client().get_or_create_collection(name=collection_name)


def _get_vector_store(collection_name: str) -> ChromaVectorStore:
    if collection_name not in _vector_stores:
        _vector_stores[collection_name] = ChromaVectorStore(
            chroma_collection=_get_chroma_collection(collection_name)
        )
    return _vector_stores[collection_name]


def _get_index(collection_name: str) -> VectorStoreIndex:
    if collection_name not in _indexes:
        vector_store = _get_vector_store(collection_name)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _indexes[collection_name] = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=_get_embed_model(),
        )
    return _indexes[collection_name]


def get_vector_store() -> ChromaVectorStore:
    return _get_vector_store(CHROMA_COLLECTION)


def get_index() -> VectorStoreIndex:
    return _get_index(CHROMA_COLLECTION)


def get_story_vector_store() -> ChromaVectorStore:
    return _get_vector_store(STORY_CHROMA_COLLECTION)


def get_story_index() -> VectorStoreIndex:
    return _get_index(STORY_CHROMA_COLLECTION)


def get_verified_vector_store() -> ChromaVectorStore:
    return _get_vector_store(VERIFIED_CHROMA_COLLECTION)


def get_verified_index() -> VectorStoreIndex:
    return _get_index(VERIFIED_CHROMA_COLLECTION)


def reset_index_cache() -> None:
    """Clear cached store/index (e.g. after deleting the collection)."""
    _vector_stores.clear()
    _indexes.clear()


def _delete_index(collection_name: str) -> bool:
    try:
        _chroma_client().delete_collection(collection_name)
        return True
    except Exception:
        return False
    finally:
        _vector_stores.pop(collection_name, None)
        _indexes.pop(collection_name, None)


def delete_collection() -> bool:
    """Delete the Chroma collection if it exists. Returns True if deleted."""
    return _delete_index(CHROMA_COLLECTION)


def delete_story_index() -> bool:
    """Delete the story Chroma collection if it exists. Returns True if deleted."""
    return _delete_index(STORY_CHROMA_COLLECTION)


def delete_verified_index() -> bool:
    """Delete the verified Chroma collection if it exists. Returns True if deleted."""
    return _delete_index(VERIFIED_CHROMA_COLLECTION)


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


def _upsert_single_document(
    collection_name: str,
    document_id: str,
    text: str,
    metadata: dict[str, Any],
) -> None:
    collection = _get_chroma_collection(collection_name)
    try:
        collection.delete(ids=[document_id])
    except Exception:
        pass

    from llama_index.core.schema import TextNode

    node = TextNode(
        text=text,
        id_=document_id,
        metadata=metadata,
    )
    _get_index(collection_name).insert_nodes([node])


def index_story(cluster_id: str, description: str, created_at: str) -> None:
    """Upsert one vector document per story description."""
    text = (description or "").strip()
    if not text:
        return

    _upsert_single_document(
        STORY_CHROMA_COLLECTION,
        cluster_id,
        text,
        {
            "cluster_id": cluster_id,
            "created_at": created_at or "",
        },
    )


def retrieve_stories(query: str, n_results: int) -> list[RetrievedStory]:
    """Semantic retrieve of story descriptions (ranked)."""
    if n_results < 1:
        return []
    retriever = get_story_index().as_retriever(similarity_top_k=n_results)
    results = retriever.retrieve(query)
    stories: list[RetrievedStory] = []
    for node_with_score in results:
        node = node_with_score.node
        meta = node.metadata or {}
        cluster_id = str(meta.get("cluster_id") or node.node_id or "")
        if not cluster_id:
            continue
        stories.append(
            RetrievedStory(
                cluster_id=cluster_id,
                description=node.get_content() or "",
                score=float(node_with_score.score or 0.0),
                created_at=str(meta.get("created_at") or ""),
            )
        )
    return stories


def index_verified_article(
    *,
    cluster_id: str,
    title: str,
    content: str,
    date: str | None = None,
    status: str = "draft",
) -> None:
    """Upsert one vector document per verified article (title + body)."""
    title = (title or "").strip()
    content = (content or "").strip()
    text = f"{title}\n\n{content}".strip() if title else content
    if not text:
        return

    _upsert_single_document(
        VERIFIED_CHROMA_COLLECTION,
        cluster_id,
        text,
        {
            "cluster_id": cluster_id,
            "title": title,
            "date": date or "",
            "status": status or "draft",
        },
    )


def retrieve_verified(query: str, n_results: int) -> list[RetrievedVerified]:
    """Semantic retrieve of verified articles (ranked)."""
    if n_results < 1:
        return []
    retriever = get_verified_index().as_retriever(similarity_top_k=n_results)
    results = retriever.retrieve(query)
    articles: list[RetrievedVerified] = []
    for node_with_score in results:
        node = node_with_score.node
        meta = node.metadata or {}
        cluster_id = str(meta.get("cluster_id") or node.node_id or "")
        if not cluster_id:
            continue
        articles.append(
            RetrievedVerified(
                cluster_id=cluster_id,
                title=str(meta.get("title") or ""),
                score=float(node_with_score.score or 0.0),
                date=str(meta.get("date") or ""),
                status=str(meta.get("status") or ""),
            )
        )
    return articles
