import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { createInitialFlowState, type FlowState } from '../lib/interventionFlow/logRouter'
import type { AttackMode } from '../lib/attackModeToggle'
import type { FactionReport, PostFactionsSummary } from '../services/api'

// ==================== 类型定义 ====================

export interface HeatPost {
  id: string
  summary: string
  heat: number
  author: string
  createdAt: string
  feedScore?: number
  excerpt?: string
  authorId?: string
  postId?: string
  content?: string
  likeCount?: number
  shareCount?: number
  commentCount?: number
}

export interface DefenseDashboard {
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

// FactionReport 和 PostFactionsSummary 从 api.ts 导入

interface SimulationState {
  // 运行状态
  isRunning: boolean
  databaseRunning: boolean
  mainRunning: boolean
  currentTick: number

  // 控制开关
  enableAttack: boolean
  enableAftercare: boolean
  enableModeration: boolean
  enableEvoCorps: boolean
  attackMode: AttackMode | null

  // 选中的帖子
  selectedPost: HeatPost | null

  // 干预流程状态
  flowState: FlowState
  opinionBalanceStartMs: number | null

  // 防御仪表盘数据
  defenseDashboard: DefenseDashboard | null

  // 派系数据
  factionReport: FactionReport | null
  postFactions: PostFactionsSummary | null

  // 加载状态
  isStarting: boolean
  isStopping: boolean
  isTogglingAttack: boolean
  isTogglingAftercare: boolean
  isTogglingModeration: boolean
}

interface SimulationContextValue extends SimulationState {
  // 状态更新方法
  setIsRunning: (value: boolean) => void
  setDatabaseRunning: (value: boolean) => void
  setMainRunning: (value: boolean) => void
  setCurrentTick: (value: number) => void

  setEnableAttack: (value: boolean) => void
  setEnableAftercare: (value: boolean) => void
  setEnableModeration: (value: boolean) => void
  setEnableEvoCorps: (value: boolean) => void
  setAttackMode: (value: AttackMode | null) => void

  setSelectedPost: (post: HeatPost | null) => void

  setFlowState: (state: FlowState | ((prev: FlowState) => FlowState)) => void
  setOpinionBalanceStartMs: (ms: number | null) => void

  setDefenseDashboard: (dashboard: DefenseDashboard | null) => void
  setFactionReport: (report: FactionReport | null) => void
  setPostFactions: (factions: PostFactionsSummary | null) => void

  setIsStarting: (value: boolean) => void
  setIsStopping: (value: boolean) => void
  setIsTogglingAttack: (value: boolean) => void
  setIsTogglingAftercare: (value: boolean) => void
  setIsTogglingModeration: (value: boolean) => void

