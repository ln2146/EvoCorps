import { useState, useEffect } from 'react'
import { Activity, User as UserIcon, FileText, Search } from 'lucide-react'
import { getDatabases, getUsers, getUserDetail, User, UserDetail, getPosts, getPostDetail, Post, PostDetail } from '../services/api'
import DatabaseSelector from '../components/DatabaseSelector'

// 分页组件
function Pagination({ currentPage, totalPages, onPageChange }: { currentPage: number; totalPages: number; onPageChange: (page: number) => void }) {
  const pages = []
  const maxVisible = 5
  
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2))
  let endPage = Math.min(totalPages, startPage + maxVisible - 1)
  
  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1)
  }
  
  for (let i = startPage; i <= endPage; i++) {
    pages.push(i)
  }
  
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
      >
        上一页
      </button>
      {startPage > 1 && (
        <>
          <button onClick={() => onPageChange(1)} className="px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50">1</button>
          {startPage > 2 && <span className="text-slate-400">...</span>}
        </>
      )}
      {pages.map(page => (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          className={`px-3 py-1 rounded-lg ${
            page === currentPage
              ? 'bg-blue-500 text-white'
              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
          }`}
        >
          {page}
        </button>
      ))}
      {endPage < totalPages && (
        <>
          {endPage < totalPages - 1 && <span className="text-slate-400">...</span>}
          <button onClick={() => onPageChange(totalPages)} className="px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50">{totalPages}</button>
        </>
      )}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
      >
        下一页
      </button>
    </div>
  )
}

function PersonaDisplay({ persona }: { persona: string }) {
  try {
    // 将Python字典格式转换为JSON格式
    let personaStr = persona.replace(/'/g, '"').replace(/None/g, 'null').replace(/True/g, 'true').replace(/False/g, 'false')
    const personaObj = JSON.parse(personaStr)
    
    // 扁平化处理嵌套对象
    const flattenObj: Record<string, any> = {}
    
    Object.entries(personaObj).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        // 如果是嵌套对象，展开它
        Object.entries(value).forEach(([subKey, subValue]) => {
          flattenObj[subKey] = subValue
        })
      } else {
        flattenObj[key] = value
      }
    })

    return (
      <div className="space-y-3">
        {Object.entries(flattenObj).map(([key, value]) => (
          <div key={key} className="flex gap-3">
            <span className="text-sm text-slate-600 font-mono min-w-40 flex-shrink-0">{key}:</span>
            <span className="text-sm text-slate-800 break-words">{Array.isArray(value) ? value.join(', ') : String(value)}</span>
          </div>
        ))}
      </div>
    )
  } catch (e) {
    return <p className="text-sm text-slate-800">{persona}</p>
  }
}

