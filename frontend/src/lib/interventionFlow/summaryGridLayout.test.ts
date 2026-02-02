import { describe, expect, it } from 'vitest'

import { getSummaryGridClassName } from './summaryGridLayout'

describe('getSummaryGridClassName', () => {
  it('widens Strategist first column while keeping 2 columns', () => {
    const cls = getSummaryGridClassName('Strategist')
    expect(cls).toContain('grid')
    expect(cls).toContain('grid-cols-[')
  })

  it('uses 2 equal columns for other roles', () => {
    expect(getSummaryGridClassName('Analyst')).toContain('grid-cols-2')
    expect(getSummaryGridClassName('Leader')).toContain('grid-cols-2')
  })
})

