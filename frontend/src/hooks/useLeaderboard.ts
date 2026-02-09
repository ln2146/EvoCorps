import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

// 榜单项接口
export interface LeaderboardItem {
    postId: string
    excerpt: string
    score: number
    authorId: string
    createdAt: string
    likeCount: number
    shareCount: number
    commentCount: number
}

// 榜单响应接口
interface LeaderboardResponse {
    items: LeaderboardItem[]
    timeStep: number
    fingerprint: string
}

// Hook 参数接口
interface UseLeaderboardOptions {
    enableSSE?: boolean
    limit?: number
}

// Hook 返回值接口
interface UseLeaderboardResult {
    data: LeaderboardItem[] | undefined
    isLoading: boolean
    error: Error | null
    timeStep: number | undefined
    fingerprint: string | undefined
    refetch: () => Promise<void>
}

/**
 * useLeaderboard Hook
 * 
 * 管理热度榜数据获取和 SSE 实时更新
 * 
 * @param options - 配置选项
 * @param options.enableSSE - 是否启用 SSE 实时更新，默认 true
 * @param options.limit - 返回数量限制，默认 20
 * @returns 榜单数据和状态
 */
export function useLeaderboard(options: UseLeaderboardOptions = {}): UseLeaderboardResult {
    const { enableSSE = true, limit = 20 } = options
    const queryClient = useQueryClient()
    const eventSourceRef = useRef<EventSource | null>(null)
    const lastFingerprintRef = useRef<string | null>(null)

    // 使用 React Query 获取初始数据
    const { data, isLoading, error, refetch } = useQuery<LeaderboardResponse, Error>({
        queryKey: ['leaderboard', limit],
        queryFn: async () => {
            const response = await axios.get<LeaderboardResponse>('/api/leaderboard', {
                params: { limit },
            })
            // 保存初始 fingerprint
            lastFingerprintRef.current = response.data.fingerprint
            return response.data
        },
        staleTime: 1000, // 1 秒内认为数据是新鲜的
        refetchOnWindowFocus: false,
    })

    // 使用 useEffect 管理 SSE 连接
    useEffect(() => {
        // 如果不启用 SSE，断开连接并返回
        if (!enableSSE) {
            if (eventSourceRef.current) {
                eventSourceRef.current.close()
                eventSourceRef.current = null
            }
            return
        }

        // 如果已经有连接，不重复创建
        if (eventSourceRef.current) {
            return
        }

        // 创建 SSE 连接
        const eventSource = new EventSource('/api/events')
        eventSourceRef.current = eventSource

        // 监听 leaderboard-update 事件
        eventSource.addEventListener('leaderboard-update', (event) => {
            try {
                const newData: LeaderboardResponse = JSON.parse(event.data)

                // 双重验证：检查 fingerprint 是否变化
                if (newData.fingerprint === lastFingerprintRef.current) {
                    // fingerprint 相同，忽略更新
                    return
                }

                // fingerprint 不同，更新缓存
                lastFingerprintRef.current = newData.fingerprint
                queryClient.setQueryData(['leaderboard', limit], newData)
            } catch (err) {
                console.error('Failed to parse SSE data:', err)
            }
        })

        // 监听错误事件
        eventSource.addEventListener('error', (err) => {
            console.error('SSE connection error:', err)
            // 连接错误时关闭连接
            eventSource.close()
            eventSourceRef.current = null
        })

        // 清理函数：组件卸载或 enableSSE 变化时关闭连接
        return () => {
            eventSource.close()
            eventSourceRef.current = null
        }
    }, [enableSSE, limit, queryClient])

    return {
        data: data?.items,
        isLoading,
        error: error || null,
        timeStep: data?.timeStep,
        fingerprint: data?.fingerprint,
        refetch: async () => {
            await refetch()
        },
    }
}
