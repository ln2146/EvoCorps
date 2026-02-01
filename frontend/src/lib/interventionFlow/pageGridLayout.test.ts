import { describe, expect, it } from 'vitest'

import { getDynamicDemoGridClassName } from './pageGridLayout'

describe('pageGridLayout', () => {
  it('uses minmax(0, ...) tracks so long unbroken text cannot widen columns', () => {
    const cls = getDynamicDemoGridClassName()
    expect(cls).toContain('xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_minmax(0,1fr)]')
  })
})

