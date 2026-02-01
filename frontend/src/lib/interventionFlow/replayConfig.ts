const REAL_STREAM_URL = '/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=true'

// UI default for log replay: slower so users can actually read stages and milestones.
// If you need faster/slower, change this value and keep tests in sync.
export const DEFAULT_WORKFLOW_REPLAY_DELAY_MS = 800

export function getOpinionBalanceLogStreamUrl(opts: {
  replay: boolean
  replayFile: string
  delayMs: number
}) {
  if (!opts.replay) return REAL_STREAM_URL

  const file = encodeURIComponent(opts.replayFile)
  const delay = Math.max(0, Math.min(2000, Math.floor(opts.delayMs)))
  return `/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=false&replay=1&file=${file}&delay_ms=${delay}`
}

export function shouldCallOpinionBalanceProcessApi(replay: boolean) {
  return !replay
}
