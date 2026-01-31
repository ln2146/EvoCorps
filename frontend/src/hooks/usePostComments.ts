import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

// 评论接口
export interface Comment {
    commentId: string
    content: string
    authorId: string
    createdAt: string
    likeCount: number
}

// 评论响应接口
interface CommentsResponse {
    comments: Comment[]
}

// 排序类型
export type CommentSort = 'likes' | 'time'

// Hook 返回值接口
interface UsePostCommentsResult {
    data: Comment[] | undefined
    isLoading: boolean
    error: Error | null
}

/**
 * usePostComments Hook
 * 
 * 管理评论列表数据获取
 * 
 * @param postId - 帖子 ID，为 null 时不发起请求
 * @param sort - 排序方式，'likes' 或 'time'，默认 'likes'
 * @returns 评论列表数据和状态
 */
export function usePostComments(
    postId: string | null,
    sort: CommentSort = 'likes'
): UsePostCommentsResult {
    const { data, isLoading, error } = useQuery<CommentsResponse, Error>({
        queryKey: ['postComments', postId, sort],
        queryFn: async () => {
            if (!postId) {
                throw new Error('postId is required')
            }
            const response = await axios.get<CommentsResponse>(`/api/leaderboard/posts/${postId}/comments`, {
                params: { sort },
            })
            return response.data
        },
        // 只有当 postId 不为 null 时才启用查询
        enabled: postId !== null,
        staleTime: 3000, // 3 秒内认为数据是新鲜的
        refetchOnWindowFocus: false,
    })

    return {
        data: data?.comments,
        isLoading,
        error: error || null,
    }
}
