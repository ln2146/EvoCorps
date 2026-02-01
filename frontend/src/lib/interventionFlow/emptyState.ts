export function isPreRunEmptyState({
  enabled,
  status,
  linesCount,
}: {
  enabled: boolean
  status: 'idle' | 'running' | 'done' | 'error'
  linesCount: number
}) {
  // When opinion-balance is disabled, keep the panel in a clean "pre-run" state
  // (no metric pills; just a short prompt).
  if (!enabled) return true
  return status === 'idle' && linesCount <= 0
}
