export function getEmptyCopy({ enabled }: { enabled: boolean }): {
  metrics: string
  stream: string
} {
  if (!enabled) {
    return {
      metrics: '',
      stream: '点击“开启舆论平衡”，开始展示干预流程关键节点。',
    }
  }

  return {
    metrics: '',
    stream: '已开始监听流程输出，等待关键节点…',
  }
}
