import type { Role } from './logRouter'

export function getSummaryGridClassName(role: Role) {
  // Strategist: keep a 2x2 layout; give the strategy card a bit more room so long names don't truncate too early.
  if (role === 'Strategist') {
    return 'mt-3 grid gap-2 grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]'
  }
  return 'mt-3 grid grid-cols-2 gap-2'
}
