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

export type TimestampSmoothLineQueueOptions = {
  minDelayMs: number
  maxDelayMs: number
  timeScale: number
  smoothingAlpha: number
  delayOverrideMs?: (line: string) => number | null | undefined
  onDrain: (lines: string[]) => void
}

export type TimestampSmoothLineQueue = {
  start: () => void
  stop: () => void
  push: (...lines: string[]) => void
  size: () => number
  isRunning: () => boolean
}

export function parseLogPrefixTimestampMs(line: string): number | null {
  const m = line.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})\b/)
  if (!m) return null

  const year = Number(m[1])
  const month = Number(m[2])
  const day = Number(m[3])
  const hour = Number(m[4])
  const minute = Number(m[5])
  const second = Number(m[6])
  const ms = Number(m[7])

  if (
    !Number.isFinite(year) ||
    !Number.isFinite(month) ||
    !Number.isFinite(day) ||
    !Number.isFinite(hour) ||
    !Number.isFinite(minute) ||
    !Number.isFinite(second) ||
    !Number.isFinite(ms)
  ) {
    return null
  }

  // Treat log timestamps as local time. Absolute epoch does not matter; only deltas do.
  const d = new Date(year, month - 1, day, hour, minute, second, ms)
  const t = d.getTime()
  return Number.isFinite(t) ? t : null
}

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n))
}

export function createTimestampSmoothLineQueue(opts: TimestampSmoothLineQueueOptions): TimestampSmoothLineQueue {
  if (!Number.isFinite(opts.minDelayMs) || opts.minDelayMs < 0) {
    throw new Error(`minDelayMs must be a non-negative number, got: ${opts.minDelayMs}`)
  }
  if (!Number.isFinite(opts.maxDelayMs) || opts.maxDelayMs < opts.minDelayMs) {
    throw new Error(`maxDelayMs must be >= minDelayMs, got: ${opts.maxDelayMs}`)
  }
  if (!Number.isFinite(opts.timeScale) || opts.timeScale <= 0) {
    throw new Error(`timeScale must be a positive number, got: ${opts.timeScale}`)
  }
  if (!Number.isFinite(opts.smoothingAlpha) || opts.smoothingAlpha < 0 || opts.smoothingAlpha > 1) {
    throw new Error(`smoothingAlpha must be within [0,1], got: ${opts.smoothingAlpha}`)
  }

  let timer: ReturnType<typeof setTimeout> | null = null
  const queue: string[] = []
  let lastTsMs: number | null = null
  let lastDelayMs: number | null = null

  const scheduleNext = () => {
    if (timer || !queue.length) return

    const next = queue[0]
    const ts = parseLogPrefixTimestampMs(next)

    const deltaMsRaw =
      ts != null && lastTsMs != null && ts >= lastTsMs ? Math.max(0, ts - lastTsMs) : null

    const override = opts.delayOverrideMs?.(next)
    const baseDelayMsRaw = override != null ? override : (Number.isFinite(deltaMsRaw) ? deltaMsRaw * opts.timeScale : opts.minDelayMs)
    const baseDelayMs = clamp(baseDelayMsRaw, opts.minDelayMs, opts.maxDelayMs)

    const smoothedDelayMs =
      lastDelayMs == null ? baseDelayMs : opts.smoothingAlpha * baseDelayMs + (1 - opts.smoothingAlpha) * lastDelayMs

    const delayMs = clamp(smoothedDelayMs, opts.minDelayMs, opts.maxDelayMs)

    // Low-latency first paint: when starting, do not delay the first line.
    const isFirst = lastTsMs == null && lastDelayMs == null
    timer = setTimeout(
      () => {
        timer = null
        const line = queue.shift()
        if (line) opts.onDrain([line])
        if (ts != null) lastTsMs = ts
        lastDelayMs = delayMs
        scheduleNext()
      },
      isFirst ? 0 : Math.max(0, Math.floor(delayMs)),
    )
  }

  return {
    start: () => {
      scheduleNext()
    },
    stop: () => {
      if (timer) clearTimeout(timer)
      timer = null
      queue.length = 0
      lastTsMs = null
      lastDelayMs = null
    },
    push: (...lines: string[]) => {
      for (const line of lines) {
        if (line) queue.push(line)
      }
      scheduleNext()
    },
    size: () => queue.length,
    isRunning: () => timer != null,
  }
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
