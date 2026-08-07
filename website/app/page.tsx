import type { Metadata } from 'next'
import { SiteHeader } from '@/components/site-header'
import { LeadStory } from '@/components/lead-story'
import { SecondaryStories, StoryList } from '@/components/story-sections'
import { MoreStories } from '@/components/more-stories'
import { SupportCta } from '@/components/support-cta'
import { SiteFooter } from '@/components/site-footer'
import { getHomeData } from '@/lib/api'
import { HOME_REVALIDATE_SECONDS } from '@/lib/cache'
import {
  DEFAULT_SOCIAL_IMAGE,
  SITE_DESCRIPTION,
  SITE_NAME,
} from '@/lib/seo'

export const revalidate = HOME_REVALIDATE_SECONDS

export const metadata: Metadata = {
  title: { absolute: `${SITE_NAME} — Noticias curadas y sin sesgo` },
  description: SITE_DESCRIPTION,
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    locale: 'es_DO',
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    url: '/',
    images: [{ url: DEFAULT_SOCIAL_IMAGE, alt: SITE_NAME }],
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: [DEFAULT_SOCIAL_IMAGE],
  },
}

export default async function HomePage() {
  const { leadArticle, secondaryArticles, listArticles, moreArticles } =
    await getHomeData()

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      <main>
        <h1 className="sr-only">
          Noticias dominicanas verificadas por Ojo Crítico
        </h1>
        <section className="mx-auto max-w-6xl px-4 py-10">
          {leadArticle ? (
            <LeadStory article={leadArticle} />
          ) : (
            <p className="font-sans text-foreground/70">
              No hay artículos publicados por el momento.
            </p>
          )}
        </section>

        {(secondaryArticles.length > 0 || listArticles.length > 0) && (
          <>
            <div className="mx-auto max-w-6xl px-4">
              <hr className="border-foreground/15" />
            </div>

            <section className="mx-auto grid max-w-6xl gap-10 px-4 py-10 lg:grid-cols-[2fr_1fr]">
              <SecondaryStories articles={secondaryArticles} />
              <StoryList articles={listArticles} />
            </section>
          </>
        )}

        <MoreStories articles={moreArticles} />
        <SupportCta />
      </main>

      <SiteFooter />
    </div>
  )
}
