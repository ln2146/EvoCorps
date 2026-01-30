export function isNoiseLogLine(line: string) {
  const s = line.trim()
  if (!s) return true

  // Infra / debug noise that doesn't help users understand the intervention flow.
  if (s.startsWith('HTTP Request:')) return true
  if (s.startsWith('Request URL:')) return true
  if (s.startsWith('Wikipedia:')) return true
  if (s.startsWith('📊 Cache status:')) return true

  return false
}

export function compressLogLine(line: string) {
  const s = line.trim()

  // Leader comment: keep the fact it was posted, drop body.
  const leaderComment = s.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\b/i)
  if (leaderComment) {
    return `💬 👑 Leader comment posted (${leaderComment[1]})`
  }

  // Echo per-agent comment: collapse.
  if (/^💬\s*🤖\s*Echo-\d+\b/i.test(s) && /\bcommented:/i.test(s)) {
    return '💬 🤖 Echo commented'
  }

  // Drop long trailing bodies after ":" for certain patterns; keep prefix.
  if (s.length > 140) {
    const idx = s.indexOf(':')
    if (idx > 0 && idx < 80) {
      return `${s.slice(0, idx + 1)} …`
    }
    return `${s.slice(0, 140)}…`
  }

  return s
}

function parseAggSuffix(line: string): { base: string; count: number } {
  const m = line.match(/^(.*?)(?:\s*×\s*(\d+))$/)
  if (!m) return { base: line, count: 1 }
  return { base: m[1].trimEnd(), count: Number(m[2] || 1) }
}

export function pushCompressedLine(
  prev: string[],
  nextLine: string,
  opts: { maxLines: number },
) {
  const maxLines = Math.max(1, opts.maxLines)
  if (!nextLine) return prev

  if (prev.length) {
    const last = prev[prev.length - 1]
    if (last.startsWith(nextLine)) {
      const parsed = parseAggSuffix(last)
      const updated = `${parsed.base} × ${parsed.count + 1}`
      return [...prev.slice(0, -1), updated]
    }
  }

  const appended = [...prev, nextLine]
  return appended.slice(Math.max(0, appended.length - maxLines))
}

