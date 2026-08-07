/**
 * Fetch Data Cache TTLs for `next: { revalidate }`.
 * Route segment `export const revalidate` must stay numeric literals in page
 * files (Next.js cannot analyze imported segment config).
 */
export const HOME_REVALIDATE_SECONDS = 10800 // 3 hours
export const ARTICLE_REVALIDATE_SECONDS = 86400 // 1 day
