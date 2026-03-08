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
    pendingMultiline: null | { kind: 'postContent' | 'leaderComment' | 'skip'; key?: string }
  }
  roles: Record<Role, RoleCardState>
}

const LOG_PREFIX_RE = /^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+\s+-\s+\w+\s+-\s+/

// Mirrors the backend parse_log_timestamp_ms logic.
// Returns the local-time epoch milliseconds for a log line, or null if not parseable.
const LOG_TS_RE = /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2}),(\d+)/
export function parseLogTimestampMs(line: string): number | null {
  const m = LOG_TS_RE.exec(line)
  if (!m) return null
  // Use local time (same as Python time.mktime) so comparisons with Date.now() are consistent.
  const dt = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6], +m[7])
  const ms = dt.getTime()
  return Number.isFinite(ms) ? ms : null
}

const MAX_DURING_LINES_DEFAULT = 10
const MAX_AFTER_LINES_DEFAULT = 6

function maxDuringLines(role: Role) {
  switch (role) {
    case 'Analyst':
      // Analyst runs a multi-step pipeline and emits many lines; keep more so the full flow stays visible.
      return 25
    case 'Strategist':
      // Strategist often emits multiple candidate strategies; keep more for readability.
      return 20
    case 'Leader':
      // Leader needs to show full evidence + candidate blocks (can be >10 lines).
      return 40
    case 'Amplifier':
      // Amplifier cluster can have 12+ agents; keep all comment lines for per-troop filtering.
      return 60
    default:
      return MAX_DURING_LINES_DEFAULT
  }
}

function maxAfterLines(role: Role) {
  switch (role) {
    case 'Strategist':
      return 12
    case 'Leader':
      // Preserve the full evidence + candidate set for review after switching tabs.
      return 40
    case 'Amplifier':
      // Preserve all agent comment lines so per-troop filter works after the round ends.
      return 60
    default:
      return MAX_AFTER_LINES_DEFAULT
  }
}

const ROLE_BEFORE_COPY: Record<Role, string> = {
  Analyst: '监测舆情信号，判断是否触发干预',
  Strategist: '生成可执行的平衡策略与投放指令',
  Leader: '生成并发布主导评论，定调讨论方向',
  Amplifier: '组织扩散者集群扩散，提升优质观点权重',
}

// Option B: 4 fixed rows per role (stable layout; values update as logs arrive).
const ROLE_SUMMARY_DEFAULT: Record<Role, [string, string, string, string]> = {
  // Defaults are empty so UI can hide unknown facts (no "pending"/"—" placeholders).
  Analyst: ['', '', '', ''],
  Strategist: ['', '', '', ''],
  Leader: ['', '', '', ''],
  Amplifier: ['', '', '', ''],
}

// (reserved) summary parsing helpers can be added here when needed.

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
  // Mid/late-stage Strategist lines — needed so the role switches back to Strategist
  // even after an isNewRoundAnchor reset caused by interleaved parallel workflow logs.
  /Query historical successful strategies/i,
  /Retrieved \d+ results from action_logs/i,
  /Found \d+ related historical strategies/i,
  /Generated \d+ strategy options/i,
  /Selected optimal strategy:/i,
  /Selected optimal option:/i,
  /Intelligent strategy creation completed/i,
  /Strategy creation completed/i,
  // Phase 3 evaluation anchor (no content execution — feedback-only pass)
  /Strategist evaluating/i,
]

const leaderAnchors = [
  /Leader Agent starting USC/i,
  /USC-Generate/i,
  /USC-Vote/i,
  /Output final copy/i,
  /Leader Agent starts USC/i,
]

