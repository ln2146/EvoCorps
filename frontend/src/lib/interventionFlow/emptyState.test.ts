import { describe, expect, it } from 'vitest'

import { isPreRunEmptyState } from './emptyState'

describe('isPreRunEmptyState', () => {
  it('is true when enabled, role is idle, and no lines yet', () => {
    expect(isPreRunEmptyState({ enabled: true, status: 'idle', linesCount: 0 })).toBe(true)
  })

  it('is false when disabled', () => {
    expect(isPreRunEmptyState({ enabled: false, status: 'idle', linesCount: 0 })).toBe(false)
  })

  it('is false once role is running', () => {
    expect(isPreRunEmptyState({ enabled: true, status: 'running', linesCount: 0 })).toBe(false)
  })

  it('is false once any lines exist', () => {
    expect(isPreRunEmptyState({ enabled: true, status: 'idle', linesCount: 1 })).toBe(false)
  })
})
