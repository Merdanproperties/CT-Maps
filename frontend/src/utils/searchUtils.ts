/**
 * Normalize search input for API use: trim and collapse runs of whitespace to a single space.
 * Use before passing to /api/search and /api/autocomplete to avoid duplicate requests
 * when the user types trailing/leading spaces or multiple spaces.
 */
export function normalizeSearchQuery(q: string): string {
  return q.trim().replace(/\s+/g, ' ')
}
