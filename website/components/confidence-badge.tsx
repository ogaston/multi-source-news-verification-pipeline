import { ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import {
  CONFIDENCE_LABELS,
  type Article,
  type ConfidenceLevel,
} from '@/lib/articles'

const ICONS: Record<
  ConfidenceLevel,
  typeof ShieldCheck
> = {
  alta: ShieldCheck,
  media: ShieldCheck,
  baja: ShieldAlert,
  en_revision: ShieldQuestion,
}

const TONES: Record<ConfidenceLevel, string> = {
  alta: 'text-primary',
  media: 'text-foreground/70',
  baja: 'text-foreground/55',
  en_revision: 'text-foreground/55',
}

type ConfidenceBadgeProps = {
  article: Article
  size?: 'sm' | 'md'
}

export function ConfidenceBadge({
  article,
  size = 'md',
}: ConfidenceBadgeProps) {
  const Icon = ICONS[article.confidence]
  const iconClass = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'

  return (
    <span
      className={`flex items-center gap-1.5 ${TONES[article.confidence]}`}
      title={`Confianza ${CONFIDENCE_LABELS[article.confidence].toLowerCase()}`}
    >
      <Icon className={iconClass} aria-hidden />
      <span>
        {CONFIDENCE_LABELS[article.confidence]}
        <span className="text-muted-foreground">
          {' '}
          · {article.sources.length}{' '}
          {article.sources.length === 1 ? 'fuente' : 'fuentes'}
        </span>
      </span>
    </span>
  )
}
