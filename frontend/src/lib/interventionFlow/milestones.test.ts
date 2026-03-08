import { describe, expect, it } from 'vitest'

import { toUserMilestone } from './milestones'

describe('toUserMilestone', () => {
  it('suppresses noisy phase headers (they duplicate role milestones)', () => {
    expect(toUserMilestone('📊 Phase 1: perception and decision')).toBeNull()
    expect(toUserMilestone('📈 Phase 3: feedback and iteration')).toBeNull()
  })

  it('maps Analyst lines', () => {
    expect(toUserMilestone('🔍 Analyst is analyzing content...')).toBe('分析师：开始分析')
    expect(toUserMilestone('📊 Analyst analysis completed:')).toBeNull()
    expect(toUserMilestone('Core viewpoint: Government overreach and privacy violation.')).toBe(
      '核心观点：Government overreach and privacy violation.',
    )
    expect(toUserMilestone('📊 Total weight calculated: 34.0 (based on 4 comments: 2 hot + 2 latest)')).toBe('分析师：权重汇总')
    expect(toUserMilestone('📊 Weighted per-comment sentiment: 0.10/1.0 (based on 4 selected comments: 2 hot + 2 latest)')).toBe('分析师：情绪汇总')
    expect(toUserMilestone('Viewpoint extremism: 8.6/10.0')).toBe('分析师：极端度 8.6/10.0')
    expect(toUserMilestone('Overall sentiment: 0.10/1.0')).toBe('分析师：情绪度 0.10/1.0')
    expect(toUserMilestone('Trigger reasons: Viewpoint extremism too high & Sentiment too low')).toBe(
      '触发原因： 观点极端度太高 & 情绪度太低',
    )
    expect(toUserMilestone('Needs intervention: yes')).toBe('分析师：判定需要干预')
    expect(toUserMilestone('Urgency level: 2')).toBe('分析师：紧急程度 2')
    expect(toUserMilestone('🚨 Analyst determined opinion balance intervention needed!')).toBe('🚨 分析师判定需要舆论平衡干预！')
    expect(toUserMilestone('⚠️  Alert generated - Urgency: 2')).toBe('⚠️ 已生成告警：紧急程度 2')
  })

  it('maps intervention header/meta lines (keep post content original)', () => {
    expect(toUserMilestone('📋 Intervention ID: action_20260130_232018')).toBe('📋 干预ID：action_20260130_232018')
    expect(toUserMilestone('🎯 Target content: 【Trending Post Opinion Analysis】')).toBe('🎯 目标内容：【Trending Post Opinion Analysis】')
    expect(toUserMilestone('Post ID: post-f053ef')).toBe('帖子ID：post-f053ef')
    expect(toUserMilestone('Author: agentverse_news')).toBe('作者：agentverse_news')
    expect(toUserMilestone('Total engagement: 48')).toBe('总互动量：48')
    expect(toUserMilestone('Feed score: 205.20')).toBe('热度值：205.20')
    // Post content is rendered via the dedicated post content block; do not repeat it as a milestone line.
    expect(toUserMilestone("Post content: [NEWS] Purdue's 'Robust Testing' is Actually Mass Surveillance!")).toBeNull()
  })

  it('maps leader memory + voting detail labels', () => {
    expect(toUserMilestone('Argument system status: completely_new')).toBe('论据系统状态：completely_new')
    expect(toUserMilestone('Theme: Science & Health')).toBe('主题：Science & Health')
    expect(toUserMilestone('Keyword: unknown')).toBeNull()
    expect(toUserMilestone('Keyword: UNKNOWN')).toBeNull()
    expect(toUserMilestone('Keyword: privacy')).toBe('关键词：privacy')
    expect(toUserMilestone('Argument 1: Legal right to privacy ... (relevance: 0.60)')).toBe(
      '论据1：Legal right to privacy ... (relevance: 0.60)',
    )

    expect(toUserMilestone('candidate_1: total 4.80/5.0')).toBe('候选1：总分 4.80/5.0')
    expect(toUserMilestone('Best candidate score: 4.80/5.0')).toBe('最佳得分：4.80/5.0')
    expect(toUserMilestone('Best comment length: 650 characters')).toBe('最佳长度：650 字符')

    expect(toUserMilestone('💬 First leader comment ID: comment-606ac9')).toBe('第一条领袖评论ID：comment-606ac9')
    expect(toUserMilestone('🎯 Target post: post-f053ef')).toBe('目标帖子：post-f053ef')
    expect(toUserMilestone('💬 Second leader comment ID: comment-0cd2c7')).toBe('第二条领袖评论ID：comment-0cd2c7')
  })

  it('maps leader evidence retrieval flow lines from English backend to Chinese UI labels', () => {
    expect(toUserMilestone('Evidence retrieval flow:')).toBe('论据检索流程：')
    expect(toUserMilestone('1. Database retrieval:')).toBe('1. 检索数据库：')
    expect(toUserMilestone('- Theme match: theme=Science & Health, matched=True')).toBe(
      '- 主题匹配：theme=Science & Health, matched=True',
    )
    expect(toUserMilestone('- Keyword retrieval: keyword=vaccine, sim=0.650<0.700 (fail)')).toBe(
      '- 关键词检索：keyword=vaccine, sim=0.650<0.700 (fail)',
    )
    expect(toUserMilestone('- Viewpoint retrieval: skipped (reason: keyword threshold not met or no matched viewpoint)')).toBe(
      '- 观点检索：skipped (reason: keyword threshold not met or no matched viewpoint)',
    )
    expect(toUserMilestone('- Conclusion: skipped (reason: keyword similarity below threshold)')).toBe(
      '- 结论：skipped (reason: keyword similarity below threshold)',
    )
    expect(toUserMilestone('2. Wikipedia retrieval: keyword=vaccine, retrieved=15, selected=0 (retrieved but none passed acceptance filtering)')).toBe(
      '2. 检索维基百科：keyword=vaccine, retrieved=15, selected=0 (retrieved but none passed acceptance filtering)',
    )
    expect(toUserMilestone('- Wikipedia selected evidence 1: score=0.77, content=W1')).toBe(
      '- 维基百科入选论据1：score=0.77, content=W1',
    )
    expect(toUserMilestone('3. LLM evidence generation: count=3, low_confidence=3')).toBe(
      '3. LLM 生成论据：count=3, low_confidence=3',
    )
    expect(toUserMilestone('- LLM evidence/comment 1: score=0.30, content=L1')).toBe(
      '- LLM论据/评论1：score=0.30, content=L1',
    )
  })

  it('maps per-comment scoring lines (keep raw content, translate labels)', () => {
    expect(toUserMilestone('🔍 Comment 1 LLM result: (8.0, 0.1)')).toBe('🔍 评论1 计算结果：极端度 8.0/10.0，情绪度 0.1/1.0')
    expect(toUserMilestone('INFO: 🔍 Comment 1 LLM result: (8.0, 0.1)')).toBe('🔍 评论1 计算结果：极端度 8.0/10.0，情绪度 0.1/1.0')
    expect(toUserMilestone('📝 Comment 1 content: This is the original comment body.')).toBe(
      '评论1 内容：This is the original comment body.',
    )
    expect(toUserMilestone('📊 Comment 1: sentiment=0.10, likes=12, weight=0.325, contribution=0.033')).toBe(
      '📊 评论1：情绪=0.10，点赞=12，权重=0.325，贡献=0.033',
    )
    expect(toUserMilestone('INFO: 📊 Comment 1: sentiment=0.10, likes=12, weight=0.325, contribution=0.033')).toBe(
      '📊 评论1：情绪=0.10，点赞=12，权重=0.325，贡献=0.033',
    )
    expect(toUserMilestone('Comment 2 content: This is the original comment body.')).toBe(
      '评论2 内容：This is the original comment body.',
    )
  })

  it('does not truncate long extracted text (no ellipsis)', () => {
    const long = 'Core viewpoint: ' + 'A'.repeat(200)
    const out = toUserMilestone(long)
    expect(out).toBe('核心观点：' + 'A'.repeat(200))
    expect(out).not.toContain('…')
  })

  it('maps Strategist lines', () => {
    expect(toUserMilestone('⚖️ Strategist is creating strategy...')).toBe('战略家：生成策略')
    expect(toUserMilestone('📋 Strategist Agent - start intelligent strategy creation workflow')).toBe('战略家：启动智能策略生成')
    expect(toUserMilestone('✅ Step 1: Confirm alert information')).toBe('战略家：确认告警信息')
    expect(toUserMilestone('📊 Alert ID: post-f053ef')).toBe('告警ID：post-f053ef')
    expect(toUserMilestone('🚨 Urgency: 2/4')).toBe('紧急程度：2/4')
    expect(toUserMilestone('📝 Recommended action: Do X then Y.')).toBe('建议动作：Do X then Y.')
    expect(toUserMilestone('🎯 Selected optimal strategy: balanced_response')).toBe('战略家：策略选定：balanced_response')
    expect(toUserMilestone('🔄 Generated 5 strategy options')).toBe('战略家：生成策略选项（5）')
    expect(toUserMilestone('📝 Decision rationale: Select Community Partnership based on Low risk')).toBe(
      '战略家：决策依据：Select Community Partnership based on Low risk',
    )
    expect(toUserMilestone('🎯 Selected optimal option: Community Partnership')).toBe('战略家：选定最优方案：Community Partnership')
    expect(toUserMilestone('📋 Step 4: Format as agent instructions')).toBe('战略家：输出指令')
  })

  it('maps Leader lines', () => {
    expect(toUserMilestone('🎯 Leader Agent starts USC process and generates candidate comments...')).toBe('领袖：启动生成流程')
    expect(toUserMilestone('📋 Step 1: Parse strategist instructions')).toBe('领袖：解析战略家指令')
    expect(toUserMilestone('📚 Step 2: Search cognitive memory core-viewpoint argument base')).toBe('领袖：检索记忆论据库')
    expect(toUserMilestone('✍️  Step 3: USC-Generate - generate 6 candidate comments')).toBe('领袖：生成候选（6）')
    expect(toUserMilestone('🔍 Step 4: USC-Vote - score and select the best version')).toBe('领袖：评分投票')
    expect(toUserMilestone('📤 Step 5: Output final copy')).toBe('领袖：输出最终文案')
    expect(toUserMilestone('Retrieved 5 relevant arguments')).toBe('领袖：检索论据（5）')
    expect(toUserMilestone('🏆 Best selection: candidate_4 (total: 4.80)')).toBe('领袖：选定版本（candidate_4）')
    expect(toUserMilestone('💬 👑 Leader comment 1 on post post-18e9eb: ...')).toBe('领袖：评论已发布（1）')
    expect(toUserMilestone('✅ USC workflow completed')).toBe('领袖：生成完成')
  })

  it('maps Leader candidate generation detail lines', () => {
    expect(toUserMilestone('Successfully generated 6 candidates')).toBe('领袖：生成候选完成（6）')
    expect(toUserMilestone('Candidate 6: hello world')).toBe('候选6：hello world')
    expect(toUserMilestone('Candidate 6: hello world (angle: test)')).toBe('候选6：hello world (angle: test)')
  })

  it('maps Amplifier lines', () => {
    expect(toUserMilestone('⚖️ Activating amplifier Agent cluster...')).toBe('扩散者：启动集群')
    expect(toUserMilestone('⚖️ Activating Amplifier Agent cluster...')).toBe('扩散者：启动集群')
    expect(toUserMilestone('🚀 Start parallel execution of 12 agent tasks...')).toBe('扩散者：并行执行')
    expect(toUserMilestone('📊 amplifier Agent results: 12 succeeded, 0 failed')).toBe('扩散者：执行结果）')
    expect(toUserMilestone('📊 Amplifier Agent results: 12 succeeded, 0 failed')).toBe('扩散者：执行结果')
    expect(toUserMilestone('📋 amplifier plan: total=12, role distribution={...}')).toBe('扩散者：集群规模')
    expect(toUserMilestone('📋 Amplifier plan: total=12, role distribution={...}')).toBe('扩散者：集群规模')
    expect(toUserMilestone('✅ 12 amplifier responses generated')).toBe('扩散者：生成回应')
    expect(toUserMilestone('✅ 12 amplifier responses generated')).toBe('扩散者：生成回应')
    expect(toUserMilestone('💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)')).toBeNull()
    expect(toUserMilestone('💖 12 Amplifier Agents liked leader comments')).toBe('扩散者：点赞扩散')
    expect(toUserMilestone('🎉 Workflow completed - effectiveness score: 10.0/10')).toBe('扩散者：点赞扩散完成')
  })

  it('maps monitoring/baseline lines', () => {
    expect(toUserMilestone('📊 Analyst Agent - generate baseline effectiveness report')).toBe('分析师：生成基线报告')
    expect(toUserMilestone('🔍 Analyst monitoring - establish baseline data')).toBe('分析师：建立基线数据')
  })

  it('returns null for infra noise', () => {
    expect(toUserMilestone('HTTP Request: POST https://x')).toBeNull()
    expect(toUserMilestone('Request URL: https://x')).toBeNull()
    expect(toUserMilestone('Wikipedia: language=en')).toBeNull()
    expect(toUserMilestone('📊 Cache status: embedding=1')).toBeNull()
  })

  it('maps post content + feed score labels (keep body original)', () => {
    expect(toUserMilestone('Post content: hello world')).toBeNull()
    expect(toUserMilestone('Feed score: 27.10')).toBe('热度值：27.10')
  })
})
