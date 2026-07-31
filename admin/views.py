"""SQLAdmin ModelViews for pipeline tables."""

from sqladmin import ModelView

from admin.models import Cluster, RawArticle, TopicCluster, VerifiedArticle


def _truncate(value: str | None, limit: int = 120) -> str:
    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit] + "…"


class RawArticleAdmin(ModelView, model=RawArticle):
    name = "Raw Article"
    name_plural = "Raw Articles"
    icon = "fa-solid fa-newspaper"

    column_list = [
        RawArticle.id,
        RawArticle.source,
        RawArticle.title,
        RawArticle.date,
        RawArticle.author,
        RawArticle.category,
        RawArticle.scraped_at,
        RawArticle.processed,
        RawArticle.url,
    ]
    column_searchable_list = [
        RawArticle.title,
        RawArticle.url,
        RawArticle.source,
        RawArticle.author,
        RawArticle.id,
    ]
    column_sortable_list = [
        RawArticle.date,
        RawArticle.scraped_at,
        RawArticle.source,
        RawArticle.processed,
    ]
    column_details_list = [
        RawArticle.id,
        RawArticle.url,
        RawArticle.source,
        RawArticle.title,
        RawArticle.content,
        RawArticle.date,
        RawArticle.author,
        RawArticle.category,
        RawArticle.scraped_at,
        RawArticle.processed,
    ]
    column_formatters = {
        RawArticle.content: lambda m, a: _truncate(m.content),
    }


class TopicClusterAdmin(ModelView, model=TopicCluster):
    name = "Topic Cluster"
    name_plural = "Topic Clusters"
    icon = "fa-solid fa-link"

    column_list = [
        TopicCluster.id,
        TopicCluster.cluster_id,
        TopicCluster.article_id,
        TopicCluster.created_at,
    ]
    column_searchable_list = [
        TopicCluster.cluster_id,
        TopicCluster.article_id,
    ]
    column_sortable_list = [
        TopicCluster.id,
        TopicCluster.cluster_id,
        TopicCluster.created_at,
    ]


class ClusterAdmin(ModelView, model=Cluster):
    name = "Cluster"
    name_plural = "Clusters"
    icon = "fa-solid fa-layer-group"

    column_list = [
        Cluster.cluster_id,
        Cluster.description,
        Cluster.processed,
        Cluster.created_at,
    ]
    column_searchable_list = [
        Cluster.cluster_id,
        Cluster.description,
    ]
    column_sortable_list = [
        Cluster.cluster_id,
        Cluster.processed,
        Cluster.created_at,
    ]
    column_details_list = [
        Cluster.cluster_id,
        Cluster.description,
        Cluster.processed,
        Cluster.created_at,
    ]
    column_formatters = {
        Cluster.description: lambda m, a: _truncate(m.description),
    }


class VerifiedArticleAdmin(ModelView, model=VerifiedArticle):
    name = "Verified Article"
    name_plural = "Verified Articles"
    icon = "fa-solid fa-check-double"

    can_create = False
    can_delete = False
    can_edit = True

    column_list = [
        VerifiedArticle.id,
        VerifiedArticle.cluster_id,
        VerifiedArticle.slug,
        VerifiedArticle.title,
        VerifiedArticle.category,
        VerifiedArticle.date,
        VerifiedArticle.sources,
        VerifiedArticle.status,
        VerifiedArticle.confidence,
        VerifiedArticle.created_at,
    ]
    column_searchable_list = [
        VerifiedArticle.title,
        VerifiedArticle.slug,
        VerifiedArticle.cluster_id,
        VerifiedArticle.sources,
        VerifiedArticle.id,
    ]
    column_sortable_list = [
        VerifiedArticle.date,
        VerifiedArticle.status,
        VerifiedArticle.created_at,
        VerifiedArticle.slug,
        VerifiedArticle.confidence,
    ]
    column_details_list = [
        VerifiedArticle.id,
        VerifiedArticle.cluster_id,
        VerifiedArticle.slug,
        VerifiedArticle.title,
        VerifiedArticle.content,
        VerifiedArticle.category,
        VerifiedArticle.image_url,
        VerifiedArticle.date,
        VerifiedArticle.sources,
        VerifiedArticle.status,
        VerifiedArticle.confidence,
        VerifiedArticle.confidence_score,
        VerifiedArticle.source_scores,
        VerifiedArticle.audit_json,
        VerifiedArticle.created_at,
    ]
    # Editors demote bad articles to draft (pipeline publishes by default).
    form_columns = [
        VerifiedArticle.status,
        VerifiedArticle.title,
        VerifiedArticle.category,
        VerifiedArticle.slug,
        VerifiedArticle.image_url,
        VerifiedArticle.date,
        VerifiedArticle.sources,
        VerifiedArticle.confidence,
        VerifiedArticle.content,
    ]
    column_formatters = {
        VerifiedArticle.content: lambda m, a: _truncate(m.content),
    }
