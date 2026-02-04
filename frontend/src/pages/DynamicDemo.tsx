import { useEffect, useMemo, useRef, useState, type ReactNode, type ElementType } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Activity, Play, Square, Shield, Bug, Sparkles, Flame, MessageSquare, ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createInitialFlowState, routeLogLine, type FlowState, type Role } from '../lib/interventionFlow/logRouter'
import { createEventSourceLogStream, createSimulatedLogStream, type LogStream } from '../lib/interventionFlow/logStream'
import { computeEffectiveRole, nextSelectedRoleOnTabClick } from '../lib/interventionFlow/selection'
import { parsePostContent } from '../lib/interventionFlow/postContent'
import { getEmptyCopy } from '../lib/interventionFlow/emptyCopy'
import { isPreRunEmptyState } from '../lib/interventionFlow/emptyState'
import { DEFAULT_WORKFLOW_REPLAY_DELAY_MS, getOpinionBalanceLogStreamUrl, shouldCallOpinionBalanceProcessApi } from '../lib/interventionFlow/replayConfig'
import { getRoleTabButtonClassName } from '../lib/interventionFlow/roleTabStyles'
import { getInterventionFlowPanelClassName, getLeaderCommentsContainerClassName } from '../lib/interventionFlow/panelLayout'
import { buildRolePills } from '../lib/interventionFlow/rolePills'
import { getSummaryCardClassName } from '../lib/interventionFlow/summaryCardStyles'
import { getSummaryGridClassName } from '../lib/interventionFlow/summaryGridLayout'
import { formatAnalysisStatus, formatDemoRunStatus, formatSseStatus, formatTopCount } from '../lib/interventionFlow/uiLabels'
import { getHeatLeaderboardCardClassName, getHeatLeaderboardListClassName } from '../lib/interventionFlow/heatLeaderboardLayout'
import { getAnalystCombinedCardClassName, getAnalystCombinedPostBodyClassName, getAnalystCombinedStreamClassName } from '../lib/interventionFlow/analystCombinedLayout'
import { buildStageStepperModel } from '../lib/interventionFlow/stageStepper'
import { getLiveBadgeClassName, getStageHeaderContainerClassName, getStageHeaderTextClassName, getStageSegmentClassName } from '../lib/interventionFlow/detailHeaderLayout'
import { getDynamicDemoGridClassName } from '../lib/interventionFlow/pageGridLayout'
import { createFixedRateLineQueue } from '../lib/interventionFlow/logRenderQueue'
import { useLeaderboard } from '../hooks/useLeaderboard'
import { usePostDetail } from '../hooks/usePostDetail'
import { usePostComments } from '../hooks/usePostComments'

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
  '2026-01-28 21:18:54,727 - INFO - 🎉 Workflow completed - effectiveness score: 10.0/10',
  '2026-01-28 21:18:54,728 - INFO - 🔄 [Monitoring round 1/3]',
  '2026-01-28 21:18:54,728 - INFO -   📊 Analyst Agent - generate baseline effectiveness report',
  '2026-01-28 21:18:54,728 - INFO -   🔍 Analyst monitoring - establish baseline data',
  '2026-01-28 21:24:38,434 - INFO - 🚀 Start workflow execution - Action ID: action_20260128_212438',
  '2026-01-28 21:24:38,434 - INFO - ⚖️ Strategist is creating strategy...',
  '2026-01-28 21:24:49,879 - INFO - 🎯 Leader Agent starts USC process and generates candidate comments...',
]

const USE_SIMULATED_LOG_STREAM = false
// Replay mode: read a fixed workflow log file and stream it via the backend SSE endpoint.
// Default to real backend streaming; set to true only when you intentionally demo a fixed replay log.
const USE_WORKFLOW_LOG_REPLAY = false
// One full round only (a single "action_..." cycle) so the demo doesn't endlessly chain.
const WORKFLOW_REPLAY_BACKEND_FILE = 'replay_workflow_20260130_round1.log'
// Slower replay so the user can actually read the UI while it streams.
const WORKFLOW_REPLAY_DELAY_MS = DEFAULT_WORKFLOW_REPLAY_DELAY_MS * 5

