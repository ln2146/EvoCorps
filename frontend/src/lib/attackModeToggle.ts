export type AttackMode = 'swarm' | 'dispersed' | 'chain'

export type AttackToggleAction =
  | { type: 'open_mode_dialog' }
  | { type: 'enable'; mode: AttackMode }
  | { type: 'disable' }

export function resolveAttackToggleAction(params: {
  enabled: boolean
  selectedMode?: AttackMode | null
}): AttackToggleAction {
  const { enabled, selectedMode } = params

  if (enabled) {
    return { type: 'disable' }
  }

  if (!selectedMode) {
    return { type: 'open_mode_dialog' }
  }

  return { type: 'enable', mode: selectedMode }
}

export function getAttackModeLabel(mode: AttackMode): string {
  if (mode === 'swarm') return 'Swarm'
  if (mode === 'dispersed') return 'Dispersed'
  return 'Chain'
}
