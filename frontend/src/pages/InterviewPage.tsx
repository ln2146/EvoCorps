import { useState, useEffect } from 'react'
import { Database, MessageSquare, Send, CheckCircle2, User, Loader2, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import axios from 'axios'

interface UserInfo {
  user_id: string
  persona: string
  influence_score: number
  follower_count: number
}

interface InterviewResponse {
  user_id: string
  question: string
  answer: string
  timestamp: string
}

export default function InterviewPage() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [users, setUsers] = useState<UserInfo[]>([])
  const [filteredUsers, setFilteredUsers] = useState<UserInfo[]>([])
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())
  const [question, setQuestion] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [responses, setResponses] = useState<InterviewResponse[]>([])
  
  // 搜索和分页
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const usersPerPage = 12

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

  // 加载用户列表
  useEffect(() => {
    if (selectedDb) {
      loadUsers()
    }
  }, [selectedDb])

  // 搜索过滤
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredUsers(users)
    } else {
      const query = searchQuery.toLowerCase()
      const filtered = users.filter(user => 
        user.user_id.toLowerCase().includes(query) ||
        user.persona.toLowerCase().includes(query)
      )
      setFilteredUsers(filtered)
    }
    setCurrentPage(1) // 重置到第一页
  }, [searchQuery, users])

  const loadUsers = async () => {
    if (!selectedDb) return
    
    setLoading(true)
    try {
      // 获取所有用户，不限制数量
      const response = await axios.get(`/api/interview/users/${selectedDb}`)
      setUsers(response.data.users || [])
      setFilteredUsers(response.data.users || [])
      setSelectedUsers(new Set())
      setResponses([])
      setSearchQuery('')
      setCurrentPage(1)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
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

  const selectAll = () => {
    if (selectedUsers.size === filteredUsers.length) {
      setSelectedUsers(new Set())
    } else {
      setSelectedUsers(new Set(filteredUsers.map(u => u.user_id)))
    }
  }

  // 分页逻辑
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage)
  const startIndex = (currentPage - 1) * usersPerPage
  const endIndex = startIndex + usersPerPage
  const currentUsers = filteredUsers.slice(startIndex, endIndex)

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }

  const sendInterview = async () => {
    if (!question.trim() || selectedUsers.size === 0) {
      alert('请输入问题并选择至少一个用户')
      return
    }

    setSending(true)
    try {
      const response = await axios.post('/api/interview/send', {
        database: selectedDb,
        user_ids: Array.from(selectedUsers),
        question: question.trim()
      })
      
      setResponses(response.data.responses || [])
      alert(`成功收到 ${response.data.responses.length} 个回答！`)
    } catch (error: any) {
      alert(`发送失败: ${error.response?.data?.error || error.message}`)
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
            已选择 <span className="font-bold text-green-600">{selectedUsers.size}</span> / {filteredUsers.length} 个用户
            {searchQuery && ` (共 ${users.length} 个用户)`}
          </div>
        </div>
      </div>

      {/* 用户列表 */}
      {selectedDb && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-800">选择采访对象</h2>
            <div className="flex items-center gap-3">
              {/* 搜索框 */}
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索用户ID或角色..."
                  className="pl-10 pr-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-green-500 w-64"
                />
              </div>
              <button
                onClick={selectAll}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
              >
                {selectedUsers.size === filteredUsers.length && filteredUsers.length > 0 ? '取消全选' : '全选当前页'}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <Loader2 size={48} className="mx-auto mb-4 animate-spin text-green-500" />
              <p className="text-slate-600">加载用户中...</p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <User size={48} className="mx-auto mb-4 opacity-30 text-slate-400" />
              <p className="text-slate-600">
                {searchQuery ? '未找到匹配的用户' : '暂无用户数据'}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {currentUsers.map((user) => {
                const isSelected = selectedUsers.has(user.user_id)
                return (
                  <div
                    key={user.user_id}
                    onClick={() => toggleUser(user.user_id)}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
                      isSelected
                        ? 'border-green-500 bg-gradient-to-br from-green-50 to-teal-50 shadow-lg'
                        : 'border-slate-200 bg-white hover:border-green-300 hover:shadow-md'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <User size={16} className={isSelected ? 'text-green-600' : 'text-slate-400'} />
                        <span className="font-mono text-xs text-slate-600 truncate max-w-[150px]">
                          {user.user_id}
                        </span>
                      </div>
                      {isSelected && (
                        <CheckCircle2 size={20} className="text-green-600 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-sm text-slate-700 mb-2 line-clamp-2">{user.persona}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>影响力: {user.influence_score?.toFixed(3) || '0.000'}</span>
                      <span>粉丝: {user.follower_count || 0}</span>
                    </div>
                  </div>
                )
              })}
              </div>
              
              {/* 分页控制 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                  <div className="text-sm text-slate-600">
                    显示 {startIndex + 1}-{Math.min(endIndex, filteredUsers.length)} / 共 {filteredUsers.length} 个用户
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => goToPage(currentPage - 1)}
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
                            onClick={() => goToPage(pageNum)}
                            className={`w-8 h-8 rounded-lg font-medium transition-all ${
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
                      onClick={() => goToPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      <ChevronRight size={18} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 问题输入 */}
      {selectedDb && filteredUsers.length > 0 && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-4">问卷问题</h2>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="请输入您想问的问题..."
            className="w-full h-32 px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
          />
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-slate-500">
              将向 {selectedUsers.size} 个用户发送此问题
            </p>
            <button
              onClick={sendInterview}
              disabled={sending || !question.trim() || selectedUsers.size === 0}
              className="px-6 py-3 bg-gradient-to-r from-green-500 to-teal-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
        </div>
      )}

      {/* 回答结果 */}
      {responses.length > 0 && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-4">
            收到的回答 ({responses.length})
          </h2>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {responses.map((response, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-white to-slate-50 rounded-xl p-4 border border-slate-200"
              >
                <div className="flex items-center gap-2 mb-2">
                  <User size={16} className="text-green-600" />
                  <span className="font-mono text-sm text-slate-600">{response.user_id}</span>
                  <span className="text-xs text-slate-400 ml-auto">{response.timestamp}</span>
                </div>
                <div className="bg-blue-50 p-3 rounded-lg mb-2">
                  <p className="text-xs text-slate-500 mb-1">问题:</p>
                  <p className="text-sm text-slate-700">{response.question}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">回答:</p>
                  <p className="text-sm text-slate-800">{response.answer}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
