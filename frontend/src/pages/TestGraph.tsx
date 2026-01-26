import { useState, useEffect } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

// 简单的测试图谱组件
export default function TestGraph() {
  const [graphData, setGraphData] = useState<any>({ nodes: [], links: [] })

  useEffect(() => {
    // 创建简单的测试数据
    const testData = {
      nodes: [
        { id: '1', name: '节点1', val: 5, color: '#3b82f6' },
        { id: '2', name: '节点2', val: 5, color: '#10b981' },
        { id: '3', name: '节点3', val: 5, color: '#f59e0b' },
        { id: '4', name: '节点4', val: 5, color: '#a855f7' },
        { id: '5', name: '节点5', val: 5, color: '#ec4899' },
      ],
      links: [
        { source: '1', target: '2' },
        { source: '2', target: '3' },
        { source: '3', target: '4' },
        { source: '4', target: '5' },
        { source: '5', target: '1' },
      ]
    }
    
    console.log('Setting test graph data:', testData)
    setGraphData(testData)
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">图谱测试页面</h1>
      <p className="mb-4">节点数: {graphData.nodes.length}, 边数: {graphData.links.length}</p>
      
      <div style={{ width: '100%', height: '600px', border: '2px solid #ccc', borderRadius: '8px', background: '#f8fafc' }}>
        <ForceGraph2D
          graphData={graphData}
          nodeLabel="name"
          nodeColor={(node: any) => node.color}
          nodeVal={(node: any) => node.val}
          linkColor={() => '#cbd5e1'}
          linkWidth={2}
          backgroundColor="#f8fafc"
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
        />
      </div>
      
      <div className="mt-4 p-4 bg-blue-50 rounded">
        <h3 className="font-bold mb-2">调试信息:</h3>
        <pre className="text-xs">{JSON.stringify(graphData, null, 2)}</pre>
      </div>
    </div>
  )
}
