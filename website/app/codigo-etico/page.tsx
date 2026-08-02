import type { Metadata } from 'next'
import { StaticPage } from '@/components/static-page'

export const metadata: Metadata = {
  title: 'Código ético',
  description:
    'Los principios editoriales que orientan el trabajo de Ojo Crítico.',
  alternates: { canonical: '/codigo-etico' },
}

export default function CodigoEticoPage() {
  return (
    <StaticPage
      eyebrow="Principios editoriales"
      title="Código ético"
      intro="Nuestra credibilidad depende de explicar cómo trabajamos, reconocer nuestros límites y corregir con transparencia."
    >
      <section>
        <h2>Independencia</h2>
        <p>
          No editamos noticias para favorecer partidos, gobiernos, empresas ni
          grupos de interés. Las decisiones editoriales responden a la relevancia
          pública y a la solidez de la evidencia.
        </p>
      </section>

      <section>
        <h2>Rigor y atribución</h2>
        <p>
          Distinguimos hechos, análisis y declaraciones. Atribuimos la
          información a sus fuentes, evitamos presentar rumores como certezas y
          damos contexto cuando una afirmación puede resultar engañosa por sí
          sola.
        </p>
      </section>

      <section>
        <h2>Pluralidad sin falsa equivalencia</h2>
        <p>
          Incorporamos perspectivas relevantes y contrastamos versiones, pero no
          tratamos como equivalentes una afirmación respaldada por evidencia y
          otra que carece de ella.
        </p>
      </section>

      <section>
        <h2>Tecnología responsable</h2>
        <p>
          La inteligencia artificial apoya la clasificación, comparación,
          verificación y redacción. No reemplaza nuestros criterios editoriales:
          exigimos trazabilidad de fuentes, controles de calidad y revisión de
          resultados.
        </p>
      </section>

      <section>
        <h2>Correcciones</h2>
        <p>
          Si encontramos un error material, lo corregimos con prontitud. Las
          observaciones documentadas de lectores y fuentes son bienvenidas y se
          evalúan con el mismo estándar aplicado a la publicación original.
        </p>
      </section>

      <section>
        <h2>Transparencia financiera</h2>
        <p>
          Buscamos sostener Ojo Crítico con el apoyo de sus lectores. Ninguna
          contribución compra cobertura, modifica conclusiones ni concede acceso
          editorial preferente.
        </p>
      </section>
    </StaticPage>
  )
}
