export type FixedRateLineQueueOptions = {
  intervalMs: number
  maxLinesPerTick: number
  onDrain: (lines: string[]) => void
}

export type FixedRateLineQueue = {
  start: () => void
  stop: () => void
  push: (...lines: string[]) => void
  size: () => number
  isRunning: () => boolean
}

export function createFixedRateLineQueue(opts: FixedRateLineQueueOptions): FixedRateLineQueue {
  if (!Number.isFinite(opts.intervalMs) || opts.intervalMs <= 0) {
    throw new Error(`intervalMs must be a positive number, got: ${opts.intervalMs}`)
  }
  if (!Number.isFinite(opts.maxLinesPerTick) || opts.maxLinesPerTick <= 0) {
    throw new Error(`maxLinesPerTick must be a positive number, got: ${opts.maxLinesPerTick}`)
  }

  let timer: ReturnType<typeof setInterval> | null = null
  const queue: string[] = []
  let lastDrainAtMs = 0

  const drainOnce = () => {
    if (!queue.length) return
    const take = Math.min(opts.maxLinesPerTick, queue.length)
    const batch = queue.splice(0, take)
    lastDrainAtMs = Date.now()
    opts.onDrain(batch)
  }

  return {
    start: () => {
      if (timer) return
      timer = setInterval(drainOnce, opts.intervalMs)
    },
    stop: () => {
      if (!timer) return
      clearInterval(timer)
      timer = null
      queue.length = 0
    },
    push: (...lines: string[]) => {
      const wasEmpty = queue.length === 0
      for (const line of lines) {
        if (line) queue.push(line)
      }
      // Reduce perceived latency for sparse logs: when the queue was empty and we are running,
      // render the first line immediately instead of waiting for the next interval tick.
      // IMPORTANT: keep the global cadence. Only drain immediately if we've been idle for
      // at least one full interval; otherwise the smoothing is defeated for bursty sources.
      if (timer && wasEmpty && Date.now() - lastDrainAtMs >= opts.intervalMs) drainOnce()
    },
    size: () => queue.length,
    isRunning: () => timer != null,
  }
}
