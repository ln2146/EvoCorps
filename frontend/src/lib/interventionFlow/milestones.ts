export function toUserMilestone(cleanLine: string): string | null {
  const s = cleanLine.trim()
  if (!s) return null

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

  // Analyst
  if (/Analyst is analyzing/i.test(s)) return '分析师：开始分析'
  // Prefer rendering the extracted core viewpoint line, so we don't show two "analysis done" lines.
  {
    const m = s.match(/^Core viewpoint:\s*(.+)$/i)
    if (m) return `核心观点：${m[1].trim()}`
  }
  if (/Total weight calculated:/i.test(s)) return '分析师：权重汇总'
  if (/Weighted per-comment sentiment:/i.test(s)) return '分析师：情绪汇总'
  if (/generate baseline effectiveness report/i.test(s)) return '分析师：生成基线报告'
  if (/Analyst monitoring\s*-\s*establish baseline data/i.test(s)) return '分析师：建立基线数据'
  if (/Monitoring task started/i.test(s)) return '分析师：启动监测任务'
  if (/Will continue monitoring/i.test(s)) return '分析师：持续监测与动态调整'
  if (/Needs intervention:\s*yes\b/i.test(s)) return '分析师：判定需要干预'
  if (/Needs intervention:\s*no\b/i.test(s)) return '分析师：判定无需干预'
  {
    const m = s.match(/^Overall sentiment:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `分析师：情绪度 ${m[1].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Viewpoint extremism:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `分析师：极端度 ${m[1].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Trigger reasons:\s*(.+)$/i)
    if (m) {
      const zh = m[1]
        .trim()
        .replace(/Viewpoint extremism too high/gi, '观点极端度太高')
        .replace(/Sentiment too low/gi, '情绪度太低')
      return `触发原因： ${zh}`
    }
  }

  // Strategist
  if (/Strategist is creating strategy/i.test(s)) return '战略家：生成策略'
  if (/Query historical successful strategies/i.test(s)) return '战略家：检索历史策略'
  {
    const m = s.match(/Found\s+(\d+)\s+related historical strategies/i)
    if (m) return `战略家：找到相关历史（${m[1]}）`
  }
  if (/Intelligent learning system initialized successfully/i.test(s)) return '战略家：智能学习系统已就绪'
  {
    const m = s.match(/Intelligent learning system recommended strategy:\s*(.+)$/i)
    if (m) return `战略家：智能学习推荐：${m[1].trim()}`
  }
  if (/Intelligent learning system found no matching strategy/i.test(s)) return '战略家：未匹配到历史策略'
  if (/Use Tree-of-Thought/i.test(s)) return '战略家：推理规划'
  if (/Start Tree-of-Thought reasoning/i.test(s)) return '战略家：开始推理'
  {
    const m = s.match(/Strategy creation completed\s*-\s*Strategy ID:\s*(\S+)/i)
    if (m) return `战略家：策略生成完成（${m[1]}）`
  }
  {
    const m = s.match(/Selected optimal strategy:\s*([a-z0-9_ -]+)/i)
    if (m) return `战略家：策略选定：${m[1].trim()}`
  }
  // Strategist workflow steps: align stage text with log "Step 4: Format as agent instructions"
  if (/Step\s*4:\s*Format as agent instructions/i.test(s) || /Format as agent instructions/i.test(s)) {
    return '战略家：输出指令'
  }

  // Leader
  if (/Leader Agent starts USC/i.test(s)) return '领袖：启动生成流程'
  {
    const m = s.match(/Retrieved\s+(\d+)\s+relevant arguments/i)
    if (m) return `领袖：检索论据（${m[1]}）`
  }
  if (/^✅\s*USC workflow completed/i.test(s)) return '领袖：生成完成'
  {
    const m = s.match(/USC-Generate\s*-\s*generate\s+(\d+)\s+candidate comments/i)
    if (m) return `领袖：生成候选（${m[1]}）`
  }
  {
    const m = s.match(/Best selection:\s*(candidate_\d+)/i)
    if (m) return `领袖：选定版本（${m[1]}）`
  }
  {
    const m = s.match(/^💬\s*👑\s*Leader comment\s+(\d+)\s+on\s+post\b/i)
    if (m) return `领袖：评论已发布（${m[1]}）`
  }

  // Amplifier
  if (/Activating Echo Agent cluster/i.test(s)) return '扩音器：启动回声集群'
  {
    const m = s.match(/Start parallel execution of\s+(\d+)\s+agent tasks/i)
    if (m) return `扩音器：并行执行（${m[1]}）`
  }
  {
    const m = s.match(/Echo Agent results:\s*(\d+)\s+succeeded,\s*(\d+)\s+failed/i)
    if (m) return `扩音器：执行结果（成功 ${m[1]} / 失败 ${m[2]}）`
  }
  {
    const m = s.match(/Echo plan:\s*total=(\d+)/i)
    if (m) return `扩音器：集群规模（${m[1]}）`
  }
  {
    const m = s.match(/(\d+)\s+echo responses generated/i)
    if (m) return `扩音器：生成回应（${m[1]}）`
  }
  {
    const m = s.match(/\(total:\s*(\d+)\s+likes\)/i)
    if (m) return '扩音器：点赞放大'
  }
  {
    const m = s.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return '扩音器：扩散完成'
  }

  return null
}
