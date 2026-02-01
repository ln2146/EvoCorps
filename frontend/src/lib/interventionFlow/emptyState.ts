export function isPreRunEmptyState({
  enabled,
  status,
  linesCount,
}: {
  enabled: boolean
  status: 'idle' | 'running' | 'done' | 'error'
  linesCount: number
}) {
  return enabled && status === 'idle' && linesCount <= 0
}
