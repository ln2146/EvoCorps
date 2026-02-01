export function getEmptyCopy({ enabled }: { enabled: boolean }): {
  metrics: string
  stream: string
} {
  if (!enabled) {
    return {
      metrics: '开启舆论平衡后，将自动提取关键指标。',
      stream: '点击“开启舆论平衡”，开始展示干预流程关键节点。',
    }
  }

  return {
    metrics: '关键指标会随流程自动提取并展示。',
    stream: '已连接流程日志，等待第一条输出…',
  }
}
