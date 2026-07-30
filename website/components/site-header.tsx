'use client'

import { useState } from 'react'
import { Heart, Menu, X } from 'lucide-react'
import { DonateDialog } from './donate-dialog'

const sections = [
  'Política',
  'Economía',
  'Clima',
  'Tecnología',
  'Sociedad',
  'Cultura',
]

export function SiteHeader() {
  const [donateOpen, setDonateOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const today = new Date().toLocaleDateString('es-ES', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <header className="border-b border-foreground/15 bg-background">
      {/* Top utility bar */}
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-2 text-xs uppercase tracking-widest text-muted-foreground font-sans">
        <span className="hidden sm:inline first-letter:uppercase">{today}</span>
        <span className="sm:hidden">Edición diaria</span>
        <div className="flex items-center gap-4">
          <span className="hidden md:inline">Edición Nacional</span>
          <button
            type="button"
            onClick={() => setDonateOpen(true)}
            className="flex items-center gap-1.5 text-primary transition-colors hover:text-primary/80"
            aria-label="Donar"
          >
            <Heart className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Donar</span>
          </button>
        </div>
      </div>

      {/* Masthead */}
      <div className="border-y border-foreground/15">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="flex h-9 w-9 items-center justify-center text-foreground md:hidden"
            aria-label="Abrir menú"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <div className="flex flex-1 flex-col items-center text-center">
            <span className="text-[0.65rem] uppercase tracking-[0.35em] text-muted-foreground font-sans">
              Sin manipulación · Sin sesgo
            </span>
            <h1 className="font-display text-4xl font-bold leading-none tracking-tight text-foreground sm:text-5xl md:text-6xl">
              Ojo Crítico
            </h1>
          </div>

          {/* Balances the mobile menu button so the brand stays centered */}
          <div className="h-9 w-9 md:hidden" aria-hidden />
        </div>
      </div>

      {/* Section navigation */}
      <nav
        className={`border-b border-foreground/15 ${menuOpen ? 'block' : 'hidden'} md:block`}
        aria-label="Secciones"
      >
        <ul className="mx-auto flex max-w-6xl flex-col gap-0 px-4 font-sans text-sm md:flex-row md:items-center md:justify-center md:gap-8 md:py-2.5">
          {sections.map((section) => (
            <li key={section} className="border-b border-foreground/10 md:border-0">
              <a
                href="#"
                className="block py-3 uppercase tracking-wide text-foreground/80 transition-colors hover:text-primary md:py-0"
              >
                {section}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <DonateDialog open={donateOpen} onOpenChange={setDonateOpen} />
    </header>
  )
}
