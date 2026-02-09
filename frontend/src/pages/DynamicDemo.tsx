import { useCallback, useEffect, useMemo, useRef, useState, type ElementType, type ReactNode } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Activity, Play, Square, Shield, Bug, Sparkles, Flame, MessageSquare, ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createInitialFlowState, routeLogLine, stripLogPrefix, type FlowState, type Role } from '../lib/interventionFlow/logRouter'
import { createEventSourceLogStream, createSimulatedLogStream, type LogStream } from '../lib/interventionFlow/logStream'
import { computeEffectiveRole, nextSelectedRoleOnTabClick } from '../lib/interventionFlow/selection'
import { parsePostContent } from '../lib/interventionFlow/postContent'
import { getEmptyCopy } from '../lib/interventionFlow/emptyCopy'
import { isPreRunEmptyState } from '../lib/interventionFlow/emptyState'
import { getOpinionBalanceLogStreamUrl, shouldCallOpinionBalanceProcessApi } from '../lib/interventionFlow/replayConfig'
import { toUserMilestone } from '../lib/interventionFlow/milestones'
import { getRoleTabButtonClassName } from '../lib/interventionFlow/roleTabStyles'
import { getInterventionFlowPanelClassName, getLeaderCommentsContainerClassName } from '../lib/interventionFlow/panelLayout'
import { buildRolePills } from '../lib/interventionFlow/rolePills'
import { getSummaryCardClassName } from '../lib/interventionFlow/summaryCardStyles'
import { getSummaryGridClassName } from '../lib/interventionFlow/summaryGridLayout'
import { formatDemoRunStatus, formatSseStatus, formatTopCount } from '../lib/interventionFlow/uiLabels'
import { getHeatLeaderboardCardClassName, getHeatLeaderboardListClassName } from '../lib/interventionFlow/heatLeaderboardLayout'
import { getAnalystCombinedCardClassName, getAnalystCombinedPostBodyClassName, getAnalystCombinedStreamClassName } from '../lib/interventionFlow/analystCombinedLayout'
import { buildStageStepperModel } from '../lib/interventionFlow/stageStepper'
import { getLiveBadgeClassName, getStageHeaderContainerClassName, getStageHeaderTextClassName, getStageSegmentClassName } from '../lib/interventionFlow/detailHeaderLayout'
import { getDynamicDemoGridClassName } from '../lib/interventionFlow/pageGridLayout'
import { createTimestampSmoothLineQueue } from '../lib/interventionFlow/logRenderQueue'
import { useLeaderboard } from '../hooks/useLeaderboard'
import { usePostDetail } from '../hooks/usePostDetail'
import { usePostComments } from '../hooks/usePostComments'
import { usePostAnalysis } from '../hooks/usePostAnalysis'

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
// Replay: let the frontend control pacing based on timestamps (avoid double-throttling).
const WORKFLOW_REPLAY_DELAY_MS = 0

