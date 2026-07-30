import {
  leadArticle,
  secondaryArticles,
  listArticles,
  allArticles,
  type Article,
} from '@/lib/articles'

export type HomeData = {
  leadArticle: Article
  secondaryArticles: Article[]
  listArticles: Article[]
}

export async function getHomeData(): Promise<HomeData> {
  return { leadArticle, secondaryArticles, listArticles }
}

export async function getArticleBySlug(
  slug: string
): Promise<Article | null> {
  return allArticles().find((article) => article.slug === slug) ?? null
}
