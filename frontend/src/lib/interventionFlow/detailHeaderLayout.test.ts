import { describe, expect, it } from 'vitest'

import { getLiveBadgeClassName, getStageHeaderContainerClassName, getStageHeaderTextClassName } from './detailHeaderLayout'

describe('detailHeaderLayout', () => {
  it('keeps the live badge on one line', () => {
    expect(getLiveBadgeClassName()).toContain('whitespace-nowrap')
    expect(getLiveBadgeClassName()).toContain('inline-flex')
  })

  it('uses a readable stage header text size without truncation', () => {
    expect(getStageHeaderTextClassName()).toContain('text-sm')
    expect(getStageHeaderTextClassName()).toContain('whitespace-normal')
    expect(getStageHeaderTextClassName()).not.toContain('truncate')
  })

  it('keeps stage header width stable', () => {
    expect(getStageHeaderContainerClassName()).toMatch(/w-\[|w-/)
    expect(getStageHeaderContainerClassName()).toContain('shrink-0')
  })
})
