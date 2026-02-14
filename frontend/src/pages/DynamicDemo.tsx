import { useCallback, useEffect, useMemo, useRef, useState, type ElementType, type ReactNode } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Activity, Play, Square, Shield, Bug, Sparkles, Flame, MessageSquare, ArrowLeft, ThumbsUp, Share2, MessageCircle, BarChart3 } from 'lucide-react'
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
  '2026-01-28 21:18:33,877 - INFO - ⚖️ Activating amplifier Agent cluster...',
  '2026-01-28 21:18:33,892 - INFO -   🚀 Start parallel execution of 12 agent tasks...',
  '2026-01-28 21:18:53,941 - INFO - 📊 amplifier Agent results: 12 succeeded, 0 failed',
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
  // 过滤掉 404 和 500 错误（数据库不存在或未就绪时的正常状态）
  const error = (() => {
    const err = leaderboardError || postDetailError || commentsError
    if (err && err.message) {
      // 404: 数据库文件不存在
      // 500: 数据库正在创建或未就绪
      if (err.message.includes('404') || err.message.includes('500')) {
        return null // 不显示这些错误
      }
    }
    return err
  })()

  const data = useMemo<DynamicDemoData>(() => {
    return {
      heatPosts,
      comments: commentItems,
      metricsSeries: [], // 移除默认数据，初始为空数组
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
  const [isStopping, setIsStopping] = useState(false)
  const [isTogglingAttack, setIsTogglingAttack] = useState(false)
  const [isTogglingAftercare, setIsTogglingAftercare] = useState(false)

  const [flowState, setFlowState] = useState<FlowState>(() => createInitialFlowState())
  const [opinionBalanceStartMs, setOpinionBalanceStartMs] = useState<number | null>(null)
  const enableEvoCorpsRef = useRef<boolean>(false)
  const streamRef = useRef<LogStream | null>(null)
  const unsubscribeRef = useRef<null | (() => void)>(null)
  const renderQueueRef = useRef<ReturnType<typeof createTimestampSmoothLineQueue> | null>(null)
  const hasCheckedInitialStatusRef = useRef(false)

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

        // 只在页面首次加载时，如果系统未运行且有追踪数据，则清除缓存
        if (!hasCheckedInitialStatusRef.current) {
          hasCheckedInitialStatusRef.current = true
          if (!bothRunning && postAnalysis.isTracking) {
            postAnalysis.stopTracking()
          }
        }

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

  // 使用 postAnalysis Hook 的趋势数据，如果没有追踪或数据为空则使用空数组
  const metricsSeries = postAnalysis.isTracking && postAnalysis.metricsSeries.length > 0
    ? postAnalysis.metricsSeries
    : []

  // 获取正在追踪的帖子数据（用于评论区总体状态分析面板）
  const trackedPostData = useMemo(() => {
    if (!postAnalysis.isTracking || !postAnalysis.trackedPostId) return null

    // 从热度榜中查找正在追踪的帖子
    const trackedPost = data.heatPosts.find(p => (p.postId || p.id) === postAnalysis.trackedPostId)

    return trackedPost ? {
      likeCount: trackedPost.likeCount,
      commentCount: trackedPost.commentCount,
      shareCount: trackedPost.shareCount,
    } : null
  }, [postAnalysis.isTracking, postAnalysis.trackedPostId, data.heatPosts])

  return (
    <DynamicDemoPage>
      <DynamicDemoHeader
        isRunning={isRunning}
        isStarting={isStarting}
        isStopping={isStopping}
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
          // 防止重复点击
          if (isStopping) return

          // 显示确认对话框
          if (!confirm('是否确认关闭模拟？')) {
            return
          }

          setIsStopping(true)

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

              // 等待 3 秒确保进程完全停止和文件锁释放
              await new Promise(resolve => setTimeout(resolve, 3000))
            } else {
              // 失败：显示错误消息
              alert(`停止失败：${data.message || '未知错误'}`)
              console.error('Failed to stop dynamic demo:', data)
            }
          } catch (error) {
            // 网络错误或其他异常
            alert(`停止失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error stopping dynamic demo:', error)
          } finally {
            setIsStopping(false)
          }
        }}
        onBack={(path) => navigate(path || '/')}
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
      />

      <div className={getDynamicDemoGridClassName()}>
        <div className="space-y-6" key={selectedPost ? 'detail-view' : 'list-view'}>
          {!selectedPost ? (
            <HeatLeaderboardCard
              posts={data.heatPosts}
              onSelect={setSelectedPost}
              error={error || undefined}
            />
          ) : (
            <div className="space-y-6">
              <PostDetailCard
                post={selectedPost}
                postDetail={postDetail}
                onBack={() => setSelectedPost(null)}
                error={error || undefined}
                isTracking={postAnalysis.trackedPostId === (selectedPost.postId || selectedPost.id)}
                onStartTracking={() => postAnalysis.startTracking(selectedPost.postId || selectedPost.id)}
                onOpenConfig={() => setAnalysisOpen(true)}
              />
              <CommentsCard
                comments={data.comments}
                sort={commentSort}
                onSortChange={setCommentSort}
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
            <div className="glass-card p-6 h-[645px] flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="flex justify-center">
                  <Shield className="text-slate-400" size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-semibold text-slate-800">干预流程</h3>
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
        trackedPostId={postAnalysis.trackedPostId}
        trackedPostStats={trackedPostData}
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
  isStopping,
  onStart,
  onStop,
  onBack,
  enableAttack,
  enableAftercare,
  enableEvoCorps,
  onToggleAttack,
  onToggleAftercare,
  onToggleEvoCorps,
}: {
  isRunning: boolean
  isStarting?: boolean
  isStopping?: boolean
  onStart: () => void
  onStop: () => void
  onBack: (path?: string) => void
  enableAttack: boolean
  enableAftercare: boolean
  enableEvoCorps: boolean
  onToggleAttack: () => void | Promise<void>
  onToggleAftercare: () => void | Promise<void>
  onToggleEvoCorps: () => void | Promise<void>
}) {
  return (
    <div className="glass-card p-6 flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex items-center gap-4">
        <img src="/logo.png" alt="EvoCorps Logo" className="w-[120px] h-auto max-w-full drop-shadow-xl transition-transform duration-300 hover:scale-110 cursor-pointer" />
        <div className="space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-emerald-600 bg-clip-text text-transparent leading-tight">
            欢迎使用 EvoCorps
          </h1>
          <p className="text-slate-600 text-xl leading-relaxed">实时监控舆情变化，动态观察指标变化的舆情现状</p>
        </div>
      </div>

      <div className="flex items-start gap-4 w-full xl:w-auto">
        <div className="flex flex-col gap-3 items-stretch">
          <div className="flex gap-3 justify-between">
            <button
              className="btn-primary inline-flex items-center justify-center gap-2 flex-1 text-lg font-medium"
              onClick={onStart}
              disabled={isRunning || isStarting || isStopping}
            >
              <Play size={18} />
              {isStarting ? '启动中...' : isRunning ? '运行中' : '开启演示'}
            </button>
            <button
              className="btn-secondary inline-flex items-center justify-center gap-2 bg-gradient-to-r from-red-500 to-rose-500 text-white border-transparent hover:shadow-xl flex-1 text-lg font-medium"
              onClick={onStop}
              disabled={isStopping}
            >
              <Square size={18} />
              {isStopping ? '停止中...' : '停止演示'}
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
        <div className="flex flex-col gap-2 justify-between h-full">
          <button
            className="btn-secondary h-[59px] w-[140px] flex flex-row items-center justify-center gap-2 px-4"
            onClick={() => onBack('/dashboard/')}
            title="静态分析"
          >
            <BarChart3 size={18} />
            <span className="text-base font-semibold">静态分析</span>
          </button>
          <button
            className="btn-secondary h-[59px] w-[140px] flex flex-row items-center justify-center gap-2 px-4"
            onClick={() => onBack('/')}
            title="返回首页"
          >
            <ArrowLeft size={18} />
            <span className="text-base font-semibold">返回首页</span>
          </button>
        </div>
      </div>
    </div>
  )
}

function HeatLeaderboardCard({
  posts,
  onSelect,
  error
}: {
  posts: HeatPost[]
  onSelect: (post: HeatPost) => void
  error?: Error | null
}) {
  return (
    <div className={getHeatLeaderboardCardClassName()}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Flame className="text-orange-500" />
          <div>
            <h2 className="text-2xl font-bold text-slate-800">帖子热度榜</h2>
            <p className="text-sm text-slate-600">实时热度排名</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
          <p className="text-sm text-red-600 mt-1">请检查系统是否运行 (Please check if the system is running)</p>
        </div>
      )}

      <div className={getHeatLeaderboardListClassName()}>
        {posts.length === 0 ? (
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
                className="w-full text-left bg-white/70 hover:bg-white transition-all rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-r from-blue-500 to-green-500 text-white text-sm font-bold shadow-md">
                      {index + 1}
                    </span>
                    <span className="text-sm font-bold text-slate-700">{id}</span>
                  </div>
                  <span className="text-sm font-bold text-orange-500">{score.toFixed(2)}</span>
                </div>
                <p className="text-sm text-slate-700 line-clamp-2 font-serif font-normal">{post.excerpt || post.summary}</p>
                <div className="flex items-center justify-between mt-3 gap-2">
                  <div className="flex items-center gap-2 text-xs text-slate-500 min-w-0">
                    <span className="truncate">{author}</span>
                    <span className="shrink-0">{new Date(post.createdAt).toLocaleString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 shrink-0">
                    {post.likeCount !== undefined && (
                      <div className="flex items-center gap-1">
                        <ThumbsUp size={14} className="text-slate-400" />
                        <span className="font-medium">{post.likeCount}</span>
                      </div>
                    )}
                    {post.commentCount !== undefined && (
                      <div className="flex items-center gap-1">
                        <MessageCircle size={14} className="text-slate-400" />
                        <span className="font-medium">{post.commentCount}</span>
                      </div>
                    )}
                    {post.shareCount !== undefined && (
                      <div className="flex items-center gap-1">
                        <Share2 size={14} className="text-slate-400" />
                        <span className="font-medium">{post.shareCount}</span>
                      </div>
                    )}
                  </div>
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
  error,
  isTracking,
  onStartTracking,
  onOpenConfig
}: {
  post: HeatPost
  postDetail?: any
  onBack: () => void
  error?: Error | null
  isTracking?: boolean
  onStartTracking?: () => void
  onOpenConfig?: () => void
}) {
  // 优先使用 postDetail 的完整内容，否则使用 post 的 summary
  const fullContent = postDetail?.content || post.content || post.summary || post.excerpt || ''

  // 获取评论数量
  const commentCount = postDetail?.commentCount ?? post.commentCount ?? 0
  const hasNoComments = commentCount === 0

  return (
    <div className="glass-card p-6 h-[300px] flex flex-col">
      <div className="flex items-start justify-between mb-4 shrink-0">
        <div className="flex items-start gap-3">
          <MessageSquare className="text-blue-500 mt-1" />
          <div>
            <h2 className="text-xl font-bold text-slate-800 leading-tight">{post.postId || post.id}</h2>
            <p className="text-sm text-slate-600 mt-1.5">
              热度：{(post.feedScore || post.heat).toFixed(2)}
            </p>
            <p className="text-sm text-slate-600 mt-0.5">
              作者：{post.authorId || post.author}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex flex-col gap-2">
            <button onClick={onBack} className="px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center justify-center gap-1.5 bg-white/80 border border-slate-200 text-slate-700 hover:bg-white transition-all shadow-md hover:shadow-lg w-full">
              <ArrowLeft size={14} />
              返回榜单
            </button>
            <div className="flex items-center gap-2">
              {onStartTracking && (
                <button
                  onClick={onStartTracking}
                  disabled={isTracking || hasNoComments}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center justify-center gap-1.5 transition-all ${isTracking || hasNoComments
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-green-500 text-white hover:shadow-lg'
                    }`}
                  title={
                    hasNoComments
                      ? '该帖子没有评论'
                      : isTracking
                        ? '已在追踪中'
                        : '开始分析此帖子'
                  }
                >
                  <Activity size={14} />
                  {isTracking ? '分析中' : '开始分析'}
                </button>
              )}
              {onOpenConfig && (
                <button
                  onClick={onOpenConfig}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center justify-center gap-1.5 bg-gradient-to-r from-blue-500 to-green-500 text-white hover:shadow-lg transition-all"
                  title="分析配置"
                >
                  <BarChart3 size={14} />
                  分析配置
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4 shrink-0">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
          <p className="text-sm text-red-600 mt-1">请检查系统是否运行 (Please check if the system is running)</p>
        </div>
      )}

      <div className="space-y-2 text-sm text-slate-700 flex-1 min-h-0 flex flex-col">
        <div className="flex-1 overflow-y-auto pr-2 min-h-0">
          <p className="whitespace-pre-wrap break-words leading-relaxed">
            {fullContent}
          </p>
        </div>

        <div className="flex items-center justify-center gap-20 text-sm pt-3 border-t border-slate-200/50 shrink-0">
          {(post.likeCount !== undefined || postDetail?.likeCount !== undefined) && (
            <div className="flex items-center gap-1.5 text-blue-500">
              <ThumbsUp size={16} />
              <span className="font-medium">{postDetail?.likeCount ?? post.likeCount ?? 0}</span>
            </div>
          )}
          {(post.commentCount !== undefined || postDetail?.commentCount !== undefined) && (
            <div className="flex items-center gap-1.5 text-green-600">
              <MessageCircle size={16} />
              <span className="font-medium">{postDetail?.commentCount ?? post.commentCount ?? 0}</span>
            </div>
          )}
          {(post.shareCount !== undefined || postDetail?.shareCount !== undefined) && (
            <div className="flex items-center gap-1.5 text-purple-500">
              <Share2 size={16} />
              <span className="font-medium">{postDetail?.shareCount ?? post.shareCount ?? 0}</span>
            </div>
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
  error
}: {
  comments: CommentItem[]
  sort: 'likes' | 'time'
  onSortChange: (value: 'likes' | 'time') => void
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
    <div className="glass-card p-6 flex flex-col h-[320px]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <MessageCircle className="text-blue-500" />
          <div>
            <h3 className="text-2xl font-bold text-slate-800">评论区</h3>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <CommentSortTabs value={sort} onChange={onSortChange} />
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-sm text-red-700">加载失败：{error.message}</p>
          <p className="text-sm text-red-600 mt-1">请检查系统是否运行 (Please check if the system is running)</p>
        </div>
      )}

      <div className="space-y-3 overflow-auto pr-2 flex-1 min-h-0">
        {comments.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-slate-500">暂无评论</p>
          </div>
        ) : (
          sorted.map((comment) => (
            <div key={comment.commentId || comment.id} className="bg-white/70 rounded-2xl p-4 border border-white/40 shadow-lg hover:shadow-xl transition-all">
              <p className="text-sm text-slate-700">{comment.content}</p>
              <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                <div className="flex items-center gap-1">
                  <ThumbsUp size={14} className="text-blue-500" />
                  <span className="font-medium">{comment.likeCount ?? comment.likes}</span>
                </div>
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
    <div className="flex items-center gap-2 bg-white/70 rounded-xl p-1 border border-slate-200 shadow-md">
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
    <div className="glass-card p-6 h-[300px] flex flex-col">
      <div className="flex items-center gap-3 mb-0">
        <Activity className="text-blue-500" />
        <div>
          <h2 className="text-2xl font-bold text-slate-800">实时指标概览</h2>
        </div>
      </div>
      <div className="space-y-6 flex-1 flex flex-col justify-center">
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
  // 为数据添加序号（分析次数）
  const displayData = useMemo(() => {
    if (data.length > 0) {
      return data.map((point, index) => ({
        ...point,
        index: index + 1, // 从 1 开始计数
      }))
    }
    // 无数据时返回占位数据，用于显示横轴刻度
    return [
      { index: 1, emotion: null, extremity: null, time: '' },
      { index: 2, emotion: null, extremity: null, time: '' },
      { index: 3, emotion: null, extremity: null, time: '' },
      { index: 4, emotion: null, extremity: null, time: '' },
      { index: 5, emotion: null, extremity: null, time: '' },
    ]
  }, [data])

  return (
    <div className="glass-card p-6 h-[320px] flex flex-col">
      <div className="flex items-center gap-3 mb-4">
        <Sparkles className="text-green-500" />
        <div>
          <h2 className="text-2xl font-bold text-slate-800">历史指标曲线</h2>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={displayData} margin={{ top: 5, right: 20, left: 3, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="index"
              stroke="#94a3b8"
              axisLine={true}
              interval={0}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              stroke="#94a3b8"
              width={40}
            />
            <Tooltip />
            <Legend />
            {/* 始终渲染 Line 组件以显示彩色图例 */}
            <Line
              type="monotone"
              dataKey="emotion"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="情绪度"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="extremity"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="极端度"
              connectNulls={false}
            />
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
    { role: 'Amplifier', tone: 'from-orange-500 to-red-500', label: '扩散者' },
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
          <h2 className="text-2xl font-bold text-slate-800">干预流程</h2>
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
                  <div className="text-base font-semibold text-slate-800 truncate">{label}</div>
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
  trackedPostId = null,
  trackedPostStats = null
}: CommentaryAnalysisPanelProps) {
  return (
    <div className="glass-card p-6 min-h-[230px]">
      <div className="flex items-center gap-3">
        <BarChart3 className="text-purple-500" />
        <div>
          <h2 className="text-2xl font-bold text-slate-800">评论区总体状态分析</h2>
        </div>
      </div>

      {/* 追踪帖子信息 */}
      {trackedPostId && (
        <div className="mt-4 bg-blue-50/70 border border-blue-200/50 rounded-xl p-3">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Activity className="text-blue-600" size={16} />
              <span className="text-sm text-slate-700">
                正在追踪：<span className="font-semibold text-blue-700">{trackedPostId}</span>
              </span>
            </div>
            {trackedPostStats && (
              <div className="flex items-center gap-4 text-xs text-slate-600">
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
        </div>
      )}

      <AnalysisResultView status={status} summary={summary} />
    </div>
  )
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
          <div className="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-green-700">正在分析中...</span>
        </div>
      )
    }
    if (status === 'Error') {
      return <span className="text-base text-red-600">分析失败，请检查系统是否运行或帖子是否有评论</span>
    }
    if (summary && summary.trim() !== '') {
      return <span className="text-base text-green-700">{summary}</span>
    }
    return <span className="text-base text-green-600">暂无分析结果</span>
  }

  return (
    <div className="mt-6">
      <div className="bg-green-50/50 rounded-2xl p-4 border border-green-300">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="inline-block bg-green-100 border border-green-400 rounded-lg px-4 py-2">
            <h4 className="text-base font-bold text-green-800">分析摘要</h4>
          </div>
          {getSummaryContent()}
        </div>
      </div>
    </div>
  )
}

function ToggleCard({ icon: Icon, label, enabled, onToggle }: { icon: ElementType; label: string; enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-3 rounded-2xl px-4 py-4 border-2 transition-all duration-300 ${enabled
        ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white border-transparent shadow-lg'
        : 'bg-gradient-to-br from-blue-50 to-purple-50 text-slate-700 border-blue-200 shadow-md hover:shadow-lg hover:border-blue-300'
        }`}
    >
      <Icon size={18} />
      <span className="text-base font-medium">{label}</span>
    </button>
  )
}
