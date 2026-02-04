import { describe, expect, it } from 'vitest'

import { buildStageStepperModel } from './stageStepper'

describe('stageStepper', () => {
  it('maps current/max to labels and totals', () => {
    const model = buildStageStepperModel('Analyst', { current: 2, max: 2, order: [0, 1, 2] })
    expect(model.currentLabel).toBe('极端度')
    expect(model.total).toBe(6)
    expect(model.seenCount).toBe(3)
    expect(model.currentPos).toBe(2)
    expect(model.maxPos).toBe(2)
    expect(model.currentStep).toBe(3)
  })

  it('clamps out-of-range current/max', () => {
    const model = buildStageStepperModel('Amplifier', { current: 99, max: 99, order: [0, 1, 3] })
    // Unknown current/max should not break; when not in order, treat as unknown.
    expect(model.currentPos).toBe(-1)
    expect(model.maxPos).toBe(-1)
    expect(model.currentLabel).toBe('')
    expect(model.currentStep).toBe(0)
  })

  it('treats -1 as unknown (no label)', () => {
    const model = buildStageStepperModel('Leader', { current: -1, max: -1, order: [] })
    expect(model.currentPos).toBe(-1)
    expect(model.maxPos).toBe(-1)
    expect(model.currentLabel).toBe('')
    expect(model.currentStep).toBe(0)
  })

  it('uses canonical stage index for progress even when order is sparse', () => {
    const model = buildStageStepperModel('Analyst', { current: 4, max: 4, order: [0, 2, 3, 4] })
    expect(model.currentLabel).toBe('干预判定')
    // Should show step 5/6 (not 4/6) even if stage 1 is missing from order.
    expect(model.currentPos).toBe(4)
    expect(model.currentStep).toBe(5)
    expect(model.total).toBe(6)
  })
})
