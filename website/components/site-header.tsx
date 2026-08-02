'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { Heart, Menu, X } from 'lucide-react'
import { DonateDialog } from './donate-dialog'
import { SECTIONS, sectionHref } from '@/lib/categories'

export function SiteHeader() {
  const [donateOpen, setDonateOpen] = useState(false)
  const [menuOpenAtPath, setMenuOpenAtPath] = useState<string | null>(null)
  const menuRef = useRef<HTMLElement>(null)
  const pathname = usePathname()
  const menuOpen = menuOpenAtPath === pathname

  useEffect(() => {
    if (!menuOpen) return
    const menu = menuRef.current
    const links = Array.from(
      menu?.querySelectorAll<HTMLElement>('a[href]') || []
    )
    links[0]?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpenAtPath(null)
        return
      }
      if (event.key !== 'Tab' || links.length === 0) return
      const first = links[0]
      const last = links[links.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [menuOpen])

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
            className="flex min-h-11 min-w-11 items-center justify-center gap-1.5 text-primary transition-all duration-200 hover:scale-105 hover:text-primary/80 active:scale-95 active:text-primary/70"
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
            onClick={() => setMenuOpenAtPath(menuOpen ? null : pathname)}
            className="flex h-11 w-11 items-center justify-center text-foreground md:hidden"
            aria-label={menuOpen ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={menuOpen}
            aria-controls="section-navigation"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <div className="flex flex-1 flex-col items-center text-center">
            <span className="text-[0.65rem] uppercase tracking-[0.35em] text-muted-foreground font-sans">
              Contexto · Fuentes · Transparencia
            </span>
            <Link
              href="/"
              className="font-display text-4xl font-bold leading-none tracking-tight text-foreground sm:text-5xl md:text-6xl"
            >
              Ojo Crítico
            </Link>
          </div>

          {/* Balances the mobile menu button so the brand stays centered */}
          <div className="h-11 w-11 md:hidden" aria-hidden />
        </div>
      </div>

      {/* Section navigation */}
      <nav
        id="section-navigation"
        ref={menuRef}
        className={`border-b border-foreground/15 ${menuOpen ? 'block' : 'hidden'} md:block`}
        aria-label="Secciones"
      >
        <ul className="mx-auto flex max-w-6xl flex-col gap-0 px-4 font-sans text-sm md:flex-row md:items-center md:justify-center md:gap-8 md:py-2.5">
          {SECTIONS.map((section) => (
            <li key={section.slug} className="border-b border-foreground/10 md:border-0">
              <Link
                href={sectionHref(section.slug)}
                onClick={() => setMenuOpenAtPath(null)}
                className="flex min-h-11 items-center py-3 uppercase tracking-wide text-foreground/80 transition-colors hover:text-primary md:min-h-0 md:py-0"
              >
                {section.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <DonateDialog open={donateOpen} onOpenChange={setDonateOpen} />
    </header>
  )
}
