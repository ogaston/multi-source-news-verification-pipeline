import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { SiteHeader } from '@/components/site-header'
import { ArticleDetail } from '@/components/article-detail'
import { SupportCta } from '@/components/support-cta'
import { SiteFooter } from '@/components/site-footer'
import { getArticleBySlug } from '@/lib/api'

type PageProps = {
  params: Promise<{ slug: string }>
}

export const dynamic = 'force-dynamic'

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params
  const article = await getArticleBySlug(slug)
  if (!article) {
    return { title: 'Artículo no encontrado — Ojo Crítico' }
  }
  return {
    title: `${article.title} — Ojo Crítico`,
    description: article.summary,
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
        <section className="mx-auto max-w-3xl px-4 py-10">
          <ArticleDetail article={article} />
        </section>

        <SupportCta />
      </main>

      <SiteFooter />
    </div>
  )
}