// Full-time smoothing: render log lines at a fixed cadence to avoid bursty UI updates.
const LOG_RENDER_INTERVAL_MS = 80
const LOG_RENDER_MAX_LINES_PER_TICK = 1

interface HeatPost {
  id: string
  summary: string
  heat: number
  author: string
  createdAt: string
  // 新增字段以支持真实 API 数据
  feedScore?: number
  excerpt?: string
  authorId?: string
  postId?: string
  content?: string
  likeCount?: number
  shareCount?: number
  commentCount?: number
}

interface CommentItem {
  id: string
  content: string
  likes: number
  createdAt: string
  // 新增字段以支持真实 API 数据
  commentId?: string
  likeCount?: number
  authorId?: string
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
  const [selectedPost, setSelectedPost] = useState<HeatPost | null>(null)
  const [commentSort, setCommentSort] = useState<'likes' | 'time'>('likes')

  // 使用 useLeaderboard Hook 获取热度榜数据
  const {
    data: leaderboardItems,
    isLoading: leaderboardLoading,
    error: leaderboardError
  } = useLeaderboard({ enableSSE: true, limit: 20 })

  // 使用 usePostDetail Hook 获取帖子详情
  const {
    data: postDetail,
    isLoading: postDetailLoading,
    error: postDetailError
  } = usePostDetail(selectedPost?.postId || selectedPost?.id || null)

  // 使用 usePostComments Hook 获取评论列表
  const {
    data: comments,
    isLoading: commentsLoading,
    error: commentsError
  } = usePostComments(selectedPost?.postId || selectedPost?.id || null, commentSort)

  // 将 API 数据转换为组件所需格式
  const heatPosts: HeatPost[] = useMemo(() => {
    if (!leaderboardItems) return []
    return leaderboardItems.map(item => ({
      id: item.postId,
      postId: item.postId,
      summary: item.excerpt,
      excerpt: item.excerpt,
      heat: item.score,
      feedScore: item.score,
      author: item.authorId,
      authorId: item.authorId,
      createdAt: item.createdAt,
      likeCount: item.likeCount,
      shareCount: item.shareCount,
      commentCount: item.commentCount,
    }))
  }, [leaderboardItems])

  // 将评论数据转换为组件所需格式
  const commentItems: CommentItem[] = useMemo(() => {
    if (!comments) return []
    return comments.map(comment => ({
      id: comment.commentId,
      commentId: comment.commentId,
      content: comment.content,
      likes: comment.likeCount,
      likeCount: comment.likeCount,
      createdAt: comment.createdAt,
      authorId: comment.authorId,
    }))
  }, [comments])

  // 合并加载状态和错误状态
  const isLoading = leaderboardLoading || (selectedPost ? (postDetailLoading || commentsLoading) : false)
  const error = leaderboardError || postDetailError || commentsError

