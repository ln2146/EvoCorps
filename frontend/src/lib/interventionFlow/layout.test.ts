import { describe, expect, it } from 'vitest'

import { computeRoleFlexGrow } from './layout'

describe('computeRoleFlexGrow', () => {
  it('returns equal sizes when no active role', () => {
    expect(computeRoleFlexGrow(null, 'Analyst')).toBe(1)
    expect(computeRoleFlexGrow(null, 'Strategist')).toBe(1)
  })

  it('expands active role and compresses others when active role exists', () => {
    expect(computeRoleFlexGrow('Analyst', 'Analyst')).toBe(6)
    expect(computeRoleFlexGrow('Analyst', 'Leader')).toBe(1)
  })
})

