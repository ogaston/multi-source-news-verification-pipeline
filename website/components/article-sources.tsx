import { ExternalLink } from 'lucide-react'
import type { ArticleSource } from '@/lib/articles'

type ArticleSourcesProps = {
  sources: ArticleSource[]
  description?: string[]
}

export function ArticleSources({ sources, description }: ArticleSourcesProps) {
  if (sources.length === 0 && !description?.length) return null

  return (
    <section className="mt-12 border-t border-foreground/15 pt-8">
      <div className="grid gap-10 sm:grid-cols-2">
        {sources.length > 0 && (
          <div>
            <h2 className="font-sans text-xs font-semibold uppercase tracking-widest text-foreground">
              Fuentes
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Medios de los que se contrastó esta noticia. Cada enlace apunta al
              artículo original en el medio.
            </p>
            <ul className="mt-4 flex flex-col gap-2">
              {sources.map((source) => (
                <li key={source.name}>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-11 items-center gap-1.5 font-sans text-sm text-primary transition-colors hover:text-primary/80"
                  >
                    {source.name}
                    <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {description && description.length > 0 && (
          <div>
            <h2 className="font-sans text-xs font-semibold uppercase tracking-widest text-foreground">
              Cómo lo cuentan las partes
            </h2>
            <ul className="mt-4 space-y-2 text-sm leading-relaxed text-foreground/75">
              {description.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
