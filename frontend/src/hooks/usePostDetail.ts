import { useQuery } from '@tanstack/react-query'
import axios, { AxiosError } from 'axios'

// 帖子详情接口
export interface PostDetail {
    postId: string
    content: string
    excerpt: string
    authorId: string
    createdAt: string
    likeCount: number
    shareCount: number
    commentCount: number
}

// Hook 返回值接口
interface UsePostDetailResult {
    data: PostDetail | undefined
    isLoading: boolean
    error: Error | null
    is404: boolean
}

/**
 * usePostDetail Hook
 * 
 * 管理帖子详情数据获取
 * 
 * @param postId - 帖子 ID，为 null 时不发起请求
 * @returns 帖子详情数据和状态
 */
export function usePostDetail(postId: string | null): UsePostDetailResult {
    const { data, isLoading, error } = useQuery<PostDetail, AxiosError>({
        queryKey: ['postDetail', postId],
        queryFn: async () => {
            if (!postId) {
                throw new Error('postId is required')
            }
            const response = await axios.get<PostDetail>(`/api/leaderboard/posts/${postId}`)
            return response.data
        },
        // 只有当 postId 不为 null 时才启用查询
        enabled: postId !== null,
        staleTime: 5000, // 5 秒内认为数据是新鲜的
        retry: (failureCount, error) => {
            // 404 错误不重试
            if (error.response?.status === 404) {
                return false
            }
            // 其他错误最多重试 2 次
            return failureCount < 2
        },
    })

    // 判断是否是 404 错误
    const is404 = error?.response?.status === 404

    return {
        data,
        isLoading,
        error: error || null,
        is404,
    }
}
