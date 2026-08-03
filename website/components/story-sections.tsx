import Image from 'next/image'
import Link from 'next/link'
import type { Article } from '@/lib/articles'
import { ConfidenceBadge } from '@/components/confidence-badge'
import { articlePath, mediaSrc } from '@/lib/seo'

function Meta({ article }: { article: Article }) {
  return (
    <div className="mt-3 flex items-center gap-3 font-sans text-[0.7rem] uppercase tracking-widest text-muted-foreground">
      <ConfidenceBadge article={article} size="sm" />
      <span>·</span>
      <span>{article.readTime}</span>
    </div>
  )
}

export function SecondaryStories({ articles }: { articles: Article[] }) {
  return (
    <div className="grid gap-8 sm:grid-cols-2">
      {articles.map((article) => (
        <article key={article.slug} className="flex flex-col">
          {article.image ? (
            <Image
              src={mediaSrc(article.image)}
              alt={article.imageAlt || article.title}
              width={800}
              height={500}
              loading="lazy"
              quality={65}
              sizes="(max-width: 639px) 100vw, (max-width: 1023px) 50vw, 33vw"
              className="aspect-[16/10] w-full object-cover"
            />
          ) : null}
          <span className="mt-4 font-sans text-xs uppercase tracking-widest text-primary">
            {article.category}
          </span>
          <h3 className="mt-2 text-balance font-display text-2xl font-bold leading-tight text-foreground">
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
          <Meta article={article} />
        </article>
      ))}
    </div>
  )
}

export function StoryList({ articles }: { articles: Article[] }) {
  return (
    <div>
      <h2 className="border-b-2 border-foreground pb-2 font-sans text-sm font-semibold uppercase tracking-widest text-foreground">
        Más noticias
      </h2>
      <ul className="divide-y divide-foreground/15">
        {articles.map((article) => (
          <li key={article.slug}>
            <article className="py-5">
              <span className="font-sans text-xs uppercase tracking-widest text-primary">
                {article.category}
              </span>
              <h3 className="mt-1.5 text-balance font-display text-xl font-bold leading-snug text-foreground">
                <Link
                  href={articlePath(article.slug)}
                  className="transition-colors hover:text-primary"
                >
                  {article.title}
                </Link>
              </h3>
              <p className="mt-1.5 text-pretty leading-relaxed text-foreground/75">
                {article.summary}
              </p>
              <Meta article={article} />
            </article>
          </li>
        ))}
      </ul>
    </div>
  )
}
