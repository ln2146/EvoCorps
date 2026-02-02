import type { Role } from './logRouter'

export function getSummaryGridClassName(role: Role) {
  // Strategist strategy names can be long; give the first column extra width while keeping a 2x2 layout.
  if (role === 'Strategist') {
    return 'mt-3 grid gap-2 grid-cols-[minmax(0,1.4fr)_minmax(0,0.6fr)]'
  }
  return 'mt-3 grid grid-cols-2 gap-2'
}

