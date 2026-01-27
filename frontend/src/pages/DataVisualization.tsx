import { useState, useEffect, useRef } from 'react'
import { Database, Network } from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'
import { getDatabases, getNetworkData } from '../services/api'

export default function DataVisualization() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const graphRef = useRef<any>()
  
  // 过滤选项
  const [showUsers, setShowUsers] = useState(true)
  const [showPosts, setShowPosts] = useState(true)
  const [showComments, setShowComments] = useState(true)
  const [userLimit, setUserLimit] = useState(100)
  const [postLimit, setPostLimit] = useState(100)
  const [commentLimit, setCommentLimit] = useState(100)

  // 关系网络数据
  const [networkData, setNetworkData] = useState<any>({
    nodes: [],
    edges: [],
    stats: {}
  })
  
  // 选中的节点（支持多选）
  const [selectedNodes, setSelectedNodes] = useState<Map<string, any>>(new Map())
  
  // 高亮的边
  const [highlightLinks, setHighlightLinks] = useState<Set<any>>(new Set())
  const [highlightNodes, setHighlightNodes] = useState<Set<any>>(new Set())

  // 网络图数据（ForceGraph格式）
  const [graphData, setGraphData] = useState<any>({ nodes: [], links: [] })

  // 加载数据库列表
  useEffect(() => {
    const loadDatabases = async () => {
      const dbs = await getDatabases()
      setDatabases(dbs)
      if (dbs.length > 0) {
        setSelectedDb(dbs[0])
      }
    }
    loadDatabases()
  }, [])

  // 当数据库改变时加载数据
  useEffect(() => {
    if (selectedDb) {
      loadData()
    }
  }, [selectedDb])
  
  // 当过滤选项改变时重新加载数据
  useEffect(() => {
    if (selectedDb && networkData.nodes && networkData.nodes.length > 0) {
      loadData()
    }
  }, [showUsers, showPosts, showComments, userLimit, postLimit, commentLimit])

  const loadData = async () => {
    if (!selectedDb) return
    
    setLoading(true)
    try {
      console.log('Loading network data for:', selectedDb)
      const networkRes = await getNetworkData(selectedDb)
      console.log('Received data:', {
        nodes: networkRes.nodes?.length || 0,
        edges: networkRes.edges?.length || 0,
        stats: networkRes.stats
      })
      
      setNetworkData(networkRes)
      
      // 计算非0条数并设置默认值（仅在首次加载时）
      if (networkRes.nodes && networkRes.nodes.length > 0) {
        const nonZeroUsers = networkRes.nodes.filter((n: any) => 
          n.type === 'user' && (n.follower_count > 0 || n.influence_score > 0)
        ).length
        const nonZeroPosts = networkRes.nodes.filter((n: any) => 
          n.type === 'post' && (n.num_likes > 0 || n.num_comments > 0 || n.num_shares > 0)
        ).length
        const nonZeroComments = networkRes.nodes.filter((n: any) => 
          n.type === 'comment' && n.num_likes > 0
        ).length
        
        // 只在首次加载时设置默认值
        if (userLimit === 100) setUserLimit(nonZeroUsers)
        if (postLimit === 100) setPostLimit(nonZeroPosts)
        if (commentLimit === 100) setCommentLimit(nonZeroComments)
      }
      
      // 转换为ForceGraph格式
      const nodes = (networkRes.nodes || []).map((node: any) => {
        let color = '#3b82f6' // 默认蓝色
        let size = 30 // 默认大小
        
        if (node.type === 'user') {
          // 用户节点 - 统一大小，颜色区分更明显
          size = 35 // 用户节点统一大小
          // 根据影响力分配颜色，色彩更鲜明（影响力范围0-1）
          if (node.influence_score > 0.5) {
            color = '#ef4444' // 鲜红色 - 超高影响力
          } else if (node.influence_score > 0.3) {
            color = '#f97316' // 鲜橙色 - 高影响力
          } else if (node.influence_score > 0.15) {
            color = '#fbbf24' // 鲜黄色 - 中高影响力
          } else if (node.influence_score > 0.05) {
            color = '#3b82f6' // 鲜蓝色 - 中等影响力
          } else if (node.influence_score > 0.01) {
            color = '#22c55e' // 鲜绿色 - 中低影响力
          } else if (node.influence_score > 0.001) {
            color = '#14b8a6' // 鲜青色 - 低影响力
          } else {
            color = '#94a3b8' // 浅灰色 - 很低影响力
          }
        } else if (node.type === 'post') {
          // 帖子节点 - 统一大小，按真假新闻分类
          size = 45 // 帖子节点统一大小（最大）
          if (node.topic === 'fake') {
            color = '#ef4444' // 鲜红色 - 假新闻
          } else if (node.topic === 'real') {
            color = '#10b981' // 鲜绿色 - 真新闻
          } else {
            color = '#c026d3' // 鲜紫色 - 其他/未分类
          }
        } else if (node.type === 'comment') {
          // 评论节点 - 统一大小
          size = 25 // 评论节点统一大小（最小）
          // 根据点赞数分配颜色
          if (node.num_likes > 50) {
            color = '#f97316' // 鲜橙色 - 热门评论
          } else if (node.num_likes > 20) {
            color = '#22c55e' // 鲜绿色 - 受欢迎评论
          } else {
            color = '#94a3b8' // 浅灰色 - 普通评论
          }
        }
        
        return {
          ...node,
          val: size,
          color: color
        }
      })
      
      // 应用过滤
      let filteredNodes = nodes
      
      // 按类型分组并按热度排序
      const userNodes = nodes
        .filter((n: any) => n.type === 'user')
        .sort((a: any, b: any) => (b.influence_score || 0) - (a.influence_score || 0)) // 按影响力排序
      
      const postNodes = nodes
        .filter((n: any) => n.type === 'post')
        .sort((a: any, b: any) => {
          const engagementA = (a.num_likes || 0) + (a.num_comments || 0) + (a.num_shares || 0)
          const engagementB = (b.num_likes || 0) + (b.num_comments || 0) + (b.num_shares || 0)
          return engagementB - engagementA // 按互动量排序
        })
      
      const commentNodes = nodes
        .filter((n: any) => n.type === 'comment')
        .sort((a: any, b: any) => (b.num_likes || 0) - (a.num_likes || 0)) // 按点赞数排序
      
      // 应用限制
      const selectedUsers = showUsers ? userNodes.slice(0, userLimit) : []
      const selectedPosts = showPosts ? postNodes.slice(0, postLimit) : []
      const selectedComments = showComments ? commentNodes.slice(0, commentLimit) : []
      
      filteredNodes = [...selectedUsers, ...selectedPosts, ...selectedComments]
      
      // 获取保留节点的ID集合
      const nodeIds = new Set(filteredNodes.map((n: any) => n.id))
      
      // 过滤边：只保留两端节点都存在的边
      const links = (networkRes.edges || [])
        .filter((edge: any) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
        .map((edge: any) => ({
          source: edge.source,
          target: edge.target,
          type: edge.type,
          label: edge.label
        }))
      
      console.log('Filtered graph data:', { 
        nodes: filteredNodes.length, 
        links: links.length,
        users: selectedUsers.length,
        posts: selectedPosts.length,
        comments: selectedComments.length
      })
      setGraphData({ nodes: filteredNodes, links })
    } catch (error) {
      console.error('Failed to load data:', error)
      alert('加载数据失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 处理节点点击（支持多选）
  const handleNodeClick = (node: any, event: any) => {
    // 按住Ctrl或Cmd键可以多选
    const isMultiSelect = event.ctrlKey || event.metaKey
    
    if (isMultiSelect) {
      // 多选模式
      const newSelectedNodes = new Map(selectedNodes)
      if (newSelectedNodes.has(node.id)) {
        // 如果已选中，则取消选中
        newSelectedNodes.delete(node.id)
      } else {
        // 添加到选中列表
        newSelectedNodes.set(node.id, node)
      }
      setSelectedNodes(newSelectedNodes)
      
      // 更新高亮
      updateHighlights(newSelectedNodes)
    } else {
      // 单选模式
      const newSelectedNodes = new Map()
      newSelectedNodes.set(node.id, node)
      setSelectedNodes(newSelectedNodes)
      
      // 更新高亮
      updateHighlights(newSelectedNodes)
    }
  }

  // 更新高亮的边和节点
  const updateHighlights = (selectedNodesMap: Map<string, any>) => {
    if (selectedNodesMap.size === 0) {
      setHighlightLinks(new Set())
      setHighlightNodes(new Set())
      return
    }

    const connectedLinks = new Set()
    const connectedNodes = new Set<string>()
    
    // 添加所有选中的节点
    selectedNodesMap.forEach((_, nodeId) => {
      connectedNodes.add(nodeId)
    })
    
    // 找出所有相关的边和节点
    graphData.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source
      const targetId = typeof link.target === 'object' ? link.target.id : link.target
      
      if (selectedNodesMap.has(sourceId) || selectedNodesMap.has(targetId)) {
        connectedLinks.add(link)
        connectedNodes.add(sourceId)
        connectedNodes.add(targetId)
      }
    })
    
    setHighlightLinks(connectedLinks)
    setHighlightNodes(connectedNodes)
  }

  // 获取节点类型的中文名
  const getNodeTypeName = (type: string) => {
    const typeMap: Record<string, string> = {
      'user': '用户',
      'post': '帖子',
      'comment': '评论'
    }
    return typeMap[type] || type
  }

  // 配置力导向参数
  useEffect(() => {
    if (graphRef.current) {
      // 使用极强的排斥力，让节点充分分散
      graphRef.current.d3Force('charge')?.strength(-5000)
      graphRef.current.d3Force('link')?.distance(350).strength(0.1)
      // 移除径向力，让节点自由分布
      graphRef.current.d3Force('radial', null)
      // 取消中心引力
      graphRef.current.d3Force('center', null)
    }
  }, [graphData])

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg">
            <Network size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">关系图谱</h1>
            <p className="text-slate-600">可视化用户、帖子、评论之间的关系网络</p>
          </div>
        </div>
      </div>

      {/* 数据库选择 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4">
          <Database size={20} className="text-slate-600" />
          <label className="text-sm font-medium text-slate-700">选择数据库:</label>
          <select
            value={selectedDb}
            onChange={(e) => setSelectedDb(e.target.value)}
            className="px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            {databases.map(db => (
              <option key={db} value={db}>{db}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* 过滤控制面板 */}
      {selectedDb && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-bold text-slate-800 mb-4">节点过滤</h3>
          <div className="grid grid-cols-3 gap-6">
            {/* 用户节点 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showUsers"
                  checked={showUsers}
                  onChange={(e) => setShowUsers(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <label htmlFor="showUsers" className="text-sm font-medium text-slate-700">
                  显示用户节点 (共 {networkData.nodes?.filter((n: any) => n.type === 'user').length || 0} 条, 
                  非0: {networkData.nodes?.filter((n: any) => n.type === 'user' && (n.follower_count > 0 || n.influence_score > 0)).length || 0} 条)
                </label>
              </div>
              {showUsers && (
                <div className="ml-6">
                  <label className="text-xs text-slate-600">显示前</label>
                  <input
                    type="number"
                    value={userLimit}
                    onChange={(e) => setUserLimit(Math.max(1, parseInt(e.target.value) || 100))}
                    min="1"
                    max="10000"
                    className="ml-2 w-20 px-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-xs text-slate-600">条</span>
                </div>
              )}
            </div>
            
            {/* 帖子节点 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showPosts"
                  checked={showPosts}
                  onChange={(e) => setShowPosts(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
                />
                <label htmlFor="showPosts" className="text-sm font-medium text-slate-700">
                  显示帖子节点 (共 {networkData.nodes?.filter((n: any) => n.type === 'post').length || 0} 条, 
                  非0: {networkData.nodes?.filter((n: any) => n.type === 'post' && (n.num_likes > 0 || n.num_comments > 0 || n.num_shares > 0)).length || 0} 条)
                </label>
              </div>
              {showPosts && (
                <div className="ml-6">
                  <label className="text-xs text-slate-600">显示前</label>
                  <input
                    type="number"
                    value={postLimit}
                    onChange={(e) => setPostLimit(Math.max(1, parseInt(e.target.value) || 100))}
                    min="1"
                    max="10000"
                    className="ml-2 w-20 px-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <span className="ml-2 text-xs text-slate-600">条</span>
                </div>
              )}
            </div>
            
            {/* 评论节点 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showComments"
                  checked={showComments}
                  onChange={(e) => setShowComments(e.target.checked)}
                  className="w-4 h-4 text-green-600 rounded focus:ring-2 focus:ring-green-500"
                />
                <label htmlFor="showComments" className="text-sm font-medium text-slate-700">
                  显示评论节点 (共 {networkData.nodes?.filter((n: any) => n.type === 'comment').length || 0} 条, 
                  非0: {networkData.nodes?.filter((n: any) => n.type === 'comment' && n.num_likes > 0).length || 0} 条)
                </label>
              </div>
              {showComments && (
                <div className="ml-6">
                  <label className="text-xs text-slate-600">显示前</label>
                  <input
                    type="number"
                    value={commentLimit}
                    onChange={(e) => setCommentLimit(Math.max(1, parseInt(e.target.value) || 100))}
                    min="1"
                    max="10000"
                    className="ml-2 w-20 px-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  <span className="ml-2 text-xs text-slate-600">条</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 数据展示区域 */}
      {loading ? (
        <div className="glass-card p-12 text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg font-medium">正在加载关系图谱...</p>
          <p className="text-slate-500 text-sm mt-2">数据量较大，请稍候</p>
        </div>
      ) : (
        <>
          {/* 关系网络图 */}
          {graphData.nodes && graphData.nodes.length > 0 ? (
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-slate-800">关系图谱</h2>
                <div className="flex items-center gap-6">
                  {/* 用户节点图例 */}
                  <div className="flex flex-col gap-1">
                    <p className="text-xs font-semibold text-slate-700 mb-1">用户影响力</p>
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#ef4444'}}></div>
                        <span className="text-slate-600">&gt;0.5</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#f97316'}}></div>
                        <span className="text-slate-600">0.3-0.5</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#fbbf24'}}></div>
                        <span className="text-slate-600">0.15-0.3</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#3b82f6'}}></div>
                        <span className="text-slate-600">0.05-0.15</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#22c55e'}}></div>
                        <span className="text-slate-600">0.01-0.05</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#14b8a6'}}></div>
                        <span className="text-slate-600">&lt;0.01</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* 帖子类型图例 */}
                  <div className="flex flex-col gap-1">
                    <p className="text-xs font-semibold text-slate-700 mb-1">帖子类型</p>
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#ef4444'}}></div>
                        <span className="text-slate-600">假新闻</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#10b981'}}></div>
                        <span className="text-slate-600">真新闻</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#c026d3'}}></div>
                        <span className="text-slate-600">其他</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* 评论热度图例 */}
                  <div className="flex flex-col gap-1">
                    <p className="text-xs font-semibold text-slate-700 mb-1">评论热度</p>
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#f97316'}}></div>
                        <span className="text-slate-600">热门(&gt;50赞)</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#22c55e'}}></div>
                        <span className="text-slate-600">受欢迎(&gt;20赞)</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2.5 h-2.5 rounded-full" style={{backgroundColor: '#94a3b8'}}></div>
                        <span className="text-slate-600">普通</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-4">
                {/* 图谱主体 */}
                <div 
                  className="bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 rounded-xl overflow-hidden shadow-inner flex-1"
                  style={{ height: '800px' }}
                >
                  <ForceGraph2D
                    ref={graphRef}
                    graphData={graphData}
                    width={undefined}
                    height={800}
                    nodeLabel={(node: any) => `${getNodeTypeName(node.type)}: ${node.name}`}
                    enableNodeDrag={true}
                    enableZoomInteraction={true}
                    enablePanInteraction={true}
                    d3AlphaDecay={0.015}
                    d3VelocityDecay={0.15}
                    warmupTicks={200}
                    cooldownTicks={300}
                    nodeCanvasObject={(node: any, ctx: any, globalScale: any) => {
                      // 检查节点坐标是否有效
                      if (!node.x || !node.y || !isFinite(node.x) || !isFinite(node.y)) {
                        return // 跳过坐标无效的节点
                      }
                      
                      const label = node.name
                      const fontSize = 10 / globalScale
                      ctx.font = `${fontSize}px Sans-Serif`
                      
                      // 判断是否高亮或选中
                      const isSelected = selectedNodes.has(node.id)
                      const isHighlight = highlightNodes.has(node.id)
                      const opacity = selectedNodes.size > 0 && !isHighlight ? 0.3 : 1
                      
                      // 绘制光晕效果（对高影响力节点）
                      if (node.type === 'user' && node.influence_score > 60) {
                        const gradient = ctx.createRadialGradient(node.x, node.y, node.val, node.x, node.y, node.val * 2.5)
                        gradient.addColorStop(0, node.color + '40')
                        gradient.addColorStop(1, node.color + '00')
                        ctx.fillStyle = gradient
                        ctx.globalAlpha = opacity * 0.6
                        ctx.beginPath()
                        ctx.arc(node.x, node.y, node.val * 2.5, 0, 2 * Math.PI, false)
                        ctx.fill()
                      }
                      
                      // 绘制外圈动画（选中节点）
                      if (isSelected) {
                        ctx.strokeStyle = '#dc2626'
                        ctx.lineWidth = 2
                        ctx.globalAlpha = 0.5
                        ctx.beginPath()
                        ctx.arc(node.x, node.y, node.val + 3, 0, 2 * Math.PI, false)
                        ctx.stroke()
                        ctx.globalAlpha = 1
                      }
                      
                      // 绘制节点主体
                      ctx.beginPath()
                      ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false)
                      
                      // 渐变填充
                      const nodeGradient = ctx.createRadialGradient(
                        node.x - node.val * 0.3, 
                        node.y - node.val * 0.3, 
                        0, 
                        node.x, 
                        node.y, 
                        node.val
                      )
                      nodeGradient.addColorStop(0, node.color + 'ff')
                      nodeGradient.addColorStop(1, node.color + 'cc')
                      ctx.fillStyle = nodeGradient
                      ctx.globalAlpha = opacity
                      ctx.fill()
                      
                      // 选中或高亮边框
                      if (isSelected) {
                        ctx.strokeStyle = '#dc2626'
                        ctx.lineWidth = 3
                        ctx.globalAlpha = 1
                        ctx.stroke()
                      } else if (isHighlight) {
                        ctx.strokeStyle = '#dc2626'
                        ctx.lineWidth = 2
                        ctx.globalAlpha = 0.8
                        ctx.stroke()
                      } else {
                        ctx.strokeStyle = '#ffffff'
                        ctx.lineWidth = 1
                        ctx.globalAlpha = opacity
                        ctx.stroke()
                      }
                      
                      ctx.globalAlpha = 1
                      
                      // 绘制节点图标（根据类型）- 增大图标
                      if (node.val > 3) {
                        ctx.fillStyle = '#ffffff'
                        ctx.globalAlpha = opacity * 0.95
                        ctx.font = `${node.val * 0.8}px Arial`
                        ctx.textAlign = 'center'
                        ctx.textBaseline = 'middle'
                        
                        let icon = ''
                        if (node.type === 'user') {
                          icon = '👤'
                        } else if (node.type === 'post') {
                          icon = '📄'
                        } else if (node.type === 'comment') {
                          icon = '💬'
                        }
                        
                        if (icon) {
                          ctx.fillText(icon, node.x, node.y)
                        }
                        ctx.globalAlpha = 1
                      }
                      
                      // 绘制标签
                      if (node.val > 4 || isHighlight || isSelected) {
                        ctx.textAlign = 'center'
                        ctx.textBaseline = 'middle'
                        
                        const shortLabel = label.length > 15 ? label.substring(0, 12) + '...' : label
                        const labelY = node.y + node.val + fontSize + 4
                        
                        // 标签文字（不要背景框）
                        ctx.fillStyle = '#1e293b'
                        ctx.globalAlpha = opacity
                        ctx.font = `bold ${fontSize}px Sans-Serif`
                        ctx.fillText(shortLabel, node.x, labelY)
                        ctx.globalAlpha = 1
                      }
                    }}
                    linkCanvasObject={(link: any, ctx: any) => {
                      // 检查边的端点坐标是否有效
                      const sourceX = link.source.x
                      const sourceY = link.source.y
                      const targetX = link.target.x
                      const targetY = link.target.y
                      
                      if (!isFinite(sourceX) || !isFinite(sourceY) || !isFinite(targetX) || !isFinite(targetY)) {
                        return // 跳过坐标无效的边
                      }
                      
                      const isHighlight = highlightLinks.has(link)
                      const opacity = selectedNodes.size > 0 && !isHighlight ? 0.2 : 0.6
                      
                      // 绘制边的阴影（高亮时）
                      if (isHighlight) {
                        ctx.beginPath()
                        ctx.moveTo(sourceX, sourceY)
                        ctx.lineTo(targetX, targetY)
                        ctx.strokeStyle = '#dc2626'
                        ctx.lineWidth = 6
                        ctx.globalAlpha = 0.2
                        ctx.stroke()
                      }
                      
                      // 绘制主边
                      ctx.beginPath()
                      ctx.moveTo(sourceX, sourceY)
                      ctx.lineTo(targetX, targetY)
                      
                      if (isHighlight) {
                        // 高亮边使用渐变
                        const gradient = ctx.createLinearGradient(sourceX, sourceY, targetX, targetY)
                        gradient.addColorStop(0, '#dc2626')
                        gradient.addColorStop(0.5, '#f59e0b')
                        gradient.addColorStop(1, '#dc2626')
                        ctx.strokeStyle = gradient
                        ctx.lineWidth = 3
                        ctx.globalAlpha = 0.9
                      } else {
                        ctx.strokeStyle = '#cbd5e1'
                        ctx.lineWidth = 1
                        ctx.globalAlpha = opacity
                      }
                      ctx.stroke()
                      ctx.globalAlpha = 1
                      
                      // 绘制箭头
                      if (isHighlight) {
                        const arrowLength = 10
                        const dx = targetX - sourceX
                        const dy = targetY - sourceY
                        const angle = Math.atan2(dy, dx)
                        const distance = Math.sqrt(dx * dx + dy * dy)
                        const targetRadius = link.target.val || 5
                        
                        if (distance > 0 && isFinite(distance)) {
                          const arrowX = sourceX + (dx / distance) * (distance - targetRadius - 2)
                          const arrowY = sourceY + (dy / distance) * (distance - targetRadius - 2)
                          
                          // 箭头阴影
                          ctx.beginPath()
                          ctx.moveTo(arrowX, arrowY)
                          ctx.lineTo(
                            arrowX - arrowLength * Math.cos(angle - Math.PI / 6),
                            arrowY - arrowLength * Math.sin(angle - Math.PI / 6)
                          )
                          ctx.lineTo(
                            arrowX - arrowLength * Math.cos(angle + Math.PI / 6),
                            arrowY - arrowLength * Math.sin(angle + Math.PI / 6)
                          )
                          ctx.closePath()
                          ctx.fillStyle = '#000000'
                          ctx.globalAlpha = 0.2
                          ctx.fill()
                          
                          // 箭头主体
                          ctx.beginPath()
                          ctx.moveTo(arrowX, arrowY)
                          ctx.lineTo(
                            arrowX - arrowLength * Math.cos(angle - Math.PI / 6),
                            arrowY - arrowLength * Math.sin(angle - Math.PI / 6)
                          )
                          ctx.lineTo(
                            arrowX - arrowLength * Math.cos(angle + Math.PI / 6),
                            arrowY - arrowLength * Math.sin(angle + Math.PI / 6)
                          )
                          ctx.closePath()
                          ctx.fillStyle = '#dc2626'
                          ctx.globalAlpha = 1
                          ctx.fill()
                        }
                      }
                    }}
                    backgroundColor="#f8fafc"
                    onNodeClick={handleNodeClick}
                    onBackgroundClick={() => {
                      setSelectedNodes(new Map())
                      setHighlightLinks(new Set())
                      setHighlightNodes(new Set())
                    }}
                    onEngineStop={() => {
                      if (graphRef.current && graphData.nodes.length > 0) {
                        // Zoom to fit with padding after initial layout
                        setTimeout(() => {
                          graphRef.current?.zoomToFit(400, 80)
                        }, 100)
                      }
                    }}
                  />
                </div>
                
                {/* 右侧详情面板 */}
                <div className="w-80 flex flex-col gap-3 overflow-y-auto" style={{ maxHeight: '800px' }}>
                  {selectedNodes.size === 0 ? (
                    <div className="bg-gradient-to-br from-white to-slate-50 rounded-xl shadow-lg p-6 text-center">
                      <Network size={48} className="mx-auto mb-3 opacity-30 text-slate-400" />
                      <p className="text-slate-500 text-sm">点击节点查看详情</p>
                      <p className="text-slate-400 text-xs mt-2">按住Ctrl可多选</p>
                    </div>
                  ) : (
                    Array.from(selectedNodes.values()).map((node) => (
                      <div
                        key={node.id}
                        className="bg-gradient-to-br from-white to-slate-50 rounded-xl shadow-lg p-4 border-2 border-blue-500"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium shadow-sm ${
                            node.type === 'user' ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white' :
                            node.type === 'post' ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white' :
                            'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
                          }`}>
                            {getNodeTypeName(node.type)}
                          </span>
                          <button
                            onClick={() => {
                              const newSelectedNodes = new Map(selectedNodes)
                              newSelectedNodes.delete(node.id)
                              setSelectedNodes(newSelectedNodes)
                              updateHighlights(newSelectedNodes)
                            }}
                            className="text-slate-400 hover:text-red-600 text-lg transition-colors"
                          >
                            ✕
                          </button>
                        </div>
                        
                        <div className="space-y-2 text-sm">
                          {/* 用户详情 */}
                          {node.type === 'user' && (
                            <>
                              <div>
                                <label className="text-xs text-slate-500">ID</label>
                                <p className="font-mono text-xs text-slate-800 break-all">{node.id}</p>
                              </div>
                              
                              {/* 角色信息 */}
                              {node.persona && typeof node.persona === 'object' && (
                                <>
                                  {node.persona.name && (
                                    <div>
                                      <label className="text-xs text-slate-500">名字</label>
                                      <p className="text-sm font-semibold text-slate-800">{node.persona.name}</p>
                                    </div>
                                  )}
                                  
                                  {node.persona.demographics && (
                                    <div className="grid grid-cols-2 gap-2">
                                      {node.persona.demographics.profession && (
                                        <div className="bg-indigo-50 p-2 rounded">
                                          <p className="text-xs text-slate-600">职业</p>
                                          <p className="text-xs font-medium text-slate-800">{node.persona.demographics.profession}</p>
                                        </div>
                                      )}
                                      {node.persona.demographics.age && (
                                        <div className="bg-pink-50 p-2 rounded">
                                          <p className="text-xs text-slate-600">年龄</p>
                                          <p className="text-xs font-medium text-slate-800">{node.persona.demographics.age}</p>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  
                                  {node.persona.personality_traits && Array.isArray(node.persona.personality_traits) && node.persona.personality_traits.length > 0 && (
                                    <div>
                                      <label className="text-xs text-slate-500">性格特征</label>
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {node.persona.personality_traits.map((trait: string, idx: number) => (
                                          <span key={idx} className="px-2 py-0.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-xs rounded-full">
                                            {trait}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {node.persona.communication_style && (
                                    <div>
                                      <label className="text-xs text-slate-500">社交风格</label>
                                      <div className="bg-slate-50 p-2 rounded mt-1 space-y-1">
                                        {node.persona.communication_style.tone && (
                                          <p className="text-xs text-slate-700">
                                            <span className="font-medium">语气:</span> {node.persona.communication_style.tone}
                                          </p>
                                        )}
                                        {node.persona.communication_style.engagement_level && (
                                          <p className="text-xs text-slate-700">
                                            <span className="font-medium">参与度:</span> {node.persona.communication_style.engagement_level}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </>
                              )}
                              
                              <div className="grid grid-cols-2 gap-2 mt-2">
                                <div className="bg-blue-50 p-2 rounded">
                                  <p className="text-xs text-slate-600">粉丝</p>
                                  <p className="text-sm font-bold text-slate-800">{node.follower_count}</p>
                                </div>
                                <div className="bg-purple-50 p-2 rounded">
                                  <p className="text-xs text-slate-600">影响力</p>
                                  <p className="text-sm font-bold text-slate-800">{node.influence_score}</p>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-2 mt-2">
                                <div className="bg-green-50 p-2 rounded">
                                  <p className="text-xs text-slate-600">帖子数</p>
                                  <p className="text-sm font-bold text-slate-800">{node.post_count || 0}</p>
                                </div>
                                <div className="bg-orange-50 p-2 rounded">
                                  <p className="text-xs text-slate-600">评论数</p>
                                  <p className="text-sm font-bold text-slate-800">{node.comment_count || 0}</p>
                                </div>
                              </div>
                            </>
                          )}
                          
                          {/* 帖子详情 */}
                          {node.type === 'post' && (
                            <>
                              <div>
                                <label className="text-xs text-slate-500">ID</label>
                                <p className="font-mono text-xs text-slate-800 break-all">{node.id}</p>
                              </div>
                              <div>
                                <label className="text-xs text-slate-500">主题</label>
                                <p className="text-xs text-slate-800">{node.topic}</p>
                              </div>
                              <div className="w-full">
                                <label className="text-xs text-slate-500 block mb-1">内容</label>
                                <div className="text-xs text-slate-700 bg-slate-50 p-3 rounded whitespace-pre-wrap break-words w-full" style={{ maxHeight: 'none', height: 'auto', overflow: 'visible' }}>
                                  {node.content}
                                </div>
                              </div>
                              <div className="grid grid-cols-3 gap-1 mt-2">
                                <div className="bg-red-50 p-1 rounded text-center">
                                  <p className="text-xs text-slate-600">赞</p>
                                  <p className="text-sm font-bold">{node.num_likes}</p>
                                </div>
                                <div className="bg-blue-50 p-1 rounded text-center">
                                  <p className="text-xs text-slate-600">评</p>
                                  <p className="text-sm font-bold">{node.num_comments}</p>
                                </div>
                                <div className="bg-green-50 p-1 rounded text-center">
                                  <p className="text-xs text-slate-600">享</p>
                                  <p className="text-sm font-bold">{node.num_shares}</p>
                                </div>
                              </div>
                            </>
                          )}
                          
                          {/* 评论详情 */}
                          {node.type === 'comment' && (
                            <>
                              <div>
                                <label className="text-xs text-slate-500">ID</label>
                                <p className="font-mono text-xs text-slate-800 break-all">{node.id}</p>
                              </div>
                              <div className="w-full">
                                <label className="text-xs text-slate-500 block mb-1">内容</label>
                                <div className="text-xs text-slate-700 bg-slate-50 p-3 rounded whitespace-pre-wrap break-words w-full" style={{ maxHeight: 'none', height: 'auto', overflow: 'visible' }}>
                                  {node.content}
                                </div>
                              </div>
                              <div className="bg-red-50 p-2 rounded mt-2">
                                <p className="text-xs text-slate-600">点赞数</p>
                                <p className="text-sm font-bold text-slate-800">{node.num_likes}</p>
                              </div>
                            </>
                          )}
                          
                          {/* 连接信息 */}
                          <div className="pt-2 border-t border-slate-200">
                            <p className="text-xs text-slate-600">
                              {highlightNodes.size - 1} 个相关节点
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 text-center">
              <Network size={48} className="mx-auto mb-4 opacity-50 text-slate-400" />
              <p className="text-slate-600">暂无关系网络数据</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
