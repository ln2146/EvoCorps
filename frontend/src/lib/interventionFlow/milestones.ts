export function toUserMilestone(cleanLine: string): string | null {
  const s = cleanLine.trim().replace(/^(?:INFO|ERROR|提示|错误)[:：]\s*/i, '')
  if (!s) return null

  // Infra noise
  if (s.startsWith('HTTP Request:')) return null
  if (s.startsWith('Request URL:')) return null
  if (s.startsWith('Wikipedia:')) return null
  if (s.startsWith('📊 Cache status:')) return null
  // Phase headers are redundant in the UI (they often duplicate the role-level milestones).
  if (/^📊\s*Phase\s+\d+:/i.test(s)) return null
  if (/^📈\s*Phase\s+\d+:/i.test(s)) return null
  // Intervention meta header (keep content original; translate only fixed labels).
  {
    const m = s.match(/^📋\s*Intervention ID:\s*(.+)$/i)
    if (m) return `📋 干预ID：${m[1].trim()}`
  }
  {
    const m = s.match(/^🎯\s*Target content:\s*(.+)$/i)
    if (m) return `🎯 目标内容：${m[1].trim()}`
  }
  {
    const m = s.match(/^Post ID:\s*(.+)$/i)
    if (m) return `帖子ID：${m[1].trim()}`
  }
  {
    const m = s.match(/^Author:\s*(.+)$/i)
    if (m) return `作者：${m[1].trim()}`
  }
  {
    const m = s.match(/^Total engagement:\s*(\d+)\b/i)
    if (m) return `总互动量：${m[1]}`
  }
  {
    const m = s.match(/^Feed score:\s*([0-9.]+)\b/i)
    if (m) return `热度值：${m[1]}`
  }
  {
    const m = s.match(/^Post content:\s*(.+)$/i)
    // Post content is rendered in the dedicated post card; avoid duplicating it in the stream.
    if (m) return null
  }

  // Leader memory + voting detail (fixed labels; values stay original)
  {
    const m = s.match(/^Argument system status:\s*(.+)$/i)
    if (m) return `论据系统状态：${m[1].trim()}`
  }
  {
    const m = s.match(/^Theme:\s*(.+)$/i)
    if (m) return `主题：${m[1].trim()}`
  }
  {
    const m = s.match(/^Keyword:\s*(.+)$/i)
    if (m) {
      const kw = m[1].trim()
      if (kw.toLowerCase() === 'unknown') return null
      return `关键词：${kw}`
    }
  }
  if (/^Evidence retrieval flow:\s*$/i.test(s)) return '论据检索流程：'
  if (/^1\.\s*Database retrieval:\s*$/i.test(s)) return '1. 检索数据库：'
  {
    const m = s.match(/^-+\s*Theme match:\s*(.+)$/i)
    if (m) return `- 主题匹配：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*Keyword retrieval:\s*(.+)$/i)
    if (m) return `- 关键词检索：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*Viewpoint retrieval:\s*(.+)$/i)
    if (m) return `- 观点检索：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*DB evidence read:\s*(.+)$/i)
    if (m) return `- DB证据读取：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*Conclusion:\s*(.+)$/i)
    if (m) return `- 结论：${m[1].trim()}`
  }
  {
    const m = s.match(/^2\.\s*Wikipedia retrieval:\s*(.+)$/i)
    if (m) return `2. 检索维基百科：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*Wikipedia selected evidence\s*(\d+):\s*(.+)$/i)
    if (m) return `- 维基百科入选论据${m[1]}：${m[2].trim()}`
  }
  {
    const m = s.match(/^3\.\s*LLM evidence generation:\s*(.+)$/i)
    if (m) return `3. LLM 生成论据：${m[1].trim()}`
  }
  {
    const m = s.match(/^-+\s*LLM evidence\/comment\s*(\d+):\s*(.+)$/i)
    if (m) return `- LLM论据/评论${m[1]}：${m[2].trim()}`
  }
  {
    const m = s.match(/^Argument\s+(\d+):\s*(.+)$/i)
    if (m) return `论据${m[1]}：${m[2].trim()}`
  }
  {
    const m = s.match(/^candidate_(\d+):\s*total\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `候选${m[1]}：总分 ${m[2].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Best candidate score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return `最佳得分：${m[1].replace(/\s+/g, '')}`
  }
  {
    const m = s.match(/^Best comment length:\s*(\d+)\s*characters/i)
    if (m) return `最佳长度：${m[1]} 字符`
  }
  {
    const m = s.match(/^💬\s*First leader comment ID:\s*(\S+)/i)
    if (m) return `第一条领袖评论ID：${m[1].trim()}`
  }
  {
    const m = s.match(/^💬\s*Second leader comment ID:\s*(\S+)/i)
    if (m) return `第二条领袖评论ID：${m[1].trim()}`
  }
  {
    const m = s.match(/^🎯\s*Target post:\s*(\S+)/i)
    if (m) return `目标帖子：${m[1].trim()}`
  }

  // New round anchor (workflow starts a new "action_..." execution).
  {
    const m = s.match(/Start workflow execution\s*-\s*Action ID:\s*([A-Za-z0-9_:-]+)/i)
    if (m) return `新回合：${m[1]}`
  }

  // Analyst
  if (/Analyst is analyzing/i.test(s)) return '分析师：开始分析'
  // Prefer rendering the extracted core viewpoint line, so we don't show two "analysis done" lines.
  {
    const m = s.match(/^Extracted core viewpoint:\s*(.+)$/i)
    if (m) return `核心观点：${m[1].trim()}`
  }
  {
    const m = s.match(/^Core viewpoint:\s*(.+)$/i)
    if (m) return `核心观点：${m[1].trim()}`
  }
  if (/Total weight calculated:/i.test(s)) return '分析师：权重汇总'
  if (/Weighted per-comment sentiment:/i.test(s)) return '分析师：情绪汇总'
  {
    const m = s.match(/^🔍\s*Comment\s+(\d+)\s+LLM result:\s*(.+)$/i)
    if (m) {
      const raw = m[2].trim()
      const cleaned = raw.replace(/^\(\s*/, '').replace(/\s*\)$/, '')
      const parts = cleaned.split(',').map((p) => p.trim()).filter(Boolean)
      const extremity = parts[0] ?? ''
      const sentiment = parts[1] ?? ''
      if (extremity && sentiment && !Number.isNaN(Number(extremity)) && !Number.isNaN(Number(sentiment))) {
        return `🔍 评论${m[1]} 计算结果：极端度 ${extremity}/10.0，情绪度 ${sentiment}/1.0`
      }
      return `🔍 评论${m[1]} 计算结果：${raw}`
    }
  }
  {
    const m = s.match(/^📊\s*Comment\s+(\d+):\s*(.+)$/i)
    if (m) {
      const idx = m[1]
      const raw = m[2]
      const zh = raw
        .replace(/\bsentiment\s*=/gi, '情绪=')
        .replace(/\blikes\s*=/gi, '点赞=')
        .replace(/\bweight\s*=/gi, '权重=')
        .replace(/\bcontribution\s*=/gi, '贡献=')
        .replace(/\s*,\s*/g, '，')
      return `📊 评论${idx}：${zh.trim()}`
    }
  }
  {
    const m = s.match(/^(?:📝\s*)?Comment\s+(\d+)\s+content:\s*(.+)$/i)
    if (m) return `评论${m[1]} 内容：${m[2].trim()}`
  }
  {
    const m = s.match(/^Urgency level:\s*(\d+)\b/i)
    if (m) return `分析师：紧急程度 ${m[1]}`
  }
  if (/Analyst determined opinion balance intervention needed/i.test(s)) return '🚨 分析师判定需要舆论平衡干预！'
  {
    const m = s.match(/Alert generated\s*-\s*Urgency:\s*(\d+)\b/i)
    if (m) return `⚠️ 已生成告警：紧急程度 ${m[1]}`
  }
  if (/generate baseline effectiveness report/i.test(s)) return '分析师：生成基线报告'
  if (/Analyst monitoring\s*-\s*establish baseline data/i.test(s)) return '分析师：建立基线数据'
  if (/Monitoring task started/i.test(s)) return '分析师：启动监测任务'
  if (/Will continue monitoring/i.test(s)) return '分析师：持续监测与动态调整'
  if (/Needs intervention:\s*yes\b/i.test(s)) return '分析师：判定需要干预'
  if (/Needs intervention:\s*no\b/i.test(s)) return '分析师：判定无需干预（继续监测，无需执行干预）'
  // 修复：匹配带 emoji 的日志行 (✅ No intervention needed...)
  if (/No intervention needed for post.*Workflow completed/i.test(s) || /✅\s*No intervention needed/i.test(s)) return '✅ 分析完成：无需干预，流程结束'
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
  if (/Strategist Agent\s*-\s*start intelligent strategy creation workflow/i.test(s)) return '战略家：启动智能策略生成'
  // Phase 3 evaluation (feedback-only — no Leader/Amplifier)
  {
    const m = s.match(/Strategist evaluating\s+(\S+)\s+effectiveness/i)
    if (m) return `战略家：评估${m[1] === 'Baseline' ? '基线' : `第${m[1].replace(/^Round\s*/i, '')}轮`}干预效果`
  }
  if (/Strategy assessment:\s*intervention partially effective/i.test(s)) return '战略家：干预初显效果，继续监测'
  if (/Strategy assessment:\s*limited effect/i.test(s)) return '战略家：效果有限，下轮扫描重新评估'
  if (/Strategist phase 3 evaluation complete/i.test(s)) return '战略家：Phase 3 评估完成'
  if (/Step\s*1:\s*Confirm alert information/i.test(s)) return '战略家：确认告警信息'
  {
    const m = s.match(/^📊\s*Alert ID:\s*(.+)$/i)
    if (m) return `告警ID：${m[1].trim()}`
  }
  {
    const m = s.match(/^🚨\s*Urgency:\s*(.+)$/i)
    if (m) return `紧急程度：${m[1].trim()}`
  }
  {
    const m = s.match(/^📝\s*Recommended action:\s*(.+)$/i)
    if (m) return `建议动作：${m[1].trim()}`
  }
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
    const m = s.match(/(?:🔄|✅)\s*Generated\s+(\d+)\s+strategy options/i)
    if (m) return `战略家：生成策略选项（${m[1]}）`
  }
  {
    const m = s.match(/^📝\s*Decision rationale:\s*(.+)$/i)
    if (m) return `战略家：决策依据：${m[1].trim()}`
  }
  {
    const m = s.match(/^🎯\s*Selected optimal option:\s*(.+)$/i)
    if (m) return `战略家：选定最优方案：${m[1].trim()}`
  }
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
  if (/Step\s*1:\s*Parse strategist instructions/i.test(s)) return '领袖：解析战略家指令'
  if (/Step\s*2:\s*Search cognitive memory/i.test(s)) return '领袖：检索记忆论据库'
  if (/Step\s*4:\s*USC-Vote/i.test(s)) return '领袖：评分投票'
  if (/Step\s*5:\s*Output final copy/i.test(s)) return '领袖：输出最终文案'
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
    const m = s.match(/^Successfully generated\s+(\d+)\s+candidates/i)
    if (m) return `领袖：生成候选完成（${m[1]}）`
  }
  {
    const m = s.match(/^Candidate\s+(\d+)\s*:\s*(.+)$/i)
    if (m) return `候选${m[1]}：${m[2].trim()}`
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
  if (/Activating Amplifier Agent cluster/i.test(s)) return '扩散者：启动集群'
  {
    const m = s.match(/Start parallel execution of\s+(\d+)\s+agent tasks/i)
    if (m) return `扩散者：并行执行（${m[1]}）`
  }
  {
    const m = s.match(/Amplifier Agent results:\s*(\d+)\s+succeeded,\s*(\d+)\s+failed/i)
    if (m) return `扩散者：执行结果（成功 ${m[1]} / 失败 ${m[2]}）`
  }
  {
    const m = s.match(/Amplifier plan:\s*total=(\d+)/i)
    if (m) return `扩散者：集群规模（${m[1]}）`
  }
  {
    const m = s.match(/(\d+)\s+amplifier responses generated/i)
    if (m) return `扩散者：生成回应（${m[1]}）`
  }
  {
    // Platform "like boosting" is internal plumbing and should not be shown in the UI.
    if (/\(total:\s*\d+\s+likes\)/i.test(s)) return null
    if (/Amplifier\s+Agents\s+start\s+liking\s+leader comments/i.test(s)) return null
    if (/successfully liked leader comments/i.test(s)) return null
    {
      const m = s.match(/^\s*💖\s*(\d+)\s+Amplifier\s+Agents\s+liked\s+leader comments/i)
      if (m) return `扩散者：点赞扩散（${m[1]}）`
    }
  }
  {
    const m = s.match(/effectiveness score:\s*([0-9.]+\s*\/\s*[0-9.]+)/i)
    if (m) return '扩散者：点赞扩散完成'
  }

  return null
}
