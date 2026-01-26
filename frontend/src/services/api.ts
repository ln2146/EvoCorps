import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface DatabaseStats {
  activeUsers: number
  totalPosts: number
  totalComments: number
  totalLikes: number
}

export interface User {
  user_id: string
  persona: string
  creation_time: string
  influence_score: number
}

export interface UserDetail {
  basic_info: {
    user_id: string
    persona: string
    background_labels: string
    creation_time: string
    influence_score: number
    is_influencer: boolean
  }
  activity_stats: {
    post_count: number
    comment_count: number
    follower_count: number
    likes_received: number
    avg_engagement: number
  }
  following: Array<{ user_id: string; followed_at: string }>
  followers: Array<{ user_id: string; followed_at: string }>
  comments: Array<{
    comment_id: string
    post_id: string
    content: string
    created_at: string
    num_likes: number
  }>
  posts: Array<{
    post_id: string
    content: string
    created_at: string
    num_likes: number
    num_comments: number
    num_shares: number
  }>
}

export interface Post {
  post_id: string
  author_id: string
  content: string
  created_at: string
  num_likes: number
  num_comments: number
  num_shares: number
  total_engagement: number
}

export interface PostDetail {
  basic_info: {
    post_id: string
    author_id: string
    content: string
    created_at: string
    topic: string
  }
  engagement_stats: {
    num_likes: number
    num_comments: number
    num_shares: number
    total_engagement: number
  }
  comments: Array<{
    comment_id: string
    author_id: string
    content: string
    created_at: string
    num_likes: number
  }>
  likes: Array<{
    user_id: string
    created_at: string
  }>
  shares: Array<{
    user_id: string
    created_at: string
  }>
}

// 获取可用的数据库列表
export const getDatabases = async (): Promise<string[]> => {
  try {
    const response = await api.get('/databases')
    return response.data.databases || []
  } catch (error) {
    console.error('Failed to fetch databases:', error)
    return []
  }
}

// 获取数据库统计信息
export const getDatabaseStats = async (dbName: string): Promise<DatabaseStats> => {
  try {
    const response = await api.get(`/stats/${dbName}`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch database stats:', error)
    return {
      activeUsers: 0,
      totalPosts: 0,
      totalComments: 0,
      totalLikes: 0,
    }
  }
}

// 获取用户列表
export const getUsers = async (dbName: string): Promise<User[]> => {
  try {
    const response = await api.get(`/users/${dbName}`)
    return response.data.users || []
  } catch (error) {
    console.error('Failed to fetch users:', error)
    return []
  }
}

// 获取用户详细信息
export const getUserDetail = async (dbName: string, userId: string): Promise<UserDetail | null> => {
  try {
    const response = await api.get(`/user/${dbName}/${userId}`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch user detail:', error)
    return null
  }
}

// 获取帖子列表
export const getPosts = async (dbName: string): Promise<Post[]> => {
  try {
    const response = await api.get(`/posts/${dbName}`)
    return response.data.posts || []
  } catch (error) {
    console.error('Failed to fetch posts:', error)
    return []
  }
}

// 获取帖子详细信息
export const getPostDetail = async (dbName: string, postId: string): Promise<PostDetail | null> => {
  try {
    const response = await api.get(`/post/${dbName}/${postId}`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch post detail:', error)
    return null
  }
}

export default api
