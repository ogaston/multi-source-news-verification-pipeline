import type { ReactNode } from 'react'
import { SiteFooter } from '@/components/site-footer'
import { SiteHeader } from '@/components/site-header'

type StaticPageProps = {
  eyebrow: string
  title: string
  intro: string
  children: ReactNode
}

export function StaticPage({
  eyebrow,
  title,
  intro,
  children,
}: Readonly<StaticPageProps>) {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main>
        <article className="mx-auto max-w-3xl px-4 py-14 sm:py-20">
          <header className="border-b border-foreground/15 pb-10">
            <p className="font-sans text-xs font-semibold uppercase tracking-[0.25em] text-primary">
              {eyebrow}
            </p>
            <h1 className="mt-3 text-balance font-display text-4xl font-bold leading-tight text-foreground sm:text-6xl">
              {title}
            </h1>
            <p className="mt-6 max-w-2xl text-pretty text-xl leading-relaxed text-foreground/75">
              {intro}
            </p>
          </header>
          <div className="space-y-10 py-10 text-lg leading-relaxed text-foreground/85 [&_h2]:mb-3 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-bold [&_h2]:text-foreground [&_p+p]:mt-4">
            {children}
          </div>
        </article>
      </main>
      <SiteFooter />
    </div>
  )
}
