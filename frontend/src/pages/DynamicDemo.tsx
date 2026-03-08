import { useCallback, useEffect, useMemo, useRef, useState, type ElementType, type ReactNode } from 'react'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Activity, Play, Square, Shield, Bug, Sparkles, Flame, MessageSquare, ArrowLeft, ThumbsUp, Share2, MessageCircle, BarChart3, Eye, RefreshCw, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createPortal } from 'react-dom'
import { createInitialFlowState, routeLogLine, stripLogPrefix, parseLogTimestampMs, type FlowState, type Role } from '../lib/interventionFlow/logRouter'
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
import { startDynamicDemoWithPreset } from '../lib/dynamicDemo/startDemo'
import { useLeaderboard } from '../hooks/useLeaderboard'
import { usePostDetail } from '../hooks/usePostDetail'
import { usePostComments } from '../hooks/usePostComments'
import { usePostAnalysis } from '../hooks/usePostAnalysis'
import { setModerationFlag, setAttackFlag, setAftercareFlag, detectFactions, getPostFactions, getSavedSnapshots, type FactionReport, type PostFactionsSummary } from '../services/api'
import { getAttackModeLabel, resolveAttackToggleAction, type AttackMode } from '../lib/attackModeToggle'
import SaveSnapshotDialog from '../components/SaveSnapshotDialog'
import SnapshotSelectDialog from '../components/SnapshotSelectDialog'
import SnapshotManageDialog from '../components/SnapshotManageDialog'
import { useSimulation } from '../contexts/SimulationContext'

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

interface DefenseDashboard {
  timestamp: string
  niche_occupancy: {
    total_topics: number
    malicious_dominant: number
    malicious_leaning: number
    defense_dominant: number
    defense_leaning: number
    neutral_dominant: number
    contested: number
    malicious_side_percentage: number
    defense_side_percentage: number
  }
  traffic_concentration: {
    gini_coefficient: number
    extreme_account_share: number
    extreme_account_count: number
    total_accounts: number
  }
  algorithmic_bias: {
    overall_gini: number
    bias_assessment: string
  }
  summary: {
    defense_health: {
      score: number
      status: string
    }
  }
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
    leaderboardLoading,
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

  // 使用全局仿真状态 Context
  const simulation = useSimulation()
  const {
    isRunning,
    setIsRunning,
    enableAttack,
    setEnableAttack,
    attackMode,
    setAttackMode,
    enableAftercare,
    setEnableAftercare,
    enableEvoCorps,
    setEnableEvoCorps,
    enableModeration,
    setEnableModeration,
    selectedPost,
    setSelectedPost,
    flowState,
    setFlowState,
    opinionBalanceStartMs,
    setOpinionBalanceStartMs,
    defenseDashboard,
    setDefenseDashboard,
    factionReport,
    setFactionReport,
    postFactions,
    setPostFactions,
    isStarting,
    setIsStarting,
    isStopping,
    setIsStopping,
    isTogglingAttack,
    setIsTogglingAttack,
    isTogglingAftercare,
    setIsTogglingAftercare,
    isTogglingModeration,
    setIsTogglingModeration,
  } = simulation

  const {
    data,
    error,
    leaderboardLoading,
    commentSort,
    setCommentSort,
    postDetail,
    refetchLeaderboard
  } = useDynamicDemoApi()
  const sse = useDynamicDemoSSE()

  // 集成 usePostAnalysis Hook
  const postAnalysis = usePostAnalysis({ defaultInterval: 60000 })

  // 本地 UI 状态（不需要持久化）
  const [attackModeDialogOpen, setAttackModeDialogOpen] = useState(false)
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [showSnapshotSelect, setShowSnapshotSelect] = useState(false)
  const [showSnapshotManage, setShowSnapshotManage] = useState(false)

  const enableEvoCorpsRef = useRef<boolean>(false)
  const streamRef = useRef<LogStream | null>(null)
  const unsubscribeRef = useRef<null | (() => void)>(null)
  const renderQueueRef = useRef<ReturnType<typeof createTimestampSmoothLineQueue> | null>(null)

  // 注：状态轮询已在 SimulationContext 中统一实现，此处不再重复轮询

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
    // Frontend-side time guard: drop any line whose log timestamp is before the
    // program start time (sinceMs). The backend already filters via since_ms, but
    // timestamp-less continuation lines can still slip through; this closes that gap.
    const unsubscribe = stream.subscribe((line) => {
      const ts = parseLogTimestampMs(line)
      if (ts !== null && ts < sinceMs) return
      renderQueue.push(line)
    })
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

  // Defense dashboard state — polls every 10 s while simulation is running
  // 注：defenseDashboard 状态已在 SimulationContext 中管理
  const [defenseFetching, setDefenseFetching] = useState(false)
  useEffect(() => {
    if (!isRunning) return
    const fetchDashboard = () => {
      setDefenseFetching(true)
      fetch('/api/defense/dashboard')
        .then((r) => r.ok ? r.json() : null)
        .then((d) => { if (d?.success) setDefenseDashboard(d.dashboard) })
        .catch(() => {})
        .finally(() => setDefenseFetching(false))
    }
    fetchDashboard()
    const id = setInterval(fetchDashboard, 10_000)
    return () => clearInterval(id)
  }, [isRunning, setDefenseDashboard])

  // ==================== 派系分析数据 ====================
  // 注：factionReport, postFactions 状态已在 SimulationContext 中管理
  const [factionLoading, setFactionLoading] = useState(false)

  const fetchFactionData = useCallback(() => {
    setFactionLoading(true)
    Promise.all([
      detectFactions('simulation'),
      getPostFactions('simulation', 15, 0)
    ])
      .then(([report, factions]) => {
        if (report) setFactionReport(report)
        if (factions) setPostFactions(factions)
      })
      .catch(() => {})
      .finally(() => setFactionLoading(false))
  }, [])

