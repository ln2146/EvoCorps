import { describe, expect, it } from 'vitest'

import { computeEffectiveRole, nextSelectedRoleOnTabClick } from './selection'

describe('computeEffectiveRole', () => {
  it('prefers selectedRole over activeRole', () => {
    expect(computeEffectiveRole('Leader', 'Analyst')).toBe('Leader')
  })

  it('follows activeRole when selectedRole is null', () => {
    expect(computeEffectiveRole(null, 'Strategist')).toBe('Strategist')
  })

  it('defaults to Analyst when both selectedRole and activeRole are null', () => {
    expect(computeEffectiveRole(null, null)).toBe('Analyst')
  })
})

describe('nextSelectedRoleOnTabClick', () => {
  it('enters review mode on first click', () => {
    expect(nextSelectedRoleOnTabClick(null, 'Leader', 'Analyst')).toBe('Leader')
  })

  it('exits review mode when clicking the active role while reviewing', () => {
    expect(nextSelectedRoleOnTabClick('Leader', 'Analyst', 'Analyst')).toBeNull()
  })

  it('switches review selection when clicking another role (not active)', () => {
    expect(nextSelectedRoleOnTabClick('Leader', 'Strategist', 'Analyst')).toBe('Strategist')
  })

  it('keeps review selection when clicking the selected role again (not active)', () => {
    expect(nextSelectedRoleOnTabClick('Leader', 'Leader', 'Analyst')).toBe('Leader')
  })
})
