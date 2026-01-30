import { useEffect, useMemo, useRef, useState, type ReactNode, type ElementType } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Activity, Play, Square, Shield, Bug, Sparkles, Flame, MessageSquare, ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createInitialFlowState, routeLogLine, type FlowState, type Role } from '../lib/interventionFlow/logRouter'
import { createEventSourceLogStream, createSimulatedLogStream, type LogStream } from '../lib/interventionFlow/logStream'

const DEMO_BACKEND_LOG_LINES: string[] = [
  '2026-01-28 21:13:09,286 - INFO - 📊 Phase 1: perception and decision',
  '2026-01-28 21:13:09,286 - INFO -   🔍 Analyst is analyzing content...',
  '2026-01-28 21:13:42,092 - INFO -    📊 Analyst analysis completed:',
  '2026-01-28 21:13:50,217 - INFO -       Viewpoint extremism: 8.6/10.0',
  '2026-01-28 21:13:50,217 - INFO -       Overall sentiment: 0.10/1.0',
  '2026-01-28 21:13:50,251 - INFO -       Needs intervention: yes',
  '2026-01-28 21:13:50,251 - INFO -       Trigger reasons: Viewpoint extremism too high (8.6/10.0 >= 4.5) & Sentiment too low (0.10/1.0 <= 0.4)',
  '2026-01-28 21:13:50,253 - INFO - ⚖️ Strategist is creating strategy...',
  '2026-01-28 21:13:57,749 - INFO -      ❌ Intelligent learning system found no matching strategy, none available',
  '2026-01-28 21:14:25,697 - INFO -         🎯 Selected optimal strategy: balanced_response',
  '2026-01-28 21:14:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...',
  '2026-01-28 21:15:42,523 - INFO -    Candidate 1: This post presents a claim that collapses under ba...',
  '2026-01-28 21:18:33,636 - INFO - ✅ USC workflow completed',
  '2026-01-28 21:18:33,637 - INFO - 💬 👑 Leader comment 1 on post post-18e9eb: This post raises serious allegations that warrant careful examination...',
  '2026-01-28 21:18:33,877 - INFO - ⚖️ Activating Echo Agent cluster...',
  '2026-01-28 21:18:33,892 - INFO -   🚀 Start parallel execution of 12 agent tasks...',
  '2026-01-28 21:18:53,941 - INFO - 📊 Echo Agent results: 12 succeeded, 0 failed',
  '2026-01-28 21:18:54,726 - INFO -   💖 Successfully added 240 likes to each of 2 leader comments (total: 480 likes)',
  '2026-01-28 21:18:54,727 - INFO - 🎉 Workflow completed - effectiveness score: 10.0/10',
  '2026-01-28 21:18:54,728 - INFO - 🔄 [Monitoring round 1/3]',
  '2026-01-28 21:18:54,728 - INFO -   📊 Analyst Agent - generate baseline effectiveness report',
  '2026-01-28 21:18:54,728 - INFO -   🔍 Analyst monitoring - establish baseline data',
  '2026-01-28 21:24:38,434 - INFO - 🚀 Start workflow execution - Action ID: action_20260128_212438',
  '2026-01-28 21:24:38,434 - INFO - ⚖️ Strategist is creating strategy...',
  '2026-01-28 21:24:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...',
]

const USE_SIMULATED_LOG_STREAM = false
const OPINION_BALANCE_LOG_STREAM_URL = '/api/opinion-balance/logs/stream?source=workflow&tail=0&follow_latest=true'

interface HeatPost {
  id: string
  summary: string
  heat: number
  author: string
  createdAt: string
}

interface CommentItem {
  id: string
  content: string
  likes: number
  createdAt: string
}

interface MetricsPoint {
  time: string
  emotion: number
  extremity: number
}

interface AgentLogItem {
  id: string
  ts: string
  message: string
}

type AgentType = 'Analyst' | 'Strategist' | 'Leader' | 'Amplifier'

interface DynamicDemoData {
  heatPosts: HeatPost[]
  comments: CommentItem[]
  metricsSeries: MetricsPoint[]
  agentLogs: Record<AgentType, AgentLogItem[]>
}

