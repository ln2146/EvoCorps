import { describe, expect, it } from 'vitest'

import type { Role } from './logRouter'
import { buildRolePills } from './rolePills'

describe('buildRolePills', () => {
  it('shows Analyst pills in the required order and labels', () => {
    const role: Role = 'Analyst'
    const pills = buildRolePills(role, {
      feedScore: 26.4,
      summary: ['判定：需要干预（U3）', '极端度：2.9/10.0', '情绪：0.52/1.0'],
    })

    expect(pills).toEqual(['热度：26.40', '情绪度：0.52/1.0', '极端度：2.9/10.0', '干预：需要'])
  })

  it('does not include heat for Strategist/Leader/Amplifier, and uses their summary lines instead', () => {
    const strategist = buildRolePills('Strategist', {
      feedScore: 999.9,
      summary: ['策略：balanced_response', '置信度：0.43', '风格：diplomatic / empathetic', '核心论点：...'],
      related: {
        amplifierSummary: ['Amplifier: 12'],
      },
    })
    expect(strategist).toEqual(['策略：balanced_response', '风格：diplomatic', '语气：empathetic', '扩散者：12'])
    expect(strategist.join(' ')).not.toContain('热度')
    // Strategist core argument should be shown in the dynamic panel, not duplicated in the summary pills.
    expect(strategist.join(' ')).not.toContain('核心论点：')

    const leader = buildRolePills('Leader', {
      feedScore: 999.9,
      summary: ['候选：6', '选定：candidate_4', '评分：4.80/5.0', '发布：2'],
    })
    expect(leader[0]).toBe('候选：6')
    expect(leader.join(' ')).not.toContain('热度')
    expect(leader.join(' ')).not.toContain('发布：')
  })

  it('filters placeholder confidence line', () => {
    const strategist = buildRolePills('Strategist', {
      summary: ['策略：x', '置信度：—', '风格：y', '核心论点：z'],
      related: {
        amplifierSummary: ['Amplifier: 3'],
      },
    })
    expect(strategist.join(' ')).not.toContain('置信度：—')
    expect(strategist.join(' ')).not.toContain('核心论点：')
  })
})
