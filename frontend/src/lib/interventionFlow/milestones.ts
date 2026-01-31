const MAX_LEN = 72

function truncate(s: string) {
  const t = s.trim()
  if (t.length <= MAX_LEN) return t
  return `${t.slice(0, MAX_LEN - 1)}…`
}

export function toUserMilestone(cleanLine: string): string | null {
  const s = cleanLine.trim()
  if (!s) return null

  // Infra noise
  if (s.startsWith('HTTP Request:')) return null
  if (s.startsWith('Request URL:')) return null
  if (s.startsWith('Wikipedia:')) return null
  if (s.startsWith('📊 Cache status:')) return null

  // Analyst
  if (/Analyst is analyzing/i.test(s)) return 'Analyst: Analysis started'
  if (/Analyst analysis completed/i.test(s)) return 'Analyst: Analysis completed'
  if (/Needs intervention:\s*yes\b/i.test(s)) return 'Analyst: Intervention required'
  if (/Needs intervention:\s*no\b/i.test(s)) return 'Analyst: Intervention not required'

  // Strategist
  if (/Strategist is creating strategy/i.test(s)) return 'Strategist: Strategy drafting'
  {
    const m = s.match(/Selected optimal strategy:\s*([a-z0-9_ -]+)/i)
    if (m) return truncate(`Strategist: Strategy selected (${m[1].trim()})`)
  }

  // Leader
  {
    const m = s.match(/USC-Generate\s*-\s*generate\s+(\d+)\s+candidate comments/i)
    if (m) return `Leader: Candidates generated (${m[1]})`
  }
  {
    const m = s.match(/Best selection:\s*(candidate_\d+)/i)
    if (m) return `Leader: Best selection (${m[1]})`
  }
  {
    const m = s.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\b/i)
    if (m) return `Leader: Comment posted (${m[1]})`
  }

  // Amplifier
  if (/Activating Echo Agent cluster/i.test(s)) return 'Amplifier: Echo cluster activated'
  {
    const m = s.match(/Echo plan:\s*total=(\d+)/i)
    if (m) return `Amplifier: Echo plan (${m[1]})`
  }
  {
    const m = s.match(/(\d+)\s+echo responses generated/i)
    if (m) return `Amplifier: Responses generated (${m[1]})`
  }
  {
    const m = s.match(/\(total:\s*(\d+)\s+likes\)/i)
    if (m) return `Amplifier: Likes boosted (+${m[1]})`
  }
  {
    const m = s.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `Amplifier: Effectiveness (${m[1].replace(/\s+/g, '')})`
  }

  return null
}

