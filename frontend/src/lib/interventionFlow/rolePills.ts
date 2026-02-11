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
    related?: {
      amplifierSummary?: string[]
    }
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

    const pills: string[] = []
    if (strategy) pills.push(strategy)

    const rawStyle = stripPrefix(style, '风格：').replace(/\\/g, '/').trim()
    const styleParts = rawStyle
      ? rawStyle
          .split('/')
          .map((s) => s.trim())
          .filter(Boolean)
      : []
    const styleAdj = styleParts[0] ?? ''
    const toneAdj = styleParts[1] ?? ''

    if (styleAdj) pills.push(`风格：${styleAdj}`)
    if (toneAdj) pills.push(`语气：${toneAdj}`)

    const amplifierSummary = normalizeSummary(input.related?.amplifierSummary ?? [])
    const rawAmplifierLine =
      amplifierSummary.find((s) => /^Amplifier:\s*\d+/i.test(s)) ??
      amplifierSummary.find((s) => /^amplifier:\s*\d+/i.test(s)) ??
      amplifierSummary.find((s) => /^Amplifiers:\s*\d+/i.test(s)) ??
      amplifierSummary.find((s) => /^扩音器：\s*\d+/.test(s)) ??
      ''
    const amplifierCount =
      rawAmplifierLine.match(/^Amplifier:\s*(\d+)/i)?.[1] ??
      rawAmplifierLine.match(/^amplifier:\s*(\d+)/i)?.[1] ??
      rawAmplifierLine.match(/^Amplifiers:\s*(\d+)/i)?.[1] ??
      rawAmplifierLine.match(/^扩音器：\s*(\d+)/)?.[1] ??
      ''
    if (amplifierCount) pills.push(`扩音器：${amplifierCount}`)

    // Strategist core argument is displayed in the dynamic panel (it can be long), so don't duplicate it here.
    return pills.slice(0, 4)
  }

  if (role === 'Amplifier') {
    const amplifiers = summary.find((s) => s.startsWith('Amplifiers:')) ?? ''
    return amplifiers ? [amplifiers] : []
  }

  if (role === 'Leader') {
    return summary.filter((s) => !s.startsWith('发布：')).slice(0, 4)
  }

  return summary.slice(0, 4)
}
