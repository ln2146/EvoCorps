import { describe, expect, it } from 'vitest'

import { getRoleTabButtonClassName } from './roleTabStyles'

describe('getRoleTabButtonClassName', () => {
  it('keeps layout-affecting classes consistent between selected/unselected', () => {
    const selected = getRoleTabButtonClassName(true)
    const unselected = getRoleTabButtonClassName(false)

    // Structural: always full-width, border-box sizing, and same shadow baseline to avoid perceived width shifts.
    for (const s of [selected, unselected]) {
      expect(s).toContain('w-full')
      expect(s).toContain('box-border')
      expect(s).toContain('border')
      expect(s).toContain('shadow-sm')
      expect(s).not.toContain('shadow-md')
    }
  })
})

