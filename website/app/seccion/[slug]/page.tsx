import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { SiteFooter } from '@/components/site-footer'
import { SiteHeader } from '@/components/site-header'
import { getArticlesByCategory } from '@/lib/api'
import type { Article } from '@/lib/articles'
import { HOME_REVALIDATE_SECONDS } from '@/lib/cache'
import { getSection, SECTIONS, sectionHref } from '@/lib/categories'
import {
  articlePath,
  articlePublishedAt,
  formatArticleDate,
  metaDescription,
} from '@/lib/seo'

type PageProps = {
  params: Promise<{ slug: string }>
}

export const revalidate = HOME_REVALIDATE_SECONDS
export const dynamicParams = false

export function generateStaticParams() {
  return SECTIONS.map(({ slug }) => ({ slug }))
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params
  const section = getSection(slug)
  if (!section) return { title: 'Sección no encontrada' }
  const description = metaDescription(
    `Últimas noticias verificadas de ${section.name.toLowerCase()} en República Dominicana. Contexto, fuentes y transparencia editorial.`
  )
  const path = sectionHref(section.slug)
  return {
    title: section.name,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: 'website',
      locale: 'es_DO',
      title: `${section.name} — Ojo Crítico`,
      description,
      url: path,
    },
    twitter: {
      card: 'summary_large_image',
      title: `${section.name} — Ojo Crítico`,
      description,
    },
  }
}

export default async function SectionPage({ params }: PageProps) {
  const { slug } = await params
  const section = getSection(slug)
  if (!section) notFound()

  let articles: Article[] = []
  try {
    articles = await getArticlesByCategory(section.slug)
  } catch (error) {
    console.error(`Unable to load section ${section.slug}`, error)
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <p className="font-sans text-xs uppercase tracking-widest text-primary">
          Sección
        </p>
        <h1 className="mt-2 font-display text-4xl font-bold sm:text-5xl">
          {section.name}
        </h1>
        <div className="mt-8 divide-y divide-foreground/15 border-t border-foreground/15">
          {articles.length ? (
            articles.map((article) => (
              <article key={article.slug} className="py-7">
                <h2 className="text-balance font-display text-2xl font-bold sm:text-3xl">
                  <Link
                    href={articlePath(article.slug)}
                    className="transition-colors hover:text-primary"
                  >
                    {article.title}
                  </Link>
                </h2>
                <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/75">
                  {article.summary}
                </p>
                <time
                  dateTime={articlePublishedAt(article)}
                  className="mt-3 block font-sans text-xs uppercase tracking-wider text-muted-foreground"
                >
                  {formatArticleDate(article)}
                </time>
              </article>
            ))
          ) : (
            <p className="py-8 text-foreground/70">
              No hay artículos publicados en esta sección.
            </p>
          )}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
