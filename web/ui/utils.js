// Shared module-level utilities for the web/ui bundle.
//
// This module exists so that several sibling UI modules can share small, pure
// helpers without introducing a circular dependency. Notably ``escapeHtml`` is
// used by both ``results.js`` and ``challenges.js``; keeping it in its own file
// breaks the results.js <-> challenges.js cycle that would otherwise result
// from importing it directly from either of them.

export function escapeHtml(value) {
  if (value === null || value === undefined) return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

export default {}
