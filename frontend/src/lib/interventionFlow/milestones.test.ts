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
  })

  it('maps per-comment scoring lines (keep raw content, translate labels)', () => {
    expect(toUserMilestone('🔍 Comment 1 LLM result: (8.0, 0.1)')).toBe('🔍 评论1 模型结果： (8.0, 0.1)')
    expect(toUserMilestone('📊 Comment 1: sentiment=0.10, likes=12, weight=0.325, contribution=0.033')).toBe(
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
    expect(toUserMilestone('🎯 Selected optimal strategy: balanced_response')).toBe('战略家：策略选定：balanced_response')
    expect(toUserMilestone('📋 Step 4: Format as agent instructions')).toBe('战略家：输出指令')
  })

  it('maps Leader lines', () => {
    expect(toUserMilestone('🎯 Leader Agent starts USC process and generates candidate comments...')).toBe('领袖：启动生成流程')
    expect(toUserMilestone('✍️  Step 3: USC-Generate - generate 6 candidate comments')).toBe('领袖：生成候选（6）')
    expect(toUserMilestone('Retrieved 5 relevant arguments')).toBe('领袖：检索论据（5）')
    expect(toUserMilestone('🏆 Best selection: candidate_4 (total: 4.80)')).toBe('领袖：选定版本（candidate_4）')
    expect(toUserMilestone('💬 👑 Leader comment 1 on post post-18e9eb: ...')).toBe('领袖：评论已发布（1）')
    expect(toUserMilestone('✅ USC workflow completed')).toBe('领袖：生成完成')
  })

  it('maps Amplifier lines', () => {
    expect(toUserMilestone('⚖️ Activating Echo Agent cluster...')).toBe('扩音器：启动回声集群')
    expect(toUserMilestone('🚀 Start parallel execution of 12 agent tasks...')).toBe('扩音器：并行执行（12）')
    expect(toUserMilestone('📊 Echo Agent results: 12 succeeded, 0 failed')).toBe('扩音器：执行结果（成功 12 / 失败 0）')
    expect(toUserMilestone('📋 Echo plan: total=12, role distribution={...}')).toBe('扩音器：集群规模（12）')
    expect(toUserMilestone('✅ 12 echo responses generated')).toBe('扩音器：生成回应（12）')
    expect(toUserMilestone('💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)')).toBe('扩音器：点赞放大')
    expect(toUserMilestone('🎉 Workflow completed - effectiveness score: 10.0/10')).toBe('扩音器：扩散完成')
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

  it('returns null for full-rendered content lines', () => {
    expect(toUserMilestone('Post content: hello world')).toBeNull()
    expect(toUserMilestone('Feed score: 27.10')).toBeNull()
  })
})
