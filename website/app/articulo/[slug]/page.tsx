import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { SiteHeader } from '@/components/site-header'
import { ArticleDetail } from '@/components/article-detail'
import { ArticleJsonLd } from '@/components/article-json-ld'
import { SupportCta } from '@/components/support-cta'
import { SiteFooter } from '@/components/site-footer'
import { getArticleBySlug } from '@/lib/api'
import { ARTICLE_REVALIDATE_SECONDS } from '@/lib/cache'
import {
  articleImage,
  articlePath,
  articlePublishedAt,
  metaDescription,
  SITE_NAME,
} from '@/lib/seo'

type PageProps = {
  params: Promise<{ slug: string }>
}

export const revalidate = ARTICLE_REVALIDATE_SECONDS
export const dynamicParams = true

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params
  const article = await getArticleBySlug(slug)
  if (!article) {
    return { title: 'Artículo no encontrado — Ojo Crítico' }
  }
  const description = metaDescription(article.summary)
  const path = articlePath(article.slug)
  const image = articleImage(article)
  const publishedTime = articlePublishedAt(article)
  return {
    title: article.title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: 'article',
      locale: 'es_DO',
      siteName: SITE_NAME,
      title: article.title,
      description,
      url: path,
      images: [{ url: image, alt: article.imageAlt || article.title }],
      publishedTime,
      authors: [article.author || SITE_NAME],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.title,
      description,
      images: [image],
    },
  }
}

export default async function ArticlePage({ params }: PageProps) {
  const { slug } = await params
  const article = await getArticleBySlug(slug)
  if (!article) notFound()

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      <main>
        <ArticleJsonLd article={article} />
        <section className="mx-auto max-w-3xl px-4 py-10">
          <ArticleDetail article={article} />
        </section>

        <SupportCta />
      </main>

      <SiteFooter />
    </div>
  )
}
