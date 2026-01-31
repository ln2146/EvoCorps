import { describe, expect, it } from 'vitest'

import { createInitialFlowState, routeLogLine, stripLogPrefix } from './logRouter'

describe('stripLogPrefix', () => {
  it('strips timestamp + level prefix', () => {
    const raw = '2026-01-28 21:13:09,264 - INFO - ⚖️ Activating Echo Agent cluster...'
    expect(stripLogPrefix(raw)).toBe('⚖️ Activating Echo Agent cluster...')
  })
})

describe('routeLogLine', () => {
  it('initializes 4-line summaries per role', () => {
    const state = createInitialFlowState()

    for (const role of ['Analyst', 'Strategist', 'Leader', 'Amplifier'] as const) {
      expect(state.roles[role].summary).toHaveLength(4)
    }
  })

  it('routes by strong anchors and freezes previous role on switch', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:13:09,286 - INFO -   🔍 Analyst is analyzing content...')
    expect(state.activeRole).toBe('Analyst')
    expect(state.roles.Analyst.status).toBe('running')
    expect(state.roles.Analyst.during[state.roles.Analyst.during.length - 1]).toBe('分析师：开始分析')

    state = routeLogLine(state, '2026-01-28 21:13:42,092 - INFO -    📊 Analyst analysis completed:')
    expect(state.activeRole).toBe('Analyst')
    expect(state.roles.Analyst.during[state.roles.Analyst.during.length - 1]).toBe('分析师：完成分析')

    state = routeLogLine(state, '2026-01-28 21:13:50,253 - INFO - ⚖️ Strategist is creating strategy...')
    expect(state.activeRole).toBe('Strategist')
    expect(state.roles.Analyst.status).toBe('done')
    expect(state.roles.Analyst.after?.length).toBeGreaterThan(0)
    expect(state.roles.Analyst.during).toEqual([])
    expect(state.roles.Strategist.during[state.roles.Strategist.during.length - 1]).toBe('战略家：生成策略')
  })

  it('keeps lines under Amplifier after activating echo cluster (sticky) even if they contain Leader keywords', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:14:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...')
    expect(state.activeRole).toBe('Leader')

    state = routeLogLine(state, '2026-01-28 21:18:33,877 - INFO - ⚖️ Activating Echo Agent cluster...')
    expect(state.activeRole).toBe('Amplifier')
    expect(state.amplifierSticky).toBe(true)

    state = routeLogLine(state, '2026-01-28 21:18:33,637 - INFO - 💬 👑 Leader comment 1 on post post-18e9eb: ...')
    expect(state.activeRole).toBe('Amplifier')
    expect(state.roles.Amplifier.during[state.roles.Amplifier.during.length - 1]).toBe('领袖：评论已发布（1）')
  })

  it('releases amplifier sticky on monitoring and allows switching back to Analyst', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:18:33,877 - INFO - ⚖️ Activating Echo Agent cluster...')
    expect(state.activeRole).toBe('Amplifier')
    expect(state.amplifierSticky).toBe(true)

    state = routeLogLine(state, '2026-01-28 21:18:54,728 - INFO - 🔄 [Monitoring round 1/3]')
    expect(state.amplifierSticky).toBe(false)

    state = routeLogLine(state, '2026-01-28 21:18:54,728 - INFO -   🔍 Analyst monitoring - establish baseline data')
    expect(state.activeRole).toBe('Analyst')
    expect(state.roles.Analyst.status).toBe('running')
  })

  it('updates Analyst summary fields from key result lines', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:13:09,286 - INFO - 🔍 Analyst is analyzing content...')
    state = routeLogLine(state, '2026-01-28 21:13:50,217 - INFO -       Viewpoint extremism: 8.6/10.0')
    state = routeLogLine(state, '2026-01-28 21:13:50,217 - INFO -       Overall sentiment: 0.10/1.0')
    state = routeLogLine(state, '2026-01-28 21:13:50,251 - INFO -       Needs intervention: yes')
    state = routeLogLine(state, '2026-01-28 21:13:50,251 - INFO -       Urgency level: 3')
    state = routeLogLine(state, '2026-01-28 21:13:50,251 - INFO -       Trigger reasons: Viewpoint extremism too high & Sentiment too low')

    expect(state.roles.Analyst.summary[0]).toContain('判定：')
    expect(state.roles.Analyst.summary[0]).toContain('U3')
    expect(state.roles.Analyst.summary[1]).toContain('8.6/10.0')
    expect(state.roles.Analyst.summary[2]).toContain('0.10/1.0')
    expect(state.roles.Analyst.summary[3]).toContain('触发原因：')
  })

  it('updates Strategist summary fields from strategy selection lines', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:13:50,253 - INFO - ⚖️ Strategist is creating strategy...')
    state = routeLogLine(state, '2026-01-30 20:46:25,342 - INFO - 🎯 Recommended strategy: action_log, confidence: 0.443')
    state = routeLogLine(state, '2026-01-28 21:14:25,697 - INFO -         🎯 Selected optimal strategy: balanced_response')
    state = routeLogLine(state, '2026-01-28 21:14:49,879 - INFO -      👑 Leader style: diplomatic')
    state = routeLogLine(state, '2026-01-28 21:14:49,879 - INFO -         💬 Tone: empathetic')

    expect(state.roles.Strategist.summary.join(' ')).toContain('策略：')
    expect(state.roles.Strategist.summary.join(' ')).toContain('balanced_response')
    expect(state.roles.Strategist.summary.join(' ')).toContain('置信度：0.443')
    expect(state.roles.Strategist.summary.join(' ')).toContain('diplomatic')
    expect(state.roles.Strategist.summary.join(' ')).toContain('empathetic')
  })

  it('updates Leader summary fields from USC generate/vote lines', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:14:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...')
    state = routeLogLine(state, '2026-01-28 21:15:36,733 - INFO - ✍️  Step 3: USC-Generate - generate 6 candidate comments')
    state = routeLogLine(state, '2026-01-28 21:18:33,636 - INFO -    🏆 Best selection: candidate_4 (total: 4.80)')
    state = routeLogLine(state, '2026-01-28 21:18:33,636 - INFO -    Best candidate score: 4.80/5.0')

    expect(state.roles.Leader.summary.join(' ')).toContain('候选：6')
    expect(state.roles.Leader.summary.join(' ')).toContain('选定：candidate_4')
    expect(state.roles.Leader.summary.join(' ')).toContain('评分：4.80')
  })

  it('updates Leader publish summary when leader comment is posted', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:14:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...')
    state = routeLogLine(state, '2026-01-28 21:18:33,637 - INFO - 💬 👑 Leader comment 1 on post post-18e9eb: ...')

    expect(state.roles.Leader.summary[3]).toContain('发布：')
    expect(state.roles.Leader.summary[3]).toContain('1')
  })

  it('updates Amplifier summary fields from echo/likes/effectiveness lines', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:18:33,877 - INFO - ⚖️ Activating Echo Agent cluster...')
    state = routeLogLine(state, '2026-01-28 21:18:33,877 - INFO -   📋 Echo plan: total=12, role distribution={...}')
    state = routeLogLine(state, '2026-01-28 21:18:53,942 - INFO -   ✅ 12 echo responses generated')
    state = routeLogLine(state, '2026-01-28 21:18:54,726 - INFO -   💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)')
    state = routeLogLine(state, '2026-01-28 21:18:54,727 - INFO - 🎉 Workflow completed - effectiveness score: 10.0/10')

    expect(state.roles.Amplifier.summary.join(' ')).toContain('12')
    expect(state.roles.Amplifier.summary.join(' ')).toContain('点赞：+480')
    expect(state.roles.Amplifier.summary.join(' ')).toContain('效果：10.0/10')
  })

  it('stores full post content and feed score in context', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:24:38,434 - INFO - Feed score: 27.10')
    state = routeLogLine(state, '2026-01-28 21:24:38,434 - INFO - Post content: [NEWS] Hello world...')

    expect(state.context.feedScore).toBeCloseTo(27.1)
    expect(state.context.postContent).toBe('[NEWS] Hello world...')
  })

  it('stores full leader comment bodies in context', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:18:33,637 - INFO - 💬 👑 Leader comment 1 on post post-18e9eb: Full body here')

    expect(state.context.leaderComments).toEqual(['Full body here'])
  })
})
