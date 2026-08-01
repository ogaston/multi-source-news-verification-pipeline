export const SECTIONS = [
  { slug: 'politica', name: 'Política' },
  { slug: 'economia', name: 'Economía' },
  { slug: 'clima', name: 'Clima' },
  { slug: 'tecnologia', name: 'Tecnología' },
  { slug: 'sociedad', name: 'Sociedad' },
  { slug: 'cultura', name: 'Cultura' },
] as const

export type SectionSlug = (typeof SECTIONS)[number]['slug']

export function getSection(slug: string) {
  return SECTIONS.find((section) => section.slug === slug)
}

export function getSectionByName(name: string) {
  return SECTIONS.find((section) => section.name === name)
}

export function categorySlug(name: string) {
  return name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export function sectionHref(slug: SectionSlug) {
  return `/seccion/${slug}`
}