  useEffect(() => {
    // 初始加载一次
    fetchFactionData()
    if (!isRunning) return
    // 运行时每 30 秒轮询
    const id = setInterval(fetchFactionData, 30_000)
    return () => clearInterval(id)
  }, [isRunning, fetchFactionData])

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

  // 启动演示的核心函数
  const handleStartDemo = async (snapshotId?: string, startTick?: number) => {
    // 设置加载状态
    setIsStarting(true)

    try {
      const data = await startDynamicDemoWithPreset({
        enableAttack,
        attackMode,
        enableAftercare,
        enableModeration,
        enableEvoCorps,
        snapshotId,
        startTick,
      })

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
  }

  // 点击开始按钮时，检查是否有已保存的快照
  const handleStartClick = async () => {
    if (isRunning || isStarting) return
    try {
      const snapshots = await getSavedSnapshots()
      if (snapshots.length > 0) {
        setShowSnapshotSelect(true)
      } else {
        await handleStartDemo()
      }
    } catch {
      await handleStartDemo()
    }
  }

  return (
    <DynamicDemoPage>
      <DynamicDemoHeader
        isRunning={isRunning}
        isStarting={isStarting}
        isStopping={isStopping}
        onStart={handleStartClick}
        onStop={() => {
          // 防止重复点击
          if (isStopping) return
          // 显示保存快照对话框
          setShowSaveDialog(true)
        }}
        onBack={(path) => navigate(path || '/')}
        enableAttack={enableAttack}
        attackMode={attackMode}
        attackModeDialogOpen={attackModeDialogOpen}
        enableAftercare={enableAftercare}
        enableEvoCorps={enableEvoCorps}
        enableModeration={enableModeration}
        onSelectAttackMode={(mode) => {
          setAttackMode(mode)
          setAttackModeDialogOpen(false)
          void (async () => {
            const action = resolveAttackToggleAction({
              enabled: enableAttack,
              selectedMode: mode,
            })
            if (action.type !== 'enable') return

            // 演示未运行时：仅预置本地状态，启动后同步到后端
            if (!isRunning) {
              setEnableAttack(true)
              return
            }

            if (isTogglingAttack) return
            setEnableAttack(true)
            setIsTogglingAttack(true)
            try {
              await setAttackMode(mode)
              const data = await setAttackFlag(true)
              if (data.attack_enabled !== undefined) {
                setEnableAttack(Boolean(data.attack_enabled))
                alert(`✅ Malicious attack enabled (${getAttackModeLabel(mode)})`)
              } else {
                setEnableAttack(false)
                throw new Error('API 返回异常')
              }
            } catch (error) {
              setEnableAttack(false)
              alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            } finally {
              setIsTogglingAttack(false)
            }
          })()
        }}
        onCloseAttackModeDialog={() => setAttackModeDialogOpen(false)}
        onToggleAttack={async () => {
          if (isTogglingAttack) return

          const action = resolveAttackToggleAction({
            enabled: enableAttack,
            selectedMode: attackMode,
          })

          if (action.type === 'open_mode_dialog') {
            setAttackModeDialogOpen(true)
            return
          }

          if (action.type === 'enable') {
            setAttackModeDialogOpen(true)
            return
          }

          // 当前为启用状态，二次点击即关闭当前模式
          if (action.type === 'disable') {
            if (!confirm('是否确认关闭恶意攻击模式？')) {
              return
            }
            if (!isRunning) {
              setEnableAttack(false)
              setAttackMode(null)
              return
            }
          }

          // 乐观更新：先改变状态，让 UI 立即响应
          const newEnabled = false
          setEnableAttack(newEnabled)

          setIsTogglingAttack(true)

          try {
            const data = await setAttackFlag(newEnabled)

            if (data && data.attack_enabled !== undefined) {
              // 以服务器返回值为准
              setEnableAttack(data.attack_enabled)
              if (!data.attack_enabled) {
                setAttackMode(null)
              }

              // 显示成功提示
              if (data.attack_enabled) {
                alert('✅ Malicious attack enabled')
              } else {
                const modeText = attackMode ? ` (${getAttackModeLabel(attackMode)})` : ''
                alert(`✅ Malicious attack disabled${modeText}`)
              }
            } else {
              // API 返回异常，回滚
              setEnableAttack(!newEnabled)
              throw new Error('API 返回异常')
            }
          } catch (error) {
            // 出错时回滚
            setEnableAttack(!newEnabled)
            alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error toggling attack:', error)
          } finally {
            setIsTogglingAttack(false)
          }
        }}
        onToggleAftercare={async () => {
          if (isTogglingAftercare) return

          // 演示未运行时：仅预置本地状态，启动后自动同步到后端
          if (!isRunning) {
            setEnableAftercare(!enableAftercare)
            return
          }

          // 如果当前是启用状态，显示确认弹窗
          if (enableAftercare) {
            if (!confirm('是否确认关闭事后干预？')) {
              return
            }
          }

          // 乐观更新：先改变状态，让 UI 立即响应
          const newEnabled = !enableAftercare
          setEnableAftercare(newEnabled)

          setIsTogglingAftercare(true)

          try {
            const data = await setAftercareFlag(newEnabled)

            if (data.aftercare_enabled !== undefined) {
              // 以服务器返回值为准
              setEnableAftercare(data.aftercare_enabled)

              // 显示成功提示
              if (data.aftercare_enabled) {
                alert('✅ 事后干预已开启')
              } else {
                alert('✅ 事后干预已关闭')
              }
            } else {
              // API 返回异常，回滚
              setEnableAftercare(!newEnabled)
              throw new Error('API 返回异常')
            }
          } catch (error) {
            // 出错时回滚
            setEnableAftercare(!newEnabled)
            alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error toggling aftercare:', error)
          } finally {
            setIsTogglingAftercare(false)
          }
        }}
        onToggleModeration={async () => {
          if (isTogglingModeration) return

          // 演示未运行时：预置本地状态，同时持久化到配置文件
          if (!isRunning) {
            const next = !enableModeration
            setEnableModeration(next)
            fetch('/api/config/moderation', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content_moderation: next }),
            }).catch(() => {})
            return
          }

          // 乐观更新：先改变状态，让 UI 立即响应
          const newEnabled = !enableModeration
          setEnableModeration(newEnabled)

          setIsTogglingModeration(true)
          try {
            const result = await setModerationFlag(newEnabled)
            if (result && 'moderation_enabled' in result) {
              // 以服务器返回值为准（通常和乐观值一致）
              setEnableModeration(result.moderation_enabled)

              // 显示成功提示
              if (result.moderation_enabled) {
                alert('✅ 内容审核已开启')
              } else {
                alert('✅ 内容审核已关闭')
              }
            } else {
              // API 返回异常，回滚
              setEnableModeration(!newEnabled)
              throw new Error('API 返回异常')
            }
          } catch (error) {
            // 出错时回滚
            setEnableModeration(!newEnabled)
            alert(`❌ 操作失败：${error instanceof Error ? error.message : '网络错误'}`)
            console.error('Error toggling moderation:', error)
          } finally {
            setIsTogglingModeration(false)
          }
        }}
        onToggleEvoCorps={async () => {
          // 演示未运行时：仅预置本地状态，启动后自动同步到后端
          if (!isRunning) {
            setEnableEvoCorps(!enableEvoCorps)
            return
          }

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
              onRefresh={refetchLeaderboard}
              isRefreshing={leaderboardLoading}
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
                onStopTracking={() => postAnalysis.pauseTracking()}
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
          <DefenseDashboardCard dashboard={defenseDashboard} isLive={isRunning} isFetching={defenseFetching} />
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

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <CommentaryAnalysisPanel
          status={postAnalysis.analysisStatus}
          summary={postAnalysis.summary}
          trackedPostId={postAnalysis.trackedPostId}
          trackedPostStats={trackedPostData}
        />
        <FactionOverviewCard report={factionReport} postFactions={postFactions} isLoading={factionLoading} onRefresh={fetchFactionData} />
      </div>

      <AnalysisConfigDialog
        open={analysisOpen}
        onClose={() => setAnalysisOpen(false)}
        interval={postAnalysis.interval}
        onSave={(newInterval) => postAnalysis.setInterval(newInterval)}
      />

      <SaveSnapshotDialog
        open={showSaveDialog}
        onSave={async (name, description) => {
          setShowSaveDialog(false)
          setIsStopping(true)
          try {
            // 保存快照
            const saveResponse = await fetch('/api/snapshots/save', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name, description }),
            })
            const saveData = await saveResponse.json()

            if (!saveData.success) {
              alert(`保存快照失败：${saveData.message || '未知错误'}`)
              return
            }

            // 停止演示
            const stopResponse = await fetch('/api/dynamic/stop', { method: 'POST' })
            const stopData = await stopResponse.json()

            if (stopData.success) {
              setIsRunning(false)
              sse.disconnect()
              postAnalysis.pauseTracking()
              await new Promise(resolve => setTimeout(resolve, 1000))
            } else {
              alert(`停止失败：${stopData.message || '未知错误'}`)
            }
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : '网络错误'
            if (errorMsg.includes('Network Error') || errorMsg.includes('ECONNREFUSED')) {
              setIsRunning(false)
              sse.disconnect()
              postAnalysis.pauseTracking()
              alert('后端服务未响应，已重置前端状态')
            } else {
              alert(`操作失败：${errorMsg}`)
            }
          } finally {
            setIsStopping(false)
          }
        }}
        onSkip={async () => {
          setShowSaveDialog(false)
          setIsStopping(true)
          try {
            const response = await fetch('/api/dynamic/stop', { method: 'POST' })
            const data = await response.json()

            if (data.success) {
              setIsRunning(false)
              sse.disconnect()
              postAnalysis.pauseTracking()
              await new Promise(resolve => setTimeout(resolve, 1000))
            } else {
              alert(`停止失败：${data.message || '未知错误'}`)
            }
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : '网络错误'
            if (errorMsg.includes('Network Error') || errorMsg.includes('ECONNREFUSED')) {
              setIsRunning(false)
              sse.disconnect()
              postAnalysis.pauseTracking()
              alert('后端服务未响应，已重置前端状态')
            } else {
              alert(`停止失败：${errorMsg}`)
            }
          } finally {
            setIsStopping(false)
          }
        }}
        onCancel={() => setShowSaveDialog(false)}
      />

      <SnapshotSelectDialog
        open={showSnapshotSelect}
        onSelect={async (snapshotId, startTick) => {
          setShowSnapshotSelect(false)
          await handleStartDemo(snapshotId, startTick)
        }}
        onStartFresh={async () => {
          setShowSnapshotSelect(false)
          await handleStartDemo()
        }}
        onCancel={() => setShowSnapshotSelect(false)}
        onManageSnapshots={() => setShowSnapshotManage(true)}
      />

      <SnapshotManageDialog
        open={showSnapshotManage}
        onClose={() => setShowSnapshotManage(false)}
        onDeleted={() => {
          // 可选：刷新快照列表或显示提示
        }}
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
  attackMode: _attackMode,
  attackModeDialogOpen,
  enableAftercare,
  enableEvoCorps,
  enableModeration,
  onToggleAttack,
  onSelectAttackMode,
  onCloseAttackModeDialog,
  onToggleAftercare,
  onToggleEvoCorps,
  onToggleModeration,
}: {
  isRunning: boolean
  isStarting?: boolean
  isStopping?: boolean
  onStart: () => void
  onStop: () => void
  onBack: (path?: string) => void
  enableAttack: boolean
  attackMode: AttackMode | null
  attackModeDialogOpen: boolean
  enableAftercare: boolean
  enableEvoCorps: boolean
  enableModeration: boolean
  onToggleAttack: () => void | Promise<void>
  onSelectAttackMode: (mode: AttackMode) => void
  onCloseAttackModeDialog: () => void
  onToggleAftercare: () => void | Promise<void>
  onToggleEvoCorps: () => void | Promise<void>
  onToggleModeration: () => void | Promise<void>
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
              {isStopping ? '结束中...' : '结束演示'}
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
              icon={Eye}
              label="开启内容审核"
              enabled={enableModeration}
              onToggle={onToggleModeration}
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

      {attackModeDialogOpen && (
        <AttackModeDialog
          onSelect={onSelectAttackMode}
          onClose={onCloseAttackModeDialog}
        />
      )}
    </div>
  )
}

