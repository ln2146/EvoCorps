import { describe, expect, it } from 'vitest'

import { getHeatLeaderboardCardClassName, getHeatLeaderboardListClassName } from './heatLeaderboardLayout'

describe('heatLeaderboardLayout', () => {
  it('fixes the card height to align with the right intervention panel', () => {
    expect(getHeatLeaderboardCardClassName()).toContain('h-[640px]')
    expect(getHeatLeaderboardCardClassName()).toContain('flex')
    expect(getHeatLeaderboardCardClassName()).toContain('flex-col')
    expect(getHeatLeaderboardCardClassName()).toContain('min-h-0')
  })

  it('makes the list scroll inside', () => {
    const cls = getHeatLeaderboardListClassName()
    expect(cls).toContain('flex-1')
    expect(cls).toContain('overflow-y-scroll')
    expect(cls).toContain('min-h-0')
  })
})
