import type { Article, ArticleSlug } from '@/lib/articles'

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

async function fetchArticles(category?: string): Promise<Article[]> {
  const query = category
    ? `?${new URLSearchParams({ category }).toString()}`
    : ''
  const res = await fetch(`${apiBaseUrl()}/api/articles${query}`, {
    next: { revalidate: 60 },
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch articles: ${res.status}`)
  }
  return res.json()
}

export async function getHomeData(): Promise<HomeData> {
  let articles: Article[]
  try {
    articles = await fetchArticles()
  } catch (error) {
    console.error('Unable to load homepage articles', error)
    articles = []
  }
  if (articles.length === 0) {
    return { leadArticle: null, secondaryArticles: [], listArticles: [] }
  }
  const [leadArticle, ...rest] = articles
  return {
    leadArticle,
    secondaryArticles: rest.slice(0, 6),
    listArticles: rest.slice(6),
  }
}

export async function getArticlesByCategory(
  category: string
): Promise<Article[]> {
  return fetchArticles(category)
}

export async function getPublishedSlugs(): Promise<ArticleSlug[]> {
  const res = await fetch(`${apiBaseUrl()}/api/articles/slugs`, {
    next: { revalidate: 60 },
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch article slugs: ${res.status}`)
  }
  return res.json()
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
