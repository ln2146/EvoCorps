import type { Role } from './logRouter'

function stripPrefix(s: string, prefix: string) {
  const t = (s || '').trim()
  if (!t) return ''
  return t.startsWith(prefix) ? t.slice(prefix.length).trim() : t
}

function parseDecisionShort(decisionLine: string) {
  const raw = stripPrefix(decisionLine, '判定：')
  if (!raw) return ''
  if (raw.includes('无需干预')) return '不需要'
  if (raw.includes('需要干预')) return '需要'
  if (raw.includes('无需')) return '不需要'
  if (raw.includes('需要')) return '需要'
  return ''
}

function normalizeSummary(summary: string[]) {
  return summary
    .map((s) => (s || '').trim())
    .filter((s) => Boolean(s) && !/^置信度：—$/.test(s))
}

export function buildRolePills(
  role: Role,
  input: {
    feedScore?: number
    summary: string[]
  },
) {
  const summary = normalizeSummary(input.summary)

  if (role === 'Analyst') {
    const decisionLine = summary.find((s) => s.startsWith('判定：')) ?? ''
    const sentimentLine = summary.find((s) => s.startsWith('情绪：')) ?? ''
    const extremityLine = summary.find((s) => s.startsWith('极端度：')) ?? ''

    const pills: string[] = []

    if (typeof input.feedScore === 'number' && Number.isFinite(input.feedScore)) {
      pills.push(`热度：${input.feedScore.toFixed(2)}`)
    }

    const sentiment = stripPrefix(sentimentLine, '情绪：')
    if (sentiment) pills.push(`情绪度：${sentiment}`)

    if (extremityLine) pills.push(extremityLine)

    const decisionShort = parseDecisionShort(decisionLine)
    if (decisionShort) pills.push(`干预：${decisionShort}`)

    return pills
  }

  // Other roles: show their own summary lines (no heat).
  if (role === 'Strategist') {
    const strategy = summary.find((s) => s.startsWith('策略：')) ?? ''
    const style = summary.find((s) => s.startsWith('风格：')) ?? ''
    const amplifiers = summary.find((s) => s.startsWith('Amplifiers:')) ?? ''

    const pills: string[] = []
    if (strategy) pills.push(strategy)

    const merged = [style, amplifiers].map((s) => s.trim()).filter(Boolean).join(' · ')
    if (merged) pills.push(merged)

    // Strategist core argument is displayed in the dynamic panel (it can be long), so don't duplicate it here.
    return pills.slice(0, 4)
  }

  if (role === 'Amplifier') {
    const amplifiers = summary.find((s) => s.startsWith('Amplifiers:')) ?? ''
    return amplifiers ? [amplifiers] : []
  }

  return summary.slice(0, 4)
}
