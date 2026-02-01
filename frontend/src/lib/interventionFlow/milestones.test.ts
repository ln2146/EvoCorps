import { describe, expect, it } from 'vitest'

import { toUserMilestone } from './milestones'

describe('toUserMilestone', () => {
  it('suppresses noisy phase headers (they duplicate role milestones)', () => {
    expect(toUserMilestone('📊 Phase 1: perception and decision')).toBeNull()
    expect(toUserMilestone('📈 Phase 3: feedback and iteration')).toBeNull()
  })

  it('maps Analyst lines', () => {
    expect(toUserMilestone('🔍 Analyst is analyzing content...')).toBe('开始分析')
    expect(toUserMilestone('📊 Analyst analysis completed:')).toBeNull()
    expect(toUserMilestone('Core viewpoint: Government overreach and privacy violation.')).toBe(
      '核心观点：Government overreach and privacy violation.',
    )
    expect(toUserMilestone('📊 Total weight calculated: 34.0 (based on 4 comments: 2 hot + 2 latest)')).toBe('权重汇总')
    expect(toUserMilestone('📊 Weighted per-comment sentiment: 0.10/1.0 (based on 4 selected comments: 2 hot + 2 latest)')).toBe('情绪汇总')
    expect(toUserMilestone('Viewpoint extremism: 8.6/10.0')).toBe('极端度：8.6/10.0')
    expect(toUserMilestone('Overall sentiment: 0.10/1.0')).toBe('情绪度：0.10/1.0')
    expect(toUserMilestone('Urgency level: 2')).toBe('紧急度：U2')
    expect(toUserMilestone('Trigger reasons: Viewpoint extremism too high & Sentiment too low')).toBe(
      '原因：极端度过高；情绪过低',
    )
    expect(toUserMilestone('Needs intervention: yes')).toBe('判定：需要干预')
    expect(toUserMilestone('Needs intervention: no')).toBe('判定：不需要干预')
    expect(toUserMilestone('🚨 Analyst determined opinion balance intervention needed!')).toBeNull()
    expect(toUserMilestone('⚠️ Alert generated - Urgency: 2')).toBe('告警：已生成（U2）')
  })

  it('does not truncate long extracted text (no ellipsis)', () => {
    const long = 'Core viewpoint: ' + 'A'.repeat(200)
    const out = toUserMilestone(long)
    expect(out).toBe('核心观点：' + 'A'.repeat(200))
    expect(out).not.toContain('…')
  })

  it('maps Strategist lines', () => {
    expect(toUserMilestone('⚖️ Strategist is creating strategy...')).toBe('生成策略')
    expect(toUserMilestone('🎯 Selected optimal strategy: balanced_response')).toBe('策略选定（balanced_response）')
    expect(toUserMilestone('📋 Step 4: Format as agent instructions')).toBe('输出指令')
    expect(toUserMilestone('🎯 Core argument: The health checks are designed to improve public health, not control...')).toBe(
      '核心论点：The health checks are designed to improve public health, not control...',
    )
  })

  it('maps Leader lines', () => {
    expect(toUserMilestone('✍️  Step 3: USC-Generate - generate 6 candidate comments')).toBe('生成候选（6）')
    expect(toUserMilestone('🏆 Best selection: candidate_4 (total: 4.80)')).toBe('选定版本（candidate_4）')
    expect(toUserMilestone('💬 👑 Leader comment 1 on post post-18e9eb: ...')).toBe('评论已发布（1）')
  })

  it('maps Amplifier lines', () => {
    expect(toUserMilestone('⚖️ Activating Echo Agent cluster...')).toBe('启动集群')
    expect(toUserMilestone('📋 Echo plan: total=12, role distribution={...}')).toBe('集群规模（12）')
    expect(toUserMilestone('✅ 12 echo responses generated')).toBe('生成回应（12）')
    expect(toUserMilestone('💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)')).toBe('点赞放大')
    expect(toUserMilestone('🎉 Workflow completed - effectiveness score: 10.0/10')).toBe('扩散完成')
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
    expect(toUserMilestone('🎯 Target content: 【Trending Post Opinion Analysis】')).toBeNull()
    expect(toUserMilestone('📋 Intervention ID: action_20260130_232018')).toBeNull()
    expect(toUserMilestone('Post ID: post-f053ef')).toBeNull()
    expect(toUserMilestone('Author: agentverse_news')).toBeNull()
    expect(toUserMilestone('Total engagement: 48')).toBeNull()
  })
})
