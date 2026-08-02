import type { Article } from '@/lib/articles'

export type HomeData = {
  leadArticle: Article | null
  secondaryArticles: Article[]
  listArticles: Article[]
  moreArticles: Article[]
}

/** Left column (imaged) after the lead. */
export const HOMEPAGE_SECONDARY_COUNT = 8
/** Right column (text list) after the secondary block. */
export const HOMEPAGE_LIST_COUNT = 8

/** Split a relevance-ordered feed into lead + left 8 + right 8. */
export function splitHomeArticles(articles: Article[]): HomeData {
  if (articles.length === 0) {
    return {
      leadArticle: null,
      secondaryArticles: [],
      listArticles: [],
      moreArticles: [],
    }
  }
  const [leadArticle, ...rest] = articles
  const visibleCount = HOMEPAGE_SECONDARY_COUNT + HOMEPAGE_LIST_COUNT
  return {
    leadArticle,
    secondaryArticles: rest.slice(0, HOMEPAGE_SECONDARY_COUNT),
    listArticles: rest.slice(
      HOMEPAGE_SECONDARY_COUNT,
      visibleCount
    ),
    moreArticles: rest.slice(visibleCount),
  }
}