export default function DataMonitoring() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [viewType, setViewType] = useState<'user' | 'post'>('user')
  const [users, setUsers] = useState<User[]>([])
  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [userDetail, setUserDetail] = useState<UserDetail | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [selectedPostId, setSelectedPostId] = useState<string>('')
  const [postDetail, setPostDetail] = useState<PostDetail | null>(null)
  const [activeTab, setActiveTab] = useState<'following' | 'followers' | 'comments' | 'posts'>('following')
  const [postActiveTab, setPostActiveTab] = useState<'likes' | 'comments' | 'shares'>('comments')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [loading, setLoading] = useState(false)
  
  const ITEMS_PER_PAGE = 25

  // 搜索和分页辅助函数
  const filterAndPaginate = (items: any[], searchFields: string[]) => {
    // 搜索过滤
    const filtered = items.filter(item => {
      if (!searchTerm) return true
      return searchFields.some(field => 
        String(item[field] || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    })
    
    // 分页
    const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE)
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
    const endIndex = startIndex + ITEMS_PER_PAGE
    const paginatedItems = filtered.slice(startIndex, endIndex)
    
    return { items: paginatedItems, total: filtered.length, totalPages }
  }

  // 重置分页当切换标签或搜索时
  useEffect(() => {
    setCurrentPage(1)
  }, [activeTab, postActiveTab, searchTerm])

  useEffect(() => {
    const loadDatabases = async () => {
      const dbs = await getDatabases()
      setDatabases(dbs)
      if (dbs.length > 0) {
        setSelectedDb(dbs[0])
      }
    }
    loadDatabases()
  }, [])

  useEffect(() => {
    if (selectedDb && viewType === 'user') {
      const loadUsers = async () => {
        setLoading(true)
        const userList = await getUsers(selectedDb)
        setUsers(userList)
        if (userList.length > 0) {
          setSelectedUserId(userList[0].user_id)
        }
        setLoading(false)
      }
      loadUsers()
    } else if (selectedDb && viewType === 'post') {
      const loadPosts = async () => {
        setLoading(true)
        const postList = await getPosts(selectedDb)
        setPosts(postList)
        if (postList.length > 0) {
          setSelectedPostId(postList[0].post_id)
        }
        setLoading(false)
      }
      loadPosts()
    }
  }, [selectedDb, viewType])

  useEffect(() => {
    if (selectedDb && selectedUserId) {
      const loadUserDetail = async () => {
        setLoading(true)
        const detail = await getUserDetail(selectedDb, selectedUserId)
        setUserDetail(detail)
        setLoading(false)
      }
      loadUserDetail()
    }
  }, [selectedDb, selectedUserId])

  useEffect(() => {
    if (selectedDb && selectedPostId) {
      const loadPostDetail = async () => {
        setLoading(true)
        const detail = await getPostDetail(selectedDb, selectedPostId)
        console.log('Post detail loaded:', detail)
        setPostDetail(detail)
        setLoading(false)
      }
      loadPostDetail()
    }
  }, [selectedDb, selectedPostId])

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
            <Activity size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-slate-800">数据监控</h1>
            <p className="text-lg text-slate-600">查看用户和帖子的详细信息</p>
          </div>
        </div>
      </div>

      <div className="glass-card p-6">
        <div className="flex items-center gap-4">
          <DatabaseSelector
            databases={databases}
            selectedDb={selectedDb}
            onSelect={setSelectedDb}
            label="选择数据库："
          />

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-slate-700">查看：</label>
            <div className="flex gap-2">
              <button
                onClick={() => setViewType('user')}
                className={`px-4 py-2 rounded-xl font-medium transition-all ${
                  viewType === 'user'
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                    : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                <UserIcon size={16} className="inline mr-2" />
                用户
              </button>
              <button
                onClick={() => setViewType('post')}
                className={`px-4 py-2 rounded-xl font-medium transition-all ${
                  viewType === 'post'
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                    : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                <FileText size={16} className="inline mr-2" />
                帖子
              </button>
            </div>
          </div>

          {loading && <span className="text-sm text-slate-500">加载中...</span>}
        </div>
      </div>

      {viewType === 'user' && (
        <div className="glass-card p-6">
          <h2 className="text-lg font-bold text-slate-800 mb-4">用户详情查看</h2>
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700">选择用户ID：</label>
            <select 
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
            >
              <option value="">请选择用户</option>
              {users.map((user) => (
                <option key={user.user_id} value={user.user_id}>
                  {user.user_id} (影响力: {user.influence_score.toFixed(2)})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {viewType === 'user' && selectedUserId && userDetail && (
        <>
          <div className="glass-card p-6">
            <h2 className="text-2xl font-bold text-slate-800 mb-4">基本信息</h2>
            <div className="space-y-4">
              <div className="p-4 bg-white/50 rounded-xl">
                <p className="text-base text-slate-600 mb-3">用户人设</p>
                <PersonaDisplay persona={userDetail.basic_info.persona} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-white/50 rounded-xl">
                  <p className="text-base text-slate-600 mb-2">创建时间</p>
                  <p className="text-lg text-slate-800">{new Date(userDetail.basic_info.creation_time).toLocaleString('zh-CN')}</p>
                </div>
                <div className="p-4 bg-white/50 rounded-xl">
                  <p className="text-base text-slate-600 mb-2">影响力分数</p>
                  <p className="text-3xl font-bold text-slate-800">{userDetail.basic_info.influence_score.toFixed(2)}</p>
                  {userDetail.basic_info.is_influencer && (
                    <span className="inline-block mt-2 px-2 py-1 bg-orange-100 text-orange-600 text-sm rounded-lg font-medium">影响者</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-2xl font-bold text-slate-800 mb-4">活动统计</h2>
            <div className="grid grid-cols-5 gap-4">
              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-600 to-blue-400 text-white">
                <p className="text-4xl font-bold mb-1">{userDetail.activity_stats.post_count}</p>
                <p className="text-base opacity-90">发帖数</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 text-white">
                <p className="text-4xl font-bold mb-1">{userDetail.activity_stats.comment_count}</p>
                <p className="text-base opacity-90">评论数</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500 to-teal-500 text-white">
                <p className="text-4xl font-bold mb-1">{userDetail.activity_stats.follower_count}</p>
                <p className="text-base opacity-90">粉丝数</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-teal-500 to-green-500 text-white">
                <p className="text-4xl font-bold mb-1">{userDetail.activity_stats.likes_received}</p>
                <p className="text-base opacity-90">获赞数</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 text-white">
                <p className="text-4xl font-bold mb-1">{userDetail.activity_stats.avg_engagement.toFixed(1)}</p>
                <p className="text-base opacity-90">平均互动</p>
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <div className="flex gap-2 mb-6 border-b border-slate-200">
              <button
                onClick={() => setActiveTab('following')}
                className={`px-6 py-3 font-medium transition-all ${
                  activeTab === 'following' 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                关注列表
              </button>
              <button
                onClick={() => setActiveTab('followers')}
                className={`px-6 py-3 font-medium transition-all ${
                  activeTab === 'followers' 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                粉丝列表
              </button>
              <button
                onClick={() => setActiveTab('posts')}
                className={`px-6 py-3 font-medium transition-all ${
                  activeTab === 'posts' 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                发布帖子
              </button>
              <button
                onClick={() => setActiveTab('comments')}
                className={`px-6 py-3 font-medium transition-all ${
                  activeTab === 'comments' 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                发布评论
              </button>
            </div>

            <div className="mb-4">
              <div className="relative">
                <Search size={20} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="搜索..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {activeTab === 'following' && (() => {
                const { items, total, totalPages } = filterAndPaginate(userDetail.following, ['user_id'])
                return (
                  <div className="space-y-2">
                    <p className="text-sm text-slate-600 mb-3">共 {total} 人 {searchTerm && `(搜索结果)`}</p>
                    {items.length === 0 ? (
                      <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无关注'}</p>
                    ) : (
                      <>
                        {items.map((follow, index) => (
                          <div key={index} className="flex items-center justify-between p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-blue-500">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold">
                                {follow.user_id.slice(-2)}
                              </div>
                              <span className="font-medium text-slate-800">{follow.user_id}</span>
                            </div>
                            <span className="text-sm text-slate-500">{new Date(follow.followed_at).toLocaleString('zh-CN')}</span>
                          </div>
                        ))}
                        {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                      </>
                    )}
                  </div>
                )
              })()}

              {activeTab === 'followers' && (() => {
                const { items, total, totalPages } = filterAndPaginate(userDetail.followers, ['user_id'])
                return (
                  <div className="space-y-2">
                    <p className="text-sm text-slate-600 mb-3">共 {total} 位粉丝 {searchTerm && `(搜索结果)`}</p>
                    {items.length === 0 ? (
                      <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无粉丝'}</p>
                    ) : (
                      <>
                        {items.map((follower, index) => (
                          <div key={index} className="flex items-center justify-between p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-green-500">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center text-white font-bold">
                                {follower.user_id.slice(-2)}
                              </div>
                              <span className="font-medium text-slate-800">{follower.user_id}</span>
                            </div>
                            <span className="text-sm text-slate-500">{new Date(follower.followed_at).toLocaleString('zh-CN')}</span>
                          </div>
                        ))}
                        {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                      </>
                    )}
                  </div>
                )
              })()}

              {activeTab === 'posts' && (() => {
                const { items, total, totalPages } = filterAndPaginate(userDetail.posts, ['content', 'post_id'])
                return (
                  <div className="space-y-3">
                    <p className="text-sm text-slate-600 mb-3">共 {total} 篇帖子 {searchTerm && `(搜索结果)`}</p>
                    {items.length === 0 ? (
                      <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无帖子'}</p>
                    ) : (
                      <>
                        {items.map((post: any) => (
                          <div key={post.post_id} className="p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-orange-500">
                            <div className="flex items-start justify-between mb-2">
                              <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded font-mono">ID: {post.post_id}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-slate-500 bg-red-50 px-2 py-1 rounded">❤️ {post.num_likes}</span>
                                <span className="text-xs text-slate-500 bg-blue-50 px-2 py-1 rounded">💬 {post.num_comments}</span>
                                <span className="text-xs text-slate-500 bg-green-50 px-2 py-1 rounded">🔄 {post.num_shares}</span>
                                <span className="text-xs text-slate-500">{new Date(post.created_at).toLocaleString('zh-CN')}</span>
                              </div>
                            </div>
                            <p className="text-slate-700 leading-relaxed">{post.content}</p>
                          </div>
                        ))}
                        {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                      </>
                    )}
                  </div>
                )
              })()}

              {activeTab === 'comments' && (() => {
                const { items, total, totalPages } = filterAndPaginate(userDetail.comments, ['content', 'post_id'])
                return (
                  <div className="space-y-3">
                    <p className="text-sm text-slate-600 mb-3">共 {total} 条评论 {searchTerm && `(搜索结果)`}</p>
                    {items.length === 0 ? (
                      <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无评论'}</p>
                    ) : (
                      <>
                        {items.map((comment) => (
                          <div key={comment.comment_id} className="p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-purple-500">
                            <div className="flex items-start justify-between mb-2">
                              <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded font-mono">Post: {comment.post_id}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-slate-500 bg-red-50 px-2 py-1 rounded">❤️ {comment.num_likes}</span>
                                <span className="text-xs text-slate-500">{new Date(comment.created_at).toLocaleString('zh-CN')}</span>
                              </div>
                            </div>
                            <p className="text-slate-700 leading-relaxed">{comment.content}</p>
                          </div>
                        ))}
                        {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                      </>
                    )}
                  </div>
                )
              })()}
            </div>
          </div>
        </>
      )}

      {viewType === 'post' && (
        <>
          <div className="glass-card p-6">
            <h2 className="text-lg font-bold text-slate-800 mb-4">帖子详情查看</h2>
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-slate-700">选择帖子ID：</label>
              <select 
                value={selectedPostId}
                onChange={(e) => setSelectedPostId(e.target.value)}
                className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              >
                <option value="">请选择帖子</option>
                {posts.map((post) => (
                  <option key={post.post_id} value={post.post_id}>
                    {post.post_id} (互动: {post.total_engagement})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedPostId && postDetail && (
            <>
              <div className="glass-card p-6">
                <h2 className="text-xl font-bold text-slate-800 mb-4">基本信息</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-white/50 rounded-xl">
                    <p className="text-sm text-slate-600 mb-2">帖子ID</p>
                    <p className="text-slate-800 font-mono">{postDetail.basic_info.post_id}</p>
                  </div>
                  <div className="p-4 bg-white/50 rounded-xl">
                    <p className="text-sm text-slate-600 mb-2">作者ID</p>
                    <p className="text-slate-800 font-mono">{postDetail.basic_info.author_id}</p>
                  </div>
                  <div className="p-4 bg-white/50 rounded-xl">
                    <p className="text-sm text-slate-600 mb-2">主题</p>
                    <p className="text-slate-800">{postDetail.basic_info.topic}</p>
                  </div>
                  <div className="p-4 bg-white/50 rounded-xl">
                    <p className="text-sm text-slate-600 mb-2">发布时间</p>
                    <p className="text-slate-800">{new Date(postDetail.basic_info.created_at).toLocaleString('zh-CN')}</p>
                  </div>
                  <div className="col-span-2 p-4 bg-white/50 rounded-xl">
                    <p className="text-sm text-slate-600 mb-2">内容</p>
                    <p className="text-slate-800 leading-relaxed">{postDetail.basic_info.content}</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <h2 className="text-xl font-bold text-slate-800 mb-4">互动统计</h2>
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-gradient-to-br from-blue-600 to-blue-400 text-white">
                    <p className="text-3xl font-bold mb-1">{postDetail.engagement_stats.num_likes}</p>
                    <p className="text-sm opacity-90">点赞数</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500 to-teal-500 text-white">
                    <p className="text-3xl font-bold mb-1">{postDetail.engagement_stats.num_comments}</p>
                    <p className="text-sm opacity-90">评论数</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-teal-500 to-green-500 text-white">
                    <p className="text-3xl font-bold mb-1">{postDetail.engagement_stats.num_shares}</p>
                    <p className="text-sm opacity-90">分享数</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 text-white">
                    <p className="text-3xl font-bold mb-1">{postDetail.engagement_stats.total_engagement}</p>
                    <p className="text-sm opacity-90">总互动</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex gap-2 mb-6 border-b border-slate-200">
                  <button
                    onClick={() => setPostActiveTab('likes')}
                    className={`px-6 py-3 font-medium transition-all ${
                      postActiveTab === 'likes' 
                        ? 'text-blue-600 border-b-2 border-blue-600' 
                        : 'text-slate-600 hover:text-slate-800'
                    }`}
                  >
                    点赞列表
                  </button>
                  <button
                    onClick={() => setPostActiveTab('comments')}
                    className={`px-6 py-3 font-medium transition-all ${
                      postActiveTab === 'comments' 
                        ? 'text-blue-600 border-b-2 border-blue-600' 
                        : 'text-slate-600 hover:text-slate-800'
                    }`}
                  >
                    评论列表
                  </button>
                  <button
                    onClick={() => setPostActiveTab('shares')}
                    className={`px-6 py-3 font-medium transition-all ${
                      postActiveTab === 'shares' 
                        ? 'text-blue-600 border-b-2 border-blue-600' 
                        : 'text-slate-600 hover:text-slate-800'
                    }`}
                  >
                    分享列表
                  </button>
                </div>

                <div className="mb-4">
                  <div className="relative">
                    <Search size={20} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      placeholder="搜索..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="max-h-96 overflow-y-auto space-y-3">
                  {postActiveTab === 'likes' && (() => {
                    const { items, total, totalPages } = filterAndPaginate(postDetail.likes || [], ['user_id'])
                    return (
                      <div className="space-y-2">
                        <p className="text-sm text-slate-600 mb-3">共 {total} 个点赞 {searchTerm && `(搜索结果)`}</p>
                        {items.length === 0 ? (
                          <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无点赞'}</p>
                        ) : (
                          <>
                            {items.map((like: any, index: number) => (
                              <div key={index} className="flex items-center justify-between p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-red-500">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center text-white font-bold">
                                    {like.user_id.slice(-2)}
                                  </div>
                                  <span className="font-medium text-slate-800">{like.user_id}</span>
                                </div>
                                <span className="text-sm text-slate-500">{new Date(like.created_at).toLocaleString('zh-CN')}</span>
                              </div>
                            ))}
                            {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                          </>
                        )}
                      </div>
                    )
                  })()}

                  {postActiveTab === 'comments' && (() => {
                    const { items, total, totalPages } = filterAndPaginate(postDetail.comments, ['content', 'author_id'])
                    return (
                      <div className="space-y-3">
                        <p className="text-sm text-slate-600 mb-3">共 {total} 条评论 {searchTerm && `(搜索结果)`}</p>
                        {items.length === 0 ? (
                          <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无评论'}</p>
                        ) : (
                          <>
                            {items.map((comment: any) => (
                              <div key={comment.comment_id} className="p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-blue-500">
                                <div className="flex items-start justify-between mb-2">
                                  <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded font-mono">作者: {comment.author_id}</span>
                                  <div className="flex items-center gap-3">
                                    <span className="text-xs text-slate-500">Likes: {comment.num_likes}</span>
                                    <span className="text-xs text-slate-500">{new Date(comment.created_at).toLocaleString('zh-CN')}</span>
                                  </div>
                                </div>
                                <p className="text-slate-700 leading-relaxed">{comment.content}</p>
                              </div>
                            ))}
                            {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                          </>
                        )}
                      </div>
                    )
                  })()}

                  {postActiveTab === 'shares' && (() => {
                    const { items, total, totalPages } = filterAndPaginate(postDetail.shares || [], ['user_id'])
                    return (
                      <div className="space-y-2">
                        <p className="text-sm text-slate-600 mb-3">共 {total} 次分享 {searchTerm && `(搜索结果)`}</p>
                        {items.length === 0 ? (
                          <p className="text-slate-500 text-center py-8">{searchTerm ? '无搜索结果' : '暂无分享'}</p>
                        ) : (
                          <>
                            {items.map((share: any, index: number) => (
                              <div key={index} className="flex items-center justify-between p-4 bg-white/50 rounded-xl hover:bg-white/70 transition-colors border-l-4 border-green-500">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center text-white font-bold">
                                    {share.user_id.slice(-2)}
                                  </div>
                                  <span className="font-medium text-slate-800">{share.user_id}</span>
                                </div>
                                <span className="text-sm text-slate-500">{new Date(share.created_at).toLocaleString('zh-CN')}</span>
                              </div>
                            ))}
                            {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />}
                          </>
                        )}
                      </div>
                    )
                  })()}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
