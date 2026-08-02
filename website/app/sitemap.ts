import type { MetadataRoute } from 'next'
import { getPublishedSlugs } from '@/lib/api'
import { SECTIONS, sectionHref } from '@/lib/categories'
import { absoluteUrl, articlePath } from '@/lib/seo'

export const revalidate = 60

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const editorialRoutes = ['/metodo', '/codigo-etico', '/contacto']
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: absoluteUrl('/'),
      changeFrequency: 'hourly',
      priority: 1,
    },
    ...SECTIONS.map((section) => ({
      url: absoluteUrl(sectionHref(section.slug)),
      changeFrequency: 'daily' as const,
      priority: 0.7,
    })),
    ...editorialRoutes.map((path) => ({
      url: absoluteUrl(path),
      changeFrequency: 'monthly' as const,
      priority: 0.5,
    })),
  ]

  try {
    const articles = await getPublishedSlugs()
    return [
      ...staticRoutes,
      ...articles.map((article) => ({
        url: absoluteUrl(articlePath(article.slug)),
        lastModified: article.publishedAt || undefined,
        changeFrequency: 'weekly' as const,
        priority: 0.8,
      })),
    ]
  } catch (error) {
    console.warn('Article API unavailable while generating sitemap', error)
    return staticRoutes
  }
}
