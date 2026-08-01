'use client'

import { useEffect, useRef } from 'react'
import Image from 'next/image'
import { Heart, X } from 'lucide-react'

const sharedDetails = [
  { label: 'Beneficiario', value: 'Chalas Creations SRL' },
  { label: 'Banco', value: 'Scotiabank' },
]

const accounts = [
  { currency: 'USD', number: '0123456789' },
  { currency: 'DOP', number: '9876543210' },
]

export function DonateDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const focusable = () =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled])'
        ) || []
      )
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
      if (e.key !== 'Tab') return
      const elements = focusable()
      if (!elements.length) return
      const first = elements[0]
      const last = elements[elements.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    requestAnimationFrame(() => focusable()[0]?.focus())
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      previouslyFocused?.focus()
    }
  }, [open, onOpenChange])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="donate-title"
      aria-describedby="donate-description"
    >
      <button
        type="button"
        aria-label="Cerrar"
        className="absolute inset-0 bg-foreground/60"
        onClick={() => onOpenChange(false)}
      />

      <div
        ref={panelRef}
        className="relative max-h-[calc(100dvh-2rem)] w-full max-w-md overflow-y-auto border border-foreground/15 bg-background p-5 shadow-2xl sm:p-8"
      >
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="absolute right-2 top-2 flex h-11 w-11 items-center justify-center text-muted-foreground transition-colors hover:text-foreground sm:right-3 sm:top-3"
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
          <p
            id="donate-description"
            className="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground"
          >
            Ojo Crítico se financia con aportaciones de sus lectores. Sin
            publicidad ni intereses de por medio, tu apoyo mantiene cada noticia
            independiente y verificada.
          </p>
        </div>

        <div className="mt-6 border border-foreground/15 p-4 font-sans text-sm">
          <div className="flex justify-center border-b border-foreground/10 pb-4">
            <Image
              src="https://upload.wikimedia.org/wikipedia/commons/5/51/Logo_Scotiabank_%28Kanada%29.svg"
              alt="Scotiabank"
              width={200}
              height={40}
              className="h-10 w-auto"
              unoptimized
            />
          </div>

          <dl className="mt-4 space-y-3">
            {sharedDetails.map((detail) => (
              <div key={detail.label}>
                <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {detail.label}
                </dt>
                <dd className="mt-1 text-foreground">{detail.value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {accounts.map((account) => (
              <div
                key={account.currency}
                className="border border-foreground/10 bg-muted/30 p-3"
              >
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  Cuenta {account.currency}
                </p>
                <p className="mt-1 font-medium tabular-nums text-foreground">
                  {account.number}
                </p>
              </div>
            ))}
          </div>
        </div>

        <p className="mt-3 text-center text-xs text-muted-foreground font-sans">
          Datos de transferencia de demostración · cuentas pendientes de
          verificación
        </p>
      </div>
    </div>
  )
}
