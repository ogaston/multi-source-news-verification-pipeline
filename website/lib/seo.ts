import type { Article } from '@/lib/articles'

export const SITE_NAME = 'Ojo Crítico'
export const SITE_DESCRIPTION =
  'Noticias dominicanas curadas, verificadas y presentadas con contexto, pluralidad y transparencia.'
export const DEFAULT_SOCIAL_IMAGE = '/placeholder-logo.png'

export function siteUrl(): URL {
  const configured = process.env.WEBSITE_URL || 'http://localhost:7003'
  return new URL(configured.endsWith('/') ? configured : `${configured}/`)
}

export function absoluteUrl(path: string): string {
  return new URL(path.replace(/^\//, ''), siteUrl()).toString()
}

export function metaDescription(value: string, fallback = SITE_DESCRIPTION): string {
  const normalized = (value || fallback).replace(/\s+/g, ' ').trim()
  if (normalized.length <= 160) return normalized
  return `${normalized.slice(0, 157).trimEnd()}…`
}

/** Prefer same-origin /media paths so next/image can optimize via website rewrite. */
export function mediaSrc(image?: string | null, fallback = '/placeholder.svg'): string {
  if (!image) return fallback
  if (image.startsWith('/media/')) return image
  try {
    const url = new URL(image)
    if (url.pathname.startsWith('/media/')) return url.pathname
  } catch {
    // not an absolute URL
  }
  return image
}

export function articleImage(article: Article): string {
  const image = mediaSrc(article.image, DEFAULT_SOCIAL_IMAGE)
  if (/^https?:\/\//i.test(image)) return image
  return absoluteUrl(image)
}

export function articlePublishedAt(article: Article): string {
  if (article.publishedAt) return article.publishedAt
  const match = article.date.match(
    /^(\d{1,2}) de ([a-záéíóú]+) de (\d{4})$/i
  )
  if (!match) return article.date
  const months: Record<string, number> = {
    enero: 0,
    febrero: 1,
    marzo: 2,
    abril: 3,
    mayo: 4,
    junio: 5,
    julio: 6,
    agosto: 7,
    septiembre: 8,
    octubre: 9,
    noviembre: 10,
    diciembre: 11,
  }
  const month = months[match[2].toLowerCase()]
  if (month === undefined) return article.date
  return new Date(Date.UTC(Number(match[3]), month, Number(match[1]))).toISOString()
}

export function formatArticleDate(article: Article): string {
  const iso = articlePublishedAt(article)
  const parsed = Date.parse(iso)
  if (Number.isNaN(parsed)) return article.date
  return new Date(parsed).toLocaleDateString('es-DO', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export function articlePath(slug: string): string {
  return `/articulo/${encodeURIComponent(slug)}`
}
