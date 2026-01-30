export type Role = 'Analyst' | 'Strategist' | 'Leader' | 'Amplifier'
export type RoleStatus = 'idle' | 'running' | 'done' | 'error'

export interface RoleCardState {
  before: string
  status: RoleStatus
  during: string[]
  after?: string[]
}

export interface FlowState {
  activeRole: Role | null
  amplifierSticky: boolean
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
    roles: {
      Analyst: { before: ROLE_BEFORE_COPY.Analyst, status: 'idle', during: [] },
      Strategist: { before: ROLE_BEFORE_COPY.Strategist, status: 'idle', during: [] },
      Leader: { before: ROLE_BEFORE_COPY.Leader, status: 'idle', during: [] },
      Amplifier: { before: ROLE_BEFORE_COPY.Amplifier, status: 'idle', during: [] },
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

function appendDuring(card: RoleCardState, cleanLine: string): RoleCardState {
  const nextDuring = [...card.during, cleanLine]
  const bounded = nextDuring.slice(Math.max(0, nextDuring.length - MAX_DURING_LINES))
  return { ...card, during: bounded }
}

function freezeAfter(card: RoleCardState): RoleCardState {
  const snapshot = card.during.slice(Math.max(0, card.during.length - MAX_AFTER_LINES))
  return { ...card, status: 'done', after: snapshot, during: [] }
}

export function routeLogLine(prev: FlowState, rawLine: string): FlowState {
  const cleanLine = stripLogPrefix(rawLine)
  if (!cleanLine) return prev

  // Sticky ends only when we observe monitoring/baseline anchors, then role switching resumes.
  const shouldReleaseSticky = prev.amplifierSticky && matchesAny(cleanLine, monitoringAnchors)
  const amplifierSticky = shouldReleaseSticky ? false : prev.amplifierSticky

  // Role switching is anchor-driven; when amplifier is sticky, we force attribution to Amplifier.
  const anchoredRole = detectRoleByAnchor(cleanLine)
  const nextRole: Role | null = amplifierSticky ? 'Amplifier' : anchoredRole

  const activeRole = prev.activeRole

  // No active role yet: only start when we have an anchor to bind to.
  if (!activeRole) {
    if (!nextRole) return { ...prev, amplifierSticky }
    const nextRoles = { ...prev.roles }
    nextRoles[nextRole] = appendDuring({ ...nextRoles[nextRole], status: 'running' }, cleanLine)
    return {
      ...prev,
      amplifierSticky: amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i]),
      activeRole: nextRole,
      roles: nextRoles,
    }
  }

  // No anchor (and not sticky): attribute line to current active role.
  if (!nextRole) {
    const nextRoles = { ...prev.roles }
    nextRoles[activeRole] = appendDuring(nextRoles[activeRole], cleanLine)
    return { ...prev, amplifierSticky, roles: nextRoles }
  }

  // Anchor resolves to the same active role: keep streaming.
  if (nextRole === activeRole) {
    const nextRoles = { ...prev.roles }
    nextRoles[activeRole] = appendDuring(nextRoles[activeRole], cleanLine)
    const nextSticky = amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i])
    return { ...prev, amplifierSticky: nextSticky, roles: nextRoles }
  }

  // Role switch: freeze previous role and start streaming to the new role.
  const nextRoles = { ...prev.roles }
  nextRoles[activeRole] = freezeAfter(nextRoles[activeRole])
  nextRoles[nextRole] = appendDuring({ ...nextRoles[nextRole], status: 'running' }, cleanLine)

  const nextSticky = (amplifierSticky || matchesAny(cleanLine, [/Activating Echo Agent cluster/i]))
  return {
    ...prev,
    activeRole: nextRole,
    amplifierSticky: nextSticky,
    roles: nextRoles,
  }
}

