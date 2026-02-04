/**
 * Post Analysis API
 * 帖子评论分析 API 调用函数
 * 
 * 调用后端 /analysis/post-comments 端点，获取帖子评论区的情绪度、极端度和总结分析
 */

// 控制 API 服务器地址
const CONTROL_API_BASE = 'http://localhost:8000'

/**
 * 帖子分析请求参数
 */
export interface PostAnalysisRequest {
    post_id: string
}

/**
 * 帖子分析响应结果
 */
export interface PostAnalysisResponse {
    /** 帖子 ID */
    post_id: string
    /** 帖子内容 */
    post_content: string
    /** 评论数量 */
    num_comments: number
    /** 整体情绪度分数 (0-1)，null 表示分析失败 */
    sentiment_score_overall: number | null
    /** 整体极端度分数 (0-1)，null 表示分析失败 */
    extremeness_score_overall: number | null
    /** 评论区总结分析文本，null 表示分析失败 */
    summary: string | null
    /** 原始 LLM 响应（可选，用于调试） */
    analysis_raw?: string
    /** 错误信息（如果有） */
    error?: string
}

/**
 * 分析帖子评论
 * 
 * 调用 POST /analysis/post-comments 端点，获取指定帖子评论区的分析结果
 * 
 * @param postId - 要分析的帖子 ID
 * @returns 分析结果，包含情绪度、极端度和总结
 * @throws Error - 网络错误或服务器错误时抛出异常
 * 
 * @example
 * ```typescript
 * const result = await analyzePostComments('post-12345')
 * console.log(result.sentiment_score_overall) // 0.42
 * console.log(result.extremeness_score_overall) // 0.38
 * console.log(result.summary) // "评论区主要观点..."
 * ```
 */
export async function analyzePostComments(postId: string): Promise<PostAnalysisResponse> {
    const url = `${CONTROL_API_BASE}/analysis/post-comments`

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ post_id: postId } as PostAnalysisRequest),
    })

    // 处理 HTTP 错误
    if (!response.ok) {
        // 尝试解析错误响应体
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`
        try {
            const errorBody = await response.json()
            if (errorBody.error) {
                errorMessage = errorBody.error
            }
        } catch {
            // 忽略 JSON 解析错误，使用默认错误信息
        }
        throw new Error(errorMessage)
    }

    // 解析响应
    const data: PostAnalysisResponse = await response.json()

    return data
}
