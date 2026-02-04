const REAL_STREAM_URL = '/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=true'

// UI default for log replay: slower so users can actually read stages and milestones.
// If you need faster/slower, change this value and keep tests in sync.
export const DEFAULT_WORKFLOW_REPLAY_DELAY_MS = 800

export function getOpinionBalanceLogStreamUrl(opts: {
  replay: boolean
  replayFile: string
  delayMs: number
  // Only used when replay=false.
  sinceMs?: number
  // Only used when replay=false (defaults to 0). A small tail combined with sinceMs
  // helps avoid missing lines between click->connect.
  tail?: number
}) {
  if (!opts.replay) {
    const tail = Math.max(0, Math.min(2000, Math.floor(opts.tail ?? 0)))
    const since = typeof opts.sinceMs === 'number' && Number.isFinite(opts.sinceMs) ? Math.floor(opts.sinceMs) : null
    const extra = `${since != null ? `&since_ms=${since}` : ''}`
    return `/api/opinion-balance/logs/stream?source=workflow&tail=${tail}&follow_latest=true${extra}`
  }

  const file = encodeURIComponent(opts.replayFile)
  // Keep in sync with backend clamp in `frontend_api.py`.
  const delay = Math.max(0, Math.min(10000, Math.floor(opts.delayMs)))
  return `/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=false&replay=1&file=${file}&delay_ms=${delay}`
}

export function shouldCallOpinionBalanceProcessApi(replay: boolean) {
  return !replay
}
