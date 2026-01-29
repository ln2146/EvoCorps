import { useState, useEffect } from 'react'
import { Database, MessageSquare, Send, CheckCircle2, User, Loader2, Info, X, ThumbsUp, MessageCircle, TrendingUp, ChevronDown, ChevronUp, Users, ChevronLeft, ChevronRight } from 'lucide-react'
import axios from 'axios'

interface UserInfo {
  user_id: string
  persona: string
  influence_score: number
  follower_count: number
}

interface PostWithUsers {
  post_id: string
  content: string
  author_id: string
  num_likes: number
  num_comments: number
  total_engagement: number
  interacted_users: UserInfo[]
}

interface InterviewResponse {
  user_id: string
  question: string
  answer: string
  timestamp: string
}

interface InterviewHistory {
  id: string
  question: string
  timestamp: string
  user_count: number
  responses: InterviewResponse[]
}

export default function InterviewPage() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [posts, setPosts] = useState<PostWithUsers[]>([])
  const [otherUsers, setOtherUsers] = useState<UserInfo[]>([])
  const [expandedPosts, setExpandedPosts] = useState<Set<string>>(new Set())
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())
  const [question, setQuestion] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [interviewHistory, setInterviewHistory] = useState<InterviewHistory[]>([])
  const [selectedHistory, setSelectedHistory] = useState<InterviewHistory | null>(null)
  const [selectedUserDetail, setSelectedUserDetail] = useState<UserInfo | null>(null)
  const [selectedPostDetail, setSelectedPostDetail] = useState<PostWithUsers | null>(null)
  
  // 帖子分页
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalPosts, setTotalPosts] = useState(0)
  const [totalUniqueUsers, setTotalUniqueUsers] = useState(0)
  const postsPerPage = 10
  
  // 用户列表分页（每个帖子内部）
  const [postUserPages, setPostUserPages] = useState<Record<string, number>>({})
  const usersPerPage = 16 // 4x4

  // 加载数据库列表
  useEffect(() => {
    const loadDatabases = async () => {
      try {
        const response = await axios.get('/api/databases')
        setDatabases(response.data.databases)
        if (response.data.databases.length > 0) {
          setSelectedDb(response.data.databases[0])
        }
      } catch (error) {
        console.error('Failed to load databases:', error)
      }
    }
    loadDatabases()
  }, [])

  // 加载帖子和用户数据
  useEffect(() => {
    if (selectedDb) {
      loadPostsWithUsers()
    }
  }, [selectedDb, currentPage])

  // 同步 selectedHistory 与 interviewHistory
  useEffect(() => {
    if (selectedHistory) {
      const updated = interviewHistory.find(h => h.id === selectedHistory.id)
      if (updated && updated !== selectedHistory) {
        setSelectedHistory(updated)
      }
    }
  }, [interviewHistory])

  const loadPostsWithUsers = async () => {
    if (!selectedDb) return
    
    setLoading(true)
    try {
      const response = await axios.get(`/api/interview/posts-with-users/${selectedDb}`, {
        params: {
          page: currentPage,
          page_size: postsPerPage
        }
      })
      setPosts(response.data.posts || [])
      setTotalPages(response.data.total_pages || 1)
      setTotalPosts(response.data.total_posts || 0)
      setTotalUniqueUsers(response.data.total_unique_users || 0)
      
      // 只在第一页时更新其他用户
      if (currentPage === 1) {
        setOtherUsers(response.data.other_users || [])
      }
      
      setExpandedPosts(new Set())
    } catch (error) {
      console.error('Failed to load posts with users:', error)
    } finally {
      setLoading(false)
    }
  }

  // 分页逻辑
  const startIndex = (currentPage - 1) * postsPerPage + 1
  const endIndex = Math.min(currentPage * postsPerPage, totalPosts)

  const togglePost = (postId: string) => {
    const newExpanded = new Set(expandedPosts)
    if (newExpanded.has(postId)) {
      newExpanded.delete(postId)
    } else {
      newExpanded.add(postId)
    }
    setExpandedPosts(newExpanded)
  }

  const toggleUser = (userId: string) => {
    const newSelected = new Set(selectedUsers)
    if (newSelected.has(userId)) {
      newSelected.delete(userId)
    } else {
      newSelected.add(userId)
    }
    setSelectedUsers(newSelected)
  }

  const selectAllInPost = (post: PostWithUsers) => {
    const postUserIds = post.interacted_users.map(u => u.user_id)
    const allSelected = postUserIds.every(id => selectedUsers.has(id))
    
    const newSelected = new Set(selectedUsers)
    if (allSelected) {
      postUserIds.forEach(id => newSelected.delete(id))
    } else {
      postUserIds.forEach(id => newSelected.add(id))
    }
    setSelectedUsers(newSelected)
  }

  const selectAllOthers = () => {
    const otherUserIds = otherUsers.map(u => u.user_id)
    const allSelected = otherUserIds.every(id => selectedUsers.has(id))
    
    const newSelected = new Set(selectedUsers)
    if (allSelected) {
      otherUserIds.forEach(id => newSelected.delete(id))
    } else {
      otherUserIds.forEach(id => newSelected.add(id))
    }
    setSelectedUsers(newSelected)
  }
  
  const selectAllUsers = async () => {
    // 从后端获取所有用户ID并选择
    if (!selectedDb) return
    
    try {
      console.log('Fetching all user IDs from:', `/api/interview/all-user-ids/${selectedDb}`)
      const response = await axios.get(`/api/interview/all-user-ids/${selectedDb}`)
      console.log('Response:', response.data)
      const allUserIds = new Set<string>(response.data.user_ids || [])
      
      // 如果当前已经全选，则取消全选
      if (selectedUsers.size === allUserIds.size) {
        setSelectedUsers(new Set())
      } else {
        setSelectedUsers(allUserIds)
      }
    } catch (error: any) {
      console.error('Failed to get all user IDs:', error)
      console.error('Error response:', error.response?.data)
      alert(`获取用户列表失败: ${error.response?.data?.error || error.message}`)
    }
  }

  const getPostUserPage = (postId: string) => {
    return postUserPages[postId] || 1
  }

  const setPostUserPage = (postId: string, page: number) => {
    setPostUserPages(prev => ({ ...prev, [postId]: page }))
  }

  const getTotalUserCount = () => {
    // 去重计算用户总数
    const uniqueUsers = new Set<string>()
    posts.forEach(post => {
      post.interacted_users.forEach(user => {
        uniqueUsers.add(user.user_id)
      })
    })
    otherUsers.forEach(user => {
      uniqueUsers.add(user.user_id)
    })
    return uniqueUsers.size
  }

  const sendInterview = async () => {
    if (!question.trim() || selectedUsers.size === 0) {
      alert('请输入问题并选择至少一个用户')
      return
    }

    setSending(true)
    
    // 创建新的历史记录（初始为空回答）
    const newHistory: InterviewHistory = {
      id: `interview_${Date.now()}`,
      question: question.trim(),
      timestamp: new Date().toLocaleString('zh-CN'),
      user_count: selectedUsers.size,
      responses: Array.from(selectedUsers).map(userId => ({
        user_id: userId,
        question: question.trim(),
        answer: '', // 初始为空，将流式填充
        timestamp: new Date().toLocaleString('zh-CN')
      }))
    }
    
    setInterviewHistory(prev => [newHistory, ...prev])
    setSelectedHistory(newHistory)
    setQuestion('')
    
    try {
      // 使用 Fetch API 接收流式数据
      const response = await fetch('/api/interview/send-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          database: selectedDb,
          user_ids: Array.from(selectedUsers),
          question: question.trim()
        })
      })

      if (!response.ok) {
        throw new Error('请求失败')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('无法读取响应流')
      }

      let currentUserId = ''
      let buffer = '' // 用于缓存不完整的数据行
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        // 解码并添加到缓冲区
        buffer += decoder.decode(value, { stream: true })
        
        // 按行分割
        const lines = buffer.split('\n')
        
        // 保留最后一个不完整的行
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'start') {
                currentUserId = data.user_id
                console.log('开始生成:', currentUserId)
              } else if (data.type === 'chunk' && currentUserId) {
                // 只更新 interviewHistory，selectedHistory 会自动同步
                setInterviewHistory(prev => {
                  const updated = prev.map(h => {
                    if (h.id === newHistory.id) {
                      return {
                        ...h,
                        responses: h.responses.map(r => 
                          r.user_id === currentUserId 
                            ? { ...r, answer: r.answer + data.content }
                            : r
                        )
                      }
                    }
                    return h
                  })
                  return updated
                })
              } else if (data.type === 'done') {
                console.log('完成生成:', currentUserId)
                currentUserId = ''
              } else if (data.type === 'complete') {
                console.log('所有回答生成完成')
              } else if (data.type === 'error') {
                console.error('生成错误:', data.error)
                alert(`生成回答时出错: ${data.error}`)
              }
            } catch (e) {
              console.error('解析数据失败:', line, e)
            }
          }
        }
      }
      
      // 更新 selectedHistory 为最终版本
      setSelectedHistory(prev => {
        if (prev && prev.id === newHistory.id) {
          const finalHistory = interviewHistory.find(h => h.id === newHistory.id)
          return finalHistory || prev
        }
        return prev
      })
      
    } catch (error: any) {
      alert(`发送失败: ${error.message}`)
      // 移除失败的历史记录
      setInterviewHistory(prev => prev.filter(h => h.id !== newHistory.id))
      setSelectedHistory(null)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-green-500 to-teal-500 flex items-center justify-center shadow-lg">
            <MessageSquare size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">采访功能</h1>
            <p className="text-slate-600">向模拟用户发送问卷问题并收集回答</p>
          </div>
        </div>
      </div>

      {/* 数据库选择 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4">
          <Database size={20} className="text-slate-600" />
          <label className="text-sm font-medium text-slate-700">选择数据库:</label>
          <select
            value={selectedDb}
            onChange={(e) => setSelectedDb(e.target.value)}
            className="px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
          >
            {databases.map((db) => (
              <option key={db} value={db}>{db}</option>
            ))}
          </select>
          <div className="ml-auto text-sm text-slate-600">
            已选择 <span className="font-bold text-green-600">{selectedUsers.size}</span> / {totalUniqueUsers} 个用户
          </div>
        </div>
      </div>

      {/* 主要内容区域 - 双栏布局 */}
      {selectedDb && (
        <div className="grid grid-cols-3 gap-6">
          {/* 左侧：采访对象选择（占2列） */}
          <div className="col-span-2 glass-card p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-800">选择采访对象</h2>
                <p className="text-sm text-slate-500 mt-1">按帖子热度组织，点击展开查看互动用户</p>
              </div>
              <button
                onClick={selectAllUsers}
                className="px-4 py-2 bg-green-700 text-white rounded-xl font-medium hover:bg-green-800 transition-all duration-200 shadow-lg"
              >
                {selectedUsers.size === totalUniqueUsers ? '取消全选' : '选择全部用户'}
              </button>
            </div>

            {loading ? (
              <div className="text-center py-12">
                <Loader2 size={48} className="mx-auto mb-4 animate-spin text-green-500" />
                <p className="text-slate-600">加载数据中...</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
                {/* 热门帖子及其互动用户 - 双栏布局 */}
                <div className="grid grid-cols-2 gap-4">
                  {posts.map((post) => {
                    const isExpanded = expandedPosts.has(post.post_id)
                    const postUserIds = post.interacted_users.map(u => u.user_id)
                    const allSelected = postUserIds.every(id => selectedUsers.has(id))
                    const someSelected = postUserIds.some(id => selectedUsers.has(id))
                    
                    // 用户分页
                    const currentUserPage = getPostUserPage(post.post_id)
                    const totalUserPages = Math.ceil(post.interacted_users.length / usersPerPage)
                    const userStartIndex = (currentUserPage - 1) * usersPerPage
                    const userEndIndex = userStartIndex + usersPerPage
                    const currentUsers = post.interacted_users.slice(userStartIndex, userEndIndex)
                    
                    return (
                      <div key={post.post_id} className="border border-slate-200 rounded-xl overflow-hidden bg-white">
                        {/* 帖子头部 - 淡绿色背景 */}
                        <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-200">
                          <div className="flex items-start gap-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <TrendingUp size={16} className="text-green-600" />
                                <span className="text-xs font-medium text-green-700">
                                  {post.total_engagement > 0 ? '热门帖子' : '帖子'}
                                </span>
                              </div>
                              {/* 只显示3行 */}
                              <p className="text-sm text-slate-700 mb-3 whitespace-pre-wrap break-words line-clamp-3">
                                {post.content}
                              </p>
                              <div className="flex items-center gap-3 text-xs text-slate-600">
                                <span className="flex items-center gap-1">
                                  <ThumbsUp size={11} />
                                  {post.num_likes}
                                </span>
                                <span className="flex items-center gap-1">
                                  <MessageCircle size={11} />
                                  {post.num_comments}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Users size={11} />
                                  {post.interacted_users.length}
                                </span>
                                <div className="ml-auto flex items-center gap-2">
                                  <button
                                    onClick={() => setSelectedPostDetail(post)}
                                    className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-green-500 text-white rounded-lg hover:from-blue-600 hover:to-green-600 font-medium transition-all shadow-md"
                                  >
                                    详情
                                  </button>
                                  {post.interacted_users.length > 0 && (
                                    <button
                                      onClick={() => togglePost(post.post_id)}
                                      className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-green-500 text-white rounded-lg hover:from-blue-600 hover:to-green-600 font-medium transition-all shadow-md flex items-center gap-1"
                                    >
                                      {isExpanded ? (
                                        <>
                                          <ChevronUp size={14} />
                                          收起
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown size={14} />
                                          查看用户
                                        </>
                                      )}
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* 互动用户列表 - 4x4分页 */}
                        {isExpanded && post.interacted_users.length > 0 && (
                          <div className="p-3 bg-slate-50">
                            <div className="grid grid-cols-4 gap-2 mb-3">
                              {currentUsers.map((user) => {
                                const isSelected = selectedUsers.has(user.user_id)
                                return (
                                  <div
                                    key={user.user_id}
                                    className={`relative p-2 rounded-lg border-2 bg-white cursor-pointer transition-all duration-200 group ${
                                      isSelected
                                        ? 'border-green-500 shadow-md'
                                        : 'border-slate-200 hover:border-slate-300'
                                    }`}
                                  >
                                    <div 
                                      onClick={() => toggleUser(user.user_id)}
                                      className="flex flex-col items-center gap-1"
                                    >
                                      <User size={16} className={isSelected ? 'text-green-600' : 'text-slate-400'} />
                                      <span className="font-mono text-xs text-slate-600 text-center truncate w-full">
                                        {user.user_id}
                                      </span>
                                    </div>
                                    {isSelected && (
                                      <CheckCircle2 size={12} className="absolute top-1 right-1 text-green-600" />
                                    )}
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setSelectedUserDetail(user)
                                      }}
                                      className="absolute top-0.5 right-0.5 p-0.5 rounded bg-green-500 text-white hover:bg-green-600 transition-all opacity-0 group-hover:opacity-100"
                                      title="查看详情"
                                    >
                                      <Info size={10} />
                                    </button>
                                  </div>
                                )
                              })}
                            </div>
                            
                            {/* 用户分页控制 */}
                            {totalUserPages > 1 && (
                              <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => selectAllInPost(post)}
                                    className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                                      allSelected
                                        ? 'bg-red-500 text-white hover:bg-red-600'
                                        : 'bg-green-600 text-white hover:bg-green-700'
                                    }`}
                                  >
                                    {allSelected ? '取消全选' : '全选本帖'}
                                  </button>
                                  <span className="text-slate-600">
                                    {userStartIndex + 1}-{Math.min(userEndIndex, post.interacted_users.length)} / {post.interacted_users.length}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => setPostUserPage(post.post_id, Math.max(1, currentUserPage - 1))}
                                    disabled={currentUserPage === 1}
                                    className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    <ChevronLeft size={14} />
                                  </button>
                                  <span className="px-2">{currentUserPage} / {totalUserPages}</span>
                                  <button
                                    onClick={() => setPostUserPage(post.post_id, Math.min(totalUserPages, currentUserPage + 1))}
                                    disabled={currentUserPage === totalUserPages}
                                    className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    <ChevronRight size={14} />
                                  </button>
                                </div>
                              </div>
                            )}
                            
                            {/* 单页时也显示全选按钮 */}
                            {totalUserPages === 1 && post.interacted_users.length > 0 && (
                              <div className="flex items-center justify-between text-xs">
                                <button
                                  onClick={() => selectAllInPost(post)}
                                  className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                                    allSelected
                                      ? 'bg-red-500 text-white hover:bg-red-600'
                                      : 'bg-green-600 text-white hover:bg-green-700'
                                  }`}
                                >
                                  {allSelected ? '取消全选' : '全选本帖'}
                                </button>
                                <span className="text-slate-600">
                                  共 {post.interacted_users.length} 个用户
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
                
                {/* 分页控制 */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                    <div className="text-sm text-slate-600">
                      显示 {startIndex}-{endIndex} / 共 {totalPosts} 个帖子
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                      >
                        <ChevronLeft size={18} />
                      </button>
                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum
                          if (totalPages <= 5) {
                            pageNum = i + 1
                          } else if (currentPage <= 3) {
                            pageNum = i + 1
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i
                          } else {
                            pageNum = currentPage - 2 + i
                          }
                          return (
                            <button
                              key={pageNum}
                              onClick={() => setCurrentPage(pageNum)}
                              className={`w-8 h-8 rounded-lg font-medium transition-all text-sm ${
                                currentPage === pageNum
                                  ? 'bg-gradient-to-r from-green-500 to-teal-500 text-white shadow-lg'
                                  : 'border border-slate-200 hover:bg-slate-50'
                              }`}
                            >
                              {pageNum}
                            </button>
                          )
                        })}
                      </div>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                      >
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  </div>
                )}

                
                {/* 其他用户（没有互动的） */}
                {otherUsers.length > 0 && (
                  <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
                    <div className="p-4 bg-gradient-to-r from-slate-50 to-slate-100 border-b border-slate-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Users size={18} className="text-slate-600" />
                          <span className="text-sm font-medium text-slate-700">其他用户</span>
                          <span className="text-xs text-slate-500">({otherUsers.length} 人)</span>
                        </div>
                        <button
                          onClick={selectAllOthers}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            otherUsers.every(u => selectedUsers.has(u.user_id))
                              ? 'bg-red-500 text-white hover:bg-red-600'
                              : 'bg-green-600 text-white hover:bg-green-700'
                          }`}
                        >
                          {otherUsers.every(u => selectedUsers.has(u.user_id)) ? '取消全选' : '全选用户'}
                        </button>
                      </div>
                    </div>
                    <div className="p-4 bg-slate-50">
                      <div className="grid grid-cols-6 gap-3 max-h-[300px] overflow-y-auto">
                        {otherUsers.map((user) => {
                          const isSelected = selectedUsers.has(user.user_id)
                          return (
                            <div
                              key={user.user_id}
                              className={`relative p-3 rounded-xl border-2 bg-white cursor-pointer transition-all duration-200 group ${
                                isSelected
                                  ? 'border-green-500 shadow-md'
                                  : 'border-slate-200 hover:border-slate-300'
                              }`}
                            >
                              <div 
                                onClick={() => toggleUser(user.user_id)}
                                className="flex flex-col items-center gap-2"
                              >
                                <User size={20} className={isSelected ? 'text-green-600' : 'text-slate-400'} />
                                <span className="font-mono text-xs text-slate-600 text-center truncate w-full px-1">
                                  {user.user_id}
                                </span>
                              </div>
                              {isSelected && (
                                <CheckCircle2 size={16} className="absolute top-2 right-2 text-green-600" />
                              )}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSelectedUserDetail(user)
                                }}
                                className="absolute top-1 right-1 p-1 rounded-lg bg-green-500 text-white hover:bg-green-600 transition-all opacity-0 group-hover:opacity-100"
                                title="查看详情"
                              >
                                <Info size={12} />
                              </button>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}
                
                {posts.length === 0 && otherUsers.length === 0 && (
                  <div className="text-center py-12 text-slate-400">
                    <User size={48} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">暂无用户数据</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 右侧：问卷发送和历史记录（占1列） */}
          <div className="col-span-1 space-y-6">
            {/* 发送问卷 */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare size={20} className="text-green-600" />
                <h2 className="text-xl font-bold text-slate-800">发送问卷</h2>
              </div>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="请输入您想问的问题..."
                className="w-full h-32 px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none mb-4 text-sm"
              />
              <div className="mb-3">
                <p className="text-sm text-slate-500">
                  将向 <span className="font-bold text-green-600">{selectedUsers.size}</span> 个用户发送
                </p>
              </div>
              <button
                onClick={sendInterview}
                disabled={sending || !question.trim() || selectedUsers.size === 0}
                className="w-full px-6 py-3 bg-gradient-to-r from-green-500 to-teal-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    发送中...
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    发送问卷
                  </>
                )}
              </button>
            </div>

            {/* 历史问答记录 */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 size={20} className="text-purple-600" />
                <h2 className="text-xl font-bold text-slate-800">历史问答</h2>
                <span className="text-sm text-slate-500">({interviewHistory.length})</span>
              </div>
              
              {interviewHistory.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <MessageSquare size={40} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm">暂无历史记录</p>
                  <p className="text-xs mt-1">发送问卷后显示</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto">
                  {interviewHistory.map((history) => (
                    <div
                      key={history.id}
                      onClick={() => setSelectedHistory(history)}
                      className={`p-3 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
                        selectedHistory?.id === history.id
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-slate-200 bg-white hover:border-purple-300 hover:bg-purple-50/50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <p className="text-sm font-medium text-slate-800 line-clamp-2 flex-1">
                          {history.question}
                        </p>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-600">
                        <span className="flex items-center gap-1">
                          <User size={11} />
                          {history.user_count} 人
                        </span>
                        <span className="text-slate-400">{history.timestamp}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 回答详情 */}
      {selectedHistory && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">问答详情</h2>
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-xl border border-purple-200">
                <p className="text-xs text-purple-600 font-medium mb-1">问题</p>
                <p className="text-sm text-slate-800">{selectedHistory.question}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedHistory(null)}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-all"
            >
              <X size={18} />
            </button>
          </div>
          
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            <p className="text-sm text-slate-600 mb-3">
              收到 <span className="font-bold text-purple-600">{selectedHistory.responses.length}</span> 个回答
            </p>
            {selectedHistory.responses.map((response, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-white to-slate-50 rounded-xl p-4 border border-slate-200 hover:border-purple-300 transition-all"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <User size={14} className="text-purple-600" />
                      <span className="font-mono text-sm text-slate-700">{response.user_id}</span>
                    </div>
                  </div>
                  <span className="text-xs text-slate-400">{response.timestamp}</span>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-teal-50 p-4 rounded-lg border border-green-200">
                  <p className="text-xs text-green-700 font-medium mb-2">回答</p>
                  <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
                    {response.answer}
                    {/* 如果回答为空或正在生成，显示光标动画 */}
                    {sending && (!response.answer || response.answer.length < 10) && (
                      <span className="inline-block w-2 h-4 bg-green-600 ml-1 animate-pulse"></span>
                    )}
                  </p>
                  {/* 正在生成提示 */}
                  {sending && response.answer && response.answer.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-green-600">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-1.5 h-1.5 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-1.5 h-1.5 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                      <span>正在生成中...</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 帖子详情弹窗 */}
      {selectedPostDetail && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedPostDetail(null)}
        >
          <div 
            className="glass-card max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between p-6 border-b border-slate-200 bg-gradient-to-r from-green-50 to-emerald-50">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-500 flex items-center justify-center shadow-lg">
                  <MessageSquare size={24} className="text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-800">帖子详情</h3>
                  <p className="text-sm text-slate-600">Post Details</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedPostDetail(null)}
                className="p-2 hover:bg-slate-100 rounded-xl transition-all"
              >
                <X size={20} className="text-slate-600" />
              </button>
            </div>
            
            {/* 内容区域 */}
            <div className="p-6 space-y-4">
              {/* 帖子内容 */}
              <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-5 border border-slate-200">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 block">
                  帖子内容
                </label>
                <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap break-words">
                  {selectedPostDetail.content}
                </p>
              </div>
              
              {/* 统计数据 */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <ThumbsUp size={16} className="text-blue-600" />
                    <label className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                      点赞数
                    </label>
                  </div>
                  <p className="text-3xl font-bold text-blue-900">
                    {selectedPostDetail.num_likes}
                  </p>
                </div>
                
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageCircle size={16} className="text-purple-600" />
                    <label className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                      评论数
                    </label>
                  </div>
                  <p className="text-3xl font-bold text-purple-900">
                    {selectedPostDetail.num_comments}
                  </p>
                </div>
                
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4 border border-orange-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Users size={16} className="text-orange-600" />
                    <label className="text-xs font-semibold text-orange-700 uppercase tracking-wide">
                      互动用户
                    </label>
                  </div>
                  <p className="text-3xl font-bold text-orange-900">
                    {selectedPostDetail.interacted_users.length}
                  </p>
                </div>
              </div>
              
              {/* 作者信息 */}
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200">
                <label className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2 block">
                  作者ID
                </label>
                <p className="font-mono text-sm text-slate-800">
                  {selectedPostDetail.author_id}
                </p>
              </div>
              
              {/* 关闭按钮 */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setSelectedPostDetail(null)}
                  className="flex-1 px-6 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 transition-all duration-200"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 用户详情弹窗 */}
      {selectedUserDetail && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedUserDetail(null)}
        >
          <div 
            className="glass-card max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg">
                  <User size={24} className="text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-800">用户详情</h3>
                  <p className="text-sm text-slate-600">User Profile</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedUserDetail(null)}
                className="p-2 hover:bg-slate-100 rounded-xl transition-all"
              >
                <X size={20} className="text-slate-600" />
              </button>
            </div>
            
            {/* 内容区域 */}
            <div className="p-6 space-y-4">
              {/* 用户ID */}
              <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-4 border border-slate-200">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">
                  用户ID
                </label>
                <p className="font-mono text-base text-slate-800 break-all">
                  {selectedUserDetail.user_id}
                </p>
              </div>
              
              {/* 统计数据 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                    <label className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                      影响力分数
                    </label>
                  </div>
                  <p className="text-3xl font-bold text-purple-900">
                    {selectedUserDetail.influence_score?.toFixed(3) || '0.000'}
                  </p>
                </div>
                
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4 border border-orange-200">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                    <label className="text-xs font-semibold text-orange-700 uppercase tracking-wide">
                      粉丝数量
                    </label>
                  </div>
                  <p className="text-3xl font-bold text-orange-900">
                    {selectedUserDetail.follower_count || 0}
                  </p>
                </div>
              </div>
              
              {/* 角色描述 */}
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-5 border border-blue-200">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <label className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                    角色描述
                  </label>
                </div>
                <div className="space-y-2 text-sm">
                  {(() => {
                    try {
                      let personaObj;
                      
                      if (typeof selectedUserDetail.persona === 'string') {
                        try {
                          personaObj = JSON.parse(selectedUserDetail.persona);
                        } catch {
                          const fixedStr = selectedUserDetail.persona
                            .replace(/'/g, '"')
                            .replace(/None/g, 'null')
                            .replace(/True/g, 'true')
                            .replace(/False/g, 'false');
                          personaObj = JSON.parse(fixedStr);
                        }
                      } else {
                        personaObj = selectedUserDetail.persona;
                      }
                      
                      const fieldLabels: Record<string, string> = {
                        'id': 'ID',
                        'type': '类型',
                        'name': '姓名',
                        'profession': '职业',
                        'age': '年龄',
                        'region': '地区',
                        'demographics': '人口统计',
                        'background': '背景',
                        'personality_traits': '性格特征',
                        'tone': '语气',
                        'communication_style': '沟通风格',
                        'engagement_level': '参与度'
                      };
                      
                      const fieldOrder = ['id', 'type', 'name', 'profession', 'age', 'region', 'demographics', 'background', 'personality_traits', 'communication_style', 'tone', 'engagement_level'];
                      
                      return (
                        <div className="space-y-2.5">
                          {fieldOrder.map(key => {
                            if (personaObj[key] !== undefined && personaObj[key] !== null) {
                              let value = personaObj[key];
                              
                              if (Array.isArray(value)) {
                                value = value.join(', ');
                              } else if (typeof value === 'object') {
                                if (key === 'demographics') {
                                  const parts = [];
                                  if (value.age) parts.push(`年龄: ${value.age}`);
                                  if (value.region) parts.push(`地区: ${value.region}`);
                                  value = parts.join(', ');
                                } else if (key === 'communication_style') {
                                  const parts = [];
                                  if (value.tone) parts.push(`语气: ${value.tone}`);
                                  if (value.engagement_level) parts.push(`参与度: ${value.engagement_level}`);
                                  value = parts.join(', ');
                                } else {
                                  value = Object.entries(value)
                                    .map(([k, v]) => `${k}: ${v}`)
                                    .join(', ');
                                }
                              }
                              
                              return (
                                <div key={key} className="flex gap-3">
                                  <span className="text-slate-500 font-mono text-xs min-w-[120px] flex-shrink-0 pt-0.5">
                                    {fieldLabels[key] || key}:
                                  </span>
                                  <span className="text-slate-700 flex-1 break-words leading-relaxed">
                                    {String(value)}
                                  </span>
                                </div>
                              );
                            }
                            return null;
                          })}
                          {Object.keys(personaObj).filter(key => !fieldOrder.includes(key)).map(key => {
                            let value = personaObj[key];
                            
                            if (Array.isArray(value)) {
                              value = value.join(', ');
                            } else if (typeof value === 'object') {
                              value = JSON.stringify(value);
                            }
                            
                            return (
                              <div key={key} className="flex gap-3">
                                <span className="text-slate-500 font-mono text-xs min-w-[120px] flex-shrink-0 pt-0.5">
                                  {fieldLabels[key] || key}:
                                </span>
                                <span className="text-slate-700 flex-1 break-words leading-relaxed">
                                  {String(value)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      );
                    } catch (e) {
                      console.error('Failed to parse persona:', e);
                      return (
                        <div className="text-slate-700 leading-relaxed whitespace-pre-wrap break-words font-mono text-xs">
                          {selectedUserDetail.persona}
                        </div>
                      );
                    }
                  })()}
                </div>
              </div>
              
              {/* 操作按钮 */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    toggleUser(selectedUserDetail.user_id)
                    setSelectedUserDetail(null)
                  }}
                  className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 ${
                    selectedUsers.has(selectedUserDetail.user_id)
                      ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white'
                      : 'bg-gradient-to-r from-blue-500 to-green-500 text-white'
                  }`}
                >
                  {selectedUsers.has(selectedUserDetail.user_id) ? '取消选择' : '选择此用户'}
                </button>
                <button
                  onClick={() => setSelectedUserDetail(null)}
                  className="px-6 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 transition-all duration-200"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
