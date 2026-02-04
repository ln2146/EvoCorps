import { describe, expect, it, vi } from 'vitest'

import { createFixedRateLineQueue, createTimestampSmoothLineQueue } from './logRenderQueue'

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

describe('createTimestampSmoothLineQueue', () => {
  it('drains lines based on timestamp deltas (scaled + clamped)', () => {
    vi.useFakeTimers()
    try {
      const drained: string[] = []
      const q = createTimestampSmoothLineQueue({
        minDelayMs: 50,
        maxDelayMs: 200,
        timeScale: 0.1,
        smoothingAlpha: 1,
        onDrain: (lines) => drained.push(...lines),
      })

      q.push('2026-02-04 10:00:00,000 - INFO - a')
      q.push('2026-02-04 10:00:02,000 - INFO - b') // delta=2000ms -> scaled=200 -> clamped=200
      q.push('2026-02-04 10:00:02,050 - INFO - c') // delta=50ms -> scaled=5 -> clamped=50

      q.start()
      expect(drained).toEqual([])

      // First line is rendered immediately (0ms) when starting.
      vi.advanceTimersByTime(0)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a'])

      vi.advanceTimersByTime(199)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a'])

      vi.advanceTimersByTime(1)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a', '2026-02-04 10:00:02,000 - INFO - b'])

      vi.advanceTimersByTime(49)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a', '2026-02-04 10:00:02,000 - INFO - b'])

      vi.advanceTimersByTime(1)
      expect(drained).toEqual([
        '2026-02-04 10:00:00,000 - INFO - a',
        '2026-02-04 10:00:02,000 - INFO - b',
        '2026-02-04 10:00:02,050 - INFO - c',
      ])

      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })

  it('uses minDelayMs when a line has no parseable timestamp', () => {
    vi.useFakeTimers()
    try {
      const drained: string[] = []
      const q = createTimestampSmoothLineQueue({
        minDelayMs: 100,
        maxDelayMs: 500,
        timeScale: 1,
        smoothingAlpha: 1,
        onDrain: (lines) => drained.push(...lines),
      })

      q.push('2026-02-04 10:00:00,000 - INFO - a')
      q.push('no-ts')
      q.push('2026-02-04 10:00:00,050 - INFO - c')

      q.start()

      // First line is rendered immediately (0ms) when starting.
      vi.advanceTimersByTime(0)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a'])

      vi.advanceTimersByTime(99)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a'])

      vi.advanceTimersByTime(1)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a', 'no-ts'])

      // Next delta should be computed from the last parseable timestamp (a -> c = 50ms), but clamped to minDelayMs.
      vi.advanceTimersByTime(100)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - a', 'no-ts', '2026-02-04 10:00:00,050 - INFO - c'])

      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })

  it('supports delayOverrideMs for stage-based pacing', () => {
    vi.useFakeTimers()
    try {
      const drained: string[] = []
      const q = createTimestampSmoothLineQueue({
        minDelayMs: 0,
        maxDelayMs: 10_000,
        timeScale: 1,
        smoothingAlpha: 1,
        delayOverrideMs: (line) => (line.includes('fast') ? 100 : 500),
        onDrain: (lines) => drained.push(...lines),
      })

      q.push('2026-02-04 10:00:00,000 - INFO - fast')
      q.push('2026-02-04 10:00:01,000 - INFO - slow')
      q.start()

      vi.advanceTimersByTime(0)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - fast'])

      vi.advanceTimersByTime(499)
      expect(drained).toEqual(['2026-02-04 10:00:00,000 - INFO - fast'])

      vi.advanceTimersByTime(1)
      expect(drained).toEqual([
        '2026-02-04 10:00:00,000 - INFO - fast',
        '2026-02-04 10:00:01,000 - INFO - slow',
      ])

      q.stop()
    } finally {
      vi.useRealTimers()
    }
  })
})
