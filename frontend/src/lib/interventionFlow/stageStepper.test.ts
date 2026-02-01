import { describe, expect, it } from 'vitest'

import { buildStageStepperModel } from './stageStepper'

describe('stageStepper', () => {
  it('maps current/max to labels and totals', () => {
    const model = buildStageStepperModel('Analyst', { current: 2, max: 2, order: [0, 1, 2] })
    expect(model.currentLabel).toBe('情绪度')
    expect(model.total).toBe(6)
    expect(model.seenCount).toBe(3)
    expect(model.currentPos).toBe(2)
    expect(model.maxPos).toBe(2)
  })

  it('clamps out-of-range current/max', () => {
    const model = buildStageStepperModel('Amplifier', { current: 99, max: 99, order: [0, 1, 3] })
    // Unknown current/max should not break; when not in order, treat as unknown.
    expect(model.currentPos).toBe(-1)
    expect(model.maxPos).toBe(-1)
    expect(model.currentLabel).toBe('')
  })

  it('treats -1 as unknown (no label)', () => {
    const model = buildStageStepperModel('Leader', { current: -1, max: -1, order: [] })
    expect(model.currentPos).toBe(-1)
    expect(model.maxPos).toBe(-1)
    expect(model.currentLabel).toBe('')
  })
})
