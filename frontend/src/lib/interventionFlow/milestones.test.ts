import { describe, expect, it } from 'vitest'

import { toUserMilestone } from './milestones'

describe('toUserMilestone', () => {
  it('maps Analyst lines', () => {
    expect(toUserMilestone('🔍 Analyst is analyzing content...')).toBe('Analyst: Analysis started')
    expect(toUserMilestone('📊 Analyst analysis completed:')).toBe('Analyst: Analysis completed')
    expect(toUserMilestone('Needs intervention: yes')).toBe('Analyst: Intervention required')
  })

  it('maps Strategist lines', () => {
    expect(toUserMilestone('⚖️ Strategist is creating strategy...')).toBe('Strategist: Strategy drafting')
    expect(toUserMilestone('🎯 Selected optimal strategy: balanced_response')).toBe('Strategist: Strategy selected (balanced_response)')
  })

  it('maps Leader lines', () => {
    expect(toUserMilestone('✍️  Step 3: USC-Generate - generate 6 candidate comments')).toBe('Leader: Candidates generated (6)')
    expect(toUserMilestone('🏆 Best selection: candidate_4 (total: 4.80)')).toBe('Leader: Best selection (candidate_4)')
    expect(toUserMilestone('💬 👑 Leader comment 1 on post post-18e9eb: ...')).toBe('Leader: Comment posted (1)')
  })

  it('maps Amplifier lines', () => {
    expect(toUserMilestone('⚖️ Activating Echo Agent cluster...')).toBe('Amplifier: Echo cluster activated')
    expect(toUserMilestone('📋 Echo plan: total=12, role distribution={...}')).toBe('Amplifier: Echo plan (12)')
    expect(toUserMilestone('✅ 12 echo responses generated')).toBe('Amplifier: Responses generated (12)')
    expect(toUserMilestone('💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)')).toBe('Amplifier: Likes boosted (+480)')
    expect(toUserMilestone('🎉 Workflow completed - effectiveness score: 10.0/10')).toBe('Amplifier: Effectiveness (10.0/10)')
  })

  it('returns null for infra noise', () => {
    expect(toUserMilestone('HTTP Request: POST https://x')).toBeNull()
    expect(toUserMilestone('Request URL: https://x')).toBeNull()
    expect(toUserMilestone('Wikipedia: language=en')).toBeNull()
    expect(toUserMilestone('📊 Cache status: embedding=1')).toBeNull()
  })
})

