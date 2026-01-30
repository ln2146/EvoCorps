import { describe, expect, it } from 'vitest'

import { createInitialFlowState, routeLogLine, stripLogPrefix } from './logRouter'

describe('stripLogPrefix', () => {
  it('strips timestamp + level prefix', () => {
    const raw = '2026-01-28 21:13:09,264 - INFO - ⚖️ Activating Echo Agent cluster...'
    expect(stripLogPrefix(raw)).toBe('⚖️ Activating Echo Agent cluster...')
  })
})

describe('routeLogLine', () => {
  it('routes by strong anchors and freezes previous role on switch', () => {
    let state = createInitialFlowState()

    state = routeLogLine(state, '2026-01-28 21:13:09,286 - INFO -   🔍 Analyst is analyzing content...')
    expect(state.activeRole).toBe('Analyst')
    expect(state.roles.Analyst.status).toBe('running')
    expect(state.roles.Analyst.during[state.roles.Analyst.during.length - 1]).toBe('🔍 Analyst is analyzing content...')

    state = routeLogLine(state, '2026-01-28 21:13:42,092 - INFO -    📊 Analyst analysis completed:')
    expect(state.activeRole).toBe('Analyst')
    expect(state.roles.Analyst.during[state.roles.Analyst.during.length - 1]).toBe('📊 Analyst analysis completed:')

    state = routeLogLine(state, '2026-01-28 21:13:50,253 - INFO - ⚖️ Strategist is creating strategy...')
    expect(state.activeRole).toBe('Strategist')
    expect(state.roles.Analyst.status).toBe('done')
    expect(state.roles.Analyst.after?.length).toBeGreaterThan(0)
    expect(state.roles.Analyst.during).toEqual([])
    expect(state.roles.Strategist.during[state.roles.Strategist.during.length - 1]).toBe('⚖️ Strategist is creating strategy...')
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
    expect(state.roles.Amplifier.during[state.roles.Amplifier.during.length - 1]).toBe('💬 👑 Leader comment 1 on post post-18e9eb: ...')
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
})
