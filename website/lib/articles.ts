export type ArticleSource = {
  name: string
  url: string
}

export type ConfidenceLevel = 'alta' | 'media' | 'baja' | 'en_revision'

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
  en_revision: 'En revisión',
}

export type Article = {
  slug: string
  category: string
  title: string
  summary: string
  body: string[]
  image?: string
  imageAlt?: string
  imageCaption?: string
  readTime: string
  confidence: ConfidenceLevel
  sources: ArticleSource[]
  date: string
  publishedAt: string
  author: string
  perspectives?: string[]
  clusterSize?: number
}

export type ArticleSlug = {
  slug: string
  category: string
  categorySlug: string
  publishedAt: string
}
