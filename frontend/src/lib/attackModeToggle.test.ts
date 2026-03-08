import { describe, expect, it } from 'vitest'

import { getAttackModeLabel, resolveAttackToggleAction } from './attackModeToggle'

describe('resolveAttackToggleAction', () => {
  it('asks for mode selection when attack is disabled and no mode is chosen', () => {
    const result = resolveAttackToggleAction({ enabled: false, selectedMode: null })
    expect(result).toEqual({ type: 'open_mode_dialog' })
  })

  it('enables attack with the chosen mode when attack is disabled', () => {
    const result = resolveAttackToggleAction({ enabled: false, selectedMode: 'dispersed' })
    expect(result).toEqual({ type: 'enable', mode: 'dispersed' })
  })

  it('disables attack when attack is already enabled', () => {
    const result = resolveAttackToggleAction({ enabled: true, selectedMode: 'swarm' })
    expect(result).toEqual({ type: 'disable' })
  })
})

describe('getAttackModeLabel', () => {
  it('maps each mode to an English label', () => {
    expect(getAttackModeLabel('swarm')).toBe('Swarm')
    expect(getAttackModeLabel('dispersed')).toBe('Dispersed')
    expect(getAttackModeLabel('chain')).toBe('Chain')
  })
})