function useDynamicDemoApi() {
  const data = useMemo<DynamicDemoData>(() => {
    return {
      heatPosts: [
        { id: 'post_1024', summary: '极端言论在话题A中迅速扩散，引发两极分化讨论哈速度...', heat: 92, author: 'user_41', createdAt: '10:21' },
        { id: 'post_1130', summary: '理性派用户发起反向引导，讨论开始回归事实...', heat: 88, author: 'user_12', createdAt: '10:20' },
        { id: 'post_1207', summary: '热点事件引发情绪化评论，传播速度异常加快...', heat: 84, author: 'user_88', createdAt: '10:19' },
        { id: 'post_1099', summary: '平台出现协调式引导行为，舆论呈现集体偏移...', heat: 81, author: 'user_07', createdAt: '10:18' },
        { id: 'post_0981', summary: '多方观点对冲，话题温度下降但争议仍在...', heat: 79, author: 'user_33', createdAt: '10:17' },
        { id: 'post_1312', summary: '核心观点被断章取义，用户情绪被持续放大...', heat: 76, author: 'user_58', createdAt: '10:16' },
        { id: 'post_1404', summary: '事实核查内容开始传播，互动热度回落...', heat: 74, author: 'user_19', createdAt: '10:15' },
        { id: 'post_1556', summary: '极端标签使用频率上升，舆论场对立明显...', heat: 72, author: 'user_76', createdAt: '10:14' },
        { id: 'post_1660', summary: '主流媒体跟进报道，讨论重心出现转移...', heat: 70, author: 'user_05', createdAt: '10:13' },
        { id: 'post_1711', summary: '多方观点交锋，评论区情绪波动加剧...', heat: 68, author: 'user_23', createdAt: '10:12' },
        { id: 'post_1802', summary: '争议话题引发二次传播，热度持续升高...', heat: 66, author: 'user_64', createdAt: '10:11' },
        { id: 'post_1925', summary: '辟谣信息出现，但传播速度较慢...', heat: 64, author: 'user_09', createdAt: '10:10' },
        { id: 'post_2050', summary: '情绪化标题吸引关注，互动集中爆发...', heat: 62, author: 'user_37', createdAt: '10:09' },
        { id: 'post_2144', summary: '讨论逐渐分化为多个子议题...', heat: 60, author: 'user_11', createdAt: '10:08' },
        { id: 'post_2237', summary: '极端内容被举报增多，平台干预加强...', heat: 58, author: 'user_90', createdAt: '10:07' },
        { id: 'post_2319', summary: '传播链条开始收敛，热度略有回落...', heat: 56, author: 'user_52', createdAt: '10:06' },
        { id: 'post_2408', summary: '意见领袖介入讨论，带动新一轮互动...', heat: 54, author: 'user_28', createdAt: '10:05' },
        { id: 'post_2566', summary: '话题焦点转向政策解读，情绪趋稳...', heat: 52, author: 'user_66', createdAt: '10:04' },
        { id: 'post_2681', summary: '用户自发总结事件脉络，讨论更理性...', heat: 50, author: 'user_31', createdAt: '10:03' },
        { id: 'post_2794', summary: '热度进入尾声阶段，互动逐步下降...', heat: 48, author: 'user_14', createdAt: '10:02' },
      ],
      comments: [
        { id: 'c_01', content: '我觉得需要更多证据支持这个观点。', likes: 132, createdAt: '10:22' },
        { id: 'c_02', content: '这类言论太极端了，应该理性讨论。', likes: 98, createdAt: '10:21' },
        { id: 'c_03', content: '平台应该及时引导，避免情绪扩大。', likes: 81, createdAt: '10:19' },
        { id: 'c_04', content: '情绪被带动很正常，但数据怎么看？', likes: 63, createdAt: '10:17' },
        { id: 'c_05', content: '我赞同这种干预方式，但尺度要控制。', likes: 52, createdAt: '10:15' },
      ],
      metricsSeries: [
        { time: '10:00', emotion: 0.42, extremity: 0.18 },
        { time: '10:05', emotion: 0.48, extremity: 0.21 },
        { time: '10:10', emotion: 0.55, extremity: 0.27 },
        { time: '10:15', emotion: 0.51, extremity: 0.24 },
        { time: '10:20', emotion: 0.58, extremity: 0.32 },
        { time: '10:25', emotion: 0.61, extremity: 0.29 },
        { time: '10:30', emotion: 0.56, extremity: 0.23 },
      ],
      agentLogs: {
        Analyst: [
          { id: 'a_01', ts: '10:20:12', message: '识别到热点话题 A 的情绪指数快速升高。' },
          { id: 'a_02', ts: '10:20:45', message: '极端度指标突破阈值，建议进入观察模式。' },
        ],
        Strategist: [
          { id: 's_01', ts: '10:21:04', message: '生成三组缓和策略备选，优先投放理性信息。' },
          { id: 's_02', ts: '10:21:50', message: '建议调整信息分发权重至中立群体。' },
        ],
        Leader: [
          { id: 'l_01', ts: '10:22:10', message: '批准轻量干预方案，限制极端内容曝光。' },
        ],
        Amplifier: [
          { id: 'm_01', ts: '10:22:22', message: '开始推送事实核查卡片，覆盖高互动用户。' },
          { id: 'm_02', ts: '10:22:40', message: '已完成首轮引导内容投放。' },
        ],
      },
    }
  }, [])

  return { data, isLoading: false, error: null }
}

