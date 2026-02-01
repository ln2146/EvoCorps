import { describe, expect, it, vi } from 'vitest'

import { createEventSourceLogStream, createFetchReplayLogStream } from './logStream'

describe('createEventSourceLogStream', () => {
  it('subscribes and forwards message events, and closes on stop', () => {
    const close = vi.fn()
    const created: { url: string; es: any }[] = []

    const factory = (url: string) => {
      const es: any = { onmessage: null, onopen: null, onerror: null, close }
      created.push({ url, es })
      return es
    }

    const stream = createEventSourceLogStream('/api/sse', { eventSourceFactory: factory as any })
    const handler = vi.fn()
    const unsub = stream.subscribe(handler)

    stream.start()
    expect(created.length).toBe(1)
    expect(created[0].url).toBe('/api/sse')

    created[0].es.onopen?.()
    expect(handler).toHaveBeenCalledWith('INFO: 已连接流程日志流')

    created[0].es.onmessage({ data: 'line-1' })
    expect(handler).toHaveBeenCalledWith('line-1')

    unsub()
    created[0].es.onmessage({ data: 'line-2' })
    expect(handler).toHaveBeenCalledTimes(2)

    stream.stop()
    expect(close).toHaveBeenCalledTimes(1)
  })
})

describe('createFetchReplayLogStream', () => {
  it('fetches a replay file and emits lines over time', async () => {
    vi.useFakeTimers()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      text: vi.fn().mockResolvedValue('l1\nl2\nl3\n'),
    })
    ;(globalThis as any).fetch = fetchMock

    const stream = createFetchReplayLogStream({ url: '/workflow/replay.log', delayMs: 1000 })
    const handler = vi.fn()
    stream.subscribe(handler)

    stream.start()

    // Let the async fetch chain resolve.
    await Promise.resolve()
    await Promise.resolve()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    // UI should get an immediate status line so toggling "enable" feels responsive.
    expect(handler).toHaveBeenCalledWith('INFO: 正在加载回放日志...')
    expect(handler).toHaveBeenCalledWith('INFO: 回放开始')
    expect(handler).toHaveBeenCalledWith('l1')

    vi.advanceTimersByTime(1000)
    expect(handler).toHaveBeenCalledWith('l2')

    vi.advanceTimersByTime(1000)
    expect(handler).toHaveBeenCalledWith('l3')

    const callsAfter = handler.mock.calls.length
    vi.advanceTimersByTime(5000)
    expect(handler.mock.calls.length).toBe(callsAfter)

    vi.useRealTimers()
  })

  it('emits an explicit error line when fetch fails', async () => {
    vi.useFakeTimers()

    const fetchMock = vi.fn().mockRejectedValue(new Error('network down'))
    ;(globalThis as any).fetch = fetchMock

    const stream = createFetchReplayLogStream({ url: '/workflow/replay.log', delayMs: 10 })
    const handler = vi.fn()
    stream.subscribe(handler)

    stream.start()

    await Promise.resolve()
    await Promise.resolve()

    // Should still emit a status line first.
    expect(String(handler.mock.calls[0][0])).toContain('INFO:')
    expect(handler.mock.calls.some((c) => String(c[0]).includes('ERROR:'))).toBe(true)

    vi.useRealTimers()
  })
})
