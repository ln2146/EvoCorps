import { describe, expect, it } from 'vitest'

import { getAnalystCombinedCardClassName, getAnalystCombinedPostBodyClassName, getAnalystCombinedStreamClassName } from './analystCombinedLayout'

describe('analystCombinedLayout', () => {
  it('uses a single scrollable card so post + milestones live together', () => {
    const cls = getAnalystCombinedCardClassName()
    expect(cls).toContain('flex-1')
    expect(cls).toContain('min-h-0')
    expect(cls).toContain('overflow-y-scroll')
  })

  it('renders full post content without an expand/collapse clamp', () => {
    const cls = getAnalystCombinedPostBodyClassName()
    expect(cls).toContain('whitespace-pre-wrap')
    expect(cls).not.toContain('line-clamp')
  })

  it('keeps the stream list as a non-scrolling wrapper', () => {
    const cls = getAnalystCombinedStreamClassName()
    expect(cls).not.toContain('overflow-y')
  })
})
