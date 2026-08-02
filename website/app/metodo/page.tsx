import type { Metadata } from 'next'
import { StaticPage } from '@/components/static-page'

export const metadata: Metadata = {
  title: 'Nuestro método',
  description:
    'Cómo Ojo Crítico selecciona, contrasta y explica las noticias dominicanas.',
  alternates: { canonical: '/metodo' },
}

export default function MetodoPage() {
  return (
    <StaticPage
      eyebrow="Transparencia editorial"
      title="Nuestro método"
      intro="Reunimos distintas coberturas de un mismo hecho para ofrecer una lectura más completa, verificable y libre del enfoque de un solo medio."
    >
      <section>
        <h2>Reunimos la cobertura</h2>
        <p>
          Recopilamos noticias publicadas por medios dominicanos y agrupamos las
          que informan sobre un mismo acontecimiento. Así podemos comparar qué
          destaca cada fuente, detectar coincidencias y reconocer diferencias.
        </p>
      </section>

      <section>
        <h2>Identificamos lo relevante</h2>
        <p>
          Ordenamos los temas según la amplitud de su cobertura y su importancia
          pública. La cantidad de publicaciones es una señal, no una garantía:
          también evaluamos el alcance del hecho y su impacto para el país.
        </p>
      </section>

      <section>
        <h2>Contrastamos antes de publicar</h2>
        <p>
          Verificamos las afirmaciones centrales con las fuentes disponibles,
          dando prioridad a documentos oficiales, datos primarios y referencias
          confiables. Cuando la evidencia es limitada o contradictoria, lo
          indicamos con claridad.
        </p>
      </section>

      <section>
        <h2>Explicamos con contexto</h2>
        <p>
          Redactamos una síntesis que separa los hechos comprobables de las
          interpretaciones y enlaza las publicaciones consultadas. Usamos
          herramientas de inteligencia artificial para apoyar este proceso,
          bajo criterios editoriales definidos y revisables.
        </p>
      </section>
    </StaticPage>
  )
}