const amplifierAnchors = [
  /Activating Amplifier Agent cluster/i,
  /Start parallel execution/i,
  /Bulk like/i,
  // Individual Amplifier agent comment lines — needed so they route back to Amplifier
  // even when Leader is the active role during parallel Leader+Amplifier execution.
  /^💬\s*🤖\s*Amplifier-\d+\b/i,
  // Per-agent decision log lines emitted before each LLM call.
  /^🎯\s*amplifier-\d+\b/i,
  // Per-agent content-analysis log lines emitted before the decision step.
  /^🔍\s*amplifier-\d+\b/i,
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
      // 内容识别 -> 评论抽样 -> 极端度 -> 情绪度 -> 干预判定 -> 监测评估
      if (/Analyst is analyzing/i.test(cleanLine) || /^📊\s*Phase 1:/i.test(cleanLine) || /^Core viewpoint:/i.test(cleanLine)) return 0
      if (/Total weight calculated:/i.test(cleanLine) || /Comment\s+\d+\s+content:/i.test(cleanLine)) return 1
      // Weighted sentiment summary belongs to the "情绪度" stage for the UI stepper.
      if (/Weighted per-comment sentiment:/i.test(cleanLine)) return 3
      if (/^Viewpoint extremism:/i.test(cleanLine)) return 2
      if (/^Overall sentiment:/i.test(cleanLine)) return 3
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
      if (/Step\s*4:\s*Format as agent instructions/i.test(cleanLine) || /Format as agent instructions/i.test(cleanLine) || /Strategy creation completed/i.test(cleanLine)) return 4
      // Phase 3 evaluation: map to stage 0 (entry) so the stepper shows activity
      if (/Strategist evaluating/i.test(cleanLine)) return 0
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
      // 启动集群 -> 生成回应 -> 点赞扩散（点赞扩散与完成信息合并展示）
      if (/Activating Amplifier Agent cluster/i.test(cleanLine) || /Amplifier plan:\s*total=/i.test(cleanLine)) return 0
      if (/Start parallel execution/i.test(cleanLine) || /\d+\s+amplifier responses generated/i.test(cleanLine) || /Amplifier Agent results:/i.test(cleanLine)) return 1
      if (/Amplifier\s+Agents\s+start\s+liking\s+leader comments/i.test(cleanLine)) return 2
      if (/^\s*💖\s*\d+\s+Amplifier\s+Agents\s+liked\s+leader comments/i.test(cleanLine)) return 2
      if (/Workflow completed\s*-\s*effectiveness score:/i.test(cleanLine) || /Base effectiveness score:/i.test(cleanLine)) return 2
      return null
    }
  }
}

function applyStageUpdateForRole(prevRoles: FlowState['roles'], role: Role, cleanLine: string): FlowState['roles'] {
  const nextIndex = mapLineToStageIndex(role, cleanLine)
  if (nextIndex === null) return prevRoles

  const cur = prevRoles[role]
  // Prevent stage regressions within the same workflow round. Replay logs (and some backends)
  // can emit earlier-phase lines again (e.g. repeated "Core viewpoint:"), which would otherwise
  // cause the UI to jump back to 1/6 and clear the streamed buffer (visible as flicker).
  if (cur.stage.current >= 0 && nextIndex < cur.stage.current) return prevRoles

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
  // Strategist/Leader panels benefit from keeping earlier context (candidate strategies / evidence / candidates)
  // across stage transitions.
  // Amplifier keeps all comment lines across stages so per-troop filtering remains usable.
  // Other roles keep stage-only stream for readability.
  const shouldResetDuring = cur.stage.current !== nextStage.current && role !== 'Strategist' && role !== 'Leader' && role !== 'Analyst' && role !== 'Amplifier'
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
  if (!line) return card
  if (card.during.length && card.during[card.during.length - 1] === line) return card
  const appended = [...card.during, line]
  const bounded = appended.slice(Math.max(0, appended.length - maxLines))
  return { ...card, during: bounded }
}

function freezeAfter(card: RoleCardState, maxLines: number): RoleCardState {
  const snapshot = card.during.slice(Math.max(0, card.during.length - maxLines))
  return { ...card, status: 'done', after: snapshot, during: [] }
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
        .replace(/Viewpoint extremism too high/gi, '观点极端度太高')
        .replace(/Sentiment too low/gi, '情绪度太低')
      update('Analyst', 3, `触发原因：${zh}`)
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
    if (arg) update('Strategist', 3, `核心论点：${arg}`)
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
    const mTotal = cleanLine.match(/Amplifier plan:\s*total=(\d+)/i)
    if (mTotal) update('Amplifier', 0, `Amplifier: ${mTotal[1]}`)

    const mResp = cleanLine.match(/(\d+)\s+amplifier responses generated/i)
    if (mResp) update('Amplifier', 1, `回应：${mResp[1]}`)

    // Like-boosting is not surfaced in the UI (keeps the panel focused on amplification outcome).

    const mEff = cleanLine.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    // Do not display effectiveness score; the stage stepper already communicates completion.
    if (mEff) update('Amplifier', 3, '')
  }

  return roles
}

