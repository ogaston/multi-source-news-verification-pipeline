import { SiteHeader } from '@/components/site-header'
import { LeadStory } from '@/components/lead-story'
import { SecondaryStories, StoryList } from '@/components/story-sections'
import { SupportCta } from '@/components/support-cta'
import { SiteFooter } from '@/components/site-footer'
import { getHomeData } from '@/lib/api'

export default async function HomePage() {
  const { leadArticle, secondaryArticles, listArticles } = await getHomeData()

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      <main>
        {/* Lead */}
        <section className="mx-auto max-w-6xl px-4 py-10">
          <LeadStory article={leadArticle} />
        </section>

        <div className="mx-auto max-w-6xl px-4">
          <hr className="border-foreground/15" />
        </div>

        {/* Secondary + list */}
        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-10 lg:grid-cols-[2fr_1fr]">
          <SecondaryStories articles={secondaryArticles} />
          <StoryList articles={listArticles} />
        </section>

        <SupportCta />
      </main>

      <SiteFooter />
    </div>
  )
}
