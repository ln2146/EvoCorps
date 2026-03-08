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

// Experiment Management APIs
export interface Experiment {
  experiment_id: string
  experiment_name: string
  scenario_type: string
  database_name: string
  timestamp: string
  saved_at: string
  database_saved: boolean
  emotion_data_saved: boolean
}

export const getExperiments = async (): Promise<Experiment[]> => {
  try {
    const response = await api.get('/experiments')
    return response.data.experiments || []
  } catch (error) {
    console.error('Failed to fetch experiments:', error)
    return []
  }
}

export const saveExperiment = async (data: {
  experiment_name: string
  scenario_type: string
  database_name: string
}) => {
  const response = await api.post('/experiments/save', data)
  return response.data
}

export const loadExperiment = async (experimentId: string) => {
  const response = await api.post(`/experiments/${experimentId}/load`)
  return response.data
}

export const deleteExperiment = async (experimentId: string) => {
  const response = await api.delete(`/experiments/${experimentId}`)
  return response.data
}

export const exportExperiment = async (experimentId: string) => {
  const response = await api.get(`/experiments/${experimentId}/export`, {
    responseType: 'blob'
  })
  return response.data
}

// Visualization APIs
export const getEmotionData = async (dbName: string) => {
  const response = await api.get(`/visualization/${dbName}/emotion`)
  return response.data
}

export const getTopUsers = async (dbName: string) => {
  const response = await api.get(`/visualization/${dbName}/top-users`)
  return response.data
}

