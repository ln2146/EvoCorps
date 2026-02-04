import { describe, expect, it } from 'vitest'

import { parsePostContent } from './postContent'

describe('parsePostContent', () => {
  it('extracts tag + title from a [TAG] first line and builds a compact preview', () => {
    const raw = '[NEWS] Renewable energy installations reach new capacity milestones nationwide: According to official reports, renewable energy installations reach new capacity milestones nationwide.'
    const parsed = parsePostContent(raw, { previewChars: 80 })

    expect(parsed.tag).toBe('NEWS')
    expect(parsed.title).toMatch(/^Renewable energy installations reach new capacity milestones nationwide/i)
    expect(parsed.full).toBe(raw)
    // Preview should not duplicate the tag prefix when tag is extracted.
    expect(parsed.preview.startsWith('[NEWS]')).toBe(false)
    expect(parsed.preview.length).toBeLessThanOrEqual(81)
  })

  it('handles multi-line content and keeps full text unchanged', () => {
    const raw = '[NEWS] Title line\n\nBody line 1\nBody line 2'
    const parsed = parsePostContent(raw, { previewChars: 999 })

    expect(parsed.tag).toBe('NEWS')
    expect(parsed.title).toBe('Title line')
    expect(parsed.full).toBe(raw)
    expect(parsed.preview).toContain('Body line 1')
  })

  it('returns empty preview for blank input', () => {
    const parsed = parsePostContent('')
    expect(parsed.tag).toBeUndefined()
    expect(parsed.title).toBeUndefined()
    expect(parsed.preview).toBe('')
    expect(parsed.full).toBe('')
  })

  it('removes [OFFICIAL EXPLANATION] block and trailing analysis prompt from preview', () => {
    const raw = [
      '[NEWS] Headline',
      '',
      "[OFFICIAL EXPLANATION] : The island's Ministry of Health reported positive cases in a vulnerable setting, like a residential and nursing home.",
      'Please analyze the opinion tendency of this post and whether intervention is needed.',
    ].join('\n')

    const parsed = parsePostContent(raw, { previewChars: 500 })
    expect(parsed.preview).toContain('Headline')
    expect(parsed.preview).not.toContain('OFFICIAL EXPLANATION')
    expect(parsed.preview).not.toContain('Please analyze the opinion tendency')
    expect(parsed.full).not.toContain('OFFICIAL EXPLANATION')
    expect(parsed.full).not.toContain('Please analyze the opinion tendency')
  })
})
