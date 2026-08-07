import type { Article, ArticleSlug } from '@/lib/articles'
import {
  ARTICLE_REVALIDATE_SECONDS,
  HOME_REVALIDATE_SECONDS,
} from '@/lib/cache'
import { splitHomeArticles, type HomeData } from '@/lib/home'

export type { HomeData }

function apiBaseUrl(): string {
  const base = process.env.WEBSITE_API_URL?.replace(/\/$/, '')
  if (!base) {
    throw new Error('WEBSITE_API_URL is not set')
  }
  return base
}

function apiHeaders(): HeadersInit {
  const key = process.env.WEBSITE_API_KEY?.trim()
  if (!key) {
    throw new Error('WEBSITE_API_KEY is not set')
  }
  return { Authorization: `Bearer ${key}` }
}

async function fetchArticles(category?: string): Promise<Article[]> {
  const query = category
    ? `?${new URLSearchParams({ category }).toString()}`
    : ''
  const res = await fetch(`${apiBaseUrl()}/api/articles${query}`, {
    headers: apiHeaders(),
    next: { revalidate: HOME_REVALIDATE_SECONDS },
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
  return splitHomeArticles(articles)
}

export async function getArticlesByCategory(
  category: string
): Promise<Article[]> {
  return fetchArticles(category)
}

export async function getPublishedSlugs(): Promise<ArticleSlug[]> {
  const res = await fetch(`${apiBaseUrl()}/api/articles/slugs`, {
    headers: apiHeaders(),
    next: { revalidate: HOME_REVALIDATE_SECONDS },
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
    {
      headers: apiHeaders(),
      next: { revalidate: ARTICLE_REVALIDATE_SECONDS },
    }
  )
  if (res.status === 404) {
    return null
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch article: ${res.status}`)
  }
  return res.json()
}
