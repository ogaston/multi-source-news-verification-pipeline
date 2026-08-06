import { Heart } from 'lucide-react'
import { DonateButton } from './donate-button'
import { SiteHeaderNav } from './site-header-nav'

export function SiteHeader() {
  const today = new Date().toLocaleDateString('es-ES', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <header className="border-b border-foreground/15 bg-background">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-2 text-xs uppercase tracking-widest text-muted-foreground font-sans">
        <span className="hidden sm:inline first-letter:uppercase">{today}</span>
        <span className="sm:hidden">Edición diaria</span>
        <div className="flex items-center gap-4">
          <span className="hidden md:inline">Edición Nacional</span>
          <DonateButton
            aria-label="Donar"
            className="flex min-h-11 min-w-11 items-center justify-center gap-1.5 text-primary transition-all duration-200 hover:scale-105 hover:text-primary/80 active:scale-95 active:text-primary/70"
          >
            <Heart className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Donar</span>
          </DonateButton>
        </div>
      </div>

      <SiteHeaderNav />
    </header>
  )
}