export const getNetworkData = async (dbName: string) => {
  try {
    const response = await api.get(`/visualization/${dbName}/network`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch network data:', error)
    throw error
  }
}

export const getOpinionBalanceData = async (dbName: string) => {
  const response = await api.get(`/visualization/${dbName}/opinion-balance`)
  return response.data
}

// Control Flags APIs
export interface ControlFlags {
  attack_enabled: boolean
  attack_mode?: 'swarm' | 'dispersed' | 'chain'
  aftercare_enabled: boolean
  auto_status: boolean | null
  moderation_enabled: boolean
}

export const getControlFlags = async (): Promise<ControlFlags> => {
  try {
    const response = await api.get('/control/status')
    return response.data
  } catch (error) {
    console.error('Failed to fetch control flags:', error)
    return {
      attack_enabled: false,
      attack_mode: 'swarm',
      aftercare_enabled: false,
      auto_status: false,
      moderation_enabled: false,
    }
  }
}

export const setModerationFlag = async (enabled: boolean): Promise<{ moderation_enabled: boolean }> => {
  try {
    const response = await api.post('/control/moderation', { enabled })
    return response.data
  } catch (error) {
    console.error('Failed to set moderation flag:', error)
    throw error
  }
}

export const setAttackFlag = async (enabled: boolean): Promise<{ attack_enabled: boolean }> => {
  try {
    const response = await api.post('/control/attack', { enabled })
    return response.data
  } catch (error) {
    console.error('Failed to set attack flag:', error)
    throw error
  }
}

export const setAttackMode = async (
  mode: 'swarm' | 'dispersed' | 'chain'
): Promise<{ attack_mode: 'swarm' | 'dispersed' | 'chain' }> => {
  try {
    const response = await api.post('/control/attack-mode', { mode })
    return response.data
  } catch (error) {
    console.error('Failed to set attack mode:', error)
    throw error
  }
}

export const setAftercareFlag = async (enabled: boolean): Promise<{ aftercare_enabled: boolean }> => {
  try {
    const response = await api.post('/control/aftercare', { enabled })
    return response.data
  } catch (error) {
    console.error('Failed to set aftercare flag:', error)
    throw error
  }
}

export const setAutoStatusFlag = async (enabled: boolean): Promise<{ auto_status: boolean | null }> => {
  try {
    const response = await api.post('/control/auto-status', { enabled })
    return response.data
  } catch (error) {
    console.error('Failed to set auto-status flag:', error)
    throw error
  }
}

// ==================== 信息茧房观测相关类型和API ====================

export interface FilterBubbleGlobalStats {
  total_users: number
  avg_homogeneity: number
  avg_diversity: number
  avg_echo_index: number
  severe_bubble_users: number
  moderate_bubble_users: number
  mild_bubble_users: number
  network_density: number
}

export interface FilterBubbleUserMetrics {
  user_id: string
  homogeneity_index: number
  activity_breadth: number
  echo_chamber_index: number
  bubble_severity: 'none' | 'mild' | 'moderate' | 'severe'
}

export interface FilterBubbleUserNetwork {
  user_id: string
  following: string[]
  followers: string[]
  interacted_users: string[]
  total_following: number
  total_followers: number
}

export interface FilterBubbleTrend {
  user_id: string
  current_metrics: {
    homogeneity: number
    diversity: number
    echo_index: number
  }
  trend: 'stable' | 'increasing' | 'decreasing'
}

// 获取全局信息茧房统计
export const getFilterBubbleGlobalStats = async (dbName: string): Promise<FilterBubbleGlobalStats> => {
  try {
    const response = await api.get('/filter-bubble/global-stats', {
      params: { db: dbName }
    })
    return response.data
  } catch (error) {
    console.error('Failed to fetch filter bubble global stats:', error)
    return {
      total_users: 0,
      avg_homogeneity: 0,
      avg_diversity: 0,
      avg_echo_index: 0,
      severe_bubble_users: 0,
      moderate_bubble_users: 0,
      mild_bubble_users: 0,
      network_density: 0,
    }
  }
}

// 获取单个用户的信息茧房指标
export const getUserBubbleMetrics = async (
  dbName: string,
  userId: string
): Promise<FilterBubbleUserMetrics | null> => {
  try {
    const response = await api.get('/filter-bubble/user-metrics', {
      params: { db: dbName, user_id: userId }
    })
    return response.data
  } catch (error) {
    console.error('Failed to fetch user bubble metrics:', error)
    return null
  }
}

// 获取所有用户的信息茧房指标
export const getAllUsersBubbleMetrics = async (
  dbName: string,
  limit: number = 100
): Promise<FilterBubbleUserMetrics[]> => {
  try {
    const response = await api.get('/filter-bubble/all-users', {
      params: { db: dbName, limit }
    })
    return response.data || []
  } catch (error) {
    console.error('Failed to fetch all users bubble metrics:', error)
    return []
  }
}

// 获取用户网络数据
export const getUserNetworkData = async (
  dbName: string,
  userId: string
): Promise<FilterBubbleUserNetwork | null> => {
  try {
    const response = await api.get('/filter-bubble/user-network', {
      params: { db: dbName, user_id: userId }
    })
    return response.data
  } catch (error) {
    console.error('Failed to fetch user network data:', error)
    return null
  }
}

// 获取信息茧房趋势
export const getBubbleTrend = async (
  dbName: string,
  userId: string,
  days: number = 7
): Promise<FilterBubbleTrend | null> => {
  try {
    const response = await api.get('/filter-bubble/bubble-trend', {
      params: { db: dbName, user_id: userId, days }
    })
    return response.data
  } catch (error) {
    console.error('Failed to fetch bubble trend:', error)
    return null
  }
}

// ==================== 社区发现与派系分析相关类型和API ====================

export interface CommunityInfo {
  id: number
  name: string
  size: number
  cohesion: number
  stance_distribution: Record<string, number>
  is_echo_chamber: boolean
  members: string[]
}

export interface FactionReport {
  num_communities: number
  total_users: number
  avg_community_size: number
  max_community_size: number
  num_echo_chambers: number
  avg_cohesion: number
  communities: CommunityInfo[]
}

// 检测派系
export const detectFactions = async (
  dbName: string,
  networkType: 'social' | 'interaction' = 'social',
  minCommunitySize: number = 3
): Promise<FactionReport | null> => {
  try {
    const response = await api.get('/community/detect-factions', {
      params: {
        db: dbName,
        network_type: networkType,
        min_size: minCommunitySize
      }
    })
    return response.data
  } catch (error) {
    console.error('Failed to detect factions:', error)
    return null
  }
}

// 获取跨派系互动
export const getCrossFactionInteractions = async (
  dbName: string
): Promise<Record<string, number> | null> => {
  try {
    const response = await api.get('/community/cross-faction-interactions', {
      params: { db: dbName }
    })
    return response.data
  } catch (error) {
    console.error('Failed to get cross faction interactions:', error)
    return null
  }
}

// 获取回声室用户
export const getEchoChamberUsers = async (
  dbName: string,
  threshold: number = 0.7
): Promise<{ echo_chamber_users: string[]; count: number } | null> => {
  try {
    const response = await api.get('/community/echo-chamber-users', {
      params: { db: dbName, threshold }
    })
    return response.data
  } catch (error) {
    console.error('Failed to get echo chamber users:', error)
    return null
  }
}

// 帖子派系分布类型
export interface PostFactionData {
  post_id: string
  total_comments?: number
  total_likes?: number
  total_interactions: number
  support_count?: number
  neutral_count?: number
  oppose_count?: number
  support_ratio: number
  neutral_ratio: number
  oppose_ratio: number
  top_commenters?: [string, string][]
  like_count?: number
  support_by_like?: number
  avg_influence_score?: number
  high_influence_count?: number
  high_influence_users?: Array<{ user_id: string; score: number; stance: string }>
  high_bubble_users_count?: number
  high_bubble_support_ratio?: number
  is_hottest?: boolean
}

export interface PostFactionsSummary {
  total_posts_analyzed: number
  avg_support_ratio: number
  avg_neutral_ratio: number
  avg_oppose_ratio: number
  avg_influence_score?: number
  high_bubble_support_ratio?: number
  hottest_post?: {
    post_id: string
    total_interactions: number
    support_ratio: number
    neutral_ratio: number
    oppose_ratio: number
    high_influence_users?: Array<{ user_id: string; score: number; stance: string }>
    high_bubble_support_ratio: number
  }
  most_divisive_post: {
    post_id: string
    support_ratio: number
    oppose_ratio: number
    total_comments?: number
    total_interactions?: number
  }
  most_consensus_post: {
    post_id: string
    dominant_stance: 'support' | 'neutral' | 'oppose'
    ratio: number
    total_comments?: number
    total_interactions?: number
  }
  most_influential_post?: {
    post_id: string
    avg_influence_score: number
    total_interactions: number
  }
  post_stances: PostFactionData[]
  post_factions?: PostFactionData[]
  analysis_type?: 'enhanced' | 'basic'
}

// 获取帖子派系分布
export const getPostFactions = async (
  dbName: string,
  limit: number = 15,
  minComments: number = 3
): Promise<PostFactionsSummary | null> => {
  try {
    const response = await api.get('/community/post-factions', {
      params: {
        db: dbName,
        limit,
        min_comments: minComments
      }
    })
    return response.data
  } catch (error) {
    console.error('Failed to get post factions:', error)
    return null
  }
}

export default api

// ==================== 快照管理 API ====================

export interface SavedSnapshot {
  id: string
  name: string
  description?: string
  created_at: string
  saved_at: string
  tick_count: number
  total_users: number
  total_posts: number
  total_comments: number
  ticks: Array<{
    tick: number
    timestamp: string
    user_count: number
    post_count: number
  }>
}

export interface SnapshotDetail extends SavedSnapshot {
  ticks: Array<{
    tick: number
    timestamp: string
    user_count: number
    post_count: number
  }>
}

// 保存命名快照
export const saveSnapshot = async (name: string, description?: string): Promise<{
  success: boolean
  snapshot_id?: string
  message?: string
}> => {
  try {
    const response = await api.post('/snapshots/save', { name, description })
    return response.data
  } catch (error) {
    console.error('Failed to save snapshot:', error)
    throw error
  }
}

// 获取已保存的快照列表
export const getSavedSnapshots = async (): Promise<SavedSnapshot[]> => {
  try {
    const response = await api.get('/snapshots/saved')
    return response.data.snapshots || []
  } catch (error) {
    console.error('Failed to get saved snapshots:', error)
    return []
  }
}

// 获取单个快照详情
export const getSnapshotDetail = async (sessionId: string): Promise<SnapshotDetail | null> => {
  try {
    const response = await api.get(`/snapshots/${sessionId}`)
    return response.data
  } catch (error) {
    console.error('Failed to get snapshot detail:', error)
    return null
  }
}

// ==================== 时间轴控制 API（桩实现）====================

export interface SnapshotInfo {
  tick: number
  timestamp: string
}

// 设置暂停标志
export const setPauseFlag = async (paused: boolean): Promise<{ paused: boolean }> => {
  try {
    const response = await api.post('/control/pause', { paused })
    return response.data
  } catch (error) {
    console.error('Failed to set pause flag:', error)
    return { paused }
  }
}

// 获取时间步快照列表
export const getSnapshots = async (): Promise<{ snapshots: SnapshotInfo[] }> => {
  try {
    const response = await api.get('/snapshots/timeline')
    return response.data
  } catch (error) {
    console.error('Failed to get snapshots:', error)
    return { snapshots: [] }
  }
}

// 恢复到指定时间步
export const restoreSnapshot = async (tick: number): Promise<{ success: boolean }> => {
  try {
    const response = await api.post('/snapshots/restore', { tick })
    return response.data
  } catch (error) {
    console.error('Failed to restore snapshot:', error)
    return { success: false }
  }
}

// 删除指定快照
export const deleteSnapshot = async (sessionId: string): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.delete(`/snapshots/${sessionId}`)
    return response.data
  } catch (error: unknown) {
    console.error('Failed to delete snapshot:', error)
    // 尝试从错误响应中提取后端返回的消息
    const axiosError = error as { response?: { data?: { message?: string } } }
    const message = axiosError.response?.data?.message || '删除失败'
    return { success: false, message }
  }
}

// 删除所有快照
export const deleteAllSnapshots = async (): Promise<{ success: boolean; message: string; deleted_count: number }> => {
  try {
    const response = await api.delete('/snapshots/all')
    return response.data
  } catch (error: unknown) {
    console.error('Failed to delete all snapshots:', error)
    const axiosError = error as { response?: { data?: { message?: string } } }
    const message = axiosError.response?.data?.message || '删除失败'
    return { success: false, message, deleted_count: 0 }
  }
}
