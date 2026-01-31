import { describe, expect, it } from 'vitest'

import { shouldShowDetailStatusLabel } from './statusLabel'

describe('shouldShowDetailStatusLabel', () => {
  it('hides IDLE', () => {
    expect(shouldShowDetailStatusLabel('idle')).toBe(false)
  })

  it('shows non-idle statuses', () => {
    expect(shouldShowDetailStatusLabel('running')).toBe(true)
    expect(shouldShowDetailStatusLabel('done')).toBe(true)
    expect(shouldShowDetailStatusLabel('error')).toBe(true)
  })
})