// Fixed-speed replay: slow and readable (consistent pacing across lines).
const LOG_RENDER_MIN_DELAY_MS = 200
const LOG_RENDER_MAX_DELAY_MS = 4000
const LOG_RENDER_TIME_SCALE = 0.01
const LOG_RENDER_SMOOTHING_ALPHA = 0
const LOG_RENDER_DELAY_DEFAULT_MS = 1400
const LOG_RENDER_DELAY_ANALYST_STAGE0_MS = 650
const LOG_RENDER_DELAY_ANALYST_STAGE_1_TO_3_MS = 2200
const LOG_RENDER_DELAY_ANALYST_STAGE_4_TO_5_MS = 1800

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
  // 从 localStorage 加载 selectedPost
  const [selectedPost, setSelectedPost] = useState<HeatPost | null>(() => {
    try {
      const saved = localStorage.getItem('dynamicDemo_selectedPost')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [commentSort, setCommentSort] = useState<'likes' | 'time'>('likes')

  // 使用 useLeaderboard Hook 获取热度榜数据
  const {
    data: leaderboardItems,
    isLoading: leaderboardLoading,
    error: leaderboardError,
    refetch: refetchLeaderboard
  } = useLeaderboard({ enableSSE: true, limit: 20 })

  // 计算当前选中的帖子 ID，确保状态一致性
  const selectedPostId = useMemo(() => {
    return selectedPost?.postId || selectedPost?.id || null
  }, [selectedPost])

  // 使用 usePostDetail Hook 获取帖子详情
  const {
    data: postDetail,
    isLoading: postDetailLoading,
    error: postDetailError
  } = usePostDetail(selectedPostId)

  // 使用 usePostComments Hook 获取评论列表
  const {
    data: comments,
    isLoading: commentsLoading,
    error: commentsError
  } = usePostComments(selectedPostId, commentSort)

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
        { time: '10:00', emotion: 0.5, extremity: 0.5 },
        { time: '10:05', emotion: 0.5, extremity: 0.5 },
        { time: '10:10', emotion: 0.5, extremity: 0.5 },
        { time: '10:15', emotion: 0.5, extremity: 0.5 },
        { time: '10:20', emotion: 0.5, extremity: 0.5 },
        { time: '10:25', emotion: 0.5, extremity: 0.5 },
        { time: '10:30', emotion: 0.5, extremity: 0.5 },
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

  // 持久化 selectedPost
  useEffect(() => {
    if (selectedPost) {
      try {
        localStorage.setItem('dynamicDemo_selectedPost', JSON.stringify(selectedPost))
      } catch (error) {
        console.warn('Failed to save selectedPost to localStorage:', error)
      }
    } else {
      try {
        localStorage.removeItem('dynamicDemo_selectedPost')
      } catch (error) {
        console.warn('Failed to remove selectedPost from localStorage:', error)
      }
    }
  }, [selectedPost])

  // 创建一个安全的 setSelectedPost 包装函数，确保状态更新正确触发
  const handleSetSelectedPost = useCallback((post: HeatPost | null) => {
    setSelectedPost(post)
  }, [])

  // 页面加载时，如果有 trackedPostId 但没有 selectedPost，尝试从热度榜中恢复
  // 使用 ref 来避免在用户主动点击"返回榜单"后自动恢复
  const hasRestoredRef = useRef(false)
  useEffect(() => {
    // 只在首次加载时尝试恢复一次
    if (hasRestoredRef.current) return

    const trackedPostId = localStorage.getItem('postAnalysis_trackedPostId')
    if (trackedPostId && !selectedPost && heatPosts.length > 0) {
      try {
        const postId = JSON.parse(trackedPostId)
        const foundPost = heatPosts.find(p => (p.postId || p.id) === postId)
        if (foundPost) {
          handleSetSelectedPost(foundPost)
          hasRestoredRef.current = true
        }
      } catch (error) {
        console.warn('Failed to restore selectedPost from trackedPostId:', error)
      }
    }
  }, [heatPosts, selectedPost, handleSetSelectedPost])

  return {
    data,
    isLoading,
    error,
    selectedPost,
    setSelectedPost: handleSetSelectedPost,
    commentSort,
    setCommentSort,
    postDetail,
    refetchLeaderboard
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
    postDetail,
    refetchLeaderboard
  } = useDynamicDemoApi()
  const sse = useDynamicDemoSSE()

  // 集成 usePostAnalysis Hook
  const postAnalysis = usePostAnalysis({ defaultInterval: 60000 })

  const [isRunning, setIsRunning] = useState(false)
  const [enableAttack, setEnableAttack] = useState(false)
  const [enableAftercare, setEnableAftercare] = useState(false)
  const [enableEvoCorps, setEnableEvoCorps] = useState(false)

  const [analysisOpen, setAnalysisOpen] = useState(false)

  const [isStarting, setIsStarting] = useState(false)
  const [isTogglingAttack, setIsTogglingAttack] = useState(false)
  const [isTogglingAftercare, setIsTogglingAftercare] = useState(false)

  const [flowState, setFlowState] = useState<FlowState>(() => createInitialFlowState())
  const [opinionBalanceStartMs, setOpinionBalanceStartMs] = useState<number | null>(null)
  const enableEvoCorpsRef = useRef<boolean>(false)
  const streamRef = useRef<LogStream | null>(null)
  const unsubscribeRef = useRef<null | (() => void)>(null)
  const renderQueueRef = useRef<ReturnType<typeof createTimestampSmoothLineQueue> | null>(null)

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

        // NOTE: Do not auto-toggle the opinion balance panel based on backend status.
        // The panel should start streaming only after the user clicks the toggle (so we can
        // treat that moment as the "start time" for which logs should be shown).

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
    enableEvoCorpsRef.current = enableEvoCorps
  }, [enableEvoCorps])

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
      // Strict "after click": do not tail historical lines.
      tail: 0,
    })

    const renderQueue = createTimestampSmoothLineQueue({
      minDelayMs: LOG_RENDER_MIN_DELAY_MS,
      maxDelayMs: LOG_RENDER_MAX_DELAY_MS,
      timeScale: LOG_RENDER_TIME_SCALE,
      smoothingAlpha: LOG_RENDER_SMOOTHING_ALPHA,
      delayOverrideMs: (line) => {
        const milestone = toUserMilestone(stripLogPrefix(line))
        if (!milestone) return LOG_RENDER_DELAY_DEFAULT_MS
        if (milestone === '分析师：开始分析' || milestone.startsWith('核心观点：') || milestone.startsWith('新回合：')) {
          return LOG_RENDER_DELAY_ANALYST_STAGE0_MS
        }
        if (milestone === '分析师：权重汇总' || milestone === '分析师：极端度' || milestone.startsWith('分析师：情绪')) {
          return LOG_RENDER_DELAY_ANALYST_STAGE_1_TO_3_MS
        }
        if (milestone.startsWith('分析师：')) return LOG_RENDER_DELAY_ANALYST_STAGE_4_TO_5_MS
        return LOG_RENDER_DELAY_DEFAULT_MS
      },
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

  // 使用 postAnalysis Hook 的指标数据，如果没有追踪则使用默认数据
  // 统一字段名：emotion/extremity 用于显示
  // 默认值固定为 0.5
  const defaultMetrics = { emotion: 0.5, extremity: 0.5 }
  const currentMetrics = postAnalysis.isTracking
    ? { emotion: postAnalysis.currentMetrics.sentiment, extremity: postAnalysis.currentMetrics.extremeness }
    : defaultMetrics

  // 使用 postAnalysis Hook 的趋势数据，如果没有追踪则使用默认数据
  const metricsSeries = postAnalysis.isTracking && postAnalysis.metricsSeries.length > 0
    ? postAnalysis.metricsSeries
    : data.metricsSeries

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

              // 重置所有状态到初始默认状态
              // 1. 停止并清除帖子分析追踪
              postAnalysis.stopTracking()

              // 2. 清除选中的帖子
              setSelectedPost(null)

              // 3. 刷新热度榜数据
              await refetchLeaderboard()
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

              // 暂停帖子分析追踪（保留最后的分析结果）
              postAnalysis.pauseTracking()
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

            // UI first: connect SSE from the current EOF so we only show logs after the click.
            setOpinionBalanceStartMs(clickedAtMs)
            setEnableEvoCorps(true)

            // Then start the backend process slightly later (best-effort) to reduce the chance
            // that startup logs are written before the SSE connection is established.
            setTimeout(() => {
              if (!enableEvoCorpsRef.current) return
              void (async () => {
                try {
                  const response = await fetch('/api/dynamic/opinion-balance/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}),
                  })
                  const data = await response.json()
                  if (!data.success && data.error !== 'ProcessAlreadyRunning') {
                    alert(`启动舆论平衡失败：${data.message || '未知错误'}`)
                    console.error('Failed to start opinion balance:', data)
                  }
                } catch (error) {
                  alert(`启动舆论平衡失败：${error instanceof Error ? error.message : '网络错误'}`)
                  console.error('Error starting opinion balance:', error)
                }
              })()
            }, 150)
            return
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
        <div className="space-y-6" key={selectedPost ? 'detail-view' : 'list-view'}>
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
                isTracking={postAnalysis.trackedPostId === (selectedPost.postId || selectedPost.id)}
                onStartTracking={() => postAnalysis.startTracking(selectedPost.postId || selectedPost.id)}
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
          <MetricsLineChartCard data={metricsSeries} />
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
        status={postAnalysis.analysisStatus}
        summary={postAnalysis.summary}
        onOpenConfig={() => setAnalysisOpen(true)}
        onRun={() => postAnalysis.analyzeNow()}
        isRunDisabled={!postAnalysis.isTracking}
        runDisabledReason="请先选择一个帖子并开始分析"
        trackedPostId={postAnalysis.trackedPostId}
        trackedPostStats={
          postAnalysis.isTracking && selectedPost
            ? {
              likeCount: postDetail?.likeCount ?? selectedPost.likeCount,
              commentCount: postDetail?.commentCount ?? selectedPost.commentCount,
              shareCount: postDetail?.shareCount ?? selectedPost.shareCount,
            }
            : null
        }
      />

      <AnalysisConfigDialog
        open={analysisOpen}
        onClose={() => setAnalysisOpen(false)}
        interval={postAnalysis.interval}
        onSave={(newInterval) => postAnalysis.setInterval(newInterval)}
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
  error,
  isTracking,
  onStartTracking
}: {
  post: HeatPost
  postDetail?: any
  onBack: () => void
  isLoading?: boolean
  error?: Error | null
  isTracking?: boolean
  onStartTracking?: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  // 优先使用 postDetail 的完整内容，否则使用 post 的 summary
  const fullContent = postDetail?.content || post.content || post.summary || post.excerpt || ''
  const previewText = useMemo(() => {
    if (fullContent.length <= 180) return fullContent
    return `${fullContent.slice(0, 180)}...`
  }, [fullContent])

  const shouldShowExpandButton = fullContent.length > 180

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
          {isTracking && <StatusBadge label="追踪中" tone="success" />}
          {onStartTracking && (
            <button
              onClick={onStartTracking}
              disabled={isTracking}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center gap-1.5 transition-all ${isTracking
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-500 to-green-500 text-white hover:shadow-lg'
                }`}
              title={isTracking ? '已在追踪中' : '开始分析此帖子'}
            >
              <Activity size={14} />
              {isTracking ? '分析中' : '开始分析'}
            </button>
          )}
          <button onClick={onBack} className="px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center gap-1.5 bg-white/80 border border-white/40 text-slate-700 hover:bg-white transition-all">
            <ArrowLeft size={14} />
            返回榜单
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
        </div>
      )}

      <div className="space-y-2 text-sm text-slate-700">
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {expanded ? fullContent : previewText}
        </p>

        {shouldShowExpandButton && (
          <div className="flex justify-center py-1">
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="px-4 py-2 rounded-lg bg-white/80 border border-white/40 text-slate-600 hover:bg-white transition-all inline-flex items-center gap-2 text-sm font-medium"
            >
              {expanded ? (
                <>
                  <ChevronUp size={16} />
                  收起内容
                </>
              ) : (
                <>
                  <ChevronDown size={16} />
                  展开全文
                </>
              )}
            </button>
          </div>
        )}

        <div className="flex items-center gap-4 text-xs text-slate-500 pt-1 border-t border-slate-200/50">
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
              阶段：{stageModel.currentLabel}（{stageModel.currentStep}/{stageModel.total}）
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


// CommentaryAnalysisPanel 组件接口
interface CommentaryAnalysisPanelProps {
  status: 'Idle' | 'Running' | 'Done' | 'Error'
  summary: string | null
  onOpenConfig: () => void
  onRun: () => void
  isRunDisabled?: boolean
  runDisabledReason?: string
  trackedPostId?: string | null
  trackedPostStats?: {
    likeCount?: number
    commentCount?: number
    shareCount?: number
  } | null
}

function CommentaryAnalysisPanel({
  status,
  summary,
  onOpenConfig,
  onRun,
  isRunDisabled = false,
  runDisabledReason = '请先选择一个帖子并开始分析',
  trackedPostId = null,
  trackedPostStats = null
}: CommentaryAnalysisPanelProps) {
  return (
    <div className="glass-card p-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">评论区总体状态分析</h2>
          <p className="text-sm text-slate-600">大模型周期性分析评论情绪与极化趋势</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {/* 分析配置按钮 */}
          <button className="btn-secondary" onClick={onOpenConfig}>分析配置</button>
          {/* 立即分析按钮 - 支持禁用状态和提示 */}
          <div className="relative group">
            <button
              className={`btn-primary ${isRunDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={isRunDisabled ? undefined : onRun}
              disabled={isRunDisabled}
            >
              立即分析
            </button>
            {/* 禁用时显示提示 */}
            {isRunDisabled && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                {runDisabledReason}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
              </div>
            )}
          </div>
          {/* 分析状态徽章 */}
          <AnalysisStatusBadge status={status} />
        </div>
      </div>

      {/* 追踪帖子信息 */}
      {trackedPostId && (
        <div className="mt-4 bg-blue-50/70 border border-blue-200/50 rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="text-blue-600" size={16} />
            <span className="text-sm text-slate-700">
              正在追踪：<span className="font-semibold text-blue-700">{trackedPostId}</span>
            </span>
          </div>
          {trackedPostStats && (
            <div className="flex items-center gap-4 text-xs text-slate-600 ml-6">
              {trackedPostStats.likeCount !== undefined && (
                <span>👍 点赞：<span className="font-medium">{trackedPostStats.likeCount}</span></span>
              )}
              {trackedPostStats.commentCount !== undefined && (
                <span>💬 评论：<span className="font-medium">{trackedPostStats.commentCount}</span></span>
              )}
              {trackedPostStats.shareCount !== undefined && (
                <span>🔄 分享：<span className="font-medium">{trackedPostStats.shareCount}</span></span>
              )}
            </div>
          )}
        </div>
      )}

      <AnalysisResultView status={status} summary={summary} />
    </div>
  )
}

// 分析状态徽章组件
function AnalysisStatusBadge({ status }: { status: 'Idle' | 'Running' | 'Done' | 'Error' }) {
  const statusConfig: Record<typeof status, { label: string; tone: 'success' | 'warning' | 'danger' | 'info' | 'muted' }> = {
    Idle: { label: '空闲', tone: 'muted' },
    Running: { label: '分析中', tone: 'warning' },
    Done: { label: '已完成', tone: 'success' },
    Error: { label: '错误', tone: 'danger' }
  }

  const config = statusConfig[status]
  return <StatusBadge label={config.label} tone={config.tone} />
}

/**
 * 分析配置对话框 Props 接口
 * Requirements: 7.2, 7.3
 */
interface AnalysisConfigDialogProps {
  /** 对话框是否打开 */
  open: boolean
  /** 关闭对话框回调 */
  onClose: () => void
  /** 当前分析间隔（毫秒） */
  interval: number
  /** 保存新间隔值回调 */
  onSave: (interval: number) => void
}

/**
 * 验证间隔值是否有效
 * Requirements: 7.5, 7.6
 * @param value - 间隔值（毫秒）
 * @returns 验证结果对象，包含是否有效和错误信息
 */
export function validateIntervalInput(value: number): { valid: boolean; error: string | null } {
  // 检查是否为正整数
  if (!Number.isInteger(value) || value <= 0) {
    return { valid: false, error: '请输入正整数' }
  }
  // 检查是否不小于 10 秒（10000ms）
  if (value < 10000) {
    return { valid: false, error: '分析间隔不能小于 10 秒' }
  }
  return { valid: true, error: null }
}

/**
 * 分析配置对话框组件
 * 
 * 提供 Analysis_Interval 输入框，支持输入验证
 * 默认值为 1 分钟（60000ms）
 * 
 * Requirements: 7.2, 7.3, 7.5, 7.6
 */
function AnalysisConfigDialog({ open, onClose, interval, onSave }: AnalysisConfigDialogProps) {
  // 将毫秒转换为秒用于显示
  const [inputValue, setInputValue] = useState<string>(String(interval / 1000))
  const [validationError, setValidationError] = useState<string | null>(null)

  // 当对话框打开或 interval 变化时，重置输入值
  useEffect(() => {
    if (open) {
      setInputValue(String(interval / 1000))
      setValidationError(null)
    }
  }, [open, interval])

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setInputValue(value)

    // 实时验证
    const numValue = parseFloat(value)
    if (isNaN(numValue)) {
      setValidationError('请输入有效数字')
    } else {
      const msValue = Math.round(numValue * 1000)
      const result = validateIntervalInput(msValue)
      setValidationError(result.error)
    }
  }

  // 处理保存
  const handleSave = () => {
    const numValue = parseFloat(inputValue)
    if (isNaN(numValue)) {
      setValidationError('请输入有效数字')
      return
    }

    const msValue = Math.round(numValue * 1000)
    const result = validateIntervalInput(msValue)

    if (!result.valid) {
      setValidationError(result.error)
      return
    }

    // 验证通过，保存并关闭
    onSave(msValue)
    onClose()
  }

  // 处理取消
  const handleCancel = () => {
    // 重置输入值并关闭
    setInputValue(String(interval / 1000))
    setValidationError(null)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/30" onClick={handleCancel} />
      <div className="relative glass-card p-6 w-full max-w-lg mx-4">
        <h3 className="text-xl font-bold text-slate-800 mb-4">分析配置</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              分析间隔（秒）
            </label>
            <input
              type="number"
              min="10"
              step="1"
              value={inputValue}
              onChange={handleInputChange}
              className={`w-full px-4 py-2 rounded-xl border focus:outline-none focus:ring-2 ${validationError
                ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                : 'border-slate-200 focus:ring-primary-500 focus:border-primary-500'
                }`}
              placeholder="输入分析间隔（秒）"
            />
            {/* 验证错误提示 */}
            {validationError && (
              <p className="mt-2 text-sm text-red-600">{validationError}</p>
            )}
            <p className="mt-2 text-xs text-slate-500">
              最小值：10 秒，默认值：60 秒（1 分钟）
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button className="btn-secondary" onClick={handleCancel}>取消</button>
          <button
            className={`btn-primary ${validationError ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={handleSave}
            disabled={!!validationError}
          >
            保存
          </button>
        </div>
      </div>
    </div>
  )
}

function AnalysisResultView({ status, summary }: { status: 'Idle' | 'Running' | 'Done' | 'Error'; summary: string | null }) {
  // 根据状态确定摘要显示内容
  const getSummaryContent = () => {
    if (status === 'Running') {
      return (
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-500">正在分析中...</span>
        </div>
      )
    }
    if (summary && summary.trim() !== '') {
      return <p className="text-sm text-slate-600 leading-relaxed">{summary}</p>
    }
    return <p className="text-sm text-slate-500">暂无分析结果</p>
  }

  return (
    <div className="mt-6">
      <div className="bg-white/70 rounded-2xl p-4 border border-white/40">
        <h4 className="text-sm font-semibold text-slate-700 mb-3">分析摘要</h4>
        {getSummaryContent()}
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
