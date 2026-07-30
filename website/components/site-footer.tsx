const columns = [
  {
    title: 'Secciones',
    links: ['Política', 'Economía', 'Clima', 'Tecnología', 'Sociedad', 'Cultura'],
  },
  {
    title: 'Ojo Crítico',
    links: ['Quiénes somos', 'Nuestro método', 'Código ético', 'Contacto'],
  },
  {
    title: 'Apoyo',
    links: ['Donar', 'Hazte socio', 'Transparencia', 'Newsletter'],
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
              Noticias curadas, verificadas y sin sesgo. Financiado por sus
              lectores.
            </p>
          </div>

          {columns.map((column) => (
            <div key={column.title}>
              <h3 className="font-sans text-xs font-semibold uppercase tracking-widest text-foreground">
                {column.title}
              </h3>
              <ul className="mt-4 space-y-2.5 font-sans text-sm">
                {column.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-muted-foreground transition-colors hover:text-primary"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-foreground/15 pt-6 font-sans text-xs text-muted-foreground sm:flex-row">
          <p>© {new Date().getFullYear()} Ojo Crítico. Todos los derechos reservados.</p>
          <div className="flex gap-4">
            <a href="#" className="transition-colors hover:text-primary">
              Privacidad
            </a>
            <a href="#" className="transition-colors hover:text-primary">
              Términos
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