function useDynamicDemoSSE() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')

  const connect = () => {
    setStatus('connected')
  }

  const disconnect = () => {
    setStatus('disconnected')
  }

  return { status, connect, disconnect }
}

export default function DynamicDemo() {
  const navigate = useNavigate()
  const { data } = useDynamicDemoApi()
  const sse = useDynamicDemoSSE()

  const [isRunning, setIsRunning] = useState(false)
  const [enableAttack, setEnableAttack] = useState(false)
  const [enableAftercare, setEnableAftercare] = useState(false)
  const [enableEvoCorps, setEnableEvoCorps] = useState(false)

  const [selectedPost, setSelectedPost] = useState<HeatPost | null>(null)
  const [commentSort, setCommentSort] = useState<'likes' | 'time'>('likes')

  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<'Idle' | 'Running' | 'Done' | 'Error'>('Idle')

  const [isStarting, setIsStarting] = useState(false)

  const [flowState, setFlowState] = useState<FlowState>(() => createInitialFlowState())
  const streamRef = useRef<LogStream | null>(null)
  const unsubscribeRef = useRef<null | (() => void)>(null)

  useEffect(() => {
    if (!enableEvoCorps) {
      streamRef.current?.stop()
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      streamRef.current = null
    }
  }, [enableEvoCorps])

  useEffect(() => {
    if (!isRunning || !enableEvoCorps) return
    if (streamRef.current) return

    const stream = USE_SIMULATED_LOG_STREAM
      ? createSimulatedLogStream({ lines: DEMO_BACKEND_LOG_LINES, intervalMs: 320 })
      : createEventSourceLogStream(OPINION_BALANCE_LOG_STREAM_URL)
    const unsubscribe = stream.subscribe((line) => {
      setFlowState((prev) => routeLogLine(prev, line))
    })
    stream.start()

    streamRef.current = stream
    unsubscribeRef.current = unsubscribe
  }, [enableEvoCorps, isRunning])

  const currentMetrics = data.metricsSeries[data.metricsSeries.length - 1]

  return (
    <DynamicDemoPage>
      <DynamicDemoHeader
        isRunning={isRunning}
        isStarting={isStarting}
        onStart={async () => {
          // 设置加载状态
          setIsStarting(true)

          try {
            // 调用后端 API 启动进程
            const response = await fetch('/api/dynamic/start', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({}),
            })

            const data = await response.json()

            if (data.success) {
              // 成功：设置 isRunning 状态，连接 SSE
              setIsRunning(true)
              sse.connect()
              setFlowState(createInitialFlowState())

              streamRef.current?.stop()
              unsubscribeRef.current?.()
              streamRef.current = null
              unsubscribeRef.current = null

              const stream = USE_SIMULATED_LOG_STREAM
                ? createSimulatedLogStream({ lines: DEMO_BACKEND_LOG_LINES, intervalMs: 320 })
                : createEventSourceLogStream(OPINION_BALANCE_LOG_STREAM_URL)
              const unsubscribe = stream.subscribe((line) => {
                setFlowState((prev) => routeLogLine(prev, line))
              })
              stream.start()
              streamRef.current = stream
              unsubscribeRef.current = unsubscribe
            } else {
              // 失败：显示错误消息
              alert(`启动失败：${data.message || '未知错误'}`)
              console.error('Failed to start dynamic demo:', data)
            }
          } catch (error) {
            // 网络错误或其他异常
            alert(`启动失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error starting dynamic demo:', error)
          } finally {
            // 清除加载状态
            setIsStarting(false)
          }
        }}
        onStop={async () => {
          // 显示确认对话框
          if (!confirm('是否确认关闭模拟？')) {
            return
          }

          try {
            // 调用后端 API 停止进程
            const response = await fetch('/api/dynamic/stop', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
            })

            const data = await response.json()

            if (data.success) {
              // 成功：设置 isRunning 为 false，断开 SSE
              setIsRunning(false)
              sse.disconnect()

              // 清理前端状态（流、订阅等）
              streamRef.current?.stop()
              unsubscribeRef.current?.()
              unsubscribeRef.current = null
              streamRef.current = null
            } else {
              // 失败：显示错误消息
              alert(`停止失败：${data.message || '未知错误'}`)
              console.error('Failed to stop dynamic demo:', data)
            }
          } catch (error) {
            // 网络错误或其他异常
            alert(`停止失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error stopping dynamic demo:', error)
          }
        }}
        onBack={() => navigate('/')}
        enableAttack={enableAttack}
        enableAftercare={enableAftercare}
        enableEvoCorps={enableEvoCorps}
        onToggleAttack={() => setEnableAttack((prev) => !prev)}
        onToggleAftercare={() => setEnableAftercare((prev) => !prev)}
        onToggleEvoCorps={async () => {
          // 如果当前是禁用状态，则启用并调用 API
          if (!enableEvoCorps) {
            try {
              // 调用后端 API 启动舆论平衡系统
              const response = await fetch('/api/dynamic/opinion-balance/start', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
              })

              const data = await response.json()

              if (data.success) {
                // 成功：设置 enableEvoCorps 为 true
                setEnableEvoCorps(true)
              } else {
                // 失败：显示错误消息，保持状态不变
                alert(`启动舆论平衡失败：${data.message || '未知错误'}`)
                console.error('Failed to start opinion balance:', data)
              }
            } catch (error) {
              // 网络错误或其他异常
              alert(`启动舆论平衡失败：${error instanceof Error ? error.message : '网络错误'}`)
              console.error('Error starting opinion balance:', error)
            }
          } else {
            // 如果当前是启用状态，则显示确认对话框
            if (!confirm('是否确认关闭舆论平衡系统？')) {
              return
            }

            try {
              // 调用后端 API 停止舆论平衡系统
              const response = await fetch('/api/dynamic/opinion-balance/stop', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
              })

              const data = await response.json()

              if (data.success) {
                // 成功：设置 enableEvoCorps 为 false
                setEnableEvoCorps(false)
              } else {
                // 失败：显示错误消息，保持状态不变
                alert(`关闭舆论平衡失败：${data.message || '未知错误'}`)
                console.error('Failed to stop opinion balance:', data)
              }
            } catch (error) {
              // 网络错误或其他异常
              alert(`关闭舆论平衡失败：${error instanceof Error ? error.message : '网络错误'}`)
              console.error('Error stopping opinion balance:', error)
            }
          }
        }}
        sseStatus={sse.status}
      />

      <div className="grid grid-cols-1 xl:grid-cols-[1.1fr_1fr_1fr] gap-6">
        <div className="space-y-6">
          {!selectedPost ? (
            <HeatLeaderboardCard posts={data.heatPosts} onSelect={setSelectedPost} />
          ) : (
            <div className="space-y-6">
              <PostDetailCard post={selectedPost} onBack={() => setSelectedPost(null)} />
              <CommentsCard comments={data.comments} sort={commentSort} onSortChange={setCommentSort} />
            </div>
          )}
        </div>

        <div className="space-y-6">
          <MetricsBarsCard emotion={currentMetrics.emotion} extremity={currentMetrics.extremity} />
          <MetricsLineChartCard data={data.metricsSeries} />
        </div>

        <div className="space-y-6">
          {enableEvoCorps ? (
            <InterventionFlowPanel state={flowState} />
          ) : (
            <div className="glass-card p-6 min-h-[720px] flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="flex justify-center">
                  <Shield className="text-slate-400" size={32} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-800">干预流程</h3>
                  <p className="text-sm text-slate-600">启用舆论平衡系统后展示 4 类角色的干预流程。</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <CommentaryAnalysisPanel
        status={analysisStatus}
        onOpenConfig={() => setAnalysisOpen(true)}
        onRun={() => setAnalysisStatus('Running')}
      />

      <AnalysisConfigDialog
        open={analysisOpen}
        onClose={() => setAnalysisOpen(false)}
      />
    </DynamicDemoPage>
  )
}

