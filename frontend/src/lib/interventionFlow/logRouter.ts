import { toUserMilestone } from './milestones'

export type Role = 'Analyst' | 'Strategist' | 'Leader' | 'Amplifier'
export type RoleStatus = 'idle' | 'running' | 'done' | 'error'

export interface RoleCardState {
  before: string
  status: RoleStatus
  summary: string[] // fixed 4-line summary; content can update, layout stays stable
  during: string[]
  after?: string[]
}

export interface FlowState {
  activeRole: Role | null
  amplifierSticky: boolean
  noiseCounters: Partial<Record<'http' | 'wiki' | 'cache' | 'request', number>>
  context: {
    postContent?: string
    feedScore?: number
    leaderComments: string[]
  }
  roles: Record<Role, RoleCardState>
}

const LOG_PREFIX_RE = /^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+\s+-\s+\w+\s+-\s+/

const MAX_DURING_LINES = 10
const MAX_AFTER_LINES = 6

const ROLE_BEFORE_COPY: Record<Role, string> = {
  Analyst: '监测舆情信号，判断是否触发干预',
  Strategist: '生成可执行的平衡策略与投放指令',
  Leader: '生成并发布主导评论，定调讨论方向',
  Amplifier: '组织回声集群扩散，提升优质观点权重',
}

// Option B: 4 fixed rows per role (stable layout; values update as logs arrive).
const ROLE_SUMMARY_DEFAULT: Record<Role, [string, string, string, string]> = {
  // Defaults are empty so UI can hide unknown facts (no "pending"/"—" placeholders).
  Analyst: ['', '', '', ''],
  Strategist: ['', '', '', ''],
  Leader: ['', '', '', ''],
  Amplifier: ['', '', '', ''],
}

const analystAnchors = [
  /Analyst is analyzing/i,
  /Analyst monitoring/i,
  /generate baseline effectiveness report/i,
  /Analyzing viewpoint extremism/i,
]

const strategistAnchors = [
  /Strategist is creating strategy/i,
  /start intelligent strategy creation workflow/i,
  /Use Tree-of-Thought/i,
]

const leaderAnchors = [
  /Leader Agent starting USC/i,
  /USC-Generate/i,
  /USC-Vote/i,
  /Output final copy/i,
  /Leader Agent starts USC/i,
]

const amplifierAnchors = [
  /Activating Echo Agent cluster/i,
  /Start parallel execution/i,
  /Bulk like/i,
]

const monitoringAnchors = [
  /\[Monitoring round/i,
  /Monitoring interval/i,
  ...analystAnchors,
]

function matchesAny(line: string, patterns: RegExp[]) {
  return patterns.some((re) => re.test(line))
}

export function stripLogPrefix(line: string) {
  return line.replace(LOG_PREFIX_RE, '').trim().replace(/^\s+/, '')
}

export function createInitialFlowState(): FlowState {
  return {
    activeRole: null,
    amplifierSticky: false,
    noiseCounters: {},
    context: { leaderComments: [] },
    roles: {
      Analyst: { before: ROLE_BEFORE_COPY.Analyst, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Analyst], during: [] },
      Strategist: { before: ROLE_BEFORE_COPY.Strategist, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Strategist], during: [] },
      Leader: { before: ROLE_BEFORE_COPY.Leader, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Leader], during: [] },
      Amplifier: { before: ROLE_BEFORE_COPY.Amplifier, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Amplifier], during: [] },
    },
  }
}

function detectRoleByAnchor(cleanLine: string): Role | null {
  if (matchesAny(cleanLine, analystAnchors)) return 'Analyst'
  if (matchesAny(cleanLine, strategistAnchors)) return 'Strategist'
  if (matchesAny(cleanLine, leaderAnchors)) return 'Leader'
  if (matchesAny(cleanLine, amplifierAnchors)) return 'Amplifier'
  return null
}

function appendDuringWithCap(card: RoleCardState, line: string, maxLines: number): RoleCardState {
  const appended = [...card.during, line]
  const bounded = appended.slice(Math.max(0, appended.length - maxLines))
  return { ...card, during: bounded }
}

