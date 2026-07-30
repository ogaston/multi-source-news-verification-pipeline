import type { Article } from '@/lib/articles'
import { ArticleSources } from '@/components/article-sources'
import { ConfidenceBadge } from '@/components/confidence-badge'

export function ArticleDetail({ article }: { article: Article }) {
  return (
    <article>
      <div className="text-center">
        <span className="font-sans text-xs uppercase tracking-widest text-primary">
          {article.category}
        </span>
        <h1 className="mt-3 text-balance font-display text-3xl font-bold leading-tight text-foreground sm:text-4xl md:text-5xl">
          {article.title}
        </h1>

        <div className="mt-5 flex flex-wrap items-center justify-center gap-3 font-sans text-xs uppercase tracking-widest text-muted-foreground">
          <span>{article.date}</span>
          <span aria-hidden>·</span>
          <ConfidenceBadge article={article} />
          <span aria-hidden>·</span>
          <span>{article.readTime} de lectura</span>
        </div>
      </div>

      {article.image && (
        <figure className="mt-8">
          <img
            src={article.image}
            alt={article.imageAlt || article.title}
            className="aspect-[16/9] w-full object-cover"
          />
          {article.imageCaption && (
            <figcaption className="mt-2 text-center font-sans text-xs text-muted-foreground">
              {article.imageCaption}
            </figcaption>
          )}
        </figure>
      )}

      <p className="mt-8 text-pretty text-lg leading-relaxed text-foreground/85">
        {article.summary}
      </p>

      <div className="mt-8 space-y-5 text-pretty text-base leading-relaxed text-foreground/85 sm:text-lg">
        {article.body.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>

      <ArticleSources
        sources={article.sources}
        description={article.perspectives}
      />
    </article>
  )
}
