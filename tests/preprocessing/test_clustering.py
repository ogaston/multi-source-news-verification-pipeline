"""Unit tests for agglomerative clustering (no embedding model required)."""

from __future__ import annotations

import numpy as np
import pytest

from preprocessing.clustering import (
    article_document_text,
    cluster_embeddings,
    l2_normalize,
)


class TestArticleDocumentText:
    def test_joins_title_and_content(self):
        assert article_document_text("Title", "Body") == "Title\n\nBody"

    def test_skips_empty_parts(self):
        assert article_document_text("", "Body") == "Body"
        assert article_document_text("Title", None) == "Title"
        assert article_document_text(None, None) == ""


class TestClusterEmbeddings:
    def test_empty(self):
        assert cluster_embeddings([], []) == {}

    def test_singleton(self):
        result = cluster_embeddings(["a"], [[1.0, 0.0, 0.0]])
        assert len(result) == 1
        assert list(result.values())[0] == ["a"]

    def test_identical_vectors_merge(self):
        v = [1.0, 0.0, 0.0]
        result = cluster_embeddings(
            ["a", "b"],
            [v, v],
            distance_threshold=0.25,
        )
        assert len(result) == 1
        members = sorted(next(iter(result.values())))
        assert members == ["a", "b"]

    def test_orthogonal_vectors_stay_separate(self):
        result = cluster_embeddings(
            ["a", "b"],
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            distance_threshold=0.25,
        )
        assert len(result) == 2
        flat = sorted(m for members in result.values() for m in members)
        assert flat == ["a", "b"]

    def test_near_threshold_pairs(self):
        # Two near-identical pairs that are far from each other.
        pair1_a = [1.0, 0.0, 0.0]
        pair1_b = [0.99, 0.01, 0.0]
        pair2_a = [0.0, 1.0, 0.0]
        pair2_b = [0.01, 0.99, 0.0]
        result = cluster_embeddings(
            ["a", "b", "c", "d"],
            [pair1_a, pair1_b, pair2_a, pair2_b],
            distance_threshold=0.25,
        )
        assert len(result) == 2
        groups = {frozenset(members) for members in result.values()}
        assert groups == {frozenset({"a", "b"}), frozenset({"c", "d"})}

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            cluster_embeddings(["a"], [[1.0], [2.0]])

    def test_l2_normalize(self):
        matrix = np.asarray([[3.0, 4.0], [0.0, 0.0]], dtype=np.float64)
        out = l2_normalize(matrix)
        assert np.allclose(out[0], [0.6, 0.8])
        assert np.allclose(out[1], [0.0, 0.0])
