import Image from 'next/image'
import Link from 'next/link'
import type { Article } from '@/lib/articles'
import { ConfidenceBadge } from '@/components/confidence-badge'
import { articlePath, mediaSrc } from '@/lib/seo'

export function LeadStory({ article }: { article: Article }) {
  return (
    <article className="grid gap-8 md:grid-cols-2 md:gap-10">
      <div className="order-2 flex flex-col justify-center md:order-1">
        <span className="font-sans text-xs uppercase tracking-widest text-primary">
          {article.category}
        </span>
        <h2 className="mt-3 text-balance font-display text-3xl font-bold leading-tight text-foreground sm:text-4xl md:text-5xl">
          <Link
            href={articlePath(article.slug)}
            className="transition-colors hover:text-primary"
          >
            {article.title}
          </Link>
        </h2>
        <p className="mt-4 text-pretty text-lg leading-relaxed text-foreground/80">
          {article.summary}
        </p>

        {article.perspectives && (
          <div className="mt-5 border-l-2 border-primary/40 pl-4">
            <p className="font-sans text-xs uppercase tracking-widest text-muted-foreground">
              Cómo lo cuentan las partes
            </p>
            <ul className="mt-2 space-y-1 text-sm text-foreground/75">
              {article.perspectives.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 flex items-center gap-4 font-sans text-xs uppercase tracking-widest text-muted-foreground">
          <ConfidenceBadge article={article} />
          <span>·</span>
          <span>{article.readTime} de lectura</span>
        </div>
      </div>

      <div className="order-1 md:order-2">
        <Image
          src={mediaSrc(article.image)}
          alt={article.imageAlt || article.title}
          width={1200}
          height={900}
          priority
          sizes="(max-width: 767px) 100vw, 50vw"
          className="aspect-[4/3] w-full object-cover"
        />
        {article.imageCaption && (
          <p className="mt-2 font-sans text-xs text-muted-foreground">
            {article.imageCaption}
          </p>
        )}
      </div>
    </article>
  )
}
