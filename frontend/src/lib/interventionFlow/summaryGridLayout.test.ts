import { describe, expect, it } from 'vitest'

import { getSummaryGridClassName } from './summaryGridLayout'

describe('getSummaryGridClassName', () => {
  it('gives Strategist first column more room for long strategy names', () => {
    const cls = getSummaryGridClassName('Strategist')
    expect(cls).toBe('mt-3 grid gap-2 grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]')
  })

  it('uses 2 equal columns for other roles', () => {
    expect(getSummaryGridClassName('Analyst')).toContain('grid-cols-2')
    expect(getSummaryGridClassName('Leader')).toContain('grid-cols-2')
  })
})
