import { useState, useRef, useCallback, useEffect } from 'react'
import { analyzePostComments, PostAnalysisResponse } from '../api/postAnalysis'

/**
 * 分析结果接口
 */
export interface AnalysisResult {
    postId: string
    sentimentScore: number | null
    extremenessScore: number | null
    summary: string | null
    timestamp: string
    error?: string
}

/**
 * 指标趋势数据点
 */
export interface MetricsDataPoint {
    /** 格式化的时间字符串，如 "10:30:45" */
    time: string
    /** 情绪度 0-1 */
    emotion: number
    /** 极端度 0-1 */
    extremity: number
}

/**
 * Hook 配置选项
 */
export interface UsePostAnalysisOptions {
    /** 默认分析间隔（毫秒），默认 60000 */
    defaultInterval?: number
}

/**
 * 分析状态类型
 */
export type AnalysisStatus = 'Idle' | 'Running' | 'Done' | 'Error'

/**
 * Hook 返回值接口
 */
export interface UsePostAnalysisResult {
    // 状态
    trackedPostId: string | null
    isTracking: boolean
    isAnalyzing: boolean
    analysisStatus: AnalysisStatus

    // 当前指标
    currentMetrics: {
        sentiment: number
        extremeness: number
    }

    // 趋势数据
    metricsSeries: MetricsDataPoint[]

    // 分析结果
    latestResult: AnalysisResult | null
    summary: string | null

    // 配置
    interval: number
    setInterval: (ms: number) => void

    // 操作
    startTracking: (postId: string) => void
    stopTracking: () => void
    analyzeNow: () => Promise<void>
}


// 默认配置常量
const DEFAULT_INTERVAL = 60000 // 1 分钟
const MIN_INTERVAL = 10000 // 最小 10 秒

/**
 * 验证间隔值是否有效
 * @param value - 间隔值（毫秒）
 * @returns 是否有效
 */
export function validateInterval(value: number): boolean {
    return Number.isInteger(value) && value >= MIN_INTERVAL
}

/**
 * 格式化时间为 HH:MM:SS 格式
 */
function formatTime(date: Date): string {
    return date.toTimeString().slice(0, 8)
}

/**
 * usePostAnalysis Hook
 * 
 * 管理帖子评论分析追踪状态和 API 调用
 * 
 * @param options - 配置选项
 * @returns 追踪状态、指标数据和操作函数
 */
