import { describe, expect, it } from 'vitest'

import { getEmptyCopy } from './emptyCopy'

describe('getEmptyCopy', () => {
  it('returns a compact, user-facing hint when feature is disabled', () => {
    const copy = getEmptyCopy({ enabled: false })
    expect(copy.metrics).toMatch(/开启舆论平衡/)
    expect(copy.stream).toMatch(/开启舆论平衡/)

    // Should not include the old/verbose copy.
    expect(copy.metrics).not.toContain('暂无关键指标')
    expect(copy.stream).not.toContain('等待系统输出')
    expect(copy.stream).not.toContain('将自动订阅 workflow 日志流')
  })

  it('returns a compact hint when enabled but no output yet', () => {
    const copy = getEmptyCopy({ enabled: true })
    expect(copy.metrics).toMatch(/运行|分析|提取/)
    expect(copy.stream).toMatch(/等待|流程|输出/)
  })
})
