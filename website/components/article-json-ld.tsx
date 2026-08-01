import type { Article } from '@/lib/articles'
import { categorySlug } from '@/lib/categories'
import {
  absoluteUrl,
  articleImage,
  articlePath,
  articlePublishedAt,
  SITE_NAME,
} from '@/lib/seo'

function jsonLd(value: unknown) {
  return JSON.stringify(value).replace(/</g, '\\u003c')
}

export function ArticleJsonLd({ article }: { article: Article }) {
  const url = absoluteUrl(articlePath(article.slug))
  const publishedAt = articlePublishedAt(article)
  const graph = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'NewsArticle',
        '@id': `${url}#article`,
        mainEntityOfPage: url,
        headline: article.title,
        description: article.summary,
        image: [articleImage(article)],
        datePublished: publishedAt,
        dateModified: publishedAt,
        author: {
          '@type': 'Organization',
          name: article.author || SITE_NAME,
          url: absoluteUrl('/'),
        },
        publisher: {
          '@type': 'Organization',
          name: SITE_NAME,
          url: absoluteUrl('/'),
          logo: {
            '@type': 'ImageObject',
            url: absoluteUrl('/apple-icon.png'),
          },
        },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Inicio',
            item: absoluteUrl('/'),
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: article.category,
            item: absoluteUrl(`/seccion/${categorySlug(article.category)}`),
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: article.title,
            item: url,
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: jsonLd(graph) }}
    />
  )
}