export function usePostAnalysis(options?: UsePostAnalysisOptions): UsePostAnalysisResult {
    const { defaultInterval = DEFAULT_INTERVAL } = options || {}

    // 追踪状态
    const [trackedPostId, setTrackedPostId] = useState<string | null>(null)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('Idle')

    // 当前指标
    const [currentMetrics, setCurrentMetrics] = useState({
        sentiment: 0,
        extremeness: 0,
    })

    // 趋势数据
    const [metricsSeries, setMetricsSeries] = useState<MetricsDataPoint[]>([])

    // 分析结果
    const [latestResult, setLatestResult] = useState<AnalysisResult | null>(null)
    const [summary, setSummary] = useState<string | null>(null)

    // 配置
    const [interval, setIntervalState] = useState(defaultInterval)

    // 定时器引用
    const timerRef = useRef<number | null>(null)
    // 追踪的 postId 引用（用于定时器回调中访问最新值）
    const trackedPostIdRef = useRef<string | null>(null)
    // 间隔值引用
    const intervalRef = useRef(defaultInterval)

    // 同步 ref 值
    useEffect(() => {
        trackedPostIdRef.current = trackedPostId
    }, [trackedPostId])

    useEffect(() => {
        intervalRef.current = interval
    }, [interval])

    // 计算 isTracking
    const isTracking = trackedPostId !== null


    /**
     * 处理 API 响应，更新状态
     */
    const handleApiResponse = useCallback((response: PostAnalysisResponse, postId: string) => {
        const timestamp = new Date().toISOString()
        const timeStr = formatTime(new Date())

        // 创建分析结果
        const result: AnalysisResult = {
            postId,
            sentimentScore: response.sentiment_score_overall,
            extremenessScore: response.extremeness_score_overall,
            summary: response.summary,
            timestamp,
            error: response.error,
        }
        setLatestResult(result)

        // 更新 summary
        if (response.summary !== null) {
            setSummary(response.summary)
        }

        // 更新当前指标（null 值保持上一次的值）
        setCurrentMetrics((prev) => ({
            sentiment: response.sentiment_score_overall ?? prev.sentiment,
            extremeness: response.extremeness_score_overall ?? prev.extremeness,
        }))

        // 追加趋势数据（只有当有有效值时才追加）
        if (response.sentiment_score_overall !== null && response.extremeness_score_overall !== null) {
            setMetricsSeries((prev) => [
                ...prev,
                {
                    time: timeStr,
                    emotion: response.sentiment_score_overall!,
                    extremity: response.extremeness_score_overall!,
                },
            ])
        }

        // 更新状态
        if (response.error) {
            setAnalysisStatus('Error')
        } else {
            setAnalysisStatus('Done')
        }
    }, [])

    /**
     * 执行一次分析 API 调用
     */
    const performAnalysis = useCallback(async (postId: string): Promise<void> => {
        setIsAnalyzing(true)
        setAnalysisStatus('Running')

        try {
            const response = await analyzePostComments(postId)
            handleApiResponse(response, postId)
        } catch (error) {
            // API 错误不中断追踪
            setAnalysisStatus('Error')
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            setLatestResult({
                postId,
                sentimentScore: null,
                extremenessScore: null,
                summary: null,
                timestamp: new Date().toISOString(),
                error: errorMessage,
            })
        } finally {
            setIsAnalyzing(false)
        }
    }, [handleApiResponse])


    /**
     * 清除定时器
     */
    const clearTimer = useCallback(() => {
        if (timerRef.current !== null) {
            window.clearInterval(timerRef.current)
            timerRef.current = null
        }
    }, [])

    /**
     * 启动定时器
     */
    const startTimer = useCallback(() => {
        clearTimer()
        timerRef.current = window.setInterval(() => {
            const currentPostId = trackedPostIdRef.current
            if (currentPostId) {
                performAnalysis(currentPostId)
            }
        }, intervalRef.current)
    }, [clearTimer, performAnalysis])

    /**
     * 开始追踪帖子
     * 设置 trackedPostId 并立即触发分析，启动定时器
     */
    const startTracking = useCallback((postId: string) => {
        // 清除旧定时器
        clearTimer()

        // 清空趋势数据
        setMetricsSeries([])

        // 重置状态
        setCurrentMetrics({ sentiment: 0, extremeness: 0 })
        setSummary(null)
        setLatestResult(null)

        // 设置新的追踪 postId
        setTrackedPostId(postId)
        trackedPostIdRef.current = postId

        // 立即触发一次分析
        performAnalysis(postId)

        // 启动定时器
        timerRef.current = window.setInterval(() => {
            const currentPostId = trackedPostIdRef.current
            if (currentPostId) {
                performAnalysis(currentPostId)
            }
        }, intervalRef.current)
    }, [clearTimer, performAnalysis])

    /**
     * 停止追踪
     */
    const stopTracking = useCallback(() => {
        clearTimer()
        setTrackedPostId(null)
        trackedPostIdRef.current = null
        setAnalysisStatus('Idle')
    }, [clearTimer])


    /**
     * 立即分析
     * 立即触发 API 调用，并重置定时器
     */
    const analyzeNow = useCallback(async (): Promise<void> => {
        const currentPostId = trackedPostIdRef.current
        // 无追踪时不执行操作
        if (!currentPostId) {
            return
        }

        // 立即执行分析
        await performAnalysis(currentPostId)

        // 重置定时器从当前时刻重新计算
        startTimer()
    }, [performAnalysis, startTimer])

    /**
     * 设置分析间隔
     * 验证间隔值并使用新间隔值重置定时器
     */
    const setInterval = useCallback((ms: number) => {
        // 验证间隔值
        if (!validateInterval(ms)) {
            console.warn(`Invalid interval value: ${ms}. Must be a positive integer >= ${MIN_INTERVAL}ms`)
            return
        }

        setIntervalState(ms)
        intervalRef.current = ms

        // 如果正在追踪，使用新间隔值重置定时器
        if (trackedPostIdRef.current) {
            startTimer()
        }
    }, [startTimer])

    // 组件卸载时清除定时器
    useEffect(() => {
        return () => {
            clearTimer()
        }
    }, [clearTimer])

    return {
        // 状态
        trackedPostId,
        isTracking,
        isAnalyzing,
        analysisStatus,

        // 当前指标
        currentMetrics,

        // 趋势数据
        metricsSeries,

        // 分析结果
        latestResult,
        summary,

        // 配置
        interval,
        setInterval,

        // 操作
        startTracking,
        stopTracking,
        analyzeNow,
    }
}
