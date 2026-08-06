import { Heart } from 'lucide-react'
import { DonateButton } from './donate-button'

export function SupportCta() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-14">
      <div className="border border-foreground/15 bg-foreground px-6 py-12 text-center text-background">
        <span className="font-sans text-xs uppercase tracking-[0.3em] text-background/70">
          Independencia
        </span>
        <h2 className="mx-auto mt-3 max-w-2xl text-balance font-display text-3xl font-bold sm:text-4xl">
          El periodismo sin sesgo lo pagan sus lectores
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-pretty leading-relaxed text-background/80">
          Ojo Crítico no tiene publicidad ni accionistas. Tu donación es lo que
          mantiene cada noticia libre de intereses.
        </p>
        <DonateButton className="mt-7 inline-flex items-center gap-2 bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-md active:translate-y-0 active:scale-[0.98] active:bg-primary/80 active:shadow-sm font-sans">
          <Heart className="h-4 w-4" />
          Hacer una donación
        </DonateButton>
      </div>
    </section>
  )
}