  // 重置状态
  resetFlowState: () => void
}

// ==================== Context 创建 ====================

const SimulationContext = createContext<SimulationContextValue | null>(null)

// ==================== Provider 组件 ====================

interface SimulationProviderProps {
  children: ReactNode
}

export function SimulationProvider({ children }: SimulationProviderProps) {
  // 从 localStorage 初始化 selectedPost
  const [selectedPost, setSelectedPostState] = useState<HeatPost | null>(() => {
    try {
      const saved = localStorage.getItem('dynamicDemo_selectedPost')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  // 运行状态
  const [isRunning, setIsRunning] = useState(false)
  const [databaseRunning, setDatabaseRunning] = useState(false)
  const [mainRunning, setMainRunning] = useState(false)
  const [currentTick, setCurrentTick] = useState(0)

  // 控制开关
  const [enableAttack, setEnableAttack] = useState(false)
  const [enableAftercare, setEnableAftercare] = useState(false)
  const [enableModeration, setEnableModeration] = useState(false)
  const [enableEvoCorps, setEnableEvoCorps] = useState(false)
  const [attackMode, setAttackMode] = useState<AttackMode | null>(null)

  // 干预流程状态
  const [flowState, setFlowState] = useState<FlowState>(() => createInitialFlowState())
  const [opinionBalanceStartMs, setOpinionBalanceStartMs] = useState<number | null>(null)

  // 防御仪表盘数据
  const [defenseDashboard, setDefenseDashboard] = useState<DefenseDashboard | null>(null)

  // 派系数据
  const [factionReport, setFactionReport] = useState<FactionReport | null>(null)
  const [postFactions, setPostFactions] = useState<PostFactionsSummary | null>(null)

  // 加载状态
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [isTogglingAttack, setIsTogglingAttack] = useState(false)
  const [isTogglingAftercare, setIsTogglingAftercare] = useState(false)
  const [isTogglingModeration, setIsTogglingModeration] = useState(false)

  // 用于跟踪是否已检查过初始状态
  const hasCheckedInitialStatusRef = useRef(false)

  // 包装 setSelectedPost 以同步 localStorage
  const setSelectedPost = useCallback((post: HeatPost | null) => {
    setSelectedPostState(post)
    if (post) {
      localStorage.setItem('dynamicDemo_selectedPost', JSON.stringify(post))
    } else {
      localStorage.removeItem('dynamicDemo_selectedPost')
    }
  }, [])

  // 重置 flowState
  const resetFlowState = useCallback(() => {
    setFlowState(createInitialFlowState())
  }, [])

  // 从后端同步状态
  const syncStatusFromBackend = useCallback(async () => {
    try {
      const response = await fetch('/api/dynamic/status')
      const data = await response.json()

      const dbRunning = data.database_running === true
      const simRunning = data.main_running === true
      const running = dbRunning && simRunning

      setDatabaseRunning(dbRunning)
      setMainRunning(simRunning)
      setIsRunning(running)
      setCurrentTick(data.current_tick || 0)

      // 同步控制开关状态（仅在首次检查时）
      if (!hasCheckedInitialStatusRef.current && running) {
        try {
          const controlResponse = await fetch('http://localhost:8000/control/status')
          if (controlResponse.ok) {
            const controlData = await controlResponse.json()
            setEnableAttack(controlData.attack_enabled === true)
            setEnableAftercare(controlData.aftercare_enabled === true)
            setEnableModeration(controlData.moderation_enabled === true)
            if (controlData.attack_mode) {
              setAttackMode(controlData.attack_mode as AttackMode)
            }
          }
        } catch {
          // 控制服务可能未启动，忽略
        }
        hasCheckedInitialStatusRef.current = true
      }
    } catch (error) {
      console.error('Failed to sync status from backend:', error)
    }
  }, [])

  // 初始化时同步状态
  useEffect(() => {
    syncStatusFromBackend()
  }, [syncStatusFromBackend])

  // 定期轮询状态（每 2 秒）
  useEffect(() => {
    const interval = setInterval(syncStatusFromBackend, 2000)
    return () => clearInterval(interval)
  }, [syncStatusFromBackend])

  const value: SimulationContextValue = {
    // 状态
    isRunning,
    databaseRunning,
    mainRunning,
    currentTick,
    enableAttack,
    enableAftercare,
    enableModeration,
    enableEvoCorps,
    attackMode,
    selectedPost,
    flowState,
    opinionBalanceStartMs,
    defenseDashboard,
    factionReport,
    postFactions,
    isStarting,
    isStopping,
    isTogglingAttack,
    isTogglingAftercare,
    isTogglingModeration,

    // 方法
    setIsRunning,
    setDatabaseRunning,
    setMainRunning,
    setCurrentTick,
    setEnableAttack,
    setEnableAftercare,
    setEnableModeration,
    setEnableEvoCorps,
    setAttackMode,
    setSelectedPost,
    setFlowState,
    setOpinionBalanceStartMs,
    setDefenseDashboard,
    setFactionReport,
    setPostFactions,
    setIsStarting,
    setIsStopping,
    setIsTogglingAttack,
    setIsTogglingAftercare,
    setIsTogglingModeration,
    resetFlowState,
  }

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  )
}

// ==================== Hook ====================

export function useSimulation(): SimulationContextValue {
  const context = useContext(SimulationContext)
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider')
  }
  return context
}
