'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowDown } from 'lucide-react'
import { ConfidenceBadge } from '@/components/confidence-badge'
import type { Article } from '@/lib/articles'
import { articlePath } from '@/lib/seo'

export function MoreStories({
  articles,
}: Readonly<{ articles: Article[] }>) {
  const [expanded, setExpanded] = useState(false)

  if (articles.length === 0) return null

  return (
    <section className="mx-auto max-w-6xl px-4 pb-10">
      {!expanded && (
        <div className="flex justify-center border-t border-foreground/15 pt-10">
          <button
            type="button"
            aria-expanded={false}
            aria-controls="more-stories"
            onClick={() => setExpanded(true)}
            className="inline-flex min-h-11 items-center gap-2 border border-foreground px-6 py-3 font-sans text-sm font-semibold uppercase tracking-widest text-foreground transition-colors hover:bg-foreground hover:text-background"
          >
            Ver más
            <ArrowDown className="h-4 w-4" aria-hidden />
          </button>
        </div>
      )}

      {expanded && (
        <div
          id="more-stories"
          className="animate-in fade-in slide-in-from-bottom-2 duration-500"
        >
          <div className="flex items-end justify-between gap-6 border-b-2 border-foreground pb-3">
            <div>
              <p className="font-sans text-xs uppercase tracking-widest text-primary">
                La edición completa
              </p>
              <h2 className="mt-1 font-display text-3xl font-bold text-foreground">
                Más cobertura
              </h2>
            </div>
            <span className="font-sans text-sm text-muted-foreground">
              {articles.length} {articles.length === 1 ? 'noticia' : 'noticias'}
            </span>
          </div>

          <ul className="grid divide-y divide-foreground/15 md:grid-cols-2 md:gap-x-10 md:[&>li:nth-child(2)]:border-t md:[&>li:nth-child(even)]:border-l md:[&>li:nth-child(even)]:pl-10">
            {articles.map((article) => (
              <li key={article.slug}>
                <article className="py-6">
                  <span className="font-sans text-xs uppercase tracking-widest text-primary">
                    {article.category}
                  </span>
                  <h3 className="mt-2 text-balance font-display text-2xl font-bold leading-snug text-foreground">
                    <Link
                      href={articlePath(article.slug)}
                      className="transition-colors hover:text-primary"
                    >
                      {article.title}
                    </Link>
                  </h3>
                  <p className="mt-2 text-pretty leading-relaxed text-foreground/75">
                    {article.summary}
                  </p>
                  <div className="mt-3 flex items-center gap-3 font-sans text-[0.7rem] uppercase tracking-widest text-muted-foreground">
                    <ConfidenceBadge article={article} size="sm" />
                    <span>·</span>
                    <span>{article.readTime}</span>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