function compressDisplayLine(cleanLine: string) {
  const trimmed = cleanLine.trim()
  // Suppress visual separators emitted by some backends (they don't carry meaning in the UI).
  if (/^=+$/.test(trimmed)) return ''
  // Suppress placeholder model identifiers (they are internal and confusing in the UI).
  if (/model\s*\(unknown\)/i.test(trimmed)) return ''
  // Suppress placeholder Leader keyword lines; they are misleading and we hide the keyword pill when unknown.
  if (/^Keyword:\s*unknown\s*$/i.test(trimmed)) return ''
  // Suppress internal like-boosting steps in the Amplifier panel.
  if (/Amplifier\s+Agents\s+start\s+liking\s+leader comments/i.test(trimmed)) return ''
  if (/successfully liked leader comments/i.test(trimmed)) return ''
  if (/\(total:\s*\d+\s+likes\)/i.test(trimmed)) return ''

  // Suppress platform-like detail lines that don't add value in the dynamic panel.
  if (/^📊\s*(?:First|Second)\s+leader comment likes (?:before|after):/i.test(trimmed)) return ''
  if (/^✅\s*Added\s+\d+\s+likes\s+to\s+(?:first|second)\s+leader comment\b/i.test(trimmed)) return ''
  if (/^📊\s*Calculating base effectiveness score\.\.\./i.test(trimmed)) return ''
  if (/^📊\s*Leader comment\b.*\bcurrent likes:/i.test(trimmed)) return ''
  if (/^📊\s*Prepare bulk likes:/i.test(trimmed)) return ''
  if (/^📊\s*Calculated bulk likes:/i.test(trimmed)) return ''
  if (/^📊\s*Bulk like operation result:/i.test(trimmed)) return ''
  if (/^🔄\s*Starting bulk like operation\.\.\./i.test(trimmed)) return ''
  if (/^🔄\s*Starting bulk like database operation\.\.\./i.test(trimmed)) return ''
  if (/^🔍\s*Bulk like method called:/i.test(trimmed)) return ''
  if (/^🔄\s*Adding\s+\d+\s+likes\s+to\s+(?:first|second)\s+leader comment\b/i.test(trimmed)) return ''

  // Normalize "Successfully created N Amplifier Agents" variants to a single stable UI line.
  // Backends may emit both "… (target: N)" and plain variants; we keep only the normalized form.
  {
    const m = trimmed.match(
      /^✅\s*Successfully created\s+(\d+)\s+Amplifier\s+Agents(?:\s*\(target:\s*\d+\))?\s*$/i,
    )
    if (m) return `✅ Successfully created ${m[1]} Amplifier Agents`
  }

  // Map Phase headers to Chinese for readability in the dynamic panel.
  // Examples:
  //   "📊 Phase 1: perception and decision" -> "📊 阶段 1：感知与决策"
  //   "📈 Phase 3: feedback and iteration" -> "📈 阶段 3：反馈与迭代"
  {
    const m = trimmed.match(/^([^\p{L}\p{N}]*)Phase\s*(\d+)\s*:\s*(.+)$/iu)
    if (m) {
      const prefixRaw = m[1].trimEnd()
      const phaseNum = m[2]
      const desc = m[3].trim()
      const descKey = desc.toLowerCase()
      const descZh =
        descKey === 'perception and decision'
          ? '感知与决策'
          : descKey === 'feedback and iteration'
            ? '反馈与迭代'
            : desc
      const prefix = prefixRaw ? `${prefixRaw} ` : ''
      return `${prefix}阶段 ${phaseNum}：${descZh}`
    }
  }

  // Amplifier per-agent analysis line: route as-is (carries 【role】 for troop filtering).
  if (/^🔍\s*amplifier-\d+\b/i.test(trimmed)) {
    return trimmed
  }
  // Amplifier per-agent decision line: route to Amplifier panel as-is (carries 【role】 for troop filtering).
  if (/^🎯\s*amplifier-\d+\b/i.test(trimmed)) {
    return trimmed
  }

  // Amplifier per-agent comment: keep the body, but normalize the label and hide model name.
  // Example:
  //   "💬 🤖 Amplifier-3 (positive_john_133) (gemini-2.0-flash) commented: ..."
  // ->"💬 🤖 Amplifier-3 (positive_john_133) commented: ..."
  if (/^💬\s*🤖\s*Amplifier-\d+\b/i.test(trimmed) && /\bcommented:/i.test(trimmed)) {
    const normalized = trimmed.replace(/^💬\s*🤖\s*Amplifier-(\d+)\b/i, '💬 🤖 Amplifier-$1')
    // 兼容两种格式：
    //   旧：Amplifier-N (persona) (model) commented:
    //   新：Amplifier-N【role】 (persona) (model) commented:
    const withoutModel = normalized.replace(
      /^(💬\s*🤖\s*Amplifier-\d+(?:【[^】]*】)?)\s+(\([^)]*\))\s+\([^)]*\)\s+commented:/i,
      '$1 $2 commented:',
    )
    return withoutModel
  }

  // Suppress redundant "analysis completed" marker; we render the extracted core viewpoint instead.
  if (/Analyst analysis completed/i.test(cleanLine)) return ''

  // Suppress workflow prelude/config lines that don't help the dynamic panel.
  // (They are useful for logs, but in the UI they read as noise.)
  if (/^⚙️\s*Force intervention:/i.test(cleanLine)) return ''
  if (/^📊\s*Monitoring interval:/i.test(cleanLine)) return ''
  if (/^🔄\s*Feedback iteration:/i.test(cleanLine)) return ''
  if (/^✅\s*Post exists:/i.test(cleanLine)) return ''
  if (/^🚨⚖️\s*Start opinion balance intervention system/i.test(cleanLine)) return ''
  // Suppress fixed agent id allocation details (they are internal plumbing; the UI shows count instead).
  if (/^(?:🔒\s*)?Allocated\s+\d+\s+fixed\s+Amplifier\s+Agent\s+IDs:/i.test(cleanLine)) return ''

  const milestone = toUserMilestone(cleanLine)
  if (milestone) {
    return milestone
  }
  // Fallback: short truncated line, but avoid dumping full bodies.
  return cleanLine.trim()
}

