import type { Metadata } from 'next'
import { StaticPage } from '@/components/static-page'
import { CONTACT_EMAIL } from '@/lib/seo'

export const metadata: Metadata = {
  title: 'Contacto',
  description:
    'Contacta a Ojo Crítico para enviar comentarios, correcciones o propuestas.',
  alternates: { canonical: '/contacto' },
}

export default function ContactoPage() {
  return (
    <StaticPage
      eyebrow="Hablemos"
      title="Contacto"
      intro="Recibimos comentarios, correcciones documentadas y propuestas que ayuden a mejorar nuestra cobertura."
    >
      <section>
        <h2>Escríbenos</h2>
        <p>
          Cuéntanos con claridad el motivo de tu mensaje e incluye enlaces o
          documentos cuando se trate de una posible corrección.
        </p>
        <p>
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-sans font-semibold text-primary underline decoration-primary/30 underline-offset-4 transition-colors hover:text-primary/75"
          >
            {CONTACT_EMAIL}
          </a>
        </p>
      </section>

      <section>
        <h2>Sobre las respuestas</h2>
        <p>
          Leemos todos los mensajes, aunque no siempre podemos responder de
          inmediato. Las solicitudes editoriales se evalúan con independencia y
          no garantizan publicación ni cambios en una noticia.
        </p>
      </section>
    </StaticPage>
  )
}
