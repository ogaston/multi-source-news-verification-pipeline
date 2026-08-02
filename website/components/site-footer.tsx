import Link from 'next/link'
import { SECTIONS, sectionHref } from '@/lib/categories'

const columns = [
  {
    title: 'Secciones',
    links: SECTIONS.map((section) => ({
      label: section.name,
      href: sectionHref(section.slug),
    })),
  },
  {
    title: 'Ojo Crítico',
    links: [
      { label: 'Nuestro método', href: '/metodo' },
      { label: 'Código ético', href: '/codigo-etico' },
      { label: 'Contacto', href: '/contacto' },
    ],
  },
  {
    title: 'Apoyo',
    links: ['Donar', 'Newsletter'].map((label) => ({ label, href: null })),
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-foreground/15 bg-background">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-10 md:grid-cols-[1.5fr_repeat(3,1fr)]">
          <div>
            <p className="font-display text-2xl font-bold text-foreground">
              Ojo Crítico
            </p>
            <p className="mt-3 max-w-xs text-pretty text-sm leading-relaxed text-muted-foreground">
              Noticias dominicanas contrastadas con múltiples fuentes,
              explicadas con contexto y transparencia.
            </p>
          </div>

          {columns.map((column) => (
            <div key={column.title}>
              <h3 className="font-sans text-xs font-semibold uppercase tracking-widest text-foreground">
                {column.title}
              </h3>
              <ul className="mt-3 font-sans text-sm">
                {column.links.map((link) => (
                  <li key={link.label} className="mb-3 last:mb-0">
                    {link.href ? (
                      <Link
                        href={link.href}
                        className="text-muted-foreground transition-colors hover:text-primary"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">{link.label}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-foreground/15 pt-6 font-sans text-xs text-muted-foreground sm:flex-row">
          <p>© {new Date().getFullYear()} Ojo Crítico. Todos los derechos reservados.</p>
          <div className="flex gap-4" aria-label="Información legal">
            <span className="py-0.5">Privacidad</span>
            <span className="py-0.5">Términos</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
