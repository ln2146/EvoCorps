export type LogLineHandler = (line: string) => void
export type Unsubscribe = () => void

export interface LogStream {
  subscribe: (handler: LogLineHandler) => Unsubscribe
  start: () => void
  stop: () => void
}

export function createFetchReplayLogStream(opts: {
  url: string
  delayMs: number
}): LogStream {
  const handlers = new Set<LogLineHandler>()
  let timerId: ReturnType<typeof setInterval> | null = null
  let cursor = 0
  let lines: string[] | null = null
  let stopped = true
  let abort: AbortController | null = null

  const emit = (line: string) => {
    for (const h of handlers) h(line)
  }

  const stop = () => {
    stopped = true
    if (timerId !== null) {
      clearInterval(timerId)
      timerId = null
    }
    if (abort) {
      try {
        abort.abort()
      } catch {
        // best-effort; abort may throw in some environments
      }
      abort = null
    }
    cursor = 0
    lines = null
  }

  const start = () => {
    if (!stopped) return
    stopped = false

    const delay = Math.max(0, Number.isFinite(opts.delayMs) ? opts.delayMs : 0)
    abort = typeof AbortController !== 'undefined' ? new AbortController() : null

    // Immediate, user-visible feedback so "enable" doesn't feel like it did nothing.
    emit('INFO: 正在加载回放日志...')

    // Load the whole replay file once, then emit it gradually to mimic streaming.
    void (async () => {
      try {
        const res = await fetch(opts.url, abort ? { signal: abort.signal } : undefined)
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ${res.statusText}`)
        }
        const text = await res.text()
        if (stopped) return

        lines = text.split(/\r?\n/).filter((l) => l.length > 0)
        if (!lines.length) {
          emit('ERROR: 回放日志为空或无法解析。')
          stop()
          return
        }

        emit('INFO: 回放开始')

        // Emit the first line immediately for responsiveness.
        emit(lines[0])
        cursor = 1

        if (cursor >= lines.length) {
          stop()
          return
        }

        timerId = setInterval(() => {
          if (stopped || !lines) {
            stop()
            return
          }

          const next = lines[cursor]
          if (!next) {
            stop()
            return
          }

          cursor += 1
          emit(next)

          if (cursor >= lines.length) {
            stop()
          }
        }, delay)
      } catch (e) {
        if (stopped) return
        const msg = e instanceof Error ? e.message : String(e)
        emit(`ERROR: 无法加载回放日志：${msg}`)
        stop()
      }
    })()
  }

  const subscribe = (handler: LogLineHandler) => {
    handlers.add(handler)
    return () => handlers.delete(handler)
  }

  return { subscribe, start, stop }
}

export function createSimulatedLogStream(opts: {
  lines: string[]
  intervalMs: number
}): LogStream {
  const handlers = new Set<LogLineHandler>()
  let timerId: ReturnType<typeof setInterval> | null = null
  let cursor = 0

  const start = () => {
    if (timerId !== null) return
    timerId = setInterval(() => {
      const nextLine = opts.lines[cursor]
      if (!nextLine) {
        stop()
        return
      }
      cursor += 1
      for (const h of handlers) h(nextLine)
    }, opts.intervalMs)
  }

  const stop = () => {
    if (timerId === null) return
    clearInterval(timerId)
    timerId = null
    cursor = 0
  }

  const subscribe = (handler: LogLineHandler) => {
    handlers.add(handler)
    return () => handlers.delete(handler)
  }

  return { subscribe, start, stop }
}

// Real backend integration seam. Expects each SSE `message` event to carry a single log line in `event.data`.
export function createEventSourceLogStream(
  url: string,
  opts?: {
    eventSourceFactory?: (url: string) => EventSource
  },
): LogStream {
  const handlers = new Set<LogLineHandler>()
  let es: EventSource | null = null
  let emittedOpen = false
  let emittedError = false

  const emit = (line: string) => {
    for (const h of handlers) h(line)
  }

  const start = () => {
    if (es) return
    const factory = opts?.eventSourceFactory ?? ((u: string) => {
      if (typeof EventSource === 'undefined') {
        throw new Error('EventSource is not available in this environment')
      }
      return new EventSource(u)
    })

    es = factory(url)
    // Give the UI an immediate, visible signal that the stream is connecting/connected,
    // and surface connection issues instead of "silently doing nothing".
    ;(es as any).onopen = () => {
      if (emittedOpen) return
      emittedOpen = true
      emit('INFO: 已连接流程日志流')
    }
    ;(es as any).onerror = () => {
      if (emittedError) return
      emittedError = true
      emit('ERROR: 流程日志流连接失败或已断开')
      // Close so a future `start()` call can create a fresh connection.
      try {
        es?.close()
      } finally {
        es = null
      }
    }
    es.onmessage = (event) => {
      for (const h of handlers) h(event.data)
    }
  }

  const stop = () => {
    if (!es) return
    es.close()
    es = null
    emittedOpen = false
    emittedError = false
  }

  const subscribe = (handler: LogLineHandler) => {
    handlers.add(handler)
    return () => handlers.delete(handler)
  }

  return { subscribe, start, stop }
}
