import { describe, expect, it } from 'vitest'

import { getInterventionFlowPanelClassName, getLeaderCommentsContainerClassName } from './panelLayout'

describe('panelLayout', () => {
  it('forces the panel to clip overflow so it never visually grows', () => {
    const cls = getInterventionFlowPanelClassName()
    expect(cls).toContain('h-[640px]')
    expect(cls).toContain('overflow-hidden')
    expect(cls).toContain('min-w-0')
    expect(cls).toContain('w-full')
    expect(cls).toContain('flex')
    expect(cls).toContain('flex-col')
  })

  it('makes leader comments scroll internally', () => {
    const cls = getLeaderCommentsContainerClassName()
    expect(cls).toContain('max-h')
    expect(cls).toContain('overflow-y-scroll')
    expect(cls).toContain('overflow-x-hidden')
  })
})
