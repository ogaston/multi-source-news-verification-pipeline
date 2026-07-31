import type { Article } from '@/lib/articles'

export type HomeData = {
  leadArticle: Article | null
  secondaryArticles: Article[]
  listArticles: Article[]
}

function apiBaseUrl(): string {
  const base = process.env.WEBSITE_API_URL?.replace(/\/$/, '')
  if (!base) {
    throw new Error('WEBSITE_API_URL is not set')
  }
  return base
}

async function fetchArticles(): Promise<Article[]> {
  const res = await fetch(`${apiBaseUrl()}/api/articles`, {
    next: { revalidate: 60 },
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch articles: ${res.status}`)
  }
  return res.json()
}

export async function getHomeData(): Promise<HomeData> {
  const articles = await fetchArticles()
  if (articles.length === 0) {
    return { leadArticle: null, secondaryArticles: [], listArticles: [] }
  }
  const [leadArticle, ...rest] = articles
  return {
    leadArticle,
    secondaryArticles: rest.slice(0, 2),
    listArticles: rest.slice(2),
  }
}

export async function getArticleBySlug(
  slug: string
): Promise<Article | null> {
  const res = await fetch(
    `${apiBaseUrl()}/api/articles/${encodeURIComponent(slug)}`,
    { next: { revalidate: 60 } }
  )
  if (res.status === 404) {
    return null
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch article: ${res.status}`)
  }
  return res.json()
}
