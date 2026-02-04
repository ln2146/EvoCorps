import { describe, expect, it, vi } from 'vitest'

import { createFixedRateLineQueue } from './logRenderQueue'

describe('createFixedRateLineQueue', () => {
  it('drains lines at a fixed rate (one line per tick)', () => {
    vi.useFakeTimers()
    try {
      const drained: string[] = []
      const q = createFixedRateLineQueue({
        intervalMs: 50,
        maxLinesPerTick: 1,
        onDrain: (lines) => drained.push(...lines),
      })

      q.push('a')
      q.push('b')
      q.push('c')

      q.start()
      expect(drained).toEqual([])

      vi.advanceTimersByTime(49)
      expect(drained).toEqual([])

      vi.advanceTimersByTime(1)
      expect(drained).toEqual(['a'])

      vi.advanceTimersByTime(50)
      expect(drained).toEqual(['a', 'b'])

      vi.advanceTimersByTime(50)
      expect(drained).toEqual(['a', 'b', 'c'])

      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not call onDrain when the queue is empty', () => {
    vi.useFakeTimers()
    try {
      const onDrain = vi.fn()
      const q = createFixedRateLineQueue({
        intervalMs: 50,
        maxLinesPerTick: 1,
        onDrain,
      })
      q.start()

      vi.advanceTimersByTime(500)
      expect(onDrain).not.toHaveBeenCalled()
      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })

  it('drains immediately on push when running and the queue was empty', () => {
    vi.useFakeTimers()
    try {
      const drained: string[] = []
      const q = createFixedRateLineQueue({
        intervalMs: 100,
        maxLinesPerTick: 1,
        onDrain: (lines) => drained.push(...lines),
      })
      q.start()

      q.push('first')
      expect(drained).toEqual(['first'])

      q.push('second')
      expect(drained).toEqual(['first'])

      vi.advanceTimersByTime(100)
      expect(drained).toEqual(['first', 'second'])

      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })
})
