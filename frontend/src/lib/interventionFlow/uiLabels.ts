export type AnalysisStatus = 'Idle' | 'Running' | 'Done' | 'Error'
export type SseStatus = 'connecting' | 'connected' | 'disconnected'

export function formatAnalysisStatus(status: AnalysisStatus) {
  switch (status) {
    case 'Idle':
      return '空闲'
    case 'Running':
      return '分析中'
    case 'Done':
      return '已完成'
    case 'Error':
      return '失败'
  }
}

export function formatDemoRunStatus(isRunning: boolean) {
  return isRunning ? '运行中' : '已停止'
}

export function formatSseStatus(status: SseStatus) {
  switch (status) {
    case 'connected':
      return 'SSE 已连接'
    case 'connecting':
      return 'SSE 连接中'
    case 'disconnected':
      return 'SSE 已断开'
  }
}

export function formatTopCount(n: number) {
  return `前 ${n}`
}

