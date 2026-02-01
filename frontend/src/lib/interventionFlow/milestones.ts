export function toUserMilestone(cleanLine: string): string | null {
  const s = cleanLine.trim()
  if (!s) return null

  const translateReasonPhrase = (raw: string) =>
    raw
      .replace(/Viewpoint extremism too high/gi, '极端度过高')
      .replace(/Sentiment too low/gi, '情绪过低')

  const parseTriggerReasons = (raw: string) => {
    // Example:
    // "Viewpoint extremism too high (8.0/10.0 >= 4.5) & Sentiment too low (0.13/1.0 <= 0.4)"
    const parts = raw.split('&').map((p) => p.trim()).filter(Boolean)
    const pick = (p: string) => {
      const zh = translateReasonPhrase(p)
      // Keep the key metric fraction (e.g. 8.0/10.0, 0.13/1.0) but drop threshold for cleanliness.
      const frac = zh.match(/\((\d+(?:\.\d+)?\s*\/\s*\d+(?:\.\d+)?)\s*[<>]=?\s*[\d.]+\)/)
      if (frac) return `${zh.replace(/\(.+\)$/, '').trim()}（${frac[1].replace(/\s+/g, '')}）`
      return zh
    }
    if (!parts.length) return translateReasonPhrase(raw)
    return parts.map(pick).join('；')
  }

  // Infra noise
  if (s.startsWith('HTTP Request:')) return null
  if (s.startsWith('Request URL:')) return null
  if (s.startsWith('Wikipedia:')) return null
  if (s.startsWith('📊 Cache status:')) return null
  // Phase headers are redundant in the UI (they often duplicate the role-level milestones).
  if (/^📊\s*Phase\s+\d+:/i.test(s)) return null
  if (/^📈\s*Phase\s+\d+:/i.test(s)) return null
  // Content that we render separately in full.
  if (s.startsWith('Post content:')) return null
  if (s.startsWith('Feed score:')) return null

  // New round anchor (workflow starts a new "action_..." execution).
  {
    const m = s.match(/Start workflow execution\s*-\s*Action ID:\s*([A-Za-z0-9_:-]+)/i)
    if (m) return `新回合：${m[1]}`
  }

  // Analyst (UI already scopes this under the Analyst tab, so avoid repeating "分析师：")
  if (/Analyst is analyzing/i.test(s)) return '开始分析'
  // Prefer rendering the extracted core viewpoint line, so we don't show two "analysis done" lines.
  {
    const m = s.match(/^Core viewpoint:\s*(.+)$/i)
    if (m) return `核心观点：${m[1].trim()}`
  }
  if (/Total weight calculated:/i.test(s)) return '权重汇总'
  if (/Weighted per-comment sentiment:/i.test(s)) return '情绪汇总'
  if (/Needs intervention:\s*yes\b/i.test(s)) return '判定：需要干预'
  if (/Needs intervention:\s*no\b/i.test(s)) return '判定：不需要干预'
  {
    const m = s.match(/^Urgency level:\s*(\d+)\b/i)
    if (m) return `紧急度：U${m[1]}`
  }
  {
    const m = s.match(/^Overall sentiment:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `情绪度：${m[1].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Viewpoint extremism:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `极端度：${m[1].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Trigger reasons:\s*(.+)$/i)
    if (m) return `原因：${parseTriggerReasons(m[1].trim())}`
  }
  // Redundant with the decision + alert milestones.
  if (/Analyst determined opinion balance intervention needed/i.test(s)) return null
  {
    const m = s.match(/Alert generated\s*-\s*Urgency:\s*(\d+)\b/i)
    if (m) return `告警：已生成（U${m[1]}）`
  }
  {
    const m = s.match(/^📊\s*Monitoring task started:\s*(.+)$/i)
    if (m) return '监测任务：已启动'
  }
  if (/Starting monitoring task:/i.test(s)) return '启动监测'
  if (/Will continue monitoring/i.test(s)) return '监测：持续中'
  {
    const m = s.match(/\[Monitoring round\s+(\d+)\s*\/\s*(\d+)\]/i)
    if (m) return `监测回合：${m[1]}/${m[2]}`
  }
  if (/Analyst monitoring/i.test(s)) return '建立基线'

  // Core argument (from Strategist output). Keep in full for the dynamic panel.
  {
    const m = s.match(/^(?:🎯\s*)?Core argument:\s*(.+)$/i)
    if (m) return `核心论点：${m[1].trim()}`
  }

  // Strategist
  if (/Strategist is creating strategy/i.test(s)) return '生成策略'
  {
    const m = s.match(/Selected optimal strategy:\s*([a-z0-9_ -]+)/i)
    if (m) return `策略选定（${m[1].trim()}）`
  }
  // Strategist workflow steps: align stage text with log "Step 4: Format as agent instructions"
  if (/Step\s*4:\s*Format as agent instructions/i.test(s) || /Format as agent instructions/i.test(s)) {
    return '输出指令'
  }

  // Leader
  {
    const m = s.match(/USC-Generate\s*-\s*generate\s+(\d+)\s+candidate comments/i)
    if (m) return `生成候选（${m[1]}）`
  }
  {
    const m = s.match(/Best selection:\s*(candidate_\d+)/i)
    if (m) return `选定版本（${m[1]}）`
  }
  {
    const m = s.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\b/i)
    if (m) return `评论已发布（${m[1]}）`
  }

  // Amplifier
  if (/Activating Echo Agent cluster/i.test(s)) return '启动集群'
  {
    const m = s.match(/Echo plan:\s*total=(\d+)/i)
    if (m) return `集群规模（${m[1]}）`
  }
  {
    const m = s.match(/(\d+)\s+echo responses generated/i)
    if (m) return `生成回应（${m[1]}）`
  }
  {
    const m = s.match(/\(total:\s*(\d+)\s+likes\)/i)
    if (m) return '点赞放大'
  }
  {
    const m = s.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return '扩散完成'
  }

  return null
}