function freezeAfter(card: RoleCardState): RoleCardState {
  const snapshot = card.during.slice(Math.max(0, card.during.length - MAX_AFTER_LINES))
  return { ...card, status: 'done', after: snapshot, during: [] }
}

function truncateEnd(s: string, max: number) {
  const t = s.trim()
  if (t.length <= max) return t
  return `${t.slice(0, Math.max(0, max - 1))}…`
}

function applySummaryUpdates(prevRoles: FlowState['roles'], cleanLine: string): FlowState['roles'] {
  let roles = prevRoles

  const update = (role: Role, idx: 0 | 1 | 2 | 3, next: string) => {
    const cur = roles[role]
    if (cur.summary[idx] === next) return
    roles = {
      ...roles,
      [role]: {
        ...cur,
        summary: cur.summary.map((v, i) => (i === idx ? next : v)),
      },
    }
  }

  // Analyst: decision + core metrics.
  {
    const mExt = cleanLine.match(/Viewpoint extremism:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (mExt) update('Analyst', 1, `极端度：${mExt[1].replace(/\s+/g, '')}`)

    const mSent = cleanLine.match(/Overall sentiment:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (mSent) update('Analyst', 2, `情绪：${mSent[1].replace(/\s+/g, '')}`)

    const mReasons = cleanLine.match(/Trigger reasons:\s*(.+)$/i)
    if (mReasons) {
      const raw = mReasons[1]
      const zh = raw
        .replace(/Viewpoint extremism too high/gi, '极端度过高')
        .replace(/Sentiment too low/gi, '情绪过低')
      update('Analyst', 3, `触发原因：${truncateEnd(zh, 80)}`)
    }

    const needs = cleanLine.match(/Needs intervention:\s*(yes|no)\b/i)
    const urg = cleanLine.match(/Urgency level:\s*(\d+)\b/i)
    if (needs || urg) {
      const cur = roles.Analyst.summary[0]
      const curUrg = cur.match(/\bU(\d+)\b/i)
      const urgency = Number(urg?.[1] ?? curUrg?.[1] ?? NaN)
      const needTxt = needs ? (needs[1].toLowerCase() === 'yes' ? '需要' : '不需要') : undefined
      const curNeed = cur.match(/^判定：\s*([^\s(]+)/)?.[1]
      const finalNeed = needTxt ?? curNeed ?? ''
      const decision = finalNeed === '需要' ? '需要干预' : finalNeed === '不需要' ? '无需干预' : finalNeed
      const withUrg = Number.isFinite(urgency) ? `判定：${decision}（U${urgency}）` : decision ? `判定：${decision}` : ''
      update('Analyst', 0, withUrg)
    }
  }

  // Strategist: strategy selection + leader style.
  {
    const mSel = cleanLine.match(/Selected optimal strategy:\s*([a-z0-9_ -]+)/i)
    if (mSel) update('Strategist', 0, `策略：${mSel[1].trim()}`)

    const mRec = cleanLine.match(/Recommended strategy:\s*([a-z0-9_ -]+),\s*confidence:\s*([0-9.]+)/i)
    if (mRec) {
      update('Strategist', 0, `策略：${mRec[1].trim()}`)
      update('Strategist', 1, `置信度：${mRec[2]}`)
    }

    const style = cleanLine.match(/Leader style:\s*([a-z0-9_ -]+)/i)?.[1]?.trim()
    const tone = cleanLine.match(/Tone:\s*([a-z0-9_ -]+)/i)?.[1]?.trim()
    if (style || tone) {
      const cur = roles.Strategist.summary[2].replace(/^风格：\s*/i, '').trim()
      const parts = new Set<string>(cur && cur !== '—' ? cur.split('/').map((s) => s.trim()).filter(Boolean) : [])
      if (style) parts.add(style)
      if (tone) parts.add(tone)
      update('Strategist', 2, `风格：${parts.size ? Array.from(parts).join(' / ') : ''}`)
    }

    const arg = cleanLine.match(/Core argument:\s*(.+)$/i)?.[1]?.trim()
    if (arg) update('Strategist', 3, `核心论点：${truncateEnd(arg, 80)}`)
  }

  // Leader: generation/vote outcomes.
  {
    const mGen = cleanLine.match(/generate\s+(\d+)\s+candidate comments/i)
    if (mGen) update('Leader', 0, `候选：${mGen[1]}`)

    const mBest = cleanLine.match(/Best selection:\s*(candidate_\d+)/i)
    if (mBest) update('Leader', 1, `选定：${mBest[1]}`)

    const mScore = cleanLine.match(/Best candidate score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (mScore) update('Leader', 2, `评分：${mScore[1].replace(/\s+/g, '')}`)

    // Publish: use the ordinal in "Leader comment N on post ..." as a stable count signal.
    const mPosted = cleanLine.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\b/i)
    if (mPosted) {
      const nextN = Number(mPosted[1])
      const cur = roles.Leader.summary[3]
      const curN = Number(cur.match(/\b(\d+)\b/)?.[1] ?? NaN)
      const n = Number.isFinite(curN) ? Math.max(curN, nextN) : nextN
      update('Leader', 3, `发布：${n}`)
    }
  }

  // Amplifier: echo size + likes + effectiveness.
  {
    const mTotal = cleanLine.match(/Echo plan:\s*total=(\d+)/i)
    if (mTotal) update('Amplifier', 0, `Echo: ${mTotal[1]}`)

    const mResp = cleanLine.match(/(\d+)\s+echo responses generated/i)
    if (mResp) update('Amplifier', 1, `回应：${mResp[1]}`)

    const mLikes = cleanLine.match(/\(total:\s*(\d+)\s+likes\)/i)
    if (mLikes) update('Amplifier', 2, `点赞：+${mLikes[1]}`)

    const mEff = cleanLine.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (mEff) update('Amplifier', 3, `效果：${mEff[1].replace(/\s+/g, '')}`)
  }

  return roles
}

function compressDisplayLine(cleanLine: string) {
  const milestone = toUserMilestone(cleanLine)
  if (milestone) return milestone
  // Fallback: short truncated line, but avoid dumping full bodies.
  if (cleanLine.length > 96) return `${cleanLine.slice(0, 95)}…`
  return cleanLine.trim()
}

function pushAggregated(prev: string[], nextLine: string, maxLines: number) {
  if (!nextLine) return prev
  if (prev.length) {
    const last = prev[prev.length - 1]
    if (last.startsWith(nextLine)) {
      const m = last.match(/^(.*?)(?:\s*×\s*(\d+))$/)
      const base = (m ? m[1] : last).trimEnd()
      const count = m ? Number(m[2] || 1) : 1
      const updated = `${base} × ${count + 1}`
      return [...prev.slice(0, -1), updated]
    }
  }
  const appended = [...prev, nextLine]
  return appended.slice(Math.max(0, appended.length - maxLines))
}

export function routeLogLine(prev: FlowState, rawLine: string): FlowState {
  const cleanLine = stripLogPrefix(rawLine)
  if (!cleanLine) return prev

  // Extract user-facing content that should be rendered in full (post body, leader comments, etc.)
  let nextContext = prev.context
  if (/^Post content:\s*/i.test(cleanLine)) {
    nextContext = { ...nextContext, postContent: cleanLine.replace(/^Post content:\s*/i, '').trim() }
  }
  const mFeed = cleanLine.match(/^Feed score:\s*([0-9.]+)/i)
  if (mFeed) {
    nextContext = { ...nextContext, feedScore: Number(mFeed[1]) }
  }
  // Keep the full leader comment body for display (do not truncate).
  {
    const m = cleanLine.match(/^💬\s*👑\s*Leader comment\s+\d+\s+on\s+post\s+\S+:\s*(.+)$/i)
    if (m) {
      nextContext = { ...nextContext, leaderComments: [...nextContext.leaderComments, m[1]] }
    }
  }

  const rolesAfterSummary = applySummaryUpdates(prev.roles, cleanLine)
  const stateAfterSummary = (rolesAfterSummary === prev.roles && nextContext === prev.context) ? prev : { ...prev, roles: rolesAfterSummary, context: nextContext }

  // Noise collection: keep UI clean while still signaling background activity.
  if (cleanLine.startsWith('HTTP Request:')) {
    return {
      ...stateAfterSummary,
      noiseCounters: { ...stateAfterSummary.noiseCounters, http: (stateAfterSummary.noiseCounters.http ?? 0) + 1 },
    }
  }
  if (cleanLine.startsWith('Request URL:')) {
    return {
      ...stateAfterSummary,
      noiseCounters: { ...stateAfterSummary.noiseCounters, request: (stateAfterSummary.noiseCounters.request ?? 0) + 1 },
    }
  }
  if (cleanLine.startsWith('Wikipedia:')) {
    return {
      ...stateAfterSummary,
      noiseCounters: { ...stateAfterSummary.noiseCounters, wiki: (stateAfterSummary.noiseCounters.wiki ?? 0) + 1 },
    }
  }
  if (cleanLine.includes('Cache status:')) {
    return {
      ...stateAfterSummary,
      noiseCounters: { ...stateAfterSummary.noiseCounters, cache: (stateAfterSummary.noiseCounters.cache ?? 0) + 1 },
    }
  }

  const displayLine = compressDisplayLine(cleanLine)

  // Sticky ends only when we observe monitoring/baseline anchors, then role switching resumes.
  const shouldReleaseSticky = stateAfterSummary.amplifierSticky && matchesAny(cleanLine, monitoringAnchors)
  const amplifierSticky = shouldReleaseSticky ? false : stateAfterSummary.amplifierSticky

  // Role switching is anchor-driven; when amplifier is sticky, we force attribution to Amplifier.
  const anchoredRole = detectRoleByAnchor(cleanLine)
  const nextRole: Role | null = amplifierSticky ? 'Amplifier' : anchoredRole

  const activeRole = stateAfterSummary.activeRole

  // No active role yet: only start when we have an anchor to bind to.
  if (!activeRole) {
    if (!nextRole) return { ...stateAfterSummary, amplifierSticky }
    const nextRoles = { ...stateAfterSummary.roles }
    nextRoles[nextRole] = {
      ...nextRoles[nextRole],
      status: 'running',
      during: pushAggregated(nextRoles[nextRole].during, displayLine, MAX_DURING_LINES),
    }
    return {
      ...stateAfterSummary,
      amplifierSticky: amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i]),
      activeRole: nextRole,
      roles: nextRoles,
    }
  }

  // No anchor (and not sticky): attribute line to current active role.
  if (!nextRole) {
    const nextRoles = { ...stateAfterSummary.roles }
    const cur = nextRoles[activeRole]
    nextRoles[activeRole] = {
      ...cur,
      during: pushAggregated(cur.during, displayLine, MAX_DURING_LINES),
    }
    return { ...stateAfterSummary, amplifierSticky, roles: nextRoles }
  }

  // Anchor resolves to the same active role: keep streaming.
  if (nextRole === activeRole) {
    const nextRoles = { ...stateAfterSummary.roles }
    nextRoles[activeRole] = appendDuringWithCap(nextRoles[activeRole], displayLine, MAX_DURING_LINES)
    const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i])
    return { ...stateAfterSummary, amplifierSticky: nextSticky, roles: nextRoles }
  }

  // Role switch: freeze previous role and start streaming to the new role.
  const nextRoles = { ...stateAfterSummary.roles }
  nextRoles[activeRole] = freezeAfter(nextRoles[activeRole])
  nextRoles[nextRole] = appendDuringWithCap({ ...nextRoles[nextRole], status: 'running' }, displayLine, MAX_DURING_LINES)

  const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i])
  return {
    ...stateAfterSummary,
    activeRole: nextRole,
    amplifierSticky: nextSticky,
    roles: nextRoles,
  }
}