function DynamicDemoPage({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <div className="max-w-[1600px] mx-auto px-4 py-8 space-y-6">
        {children}
      </div>
    </div>
  )
}

function DynamicDemoHeader({
  isRunning,
  isStarting,
  onStart,
  onStop,
  onBack,
  enableAttack,
  enableAftercare,
  enableEvoCorps,
  onToggleAttack,
  onToggleAftercare,
  onToggleEvoCorps,
  sseStatus,
}: {
  isRunning: boolean
  isStarting?: boolean
  onStart: () => void
  onStop: () => void
  onBack: () => void
  enableAttack: boolean
  enableAftercare: boolean
  enableEvoCorps: boolean
  onToggleAttack: () => void
  onToggleAftercare: () => void
  onToggleEvoCorps: () => void | Promise<void>
  sseStatus: 'connecting' | 'connected' | 'disconnected'
}) {
  return (
    <div className="glass-card p-6 flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex items-center gap-4">
        <img src="/logo.png" alt="EvoCorps Logo" className="w-[120px] h-auto max-w-full drop-shadow-xl" />
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-emerald-600 bg-clip-text text-transparent">
            欢迎使用 EvoCorps
          </h1>
          <p className="text-slate-600">实时监控舆情变化，动态观察指标变化的舆情现状</p>
          <div className="flex items-center gap-2 mt-2">
            <StatusBadge label={isRunning ? 'Running' : 'Stopped'} tone={isRunning ? 'success' : 'muted'} />
            <StatusBadge
              label={sseStatus === 'connected' ? 'SSE Connected' : sseStatus === 'connecting' ? 'SSE Connecting' : 'SSE Disconnected'}
              tone={sseStatus === 'connected' ? 'info' : sseStatus === 'connecting' ? 'warning' : 'muted'}
            />
          </div>
        </div>
      </div>

      <div className="flex items-stretch gap-4 w-full xl:w-auto">
        <div className="flex flex-col gap-3 items-center">
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              className="btn-primary inline-flex items-center gap-2"
              onClick={onStart}
              disabled={isRunning || isStarting}
            >
              <Play size={18} />
              {isStarting ? '启动中...' : '开启演示'}
            </button>
            <button className="btn-secondary inline-flex items-center gap-2" onClick={onStop} disabled={!isRunning}>
              <Square size={18} />
              停止演示
            </button>
          </div>
          <div className="flex flex-wrap gap-3 justify-center">
            <ToggleCard
              icon={Bug}
              label="开启恶意攻击"
              enabled={enableAttack}
              onToggle={onToggleAttack}
            />
            <ToggleCard
              icon={Sparkles}
              label="开启事后干预"
              enabled={enableAftercare}
              onToggle={onToggleAftercare}
            />
            <ToggleCard
              icon={Shield}
              label="开启舆论平衡"
              enabled={enableEvoCorps}
              onToggle={onToggleEvoCorps}
            />
          </div>
        </div>
        <button
          className="btn-secondary aspect-square h-full min-h-[120px] w-[120px] flex flex-col items-center justify-center gap-2 px-4"
          onClick={onBack}
          title="返回首页"
        >
          <ArrowLeft size={20} />
          <span className="text-lg font-semibold">返回首页</span>
        </button>
      </div>
    </div>
  )
}

