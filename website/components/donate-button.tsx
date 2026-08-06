'use client'

import dynamic from 'next/dynamic'
import { useState, type ReactNode } from 'react'

const DonateDialog = dynamic(
  () => import('./donate-dialog').then((mod) => mod.DonateDialog),
  { ssr: false }
)

type DonateButtonProps = {
  className?: string
  'aria-label'?: string
  children: ReactNode
}

export function DonateButton({
  className,
  'aria-label': ariaLabel,
  children,
}: Readonly<DonateButtonProps>) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={className}
        aria-label={ariaLabel}
      >
        {children}
      </button>
      {open ? <DonateDialog open={open} onOpenChange={setOpen} /> : null}
    </>
  )
}
