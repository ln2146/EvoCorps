import { describe, expect, it } from 'vitest'

import { getSummaryCardClassName } from './summaryCardStyles'

describe('getSummaryCardClassName', () => {
  it('keeps Strategist strategy card single-line', () => {
    const cls = getSummaryCardClassName('Strategist', 0)
    expect(cls).toContain('whitespace-nowrap')
    expect(cls).toContain('truncate')
    expect(cls).toContain('overflow-hidden')
    expect(cls).not.toContain('whitespace-pre-wrap')
  })

  it('uses wrapped style for other cards', () => {
    expect(getSummaryCardClassName('Strategist', 1)).toContain('whitespace-pre-wrap')
    expect(getSummaryCardClassName('Analyst', 0)).toContain('whitespace-pre-wrap')
  })
})