function HeatLeaderboardCard({ posts, onSelect }: { posts: HeatPost[]; onSelect: (post: HeatPost) => void }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Flame className="text-orange-500" />
          <div>
            <h2 className="text-xl font-bold text-slate-800">帖子热度榜</h2>
            <p className="text-sm text-slate-600">实时热度排名（占位数据）</p>
          </div>
        </div>
        <StatusBadge label="Top 20" tone="info" />
      </div>

      <div className="space-y-3 h-[580px] overflow-y-auto pr-2">
        {posts.slice(0, 20).map((post, index) => (
          <button
            key={post.id}
            onClick={() => onSelect(post)}
            className="w-full text-left bg-white/70 hover:bg-white transition-all rounded-2xl p-4 border border-white/40"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-700">#{index + 1} · {post.id}</span>
              <span className="text-sm font-bold text-orange-500">{post.heat}</span>
            </div>
            <p className="text-sm text-slate-700 line-clamp-2">{post.summary}</p>
            <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
              <span>{post.author}</span>
              <span>{post.createdAt}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function PostDetailCard({ post, onBack }: { post: HeatPost; onBack: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const previewText = useMemo(() => {
    if (post.summary.length <= 180) return post.summary
    return `${post.summary.slice(0, 180)}...`
  }, [post.summary])

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <MessageSquare className="text-blue-500" />
          <div>
            <h2 className="text-xl font-bold text-slate-800">帖子详情</h2>
            <p className="text-sm text-slate-600">{post.id} · 热度 {post.heat}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded((prev) => !prev)}
            className="w-9 h-9 rounded-full bg-white/80 border border-white/40 shadow-lg flex items-center justify-center text-slate-600 hover:bg-white transition-all"
            title={expanded ? '折叠内容' : '展开内容'}
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
          <button onClick={onBack} className="btn-secondary inline-flex items-center gap-2">
            <ArrowLeft size={16} />
            返回榜单
          </button>
        </div>
      </div>
      <div className="space-y-3 text-sm text-slate-700">
        <p className="whitespace-pre-wrap break-words leading-relaxed">{expanded ? post.summary : previewText}</p>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>作者：{post.author}</span>
          <span>发布时间：{post.createdAt}</span>
        </div>
      </div>
    </div>
  )
}

function CommentsCard({ comments, sort, onSortChange }: { comments: CommentItem[]; sort: 'likes' | 'time'; onSortChange: (value: 'likes' | 'time') => void }) {
  const sorted = useMemo(() => {
    const list = [...comments]
    if (sort === 'likes') {
      return list.sort((a, b) => b.likes - a.likes)
    }
    return list.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }, [comments, sort])

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-800">评论区</h3>
          <p className="text-sm text-slate-600">展示帖子实时评论流</p>
        </div>
        <CommentSortTabs value={sort} onChange={onSortChange} />
      </div>
      <div className="space-y-3 max-h-[420px] overflow-auto pr-2">
        {sorted.map((comment) => (
          <div key={comment.id} className="bg-white/70 rounded-2xl p-4 border border-white/40">
            <p className="text-sm text-slate-700">{comment.content}</p>
            <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
              <span>点赞 {comment.likes}</span>
              <span>{comment.createdAt}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CommentSortTabs({ value, onChange }: { value: 'likes' | 'time'; onChange: (value: 'likes' | 'time') => void }) {
  return (
    <div className="flex items-center gap-2 bg-white/70 rounded-xl p-1 border border-white/40">
      <button
        className={`px-3 py-1 rounded-lg text-sm ${value === 'likes' ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white' : 'text-slate-600'}`}
        onClick={() => onChange('likes')}
      >
        按点赞
      </button>
      <button
        className={`px-3 py-1 rounded-lg text-sm ${value === 'time' ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white' : 'text-slate-600'}`}
        onClick={() => onChange('time')}
      >
        按时间
      </button>
    </div>
  )
}

function MetricsBarsCard({ emotion, extremity }: { emotion: number; extremity: number }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-4">
        <Activity className="text-blue-500" />
        <div>
          <h2 className="text-xl font-bold text-slate-800">指标变化</h2>
          <p className="text-sm text-slate-600">情绪度与极端度实时变化</p>
        </div>
      </div>
      <div className="space-y-6">
        <MetricBar label="情绪度" value={emotion} />
        <MetricBar label="内容极端度" value={extremity} />
      </div>
    </div>
  )
}

function MetricBar({ label, value }: { label: string; value: number }) {
  const leftWidth = Math.max(10, Math.min(90, value * 100))
  const rightWidth = 100 - leftWidth

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className="text-sm font-semibold text-slate-800">{value.toFixed(2)}</span>
      </div>
      <div className="h-3 w-full rounded-full overflow-hidden bg-slate-100 flex">
        <div className="bg-blue-500" style={{ width: `${leftWidth}%` }} />
        <div className="bg-red-500" style={{ width: `${rightWidth}%` }} />
      </div>
      <div className="flex justify-between text-xs text-slate-500 mt-1">
        <span>0.0</span>
        <span>1.0</span>
      </div>
    </div>
  )
}

function MetricsLineChartCard({ data }: { data: MetricsPoint[] }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-4">
        <Sparkles className="text-green-500" />
        <div>
          <h2 className="text-xl font-bold text-slate-800">指标趋势</h2>
          <p className="text-sm text-slate-600">情绪度 / 极端度趋势曲线</p>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="time" stroke="#94a3b8" />
            <YAxis domain={[0, 1]} stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="emotion" stroke="#3b82f6" strokeWidth={2} dot={false} name="情绪度" />
            <Line type="monotone" dataKey="extremity" stroke="#ef4444" strokeWidth={2} dot={false} name="极端度" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function InterventionFlowPanel({ state }: { state: FlowState }) {
  const roles: { role: Role; tone: string; label: string }[] = [
    { role: 'Analyst', tone: 'from-blue-500 to-cyan-500', label: 'Analyst' },
    { role: 'Strategist', tone: 'from-purple-500 to-blue-500', label: 'Strategist' },
    { role: 'Leader', tone: 'from-green-500 to-emerald-500', label: 'Leader' },
    { role: 'Amplifier', tone: 'from-orange-500 to-red-500', label: 'Amplifier' },
  ]

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <Shield className="text-emerald-500" />
          <div>
            <h2 className="text-xl font-bold text-slate-800">干预流程</h2>
            <p className="text-sm text-slate-600">当前运行角色高亮，运行中日志流式刷新</p>
          </div>
        </div>
      </div>

      {roles.map(({ role, tone, label }) => (
        <RoleStepCard
          key={role}
          role={role}
          label={label}
          tone={tone}
          isActive={state.activeRole === role}
          status={state.roles[role].status}
          before={state.roles[role].before}
          during={state.roles[role].during}
          after={state.roles[role].after}
        />
      ))}
    </div>
  )
}

function RoleStepCard({
  role,
  label,
  tone,
  isActive,
  status,
  before,
  during,
  after,
}: {
  role: Role
  label: string
  tone: string
  isActive: boolean
  status: 'idle' | 'running' | 'done' | 'error'
  before: string
  during: string[]
  after?: string[]
}) {
  const statusTone: Record<'idle' | 'running' | 'done' | 'error', 'muted' | 'warning' | 'success' | 'danger'> = {
    idle: 'muted',
    running: 'warning',
    done: 'success',
    error: 'danger',
  }

  return (
    <div
      className={[
        'glass-card transition-all duration-300',
        isActive ? 'p-6 scale-[1.02] ring-2 ring-emerald-200 shadow-2xl' : 'p-4 opacity-90',
      ].join(' ')}
      aria-current={isActive ? 'step' : undefined}
      data-role={role}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={[
            'w-10 h-10 rounded-xl bg-gradient-to-r flex items-center justify-center text-white font-semibold',
            tone,
          ].join(' ')}
          >
            {label.charAt(0)}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-slate-800">{label}</h3>
              <StatusBadge label={status.toUpperCase()} tone={statusTone[status]} />
            </div>
            <p className="text-xs text-slate-600">{before}</p>
          </div>
        </div>

        <div className="text-xs text-slate-500">
          {isActive ? '运行中日志' : after?.length ? '上次结果' : '尚未运行'}
        </div>
      </div>

      {isActive ? (
        <div className="mt-4 bg-white/60 border border-white/40 rounded-2xl p-4">
          <div className="space-y-2 max-h-64 overflow-auto pr-1">
            {during.length ? (
              during.map((line, idx) => (
                <div key={`${role}_${idx}`} className="text-sm text-slate-700 leading-relaxed break-words">
                  {line}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">等待日志...</div>
            )}
          </div>
        </div>
      ) : after?.length ? (
        <div className="mt-3 bg-white/60 border border-white/40 rounded-2xl px-4 py-3 space-y-1">
          {after.slice(0, 2).map((line, idx) => (
            <div key={`${role}_after_${idx}`} className="text-xs text-slate-600 break-words line-clamp-2">
              {line}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}


function CommentaryAnalysisPanel({ status, onOpenConfig, onRun }: { status: 'Idle' | 'Running' | 'Done' | 'Error'; onOpenConfig: () => void; onRun: () => void }) {
  return (
    <div className="glass-card p-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">评论区总体状态分析</h2>
          <p className="text-sm text-slate-600">LLM 周期性分析评论情绪与极化趋势</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="btn-secondary" onClick={onOpenConfig}>分析配置</button>
          <button className="btn-primary" onClick={onRun}>立即分析</button>
          <StatusBadge label={status} tone={status === 'Running' ? 'warning' : status === 'Done' ? 'success' : status === 'Error' ? 'danger' : 'muted'} />
        </div>
      </div>
      <AnalysisResultView status={status} />
    </div>
  )
}

function AnalysisConfigDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <div className="relative glass-card p-6 w-full max-w-lg mx-4">
        <h3 className="text-xl font-bold text-slate-800 mb-4">分析配置</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">分析时间间隔 t（分钟）</label>
            <input
              type="number"
              defaultValue={10}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="w-5 h-5 rounded" />
            <span className="text-sm text-slate-700">启用周期分析</span>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button className="btn-secondary" onClick={onClose}>取消</button>
          <button className="btn-primary" onClick={onClose}>保存</button>
        </div>
      </div>
    </div>
  )
}

function AnalysisResultView({ status }: { status: 'Idle' | 'Running' | 'Done' | 'Error' }) {
  return (
    <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="bg-white/70 rounded-2xl p-4 border border-white/40">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">分析摘要</h4>
        <p className="text-sm text-slate-600">当前分析状态：{status}。后续将展示总结性文本。</p>
      </div>
      <div className="bg-white/70 rounded-2xl p-4 border border-white/40">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">情绪结构</h4>
        <p className="text-sm text-slate-600">结构化结果占位：正/负情绪比例，重点人群。</p>
      </div>
      <div className="bg-white/70 rounded-2xl p-4 border border-white/40">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">系统建议</h4>
        <p className="text-sm text-slate-600">策略建议与风险提示占位。</p>
      </div>
    </div>
  )
}

function ToggleCard({ icon: Icon, label, enabled, onToggle }: { icon: ElementType; label: string; enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-3 rounded-2xl px-4 py-3 border transition-all duration-300 ${enabled
        ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white border-transparent shadow-lg'
        : 'bg-white/70 text-slate-700 border-white/40 shadow-lg'
        }`}
    >
      <Icon size={18} />
      <span className="text-sm font-medium">{label}</span>
    </button>
  )
}

function StatusBadge({ label, tone }: { label: string; tone: 'success' | 'warning' | 'danger' | 'info' | 'muted' }) {
  const toneMap: Record<'success' | 'warning' | 'danger' | 'info' | 'muted', string> = {
    success: 'bg-green-100 text-green-700',
    warning: 'bg-amber-100 text-amber-700',
    danger: 'bg-red-100 text-red-700',
    info: 'bg-blue-100 text-blue-700',
    muted: 'bg-slate-100 text-slate-600',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${toneMap[tone]}`}>
      {label}
    </span>
  )
}