function AttackModeDialog({
  onSelect,
  onClose,
}: {
  onSelect: (mode: AttackMode) => void
  onClose: () => void
}) {
  if (typeof document === 'undefined') return null

  return createPortal(
    <div className="fixed inset-0 z-[99999] bg-slate-700/22 backdrop-blur-[2px] flex items-start justify-center pt-10 px-6 pb-6">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200/85 bg-gradient-to-br from-slate-100/97 via-slate-50/96 to-blue-50/94 shadow-[0_28px_90px_rgba(15,23,42,0.18)] p-10">
        <h3 className="text-3xl font-bold text-slate-800">选择恶意攻击模式</h3>
        <p className="text-base text-slate-600 mt-2">请选择本次开启时使用的攻击协同模式。</p>

        <div className="mt-6 grid grid-cols-1 gap-4">
          <button
            type="button"
            onClick={() => onSelect('swarm')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">蜂群式</div>
            <div className="text-sm text-slate-600 mt-1">集中攻击同一目标，放大互动信号。</div>
          </button>
          <button
            type="button"
            onClick={() => onSelect('dispersed')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">游离式</div>
            <div className="text-sm text-slate-600 mt-1">分散到多条帖子，降低集中痕迹。</div>
          </button>
          <button
            type="button"
            onClick={() => onSelect('chain')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">链式传播</div>
            <div className="text-sm text-slate-600 mt-1">主导账号→扩散账号→控评账号的三层协同攻击。</div>
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

function HeatLeaderboardCard({
  posts,
  onSelect,
  onRefresh,
  isRefreshing,
  error
}: {
  posts: HeatPost[]
  onSelect: (post: HeatPost) => void
  onRefresh?: () => void
  isRefreshing?: boolean
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
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-xl hover:bg-slate-100 transition-colors disabled:opacity-50"
            title="刷新热度榜"
          >
            <RefreshCw size={16} className={`text-slate-500 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
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
  onStopTracking,
  onOpenConfig
}: {
  post: HeatPost
  postDetail?: any
  onBack: () => void
  error?: Error | null
  isTracking?: boolean
  onStartTracking?: () => void
  onStopTracking?: () => void
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
              {isTracking && onStopTracking ? (
                <button
                  onClick={onStopTracking}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center justify-center gap-1.5 transition-all bg-gradient-to-r from-red-500 to-rose-500 text-white hover:shadow-lg"
                  title="关闭分析，停止追踪"
                >
                  <Eye size={14} />
                  关闭分析
                </button>
              ) : onStartTracking ? (
                <button
                  onClick={onStartTracking}
                  disabled={hasNoComments}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium inline-flex items-center justify-center gap-1.5 transition-all ${hasNoComments
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-green-500 text-white hover:shadow-lg'
                    }`}
                  title={hasNoComments ? '该帖子没有评论' : '开始分析此帖子'}
                >
                  <Activity size={14} />
                  开始分析
                </button>
              ) : null}
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

function DefenseDashboardCard({ dashboard, isLive, isFetching }: { dashboard: DefenseDashboard | null; isLive: boolean; isFetching: boolean }) {
  const no = dashboard?.niche_occupancy
  const malDom   = no?.malicious_dominant  ?? 0
  const malLean  = no?.malicious_leaning   ?? 0
  const defDom   = no?.defense_dominant    ?? 0
  const defLean  = no?.defense_leaning     ?? 0
  const neutDom  = no?.neutral_dominant    ?? 0
  const total    = no?.total_topics        ?? 0
  // stacked bar widths
  const malW     = total > 0 ? ((malDom + malLean) / total) * 100 : 0
  const defW     = total > 0 ? ((defDom + defLean) / total) * 100 : 0
  const neutW    = total > 0 ? (neutDom / total) * 100 : 0
  const neutralW = Math.max(0, 100 - malW - defW - neutW)

  const tc = dashboard?.traffic_concentration
  const extremeCount = tc?.extreme_account_count ?? 0
  const gini = dashboard?.algorithmic_bias.overall_gini ?? 0
  const giniBarColor = gini < 0.3 ? 'bg-green-500' : gini < 0.6 ? 'bg-amber-500' : 'bg-red-500'
  const giniLabel = gini < 0.3 ? '流量分布正常' : gini < 0.6 ? '流量轻度集中' : '⚠ 流量过度集中'
  const giniLabelColor = gini < 0.3 ? 'text-green-600' : gini < 0.6 ? 'text-amber-600' : 'text-red-600'

  return (
    <div className="glass-card p-6 h-[300px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-500" />
          <h2 className="text-2xl font-bold text-slate-800">防御监控中心</h2>
        </div>
        {isLive && (
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-600 font-medium">
            <span className={['w-2 h-2 rounded-full bg-emerald-500', isFetching ? 'animate-ping' : 'animate-pulse'].join(' ')} />
            实时更新
          </div>
        )}
      </div>
      <div className="space-y-5 flex-1 flex flex-col justify-center">

        {/* Niche Occupancy */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">生态位占有率</span>
            <span className="text-xs text-slate-400">共 {total} 个热门话题</span>
          </div>
          {/* count badges — three sides */}
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-1 text-xs font-semibold text-red-600">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
              水军主导 {malDom} 个
              {malLean > 0 && <span className="font-normal text-red-400 ml-1">+倾向 {malLean} 个</span>}
            </span>
            {neutDom > 0 && (
              <span className="flex items-center gap-1 text-xs font-semibold text-slate-500">
                <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
                中性 {neutDom} 个
              </span>
            )}
            <span className="flex items-center gap-1 text-xs font-semibold text-green-600">
              EvoCorps 主导 {defDom} 个
              {defLean > 0 && <span className="font-normal text-green-400 ml-1">+倾向 {defLean} 个</span>}
              <span className="w-2 h-2 rounded-full bg-green-500 inline-block ml-1" />
            </span>
          </div>
          <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-100">
            <div className="bg-red-500 transition-all duration-500" style={{ width: `${malW}%` }} />
            <div className="bg-slate-300 transition-all duration-500" style={{ width: `${neutW}%` }} />
            <div className="bg-slate-200 transition-all duration-500" style={{ width: `${neutralW}%` }} />
            <div className="bg-green-500 transition-all duration-500" style={{ width: `${defW}%` }} />
          </div>
        </div>

        {/* Algorithmic Bias Gini */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">算法倾斜基尼系数</span>
            <span className={`text-xs font-semibold ${giniLabelColor}`}>
              {giniLabel}
            </span>
          </div>
          {/* descriptive line */}
          <div className="text-xs text-slate-600 mb-2">
            {extremeCount > 0
              ? <>极端账号 <span className="font-semibold">{extremeCount}</span> 个</>
              : <span className="text-slate-400">暂无极端账号数据</span>
            }
          </div>
          <div className="h-3 w-full rounded-full overflow-hidden bg-slate-100">
            <div className={`${giniBarColor} h-full transition-all duration-500`} style={{ width: `${gini * 100}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 mt-1">
            <span>基尼系数 {gini.toFixed(3)}</span>
            <span>越高越集中 →</span>
          </div>
        </div>

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

function FactionOverviewCard({
  report,
  postFactions,
  isLoading,
  onRefresh
}: {
  report: FactionReport | null
  postFactions: PostFactionsSummary | null
  isLoading: boolean
  onRefresh: () => void
}) {
  const communities = report?.communities ?? []
  const numCommunities = report?.num_communities ?? 0
  const numEchoChambers = report?.num_echo_chambers ?? 0
  const totalUsers = report?.total_users ?? 0

  const avgSupport = postFactions?.avg_support_ratio ?? 0
  const avgNeutral = postFactions?.avg_neutral_ratio ?? 0
  const avgOppose = postFactions?.avg_oppose_ratio ?? 0

  const hottest = postFactions?.hottest_post
  const divisive = postFactions?.most_divisive_post

  const hasData = numCommunities > 0 || (postFactions?.total_posts_analyzed ?? 0) > 0

  return (
    <div className="glass-card p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Users className="text-purple-500" />
          <h2 className="text-2xl font-bold text-slate-800">派系分析概览</h2>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-4 h-4 text-slate-400 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {!hasData ? (
        <div className="flex-1 flex items-center justify-center py-8">
          <p className="text-sm text-slate-400">{isLoading ? '正在分析派系数据...' : '暂无派系数据，请先启动仿真'}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 摘要指标 */}
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-500 inline-block" />
              <span className="text-slate-600">社区 <span className="font-semibold text-slate-800">{numCommunities}</span> 个</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
              <span className="text-slate-600">回声室 <span className="font-semibold text-slate-800">{numEchoChambers}</span> 个</span>
            </span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-500">覆盖 {totalUsers} 用户</span>
          </div>

          {/* 全局立场分布 - 堆叠条形图 */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-medium text-slate-700">全局立场分布</span>
              <span className="text-xs text-slate-400">基于 {postFactions?.total_posts_analyzed ?? 0} 条帖子</span>
            </div>
            <div className="flex items-center justify-between mb-1.5 text-xs">
              <span className="flex items-center gap-1 font-semibold text-green-600">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                支持 {(avgSupport * 100).toFixed(0)}%
              </span>
              <span className="flex items-center gap-1 font-semibold text-slate-500">
                <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
                中立 {(avgNeutral * 100).toFixed(0)}%
              </span>
              <span className="flex items-center gap-1 font-semibold text-red-600">
                反对 {(avgOppose * 100).toFixed(0)}%
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
              </span>
            </div>
            <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-100">
              <div className="bg-green-500 transition-all duration-500" style={{ width: `${avgSupport * 100}%` }} />
              <div className="bg-slate-300 transition-all duration-500" style={{ width: `${avgNeutral * 100}%` }} />
              <div className="bg-red-500 transition-all duration-500" style={{ width: `${avgOppose * 100}%` }} />
            </div>
          </div>

          {/* 各社区概览 */}
          {communities.length > 0 && (
            <div>
              <span className="text-sm font-medium text-slate-700">各社区概览</span>
              <div className="mt-1.5 space-y-1.5 max-h-[140px] overflow-y-auto">
                {communities.slice(0, 6).map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-xs bg-slate-50 rounded-lg px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700">{c.name}</span>
                      <span className="text-slate-400">{c.size ?? c.members?.length ?? 0} 人</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">紧密度 {(c.cohesion ?? 0).toFixed(2)}</span>
                      {c.is_echo_chamber && (
                        <span className="text-[10px] font-semibold text-red-500 bg-red-50 px-1.5 py-0.5 rounded">回声室</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 最火帖 & 最分歧帖 */}
          <div className="flex gap-3 text-xs">
            {hottest && (
              <div className="flex-1 bg-amber-50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1 text-amber-600 font-semibold mb-1">
                  <Flame className="w-3 h-3" /> 最火帖
                </div>
                <div className="text-slate-600 truncate">{hottest.post_id}</div>
                <div className="text-slate-500 mt-0.5">
                  支持{(hottest.support_ratio * 100).toFixed(0)}%
                  {' '}中立{(hottest.neutral_ratio * 100).toFixed(0)}%
                  {' '}反对{(hottest.oppose_ratio * 100).toFixed(0)}%
                </div>
              </div>
            )}
            {divisive && (
              <div className="flex-1 bg-rose-50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1 text-rose-600 font-semibold mb-1">
                  <Activity className="w-3 h-3" /> 最分歧帖
                </div>
                <div className="text-slate-600 truncate">{divisive.post_id}</div>
                <div className="text-slate-500 mt-0.5">
                  支持{(divisive.support_ratio * 100).toFixed(0)}%
                  {' '}vs 反对{(divisive.oppose_ratio * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Lines stored in `during`/`after` are processed by compressDisplayLine() in logRouter.ts,
// which converts key events into Chinese milestone strings via toUserMilestone():
//   "Activating Amplifier Agent cluster"  → "扩散者：启动集群"
//   "Amplifier plan: total=N"             → "扩散者：集群规模（N）"
//   "N amplifier responses generated"     → "扩散者：生成回应（N）"
//   "💖 N amplifier Agents liked..."      → "扩散者：点赞扩散（N）"
// Other lines stay in English (possibly normalized).
// Patterns must match BOTH the Chinese milestone form AND the English fallback form.

// 后端角色类型到前端兵种的映射
// 后端角色：balanced_moderates, technical_experts, community_voices, fact_checkers
// 前端兵种：empath (同理心安抚者), factchecker (逻辑辟谣者), amplifier (意见领袖护盘者), nichefiller (生态位填补者)
const BACKEND_ROLE_TO_TROOP: Record<string, string> = {
  'balanced_moderates': 'empath',      // 平衡温和派 -> 同理心安抚者
  'technical_experts': 'factchecker',  // 技术专家 -> 逻辑辟谣者
  'community_voices': 'amplifier',     // 社区声音 -> 意见领袖护盘者
  'fact_checkers': 'factchecker',      // 事实核查者 -> 逻辑辟谣者
  'empath': 'empath',                  // 直接映射
  'fact_checker': 'factchecker',       // 后端下划线格式直接映射
  'factchecker': 'factchecker',        // 直接映射
  'amplifier': 'amplifier',            // 直接映射
  'niche_filler': 'nichefiller',       // 后端下划线格式直接映射
  'nichefiller': 'nichefiller',        // 直接映射
  'general': 'empath',                 // 通用角色默认为同理心安抚者
}

// 从日志中提取【角色类型】标注
// 新格式：💬 🤖 amplifier-1【balanced_moderates】(persona_id) (model) commented: ...
function extractRoleFromLogLine(line: string): string | null {
  // 匹配【角色类型】格式
  const roleMatch = line.match(/【([^】]+)】/)
  if (roleMatch) {
    return roleMatch[1].toLowerCase()
  }
  return null
}

// 生态位填补者 (Niche Fillers): 监测"封号真空期"，迅速抛出温和的替代性议题
// 匹配：集群启动、规模规划、代理创建
const _TROOP_NICHEFILLER =
  /扩散者：启动集群|扩散者：集群规模|Successfully created.*Amplifier|Activating.*Amplifier.*cluster/i

// 同理心安抚者 (Empaths): 降低社区愤怒值，提供情绪价值
// 匹配：并行执行、生成回应、代理评论（温和、安抚类内容）
const _TROOP_EMPATH =
  /扩散者：并行执行|扩散者：生成回应|Amplifier.*commented|amplifier responses generated/i

// 逻辑辟谣者 (Fact-checkers): 提供核心证据链，主要影响高认知用户
// 匹配：执行结果（包含成功/失败统计）、事实核查相关
const _TROOP_FACTCHECKER =
  /扩散者：执行结果|扩散者：事实核查|扩散者：证据链|Agent results|Fact.?check|evidence/i

// 意见领袖护盘者 (Amplifiers): 利用高信誉度强行阻断谣言传播链
// 匹配：点赞扩散（利用高 follower 数量提升优质内容权重）
const _TROOP_LEADER =
  /扩散者：点赞扩散|liked leader comments|Workflow completed.*effectiveness/i

const TROOP_STAGES: Record<string, readonly [string, string, string]> = {
  empath:      ['情绪感知', '共情策略', '发布安抚'],
  factchecker: ['声明识别', '组织论据', '发布辟谣'],
  amplifier:   ['影响力评估', '确立立场', '发布评论'],
  nichefiller: ['空位检测', '设计议题', '发布引导'],
}

function getTroopStageProgress(filteredLines: string[]): number {
  if (filteredLines.some((l) => /^💬\s*🤖\s*amplifier-\d+\b/i.test(l))) return 2
  if (filteredLines.some((l) => /^🎯\s*amplifier-\d+\b/i.test(l))) return 1
  if (filteredLines.some((l) => /^🔍\s*amplifier-\d+\b/i.test(l))) return 0
  return -1
}

function getAmplifierTroopLabel(line: string): { icon: string; name: string; color: string } | null {
  // 优先从日志中提取【角色类型】标注
  const backendRole = extractRoleFromLogLine(line)
  if (backendRole) {
    const troopKey = BACKEND_ROLE_TO_TROOP[backendRole]
    if (troopKey) {
      switch (troopKey) {
        case 'nichefiller':
          return { icon: '🌱', name: '生态位填补者', color: 'text-emerald-600' }
        case 'empath':
          return { icon: '💗', name: '同理心安抚者', color: 'text-pink-600' }
        case 'factchecker':
          return { icon: '🔍', name: '逻辑辟谣者', color: 'text-blue-600' }
        case 'amplifier':
          return { icon: '👑', name: '意见领袖护盘者', color: 'text-amber-600' }
      }
    }
  }
  
  // 回退到正则表达式匹配
  if (_TROOP_NICHEFILLER.test(line))
    return { icon: '🌱', name: '生态位填补者', color: 'text-emerald-600' }
  if (_TROOP_EMPATH.test(line))
    return { icon: '💗', name: '同理心安抚者', color: 'text-pink-600' }
  if (_TROOP_FACTCHECKER.test(line))
    return { icon: '🔍', name: '逻辑辟谣者', color: 'text-blue-600' }
  if (_TROOP_LEADER.test(line))
    return { icon: '👑', name: '意见领袖护盘者', color: 'text-amber-600' }
  return null
}

function getAmplifierTroopKey(line: string): string | null {
  // 优先从日志中提取【角色类型】标注
  const backendRole = extractRoleFromLogLine(line)
  if (backendRole) {
    const troopKey = BACKEND_ROLE_TO_TROOP[backendRole]
    if (troopKey) {
      return troopKey
    }
  }
  
  // 回退到正则表达式匹配
  if (_TROOP_NICHEFILLER.test(line)) return 'nichefiller'
  if (_TROOP_EMPATH.test(line)) return 'empath'
  if (_TROOP_FACTCHECKER.test(line)) return 'factchecker'
  if (_TROOP_LEADER.test(line)) return 'amplifier'
  return null
}

function AmplifierTroopGrid({
  summary,
  status,
  selectedTroopKey,
  onSelectTroopKey,
}: {
  summary: string[]
  status: string
  selectedTroopKey: string | null
  onSelectTroopKey: (key: string | null) => void
}) {
  const clusterCount = useMemo(() => {
    for (const line of summary) {
      const m = line.match(/集群规模[（(](\d+)[）)]/)
      if (m) return parseInt(m[1], 10)
    }
    for (const line of summary) {
      const m = line.match(/并行执行[（(](\d+)[）)]/)
      if (m) return parseInt(m[1], 10)
    }
    for (const line of summary) {
      const m = line.match(/生成回应[（(](\d+)[）)]/)
      if (m) return parseInt(m[1], 10)
    }
    return null
  }, [summary])

  const isActive = status === 'running' || status === 'done'
  const base = clusterCount ?? 12

  const troops = [
    {
      key: 'empath',
      icon: '💗',
      name: '同理心安抚者',
      subtitle: 'Empaths',
      desc: '降低社区愤怒值，提供情绪价值',
      count: Math.ceil(base * 0.25),
      bg: 'bg-pink-50/80',
      border: 'border-pink-200/60',
      text: 'text-pink-700',
      dot: 'bg-pink-400',
      ring: 'ring-pink-400',
      isNew: false,
    },
    {
      key: 'factchecker',
      icon: '🔍',
      name: '逻辑辟谣者',
      subtitle: 'Fact-checkers',
      desc: '提供核心证据链，主要影响高认知用户',
      count: Math.ceil(base * 0.25),
      bg: 'bg-blue-50/80',
      border: 'border-blue-200/60',
      text: 'text-blue-700',
      dot: 'bg-blue-400',
      ring: 'ring-blue-400',
      isNew: false,
    },
    {
      key: 'amplifier',
      icon: '👑',
      name: '意见领袖护盘者',
      subtitle: 'Amplifiers',
      desc: '利用高信誉度（Follower 数量）强行阻断谣言传播链口',
      count: Math.ceil(base * 0.25),
      bg: 'bg-amber-50/80',
      border: 'border-amber-200/60',
      text: 'text-amber-700',
      dot: 'bg-amber-400',
      ring: 'ring-amber-400',
      isNew: false,
    },
    {
      key: 'nichefiller',
      icon: '🌱',
      name: '生态位填补者',
      subtitle: 'Niche Fillers',
      desc: '监测"封号真空期"，迅速抛出温和的替代性议题，收编流失的流量',
      count: Math.ceil(base * 0.25),
      bg: 'bg-emerald-50/80',
      border: 'border-emerald-200/60',
      text: 'text-emerald-700',
      dot: 'bg-emerald-400',
      ring: 'ring-emerald-400',
      isNew: true,
    },
  ]

  const anySelected = selectedTroopKey !== null

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">兵种分工</div>
        {anySelected && (
          <button
            type="button"
            onClick={() => onSelectTroopKey(null)}
            className="text-[9px] text-slate-400 hover:text-slate-600 underline transition-colors"
          >
            查看全部
          </button>
        )}
      </div>
      <div className="grid grid-cols-4 gap-2">
        {troops.map((t) => {
          const isSelected = selectedTroopKey === t.key
          const isDimmed = anySelected && !isSelected
          return (
            <button
              type="button"
              key={t.key}
              onClick={() => onSelectTroopKey(isSelected ? null : t.key)}
              className={[
                'relative rounded-xl p-2.5 border text-left transition-all cursor-pointer',
                t.bg,
                t.border,
                t.isNew && !isSelected ? 'ring-1 ring-emerald-400/50' : '',
                isSelected ? 'ring-2 ring-offset-1 ' + t.ring : '',
                isDimmed ? 'opacity-40' : 'hover:brightness-95',
              ].join(' ')}
            >
              <div className="flex flex-col items-center gap-1 text-center">
                <span className="text-base leading-none">{t.icon}</span>
                <div className={['text-[11px] font-semibold', t.text].join(' ')}>{t.name}</div>
              </div>
              {t.isNew && isActive ? (
                <div className="mt-1.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[9px] text-emerald-600 font-medium">真空期监测中</span>
                </div>
              ) : isActive && clusterCount ? (
                <div className="mt-1.5 flex items-center gap-1">
                  <span className={['w-1.5 h-1.5 rounded-full', t.dot].join(' ')} />
                  <span className={['text-[9px] font-medium', t.text].join(' ')}>{t.count} 名活跃</span>
                </div>
              ) : null}
              {isSelected && (
                <div className="absolute top-1.5 right-1.5 w-3 h-3 rounded-full bg-white/80 flex items-center justify-center">
                  <span className={['w-1.5 h-1.5 rounded-full', t.dot].join(' ')} />
                </div>
              )}
            </button>
          )
        })}
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
  const [selectedTroopKey, setSelectedTroopKey] = useState<string | null>(null)
  // Reset troop filter whenever the viewed role changes
  useEffect(() => { setSelectedTroopKey(null) }, [role])
  const filteredDisplayLines = useMemo(() => {
    if (role !== 'Amplifier' || !selectedTroopKey) return displayLines
    const filtered = displayLines.filter((line) => getAmplifierTroopKey(line) === selectedTroopKey)
    return filtered
  }, [role, selectedTroopKey, displayLines])
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

      {role === 'Amplifier' && (
        <AmplifierTroopGrid
          summary={summary}
          status={status}
          selectedTroopKey={selectedTroopKey}
          onSelectTroopKey={setSelectedTroopKey}
        />
      )}

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
          {role === 'Amplifier' && selectedTroopKey ? (
            <div className="mb-3">
              <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {(() => {
                  const label = { empath: '💗 同理心安抚者', factchecker: '🔍 逻辑辟谣者', amplifier: '👑 意见领袖护盘者', nichefiller: '🌱 生态位填补者' }[selectedTroopKey]
                  return `${label ?? selectedTroopKey} · 工作流`
                })()}
              </div>
              {(() => {
                const stages = TROOP_STAGES[selectedTroopKey]
                const currentStage = getTroopStageProgress(filteredDisplayLines)
                if (!stages || currentStage < 0) return null
                return (
                  <div className="flex items-start mb-3">
                    {stages.map((stageLabel, idx) => {
                      const isDone = idx < currentStage
                      const isCurrent = idx === currentStage
                      const isLast = idx === stages.length - 1
                      return (
                        <div key={idx} className="flex items-center flex-1">
                          {idx > 0 && (
                            <div className={['h-px flex-1', idx <= currentStage ? 'bg-emerald-300' : 'bg-slate-200'].join(' ')} />
                          )}
                          <div className="flex flex-col items-center gap-0.5 shrink-0">
                            <div className={[
                              'w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold',
                              isDone ? 'bg-emerald-300 text-white' : isCurrent ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-400',
                            ].join(' ')}>
                              {isDone ? '✓' : idx + 1}
                            </div>
                            <span className={[
                              'text-[9px] font-medium text-center leading-tight max-w-[56px]',
                              isCurrent ? 'text-emerald-700 font-semibold' : isDone ? 'text-slate-500' : 'text-slate-300',
                            ].join(' ')}>
                              {stageLabel}
                            </span>
                          </div>
                          {!isLast && (
                            <div className={['h-px flex-1', idx < currentStage ? 'bg-emerald-300' : 'bg-slate-200'].join(' ')} />
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>
          ) : null}
          <div className="space-y-2 h-full overflow-y-auto overflow-x-hidden pr-1">
            {filteredDisplayLines.length ? (
              filteredDisplayLines.map((line, idx) => {
                const troop = role === 'Amplifier' ? getAmplifierTroopLabel(line) : null
                const isAnalysisLine = role === 'Amplifier' && /^🔍\s*amplifier-\d+\b/i.test(line)
                const isDecisionLine = role === 'Amplifier' && /^🎯\s*amplifier-\d+\b/i.test(line)
                const isCommentLine  = role === 'Amplifier' && /^💬\s*🤖\s*amplifier-\d+\b/i.test(line)

                if (isAnalysisLine) {
                  return (
                    <div key={`${role}_${idx}`} className="flex items-start gap-1.5 leading-relaxed break-all">
                      <span className="text-[9px] font-bold shrink-0 mt-0.5 px-1.5 py-0.5 rounded bg-sky-50 text-sky-400 whitespace-nowrap">分析</span>
                      <span className="text-slate-400 text-[11px]">{line}</span>
                    </div>
                  )
                }

                if (isDecisionLine) {
                  return (
                    <div key={`${role}_${idx}`} className="flex items-start gap-1.5 leading-relaxed break-all">
                      <span className="text-[9px] font-bold shrink-0 mt-0.5 px-1.5 py-0.5 rounded bg-slate-100 text-slate-400 whitespace-nowrap">决策</span>
                      <span className="text-slate-400 text-[11px]">{line}</span>
                    </div>
                  )
                }

                if (isCommentLine) {
                  const publishBg: Record<string, string> = {
                    'text-pink-600': 'bg-pink-100',
                    'text-blue-600': 'bg-blue-100',
                    'text-amber-600': 'bg-amber-100',
                    'text-emerald-600': 'bg-emerald-100',
                  }
                  const bgClass = troop ? (publishBg[troop.color] ?? 'bg-slate-100') : 'bg-slate-100'
                  return (
                    <div key={`${role}_${idx}`} className="flex items-start gap-1.5 text-sm leading-relaxed break-all">
                      <span className={['text-[9px] font-bold shrink-0 mt-0.5 px-1.5 py-0.5 rounded whitespace-nowrap', troop ? troop.color : 'text-slate-500', bgClass].join(' ')}>发布</span>
                      <span className="text-slate-700">{line}</span>
                    </div>
                  )
                }

                return (
                  <div key={`${role}_${idx}`} className="flex items-start gap-1.5 text-sm leading-relaxed break-all">
                    {troop ? (
                      <span className={['text-[10px] font-semibold shrink-0 mt-0.5 whitespace-nowrap', troop.color].join(' ')}>
                        {troop.icon}{troop.name}
                      </span>
                    ) : null}
                    <span className="text-slate-700">{line}</span>
                  </div>
                )
              })
            ) : selectedTroopKey ? (
              <div className="text-sm text-slate-400 italic">暂无该兵种专属日志</div>
            ) : (
              <div className="text-sm text-slate-600">{emptyCopy.stream}</div>
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
          <button type="button" className="btn-secondary" onClick={handleCancel}>取消</button>
          <button
            type="button"
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
      type="button"
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
