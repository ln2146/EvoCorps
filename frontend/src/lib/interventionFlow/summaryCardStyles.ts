import type { Role } from './logRouter'

const BASE =
  'text-xs text-slate-700 px-3 py-2 rounded-xl bg-white/60 border border-white/40 leading-snug max-h-16'

export function getSummaryCardClassName(role: Role, idx: number) {
  // Strategist strategy names can be long (e.g. "Community Partnership"). Keep it on one line so the
  // 2x2 cards stay visually stable; users can still see full text via the title tooltip.
  //
  // Also keep "风格：diplomatic" on a single line to avoid the adjective wrapping into a second line
  // in narrow 2-column layouts (which makes the row height jump).
  if (role === 'Strategist' && (idx === 0 || idx === 1)) {
    return [BASE, 'whitespace-nowrap truncate overflow-hidden'].join(' ')
  }

  return [BASE, 'whitespace-pre-wrap break-words overflow-y-auto'].join(' ')
}
