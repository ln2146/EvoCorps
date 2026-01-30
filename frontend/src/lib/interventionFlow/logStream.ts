export type LogLineHandler = (line: string) => void
export type Unsubscribe = () => void

export interface LogStream {
  subscribe: (handler: LogLineHandler) => Unsubscribe
  start: () => void
  stop: () => void
}

export function createSimulatedLogStream(opts: {
  lines: string[]
  intervalMs: number
}): LogStream {
  const handlers = new Set<LogLineHandler>()
  let timerId: number | null = null
  let cursor = 0

  const start = () => {
    if (timerId !== null) return
    timerId = window.setInterval(() => {
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
    window.clearInterval(timerId)
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

  const start = () => {
    if (es) return
    const factory = opts?.eventSourceFactory ?? ((u: string) => {
      if (typeof EventSource === 'undefined') {
        throw new Error('EventSource is not available in this environment')
      }
      return new EventSource(u)
    })

    es = factory(url)
    es.onmessage = (event) => {
      for (const h of handlers) h(event.data)
    }
  }

  const stop = () => {
    if (!es) return
    es.close()
    es = null
  }

  const subscribe = (handler: LogLineHandler) => {
    handlers.add(handler)
    return () => handlers.delete(handler)
  }

  return { subscribe, start, stop }
}
