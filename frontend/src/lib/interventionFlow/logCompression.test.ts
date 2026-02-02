import { describe, expect, it } from 'vitest'

import { compressLogLine, isNoiseLogLine, pushCompressedLine } from './logCompression'

describe('isNoiseLogLine', () => {
  it('filters infrastructure noise', () => {
    expect(isNoiseLogLine('HTTP Request: POST https://x/v1/chat/completions "HTTP/1.1 200 OK"')).toBe(true)
    expect(isNoiseLogLine('Request URL: https://en.wikipedia.org/w/api.php?...')).toBe(true)
    expect(isNoiseLogLine('Wikipedia: language=en, user_agent=...')).toBe(true)
    expect(isNoiseLogLine('📊 Cache status: embedding=2, FAISS viewpoints=6, FAISS keywords=6')).toBe(true)
  })
})

describe('compressLogLine', () => {
  it('shortens leader comment body while preserving intent', () => {
    const raw = '💬 👑 Leader comment 1 on post post-18e9eb: This post raises serious allegations that warrant careful examination...'
    expect(compressLogLine(raw)).toBe('💬 👑 Leader comment posted (1)')
  })

  it('shortens echo per-agent comments into a single category line', () => {
    const raw = "💬 🤖 Echo-12 (positive_david_180) (deepseek-chat) commented: That's a thoughtful analysis..."
    expect(compressLogLine(raw)).toBe('💬 🤖 Amplifier commented')
  })
})

describe('pushCompressedLine', () => {
  it('aggregates consecutive echo comments and caps at 10 lines', () => {
    const lines: string[] = []
    let next = lines
    for (let i = 0; i < 12; i++) {
      next = pushCompressedLine(next, '💬 🤖 Amplifier commented', { maxLines: 10 })
    }
    // Should be deduplicated rather than 12 separate lines.
    expect(next.length).toBeLessThanOrEqual(10)
    expect(next[0].startsWith('💬 🤖 Amplifier commented')).toBe(true)
    expect(next[0]).not.toContain('×')
  })
})