function pushAggregated(prev: string[], nextLine: string, maxLines: number) {
  if (!nextLine) return prev
  if (prev.length) {
    if (prev.includes(nextLine)) {
      // Avoid showing duplicate milestone lines when backends emit both "in-progress" and "completed" variants.
      // (e.g. "🔄 Generated N ..." then later "✅ Generated N ..." -> same milestone string in the UI)
      return prev
    }
    const last = prev[prev.length - 1]
    if (last.startsWith(nextLine)) {
      // Do not show repetition counters (×N) in the UI; keep the latest line as-is.
      return prev
    }
  }
  const appended = [...prev, nextLine]
  return appended.slice(Math.max(0, appended.length - maxLines))
}

export function routeLogLine(prev: FlowState, rawLine: string): FlowState {
  const hasPrefix = LOG_PREFIX_RE.test(rawLine)
  const cleanLine = stripLogPrefix(rawLine)
  if (!cleanLine) return prev

  // Surface stream status lines (produced by the backend SSE wrapper or our EventSource onopen/onerror)
  // even before any role anchors appear. Without this, the UI can look "stuck" on connect failures.
  if (/^(INFO|ERROR|提示|错误)：/i.test(cleanLine) && !hasPrefix && !prev.context.pendingMultiline) {
    const displayLine = compressDisplayLine(cleanLine)
    const role: Role = prev.activeRole ?? 'Analyst'
    const nextRoles = { ...prev.roles }
    const cur = nextRoles[role]
    nextRoles[role] = {
      ...cur,
      status: /^ERROR:/i.test(cleanLine) || cleanLine.startsWith('错误：') ? 'error' : (cur.status === 'idle' ? 'running' : cur.status),
      during: pushAggregated(cur.during, displayLine, maxDuringLines(role)),
    }
    return {
      ...prev,
      activeRole: prev.activeRole ?? role,
      roles: nextRoles,
    }
  }

  // If logger emitted embedded newlines, continuation lines often come without a timestamp prefix.
  // In that case we append to the last captured field (post content / leader comment) and do not
  // route as a standalone log line (prevents truncation and preserves full bodies for display).
  if (!hasPrefix && prev.context.pendingMultiline) {
    const pending = prev.context.pendingMultiline

    if (pending.kind === 'skip') {
      return prev
    }

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

  // Some backend log lines include embedded newlines inside "Comment N content:" blocks (markdown bodies).
  // Those continuation lines come without a prefix and would otherwise flood the dynamic panel, pushing
  // out key metrics like extremity/sentiment. We skip that whole block until the next prefixed line.
  if (hasPrefix && /^(?:📝\s*)?Comment\s+\d+\s+content:\s*/i.test(cleanLine)) {
    return {
      ...prev,
      context: {
        ...prev.context,
        pendingMultiline: { kind: 'skip' },
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

  // No-intervention completion: freeze all 4 role cards so the user can see a complete
  // round result (Analyst done + the other 3 roles explicitly marked as "not triggered").
  // 修复：正则需要匹配开头可能有 emoji 的情况 (✅ No intervention needed...)
  if (/No intervention needed for post.*Workflow completed/i.test(cleanLine) || /✅\s*No intervention needed/i.test(cleanLine)) {
    const displayLine = compressDisplayLine(cleanLine)
    const nextRoles = { ...prev.roles }

    // Freeze Analyst with its accumulated analysis lines + the completion message.
    const analyst = nextRoles.Analyst
    const withLine = appendDuringWithCap(analyst, displayLine, maxDuringLines('Analyst'))
    nextRoles.Analyst = freezeAfter(withLine, maxAfterLines('Analyst'))

    // Mark the other 3 roles as "done / not triggered" so the tab indicators turn
    // green and the cards show a clear "no action" placeholder instead of idle copy.
    const noActionLine = '✅ 本轮分析完成，无需执行干预'
    for (const role of ['Strategist', 'Leader', 'Amplifier'] as const) {
      const card = nextRoles[role]
      const withMsg = appendDuringWithCap(card, noActionLine, 1)
      nextRoles[role] = freezeAfter(withMsg, 1)
    }

    return { ...prev, activeRole: null, roles: nextRoles }
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

  // Role switching is anchor-driven; when amplifier is sticky, all non-anchored lines
  // are forced to Amplifier (sequential execution: Leader finishes before Amplifier starts).
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
      during: pushAggregated(nextRoles[nextRole].during, displayLine, maxDuringLines(nextRole)),
    }
    return {
      ...stateAfterStage,
      amplifierSticky: amplifierSticky || matchesAny(cleanLine, [/Activating Amplifier Agent cluster/i]),
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
      during: pushAggregated(cur.during, displayLine, maxDuringLines(activeRole)),
    }
    return { ...stateAfterStage, amplifierSticky, roles: nextRoles }
  }

  // Anchor resolves to the same active role: keep streaming.
  if (nextRole === activeRole) {
    const nextRoles = { ...stateAfterStage.roles }
    nextRoles[activeRole] = appendDuringWithCap(nextRoles[activeRole], displayLine, maxDuringLines(activeRole))
    const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Amplifier Agent cluster/i])
    return { ...stateAfterStage, amplifierSticky: nextSticky, roles: nextRoles }
  }

  // Role switch: freeze previous role and start streaming to the new role.
  const nextRoles = { ...stateAfterStage.roles }
  nextRoles[activeRole] = freezeAfter(nextRoles[activeRole], maxAfterLines(activeRole))
  nextRoles[nextRole] = appendDuringWithCap(
    { ...nextRoles[nextRole], status: 'running' },
    displayLine,
    maxDuringLines(nextRole),
  )

  const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Amplifier Agent cluster/i])
  return {
    ...stateAfterStage,
    activeRole: nextRole,
    amplifierSticky: nextSticky,
    roles: nextRoles,
  }
}
