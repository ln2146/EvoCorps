import { describe, expect, it } from 'vitest'

import { formatRoleStagesTooltip, getRoleStages } from './roleStages'

describe('roleStages', () => {
  it('defines Analyst stages', () => {
    expect(getRoleStages('Analyst')).toEqual(['内容识别', '评论抽样', '情绪度', '极端度', '干预判定', '监测评估'])
  })

  it('defines Strategist stages', () => {
    expect(getRoleStages('Strategist')).toEqual(['确认告警', '检索历史', '生成方案', '选择策略', '输出指令'])
  })

  it('defines Leader stages', () => {
    expect(getRoleStages('Leader')).toEqual(['解析指令', '检索论据', '生成候选', '投票选优', '发布评论'])
  })

  it('defines Amplifier stages', () => {
    expect(getRoleStages('Amplifier')).toEqual(['启动集群', '生成回应', '点赞放大', '扩散完成'])
  })

  it('formats tooltip as a single line', () => {
    expect(formatRoleStagesTooltip('Analyst')).toMatch(/内容识别.*->.*监测评估/)
  })
})

