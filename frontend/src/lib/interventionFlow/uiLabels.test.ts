import { describe, expect, it } from 'vitest'

import { formatAnalysisStatus, formatDemoRunStatus, formatSseStatus, formatTopCount } from './uiLabels'

describe('uiLabels', () => {
  it('formats analysis status', () => {
    expect(formatAnalysisStatus('Idle')).toBe('空闲')
    expect(formatAnalysisStatus('Running')).toBe('分析中')
    expect(formatAnalysisStatus('Done')).toBe('已完成')
    expect(formatAnalysisStatus('Error')).toBe('失败')
  })

  it('formats demo run status', () => {
    expect(formatDemoRunStatus(true)).toBe('运行中')
    expect(formatDemoRunStatus(false)).toBe('已停止')
  })

  it('formats SSE status', () => {
    expect(formatSseStatus('connected')).toBe('SSE 已连接')
    expect(formatSseStatus('connecting')).toBe('SSE 连接中')
    expect(formatSseStatus('disconnected')).toBe('SSE 已断开')
  })

  it('formats top count', () => {
    expect(formatTopCount(20)).toBe('前 20')
  })
})

