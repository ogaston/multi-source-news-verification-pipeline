'use client'

import { useEffect, useState } from 'react'
import { Heart, X } from 'lucide-react'

const amounts = ['5 €', '15 €', '30 €', '50 €']

export function DonateDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [selected, setSelected] = useState('15 €')

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onOpenChange])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="donate-title"
    >
      <button
        type="button"
        aria-label="Cerrar"
        className="absolute inset-0 bg-foreground/60"
        onClick={() => onOpenChange(false)}
      />

      <div className="relative w-full max-w-md border border-foreground/15 bg-background p-8 shadow-2xl">
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="absolute right-4 top-4 text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Cerrar"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex flex-col items-center text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Heart className="h-6 w-6" />
          </span>
          <h2
            id="donate-title"
            className="mt-4 font-display text-2xl font-bold text-foreground"
          >
            Apoya el periodismo sin sesgo
          </h2>
          <p className="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground">
            Ojo Crítico se financia con aportaciones de sus lectores. Sin
            publicidad ni intereses de por medio, tu apoyo mantiene cada noticia
            independiente y verificada.
          </p>
        </div>

        <div className="mt-6 grid grid-cols-4 gap-2 font-sans">
          {amounts.map((amount) => (
            <button
              key={amount}
              type="button"
              onClick={() => setSelected(amount)}
              className={`border py-2.5 text-sm font-medium transition-colors ${
                selected === amount
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-foreground/20 text-foreground hover:border-primary'
              }`}
            >
              {amount}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="mt-4 flex w-full items-center justify-center gap-2 bg-primary py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 font-sans"
        >
          <Heart className="h-4 w-4" />
          Donar {selected}
        </button>

        <p className="mt-3 text-center text-xs text-muted-foreground font-sans">
          Demostración visual · aún no se procesan pagos reales
        </p>
      </div>
    </div>
  )
}
