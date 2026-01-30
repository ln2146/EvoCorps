import { describe, expect, it, vi } from 'vitest'

import { createEventSourceLogStream } from './logStream'

describe('createEventSourceLogStream', () => {
  it('subscribes and forwards message events, and closes on stop', () => {
    const close = vi.fn()
    const created: { url: string; es: any }[] = []

    const factory = (url: string) => {
      const es: any = { onmessage: null, close }
      created.push({ url, es })
      return es
    }

    const stream = createEventSourceLogStream('/api/sse', { eventSourceFactory: factory as any })
    const handler = vi.fn()
    const unsub = stream.subscribe(handler)

    stream.start()
    expect(created.length).toBe(1)
    expect(created[0].url).toBe('/api/sse')

    created[0].es.onmessage({ data: 'line-1' })
    expect(handler).toHaveBeenCalledWith('line-1')

    unsub()
    created[0].es.onmessage({ data: 'line-2' })
    expect(handler).toHaveBeenCalledTimes(1)

    stream.stop()
    expect(close).toHaveBeenCalledTimes(1)
  })
})

