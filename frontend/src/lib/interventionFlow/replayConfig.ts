function withDevBackendBase(path: string) {
  // In some Windows setups, Vite may bind on IPv6 (::1) while the Flask backend binds on IPv4 (127.0.0.1).
  // That can break Vite proxy for SSE (it may buffer or stall). When running on port 3000, bypass the proxy
  // and connect to the backend directly.
  if (typeof window !== 'undefined' && window.location && window.location.port === '3000') {
    return `http://127.0.0.1:5001${path}`
  }
  return path
}

// UI default for log replay: slower so users can actually read stages and milestones.
// If you need faster/slower, change this value and keep tests in sync.
export const DEFAULT_WORKFLOW_REPLAY_DELAY_MS = 800

export function getOpinionBalanceLogStreamUrl(opts: {
  replay: boolean
  replayFile: string
  delayMs: number
}) {
  if (!opts.replay) {
    return withDevBackendBase('/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=true')
  }

  const file = encodeURIComponent(opts.replayFile)
  // Keep in sync with backend clamp in `frontend_api.py`.
  const delay = Math.max(0, Math.min(10000, Math.floor(opts.delayMs)))
  return withDevBackendBase(
    `/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=false&replay=1&file=${file}&delay_ms=${delay}`,
  )
}

export function shouldCallOpinionBalanceProcessApi(replay: boolean) {
  return !replay
}
