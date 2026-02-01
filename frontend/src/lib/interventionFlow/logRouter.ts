import { toUserMilestone } from './milestones'

export type Role = 'Analyst' | 'Strategist' | 'Leader' | 'Amplifier'
export type RoleStatus = 'idle' | 'running' | 'done' | 'error'

export interface RoleCardState {
  before: string
  status: RoleStatus
  summary: string[] // fixed 4-line summary; content can update, layout stays stable
  // Stage progress:
  // - current: what the system is doing *now* (best-effort; can move non-monotonically if logs interleave)
  // - max: furthest reached in this round (monotonic)
  // - order: first-seen order of stages in this round (Option A UI: render only observed stages in log order)
  stage: { current: number; max: number; order: number[] }
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
    leaderCommentKeys: Record<string, true>
    leaderCommentIndices: Record<string, number>
    pendingMultiline: null | { kind: 'postContent' | 'leaderComment'; key?: string }
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
  // Monitoring lifecycle lines (should return control to Analyst after Amplifier sticky).
  /Monitoring task started/i,
  /Will continue monitoring/i,
  /Starting monitoring task/i,
  /^📈\s*Phase 3:/i,
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
    context: { leaderComments: [], leaderCommentKeys: {}, leaderCommentIndices: {}, pendingMultiline: null },
    roles: {
      Analyst: { before: ROLE_BEFORE_COPY.Analyst, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Analyst], stage: { current: -1, max: -1, order: [] }, during: [] },
      Strategist: { before: ROLE_BEFORE_COPY.Strategist, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Strategist], stage: { current: -1, max: -1, order: [] }, during: [] },
      Leader: { before: ROLE_BEFORE_COPY.Leader, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Leader], stage: { current: -1, max: -1, order: [] }, during: [] },
      Amplifier: { before: ROLE_BEFORE_COPY.Amplifier, status: 'idle', summary: [...ROLE_SUMMARY_DEFAULT.Amplifier], stage: { current: -1, max: -1, order: [] }, during: [] },
    },
  }
}

function isNewRoundAnchor(cleanLine: string) {
  // Option A: when a new workflow execution round starts, reset stage progress and streaming buffers.
  return /Start workflow execution\s*-\s*Action ID:/i.test(cleanLine)
}

