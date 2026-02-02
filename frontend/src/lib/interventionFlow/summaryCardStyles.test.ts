import { describe, expect, it } from 'vitest'

import { getSummaryCardClassName } from './summaryCardStyles'

describe('getSummaryCardClassName', () => {
  it('keeps Strategist strategy + style cards on one line', () => {
    expect(getSummaryCardClassName('Strategist', 0)).toContain('whitespace-nowrap')
    expect(getSummaryCardClassName('Strategist', 1)).toContain('whitespace-nowrap')
  })

  it('uses wrapped layout for other cards', () => {
    expect(getSummaryCardClassName('Strategist', 2)).toContain('whitespace-pre-wrap')
    expect(getSummaryCardClassName('Leader', 0)).toContain('whitespace-pre-wrap')
  })
})

