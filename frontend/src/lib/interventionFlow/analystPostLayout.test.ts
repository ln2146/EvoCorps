import { describe, expect, it } from 'vitest'

import { getAnalystPostCardClassName, getAnalystPostBodyClassName } from './analystPostLayout'

describe('analystPostLayout', () => {
  it('keeps the post card at a fixed height (half-ish) so the rest of the panel keeps space', () => {
    const cls = getAnalystPostCardClassName()
    expect(cls).toContain('h-28')
    expect(cls).toContain('flex')
    expect(cls).toContain('flex-col')
    expect(cls).toContain('min-h-0')
  })

  it('switches body behavior between clamped preview and scrollable full text', () => {
    expect(getAnalystPostBodyClassName(false)).toContain('line-clamp-3')
    expect(getAnalystPostBodyClassName(true)).toContain('overflow-y-auto')
  })
})