function mapLineToStageIndex(role: Role, cleanLine: string): number | null {
  switch (role) {
    case 'Analyst': {
      // 内容识别 -> 评论抽样 -> 情绪度 -> 极端度 -> 干预判定 -> 监测评估
      if (/Analyst is analyzing/i.test(cleanLine) || /^📊\s*Phase 1:/i.test(cleanLine) || /^Core viewpoint:/i.test(cleanLine)) return 0
      if (/Total weight calculated:/i.test(cleanLine) || /Comment\s+\d+\s+content:/i.test(cleanLine)) return 1
      if (/Weighted per-comment sentiment:/i.test(cleanLine) || /^Overall sentiment:/i.test(cleanLine)) return 2
      if (/^Viewpoint extremism:/i.test(cleanLine)) return 3
      if (/Needs intervention:/i.test(cleanLine) || /Urgency level:/i.test(cleanLine) || /Analyst determined opinion balance intervention needed/i.test(cleanLine)) return 4
      if (
        /\[Monitoring round/i.test(cleanLine) ||
        /^📈\s*Phase 3:/i.test(cleanLine) ||
        /Starting monitoring task/i.test(cleanLine) ||
        /Monitoring task started/i.test(cleanLine) ||
        /Will continue monitoring/i.test(cleanLine)
      ) return 5
      return null
    }
    case 'Strategist': {
      // 确认告警 -> 检索历史 -> 生成方案 -> 选择策略 -> 输出指令
      if (/Alert generated/i.test(cleanLine) || /Confirm alert information/i.test(cleanLine) || /Strategist is creating strategy/i.test(cleanLine)) return 0
      if (/Query historical successful strategies/i.test(cleanLine) || /Retrieved \d+ results from action_logs/i.test(cleanLine) || /Found \d+ related historical strategies/i.test(cleanLine)) return 1
      if (/Tree-of-Thought/i.test(cleanLine) || /Generated \d+ strategy options/i.test(cleanLine)) return 2
      if (/Selected optimal strategy:/i.test(cleanLine)) return 3
      if (/Format as agent instructions/i.test(cleanLine) || /Strategy creation completed/i.test(cleanLine)) return 4
      return null
    }
    case 'Leader': {
      // 解析指令 -> 检索论据 -> 生成候选 -> 投票选优 -> 发布评论
      if (/Parse strategist instructions/i.test(cleanLine) || /starting USC workflow/i.test(cleanLine)) return 0
      if (/Search cognitive memory/i.test(cleanLine) || /Retrieved \d+ relevant arguments/i.test(cleanLine)) return 1
      if (/USC-Generate/i.test(cleanLine) || /generate\s+\d+\s+candidate comments/i.test(cleanLine)) return 2
      if (/USC-Vote/i.test(cleanLine) || /Best selection:/i.test(cleanLine) || /Best candidate score:/i.test(cleanLine)) return 3
      if (/^💬\s*👑\s*Leader comment\s+\d+\s+on\s+post\b/i.test(cleanLine)) return 4
      return null
    }
    case 'Amplifier': {
      // 启动集群 -> 生成回应 -> 点赞放大 -> 扩散完成
      if (/Activating Echo Agent cluster/i.test(cleanLine) || /Echo plan:\s*total=/i.test(cleanLine)) return 0
      if (/Start parallel execution/i.test(cleanLine) || /\d+\s+echo responses generated/i.test(cleanLine) || /Echo Agent results:/i.test(cleanLine)) return 1
      if (/start liking leader comments/i.test(cleanLine) || /Bulk like/i.test(cleanLine) || /\(total:\s*\d+\s+likes\)/i.test(cleanLine)) return 2
      if (/Workflow completed\s*-\s*effectiveness score:/i.test(cleanLine) || /Base effectiveness score:/i.test(cleanLine)) return 3
      return null
    }
  }
}

function applyStageUpdateForRole(prevRoles: FlowState['roles'], role: Role, cleanLine: string): FlowState['roles'] {
  const nextIndex = mapLineToStageIndex(role, cleanLine)
  if (nextIndex === null) return prevRoles

  const cur = prevRoles[role]
  const order = cur.stage.order.includes(nextIndex) ? cur.stage.order : [...cur.stage.order, nextIndex]
  const nextStage = {
    current: nextIndex,
    max: Math.max(cur.stage.max, nextIndex),
    order,
  }

  if (
    cur.stage.current === nextStage.current &&
    cur.stage.max === nextStage.max &&
    cur.stage.order.length === nextStage.order.length
  ) return prevRoles

  // Keep stage and streamed lines aligned: when we enter a new stage, reset the
  // per-role streaming buffer so the UI shows only the current stage's lines.
  // (Persistent info is rendered via summary/context, not this buffer.)
  const shouldResetDuring = cur.stage.current !== nextStage.current
  return {
    ...prevRoles,
    [role]: { ...cur, stage: nextStage, during: shouldResetDuring ? [] : cur.during },
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
    if (arg) update('Strategist', 3, `核心论点：${truncateEnd(arg, 220)}`)
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
    // Do not show exact like counts in the UI; keep it as a qualitative signal.
    if (mLikes) update('Amplifier', 2, '点赞：放大')

    const mEff = cleanLine.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    // Do not display effectiveness score; the stage stepper already communicates completion.
    if (mEff) update('Amplifier', 3, '')
  }

  return roles
}

function compressDisplayLine(cleanLine: string) {
  // Suppress redundant "analysis completed" marker; we render the extracted core viewpoint instead.
  if (/Analyst analysis completed/i.test(cleanLine)) return ''

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
  const hasPrefix = LOG_PREFIX_RE.test(rawLine)
  const cleanLine = stripLogPrefix(rawLine)
  if (!cleanLine) return prev

  // If logger emitted embedded newlines, continuation lines often come without a timestamp prefix.
  // In that case we append to the last captured field (post content / leader comment) and do not
  // route as a standalone log line (prevents truncation and preserves full bodies for display).
  if (!hasPrefix && prev.context.pendingMultiline) {
    const pending = prev.context.pendingMultiline

    if (pending.kind === 'postContent' && prev.context.postContent) {
      return {
        ...prev,
        context: {
          ...prev.context,
          postContent: `${prev.context.postContent}\n${cleanLine}`,
        },
      }
    }

    if (pending.kind === 'leaderComment' && pending.key) {
      const idx = prev.context.leaderCommentIndices[pending.key]
      if (typeof idx === 'number' && prev.context.leaderComments[idx] != null) {
        const nextComments = [...prev.context.leaderComments]
        nextComments[idx] = `${nextComments[idx]}\n${cleanLine}`
        return {
          ...prev,
          context: {
            ...prev.context,
            leaderComments: nextComments,
          },
        }
      }
    }
  }

  // Any prefixed line ends the previous multiline capture session.
  if (hasPrefix && prev.context.pendingMultiline) {
    prev = {
      ...prev,
      context: {
        ...prev.context,
        pendingMultiline: null,
      },
    }
  }

  if (isNewRoundAnchor(cleanLine)) {
    // Reset per-round state but immediately attach the new round to Analyst so the UI
    // starts showing progress right away (replay logs often have many prelude lines
    // before the first agent anchor appears).
    const next = createInitialFlowState()
    const displayLine = compressDisplayLine(cleanLine)
    next.activeRole = 'Analyst'
    next.roles.Analyst = {
      ...next.roles.Analyst,
      status: 'running',
      // Show stage immediately so we don't stream a bunch of Analyst lines while the
      // stage header is still hidden (stage=-1). New rounds always start at stage 0.
      stage: { current: 0, max: 0, order: [0] },
      during: displayLine ? [displayLine] : [],
    }
    return next
  }

  // Extract user-facing content that should be rendered in full (post body, leader comments, etc.)
  let nextContext = prev.context
  if (/^Post content:\s*/i.test(cleanLine)) {
    nextContext = {
      ...nextContext,
      postContent: cleanLine.replace(/^Post content:\s*/i, '').trim(),
      pendingMultiline: { kind: 'postContent' },
    }
  }
  const mFeed = cleanLine.match(/^Feed score:\s*([0-9.]+)/i)
  if (mFeed) {
    nextContext = { ...nextContext, feedScore: Number(mFeed[1]) }
  }
  // Keep the full leader comment body for display (do not truncate).
  {
    const m = cleanLine.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\s+(\S+):\s*(.+)$/i)
    if (m) {
      const ordinal = m[1]
      const postId = m[2]
      const body = m[3]
      const key = `${postId}:${ordinal}`

      if (!nextContext.leaderCommentKeys[key]) {
        const nextIndex = nextContext.leaderComments.length
        nextContext = {
          ...nextContext,
          leaderCommentKeys: { ...nextContext.leaderCommentKeys, [key]: true },
          leaderCommentIndices: { ...nextContext.leaderCommentIndices, [key]: nextIndex },
          leaderComments: [...nextContext.leaderComments, body],
          pendingMultiline: { kind: 'leaderComment', key },
        }
      }
    }
  }

  const rolesAfterSummary = applySummaryUpdates(prev.roles, cleanLine)
  const stateAfterSummary =
    (rolesAfterSummary === prev.roles && nextContext === prev.context) ? prev : { ...prev, roles: rolesAfterSummary, context: nextContext }

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

  // Update stage progress for the same role that will receive this line in the UI.
  // This keeps stage and content aligned (especially important when Amplifier is sticky).
  const roleForStage: Role | null = !activeRole
    ? nextRole
    : (nextRole ?? activeRole)

  const rolesAfterStage =
    roleForStage ? applyStageUpdateForRole(stateAfterSummary.roles, roleForStage, cleanLine) : stateAfterSummary.roles

  const stateAfterStage =
    rolesAfterStage === stateAfterSummary.roles ? stateAfterSummary : { ...stateAfterSummary, roles: rolesAfterStage }

  // No active role yet: only start when we have an anchor to bind to.
  if (!activeRole) {
    if (!nextRole) return { ...stateAfterStage, amplifierSticky }
    const nextRoles = { ...stateAfterStage.roles }
    nextRoles[nextRole] = {
      ...nextRoles[nextRole],
      status: 'running',
      during: pushAggregated(nextRoles[nextRole].during, displayLine, MAX_DURING_LINES),
    }
    return {
      ...stateAfterStage,
      amplifierSticky: amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i]),
      activeRole: nextRole,
      roles: nextRoles,
    }
  }

  // No anchor (and not sticky): attribute line to current active role.
  if (!nextRole) {
    const nextRoles = { ...stateAfterStage.roles }
    const cur = nextRoles[activeRole]
    nextRoles[activeRole] = {
      ...cur,
      during: pushAggregated(cur.during, displayLine, MAX_DURING_LINES),
    }
    return { ...stateAfterStage, amplifierSticky, roles: nextRoles }
  }

  // Anchor resolves to the same active role: keep streaming.
  if (nextRole === activeRole) {
    const nextRoles = { ...stateAfterStage.roles }
    nextRoles[activeRole] = appendDuringWithCap(nextRoles[activeRole], displayLine, MAX_DURING_LINES)
    const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i])
    return { ...stateAfterStage, amplifierSticky: nextSticky, roles: nextRoles }
  }

  // Role switch: freeze previous role and start streaming to the new role.
  const nextRoles = { ...stateAfterStage.roles }
  nextRoles[activeRole] = freezeAfter(nextRoles[activeRole])
  nextRoles[nextRole] = appendDuringWithCap({ ...nextRoles[nextRole], status: 'running' }, displayLine, MAX_DURING_LINES)

  const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i])
  return {
    ...stateAfterStage,
    activeRole: nextRole,
    amplifierSticky: nextSticky,
    roles: nextRoles,
  }
}