  const data = useMemo<DynamicDemoData>(() => {
    return {
      heatPosts,
      comments: commentItems,
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
  }, [heatPosts, commentItems])

  return {
    data,
    isLoading,
    error,
    selectedPost,
    setSelectedPost,
    commentSort,
    setCommentSort,
    postDetail
  }
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
  const {
    data,
    isLoading,
    error,
    selectedPost,
    setSelectedPost,
    commentSort,
    setCommentSort,
    postDetail
  } = useDynamicDemoApi()
  const sse = useDynamicDemoSSE()

  const [isRunning, setIsRunning] = useState(false)
  const [enableAttack, setEnableAttack] = useState(false)
  const [enableAftercare, setEnableAftercare] = useState(false)
  const [enableEvoCorps, setEnableEvoCorps] = useState(false)

  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<'Idle' | 'Running' | 'Done' | 'Error'>('Idle')

  const [isStarting, setIsStarting] = useState(false)
  const [isTogglingAttack, setIsTogglingAttack] = useState(false)
  const [isTogglingAftercare, setIsTogglingAftercare] = useState(false)

  const [flowState, setFlowState] = useState<FlowState>(() => createInitialFlowState())
  const [opinionBalanceStartMs, setOpinionBalanceStartMs] = useState<number | null>(null)
  const streamRef = useRef<LogStream | null>(null)
  const unsubscribeRef = useRef<null | (() => void)>(null)
  const renderQueueRef = useRef<ReturnType<typeof createFixedRateLineQueue> | null>(null)

  // 添加状态轮询机制
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch('/api/dynamic/status')
        const data = await response.json()

        // 检查 database 和 main 进程状态
        const dbRunning = data.database?.status === 'running'
        const mainRunning = data.main?.status === 'running'
        const bothRunning = dbRunning && mainRunning

        setIsRunning(bothRunning)

        // Only sync opinion-balance toggle from backend when we actually manage the backend process.
        // In workflow log replay mode, enableEvoCorps is a pure UI stream toggle and must not be
        // overridden by status polling (otherwise it flips back off immediately).
        if (shouldCallOpinionBalanceProcessApi(USE_WORKFLOW_LOG_REPLAY)) {
          const obRunning = data.opinion_balance?.status === 'running'
          setEnableEvoCorps(obRunning)
        }

        // 同步恶意攻击和事后干预的状态
        if (data.control_flags) {
          setEnableAttack(data.control_flags.attack_enabled ?? false)
          setEnableAftercare(data.control_flags.aftercare_enabled ?? false)
        }
      } catch (error) {
        console.error('Failed to check status:', error)
      }
    }

    // 初始检查
    checkStatus()

    // 每 2 秒轮询一次
    const interval = setInterval(checkStatus, 2000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Spec:
    // - enableEvoCorps on => connect log stream and render (independent from isRunning)
    // - enableEvoCorps off => disconnect stream and clear/freeze UI
    if (!enableEvoCorps) {
      streamRef.current?.stop()
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      streamRef.current = null
      renderQueueRef.current?.stop()
      renderQueueRef.current = null
      setFlowState(createInitialFlowState())
      setOpinionBalanceStartMs(null)
      return
    }

    // reset display for a new "session" of opinion balance viewing
    setFlowState(createInitialFlowState())

    if (streamRef.current) return

    const sinceMs = opinionBalanceStartMs ?? Date.now()

    const streamUrl = getOpinionBalanceLogStreamUrl({
      replay: USE_WORKFLOW_LOG_REPLAY,
      replayFile: WORKFLOW_REPLAY_BACKEND_FILE,
      delayMs: WORKFLOW_REPLAY_DELAY_MS,
      // Real-time: only show logs after the user clicked the toggle.
      sinceMs,
      // Small tail to cover the click->connect gap, filtered by sinceMs on the backend.
      tail: 200,
    })

    const renderQueue = createFixedRateLineQueue({
      intervalMs: LOG_RENDER_INTERVAL_MS,
      maxLinesPerTick: LOG_RENDER_MAX_LINES_PER_TICK,
      onDrain: (lines) => {
        setFlowState((prev) => {
          let next = prev
          for (const line of lines) next = routeLogLine(next, line)
          return next
        })
      },
    })
    renderQueue.start()
    renderQueueRef.current = renderQueue

    const stream = USE_SIMULATED_LOG_STREAM
      ? createSimulatedLogStream({ lines: DEMO_BACKEND_LOG_LINES, intervalMs: 320 })
      : createEventSourceLogStream(streamUrl)
    const unsubscribe = stream.subscribe((line) => renderQueue.push(line))
    stream.start()

    streamRef.current = stream
    unsubscribeRef.current = unsubscribe

    return () => {
      streamRef.current?.stop()
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      streamRef.current = null
      renderQueueRef.current?.stop()
      renderQueueRef.current = null
    }
  }, [enableEvoCorps, opinionBalanceStartMs])

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
        onToggleAttack={async () => {
          if (isTogglingAttack) return

          // 如果当前是启用状态，显示确认弹窗
          if (enableAttack) {
            if (!confirm('是否确认关闭恶意水军攻击？')) {
              return
            }
          }

          setIsTogglingAttack(true)

          try {
            const response = await fetch('http://localhost:8000/control/attack', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ enabled: !enableAttack }),
            })

            const data = await response.json()

            if (response.ok && data.attack_enabled !== undefined) {
              setEnableAttack(data.attack_enabled)

              // 显示成功提示
              if (data.attack_enabled) {
                alert('✅ 恶意水军攻击已开启')
              } else {
                alert('✅ 恶意水军攻击已关闭')
              }
            } else {
              throw new Error('API 返回异常')
            }
          } catch (error) {
            alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error toggling attack:', error)
          } finally {
            setIsTogglingAttack(false)
          }
        }}
        onToggleAftercare={async () => {
          if (isTogglingAftercare) return

          // 如果当前是启用状态，显示确认弹窗
          if (enableAftercare) {
            if (!confirm('是否确认关闭事后干预？')) {
              return
            }
          }

          setIsTogglingAftercare(true)

          try {
            const response = await fetch('http://localhost:8000/control/aftercare', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ enabled: !enableAftercare }),
            })

            const data = await response.json()

            if (response.ok && data.aftercare_enabled !== undefined) {
              setEnableAftercare(data.aftercare_enabled)

              // 显示成功提示
              if (data.aftercare_enabled) {
                alert('✅ 事后干预已开启')
              } else {
                alert('✅ 事后干预已关闭')
              }
            } else {
              throw new Error('API 返回异常')
            }
          } catch (error) {
            alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error toggling aftercare:', error)
          } finally {
            setIsTogglingAftercare(false)
          }
        }}
        onToggleEvoCorps={async () => {
          const manageProcess = shouldCallOpinionBalanceProcessApi(USE_WORKFLOW_LOG_REPLAY)
          // 如果当前是禁用状态，则启用并调用 API
          if (!enableEvoCorps) {
            const clickedAtMs = Date.now()
            if (!manageProcess) {
              // Replay-only mode: do not start any backend workflow process, just connect to the SSE replay stream.
              setEnableEvoCorps(true)
              setOpinionBalanceStartMs(clickedAtMs)
              return
            }

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
                setOpinionBalanceStartMs(clickedAtMs)
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
            // 显示确认对话框
            if (!confirm('是否确认关闭舆论平衡系统？')) {
              return
            }

            if (!manageProcess) {
              // Replay-only mode: no backend process to stop.
              setEnableEvoCorps(false)
              setOpinionBalanceStartMs(null)
              return
            }

            // 如果当前是启用状态，则停止舆论平衡系统
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
                setOpinionBalanceStartMs(null)
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

      <div className={getDynamicDemoGridClassName()}>
        <div className="space-y-6">
          {!selectedPost ? (
            <HeatLeaderboardCard
              posts={data.heatPosts}
              onSelect={setSelectedPost}
              isLoading={isLoading}
              error={error || undefined}
            />
          ) : (
            <div className="space-y-6">
              <PostDetailCard
                post={selectedPost}
                postDetail={postDetail}
                onBack={() => setSelectedPost(null)}
                isLoading={isLoading}
                error={error || undefined}
              />
              <CommentsCard
                comments={data.comments}
                sort={commentSort}
                onSortChange={setCommentSort}
                isLoading={isLoading}
                error={error || undefined}
              />
            </div>
          )}
        </div>

        <div className="space-y-6">
          <MetricsBarsCard emotion={currentMetrics.emotion} extremity={currentMetrics.extremity} />
          <MetricsLineChartCard data={data.metricsSeries} />
        </div>

        <div className="space-y-6">
          {enableEvoCorps ? (
            <InterventionFlowPanel state={flowState} enabled={enableEvoCorps} />
          ) : (
            <div className="glass-card p-6 min-h-[640px] flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="flex justify-center">
                  <Shield className="text-slate-400" size={32} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-800">干预流程</h3>
                  <p className="text-sm text-slate-600">启用舆论平衡系统后展示实时干预过程。</p>
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
  onToggleAttack: () => void | Promise<void>
  onToggleAftercare: () => void | Promise<void>
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
            <StatusBadge label={formatDemoRunStatus(isRunning)} tone={isRunning ? 'success' : 'muted'} />
            <StatusBadge
              label={formatSseStatus(sseStatus)}
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
              {isStarting ? '启动中...' : isRunning ? '运行中' : '开启演示'}
            </button>
            <button className="btn-secondary inline-flex items-center gap-2" onClick={onStop}>
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

function HeatLeaderboardCard({
  posts,
  onSelect,
  isLoading,
  error
}: {
  posts: HeatPost[]
  onSelect: (post: HeatPost) => void
  isLoading?: boolean
  error?: Error | null
}) {
  return (
    <div className={getHeatLeaderboardCardClassName()}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Flame className="text-orange-500" />
          <div>
            <h2 className="text-xl font-bold text-slate-800">帖子热度榜</h2>
            <p className="text-sm text-slate-600">实时热度排名</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge label={formatTopCount(posts.length)} tone="info" />
          {isLoading && <StatusBadge label="加载中" tone="warning" />}
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
        </div>
      )}

      <div className={getHeatLeaderboardListClassName()}>
        {isLoading && posts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-500">加载中...</p>
          </div>
        ) : posts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-500">暂无数据</p>
          </div>
        ) : (
          posts.slice(0, 20).map((post, index) => {
            const id = post.postId || post.id
            const score = post.feedScore ?? post.heat
            const author = post.authorId || post.author
            return (
              <button
                key={id}
                onClick={() => onSelect(post)}
                className="w-full text-left bg-white/70 hover:bg-white transition-all rounded-2xl p-4 border border-white/40"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-700">#{index + 1} · {id}</span>
                  <span className="text-sm font-bold text-orange-500">{score.toFixed(2)}</span>
                </div>
                <p className="text-sm text-slate-700 line-clamp-2">{post.excerpt || post.summary}</p>
                <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                  <span className="truncate max-w-[55%]">{author}</span>
                  <span className="shrink-0">{post.createdAt}</span>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}

function PostDetailCard({
  post,
  postDetail,
  onBack,
  isLoading,
  error
}: {
  post: HeatPost
  postDetail?: any
  onBack: () => void
  isLoading?: boolean
  error?: Error | null
}) {
  const [expanded, setExpanded] = useState(false)

  // 优先使用 postDetail 的完整内容，否则使用 post 的 summary
  const fullContent = postDetail?.content || post.content || post.summary || post.excerpt || ''
  const previewText = useMemo(() => {
    if (fullContent.length <= 180) return fullContent
    return `${fullContent.slice(0, 180)}...`
  }, [fullContent])

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <MessageSquare className="text-blue-500" />
          <div>
            <h2 className="text-xl font-bold text-slate-800">帖子详情</h2>
            <p className="text-sm text-slate-600">
              {post.postId || post.id} · 热度 {(post.feedScore || post.heat).toFixed(2)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && <StatusBadge label="加载中" tone="warning" />}
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

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
        </div>
      )}

      <div className="space-y-3 text-sm text-slate-700">
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {expanded ? fullContent : previewText}
        </p>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>作者：{post.authorId || post.author}</span>
          <span>发布时间：{new Date(post.createdAt).toLocaleString('zh-CN')}</span>
          {(post.likeCount !== undefined || postDetail?.likeCount !== undefined) && (
            <span>点赞：{postDetail?.likeCount ?? post.likeCount}</span>
          )}
          {(post.shareCount !== undefined || postDetail?.shareCount !== undefined) && (
            <span>分享：{postDetail?.shareCount ?? post.shareCount}</span>
          )}
          {(post.commentCount !== undefined || postDetail?.commentCount !== undefined) && (
            <span>评论：{postDetail?.commentCount ?? post.commentCount}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function CommentsCard({
  comments,
  sort,
  onSortChange,
  isLoading,
  error
}: {
  comments: CommentItem[]
  sort: 'likes' | 'time'
  onSortChange: (value: 'likes' | 'time') => void
  isLoading?: boolean
  error?: Error | null
}) {
  const sorted = useMemo(() => {
    const list = [...comments]
    if (sort === 'likes') {
      return list.sort((a, b) => (b.likeCount ?? b.likes) - (a.likeCount ?? a.likes))
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
        <div className="flex items-center gap-2">
          {isLoading && <StatusBadge label="加载中" tone="warning" />}
          <CommentSortTabs value={sort} onChange={onSortChange} />
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
        </div>
      )}

      <div className="space-y-3 max-h-[420px] overflow-auto pr-2">
        {isLoading && comments.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-slate-500">加载中...</p>
          </div>
        ) : comments.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-slate-500">暂无评论</p>
          </div>
        ) : (
          sorted.map((comment) => (
            <div key={comment.commentId || comment.id} className="bg-white/70 rounded-2xl p-4 border border-white/40">
              <p className="text-sm text-slate-700">{comment.content}</p>
              <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                <span>点赞 {comment.likeCount ?? comment.likes}</span>
                <span>{new Date(comment.createdAt).toLocaleString('zh-CN', {
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}</span>
              </div>
            </div>
          ))
        )}
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

function InterventionFlowPanel({ state, enabled }: { state: FlowState; enabled: boolean }) {
  const roles: { role: Role; tone: string; label: string }[] = [
    { role: 'Analyst', tone: 'from-blue-500 to-cyan-500', label: '分析师' },
    { role: 'Strategist', tone: 'from-purple-500 to-blue-500', label: '战略家' },
    { role: 'Leader', tone: 'from-green-500 to-emerald-500', label: '领袖' },
    { role: 'Amplifier', tone: 'from-orange-500 to-red-500', label: '扩音器' },
  ]

  // Review mode (A): once user clicks a tab, don't auto-jump when activeRole changes.
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  useEffect(() => {
    if (!enabled) setSelectedRole(null)
  }, [enabled])

  const effectiveRole = computeEffectiveRole(selectedRole, state.activeRole)
  const roleMeta = roles.find((r) => r.role === effectiveRole)
  const roleState = state.roles[effectiveRole]
  const isLive = enabled && state.activeRole === effectiveRole && roleState.status === 'running'

  return (
    <div className={getInterventionFlowPanelClassName()}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Shield className="text-emerald-500" />
          <h2 className="text-xl font-bold text-slate-800">干预流程</h2>
        </div>
        {/* No follow button; user can exit review mode by clicking the active role tab. */}
      </div>

      <RoleTabsRow
        enabled={enabled}
        roles={roles}
        activeRole={state.activeRole}
        effectiveRole={effectiveRole}
        roleStatuses={{
          Analyst: state.roles.Analyst.status,
          Strategist: state.roles.Strategist.status,
          Leader: state.roles.Leader.status,
          Amplifier: state.roles.Amplifier.status,
        }}
        onSelect={(r) => setSelectedRole((prev) => nextSelectedRoleOnTabClick(prev, r, state.activeRole))}
      />

      <RoleDetailSection
        role={effectiveRole}
        label={roleMeta?.label ?? effectiveRole}
        tone={roleMeta?.tone ?? 'from-slate-500 to-slate-600'}
        enabled={enabled}
        isLive={isLive}
        status={roleState.status}
        stage={roleState.stage}
        summary={roleState.summary}
        during={roleState.during}
        after={roleState.after}
        context={state.context}
        amplifierSummary={state.roles.Amplifier.summary}
      />
    </div>
  )
}

function RoleTabsRow({
  enabled,
  roles,
  activeRole,
  effectiveRole,
  roleStatuses,
  onSelect,
}: {
  enabled: boolean
  roles: { role: Role; tone: string; label: string }[]
  activeRole: Role | null
  effectiveRole: Role
  roleStatuses: Record<Role, 'idle' | 'running' | 'done' | 'error'>
  onSelect: (role: Role) => void
}) {
  return (
    <div className="mt-4 grid grid-cols-2 gap-2">
      {roles.map(({ role, tone, label }) => {
        const isSelected = effectiveRole === role
        const isActive = enabled && activeRole === role
        const status = roleStatuses[role]

        return (
          <button
            key={role}
            onClick={() => onSelect(role)}
            className={getRoleTabButtonClassName(isSelected)}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={[
                    'w-8 h-8 rounded-xl bg-gradient-to-r flex items-center justify-center text-white font-semibold shrink-0',
                    tone,
                  ].join(' ')}
                >
                  {label.charAt(0)}
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-800 truncate">{label}</div>
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                <span
                  className={[
                    'w-2 h-2 rounded-full',
                    isActive
                      ? 'bg-emerald-500 animate-pulse'
                      : status === 'done'
                        ? 'bg-emerald-400'
                        : status === 'error'
                          ? 'bg-red-500'
                          : 'bg-slate-300',
                  ].join(' ')}
                  aria-label={isActive ? 'active' : 'inactive'}
                />
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

function RoleDetailSection({
  role,
  label,
  tone,
  enabled,
  isLive,
  status,
  stage,
  summary,
  during,
  after,
  context,
  amplifierSummary,
}: {
  role: Role
  label: string
  tone: string
  enabled: boolean
  isLive: boolean
  status: 'idle' | 'running' | 'done' | 'error'
  stage: { current: number; max: number; order: number[] }
  summary: string[]
  during: string[]
  after?: string[]
  context: FlowState['context']
  amplifierSummary: string[]
}) {
  const displayLines = isLive ? during : (after ?? [])
  const emptyCopy = useMemo(() => getEmptyCopy({ enabled }), [enabled])
  const parsedPost = useMemo(() => {
    if (!context.postContent) return null
    return parsePostContent(context.postContent, { previewChars: 160 })
  }, [context.postContent])

  const pills = buildRolePills(role, {
    feedScore: context.feedScore,
    summary,
    related: role === 'Strategist' ? { amplifierSummary } : undefined,
  })
  const preRunEmpty = isPreRunEmptyState({ enabled, status, linesCount: displayLines.length })
  const stageModel = useMemo(() => buildStageStepperModel(role, stage), [role, stage.current, stage.max, stage.order])
  const shouldShowStage =
    enabled &&
    status !== 'idle' &&
    stageModel.currentPos >= 0 &&
    stageModel.total > 0 &&
    stageModel.seenCount > 0 &&
    stageModel.currentLabel

  return (
    <div className="mt-4 min-h-0 flex-1 flex flex-col" aria-current="step" data-role={role}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={['w-10 h-10 rounded-xl bg-gradient-to-r flex items-center justify-center text-white font-semibold shrink-0', tone].join(' ')}>
            {label.charAt(0)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <h3 className="text-lg font-semibold text-slate-800 whitespace-nowrap">{label}</h3>
              {isLive ? (
                <span className={getLiveBadgeClassName()}>
                  实时
                </span>
              ) : null}
            </div>
          </div>
        </div>

        {shouldShowStage ? (
          <div className={getStageHeaderContainerClassName()} title={stageModel.tooltip}>
            <div className={getStageHeaderTextClassName()}>
              阶段：{stageModel.currentLabel}（{stageModel.seenCount}/{stageModel.total}）
            </div>
            <div className="mt-1 flex items-center justify-end gap-1">
              {stageModel.stages.map((_, idx) => {
                const isDone = stageModel.maxPos >= 0 ? idx < stageModel.maxPos : false
                const isCurrent = idx === stageModel.currentPos
                return (
                  <span
                    key={`${role}_stage_${idx}`}
                    className={getStageSegmentClassName(isCurrent ? 'current' : isDone ? 'done' : 'todo')}
                  />
                )
              })}
            </div>
          </div>
        ) : null}
      </div>

      {!preRunEmpty && pills.length ? (
        <div className={getSummaryGridClassName(role)}>
          {pills.slice(0, 4).map((line, idx) => (
            <div
              key={`${role}_summary_${idx}`}
              className={getSummaryCardClassName(role, idx)}
              title={line}
            >
              {line}
            </div>
          ))}
        </div>
      ) : null}

      {role === 'Analyst' ? (
        <div className={getAnalystCombinedCardClassName()}>
          {parsedPost ? (
            <div>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="text-xs font-semibold text-slate-700 shrink-0">帖子与分析</div>
                  {parsedPost.tag ? (
                    <span className="text-[10px] font-semibold text-slate-700 px-2 py-1 rounded-full bg-white/70 border border-white/40 shrink-0">
                      {parsedPost.tag}
                    </span>
                  ) : null}
                </div>
                {/* Always show full post content; no expand/collapse. */}
              </div>

              <div className="mt-2">
                <div className={getAnalystCombinedPostBodyClassName()}>
                  {parsedPost.full}
                </div>
              </div>
            </div>
          ) : null}

          <div className="h-px bg-white/60" />

          <div className={getAnalystCombinedStreamClassName()}>
            {displayLines.length ? (
              displayLines.map((line, idx) => (
                <div key={`${role}_${idx}`} className="text-sm text-slate-700 leading-relaxed break-all">
                  {line}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-600">{emptyCopy.stream}</div>
            )}
          </div>
        </div>
      ) : null}

      {role === 'Leader' && context.leaderComments.length ? (
        <div className="mt-4 bg-white/60 border border-white/40 rounded-2xl p-4">
          <div className="text-xs font-semibold text-slate-700 mb-2">领袖评论</div>
          <div className={getLeaderCommentsContainerClassName()}>
            {context.leaderComments.map((c, idx) => (
              <div key={`leader_comment_${idx}`} className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap break-all">
                {c}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {role !== 'Analyst' ? (
        <div className="mt-4 bg-white/60 border border-white/40 rounded-2xl p-4 min-h-0 flex-1">
          <div className="space-y-2 h-full overflow-y-auto overflow-x-hidden pr-1">
            {displayLines.length ? (
              displayLines.map((line, idx) => (
                <div key={`${role}_${idx}`} className="text-sm text-slate-700 leading-relaxed break-all">
                  {line}
                </div>
              ))
            ) : (
              <div className="space-y-1">
                <div className="text-sm text-slate-600">{emptyCopy.stream}</div>
              </div>
            )}
          </div>
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
          <p className="text-sm text-slate-600">大模型周期性分析评论情绪与极化趋势</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="btn-secondary" onClick={onOpenConfig}>分析配置</button>
          <button className="btn-primary" onClick={onRun}>立即分析</button>
          <StatusBadge label={formatAnalysisStatus(status)} tone={status === 'Running' ? 'warning' : status === 'Done' ? 'success' : status === 'Error' ? 'danger' : 'muted'} />
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
            <label className="block text-sm font-medium text-slate-700 mb-2">分析间隔（分钟）</label>
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
        <p className="text-sm text-slate-600">当前分析状态：{formatAnalysisStatus(status)}。后续将展示总结性文本。</p>
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
