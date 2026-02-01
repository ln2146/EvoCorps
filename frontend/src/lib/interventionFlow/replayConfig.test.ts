import { describe, expect, it } from 'vitest'

import { DEFAULT_WORKFLOW_REPLAY_DELAY_MS, getOpinionBalanceLogStreamUrl, shouldCallOpinionBalanceProcessApi } from './replayConfig'

describe('replayConfig', () => {
  it('uses a slower default replay delay for readable stage progression', () => {
    expect(DEFAULT_WORKFLOW_REPLAY_DELAY_MS).toBe(800)
  })

  it('builds the real stream url when replay is disabled', () => {
    const url = getOpinionBalanceLogStreamUrl({ replay: false, replayFile: 'workflow_20260130.log', delayMs: 40 })
    expect(url).toContain('/api/opinion-balance/logs/stream')
    expect(url).toContain('source=workflow')
    expect(url).toContain('follow_latest=true')
    expect(url).not.toContain('replay=1')
  })

  it('builds the replay url when replay is enabled', () => {
    const url = getOpinionBalanceLogStreamUrl({ replay: true, replayFile: 'workflow_20260130.log', delayMs: 40 })
    expect(url).toContain('replay=1')
    expect(url).toContain('file=workflow_20260130.log')
    expect(url).toContain('delay_ms=40')
    expect(url).toContain('follow_latest=false')
  })

  it('clamps replay delay to the backend max', () => {
    const url = getOpinionBalanceLogStreamUrl({ replay: true, replayFile: 'workflow_20260130.log', delayMs: 999999 })
    expect(url).toContain('delay_ms=10000')
  })

  it('skips process start/stop calls in replay mode', () => {
    expect(shouldCallOpinionBalanceProcessApi(false)).toBe(true)
    expect(shouldCallOpinionBalanceProcessApi(true)).toBe(false)
  })
})
