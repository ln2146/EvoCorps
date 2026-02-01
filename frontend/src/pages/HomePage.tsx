import { useState, useEffect } from 'react'
import { Users, MessageSquare, ThumbsUp, FileText, Activity, TrendingUp, Zap } from 'lucide-react'
import { getDatabases, getDatabaseStats, DatabaseStats } from '../services/api'
import DatabaseSelector from '../components/DatabaseSelector'

export default function HomePage() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [stats, setStats] = useState<DatabaseStats>({
    activeUsers: 0,
    totalPosts: 0,
    totalComments: 0,
    totalLikes: 0,
  })
  const [loading, setLoading] = useState(false)

  // 加载数据库列表
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

  // 加载统计数据
  useEffect(() => {
    if (selectedDb) {
      const loadStats = async () => {
        setLoading(true)
        const data = await getDatabaseStats(selectedDb)
        setStats(data)
        setLoading(false)
      }
      loadStats()
    }
  }, [selectedDb])

  const statsCards = [
    { label: '活跃用户', value: stats.activeUsers, icon: Users, color: 'from-blue-500 to-cyan-500' },
    { label: '发布内容', value: stats.totalPosts, icon: FileText, color: 'from-purple-500 to-blue-500' },
    { label: '用户评论', value: stats.totalComments, icon: MessageSquare, color: 'from-cyan-500 to-green-500' },
    { label: '互动点赞', value: stats.totalLikes, icon: ThumbsUp, color: 'from-green-500 to-emerald-500' },
  ]

  const features = [
    {
      title: '实时监控',
      description: '7x24小时监控网络舆论动态，及时发现极端内容',
      icon: Activity,
      gradient: 'from-blue-500 to-cyan-500',
    },
    {
      title: '智能干预',
      description: '基于AI的多智能体协同干预，降低情绪对立',
      icon: Zap,
      gradient: 'from-purple-500 to-blue-500',
    },
    {
      title: '效果评估',
      description: '实时评估干预效果，动态调整策略',
      icon: TrendingUp,
      gradient: 'from-cyan-500 to-green-500',
    },
    {
      title: '关系图谱',
      description: '直观展示舆论走势和系统运行状态',
      icon: MessageSquare,
      gradient: 'from-green-500 to-emerald-500',
    },
  ]

  return (
    <div className="space-y-8">
      {/* 欢迎区域 */}
      <div className="glass-card p-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
              欢迎使用 EvoCorps
            </h1>
            <p className="text-slate-600 text-lg">
              面向网络舆论去极化的进化式多智能体框架
            </p>
          </div>
          <img 
            src="/logot.png" 
            alt="EvoCorps Icon" 
            className="h-24 w-auto drop-shadow-xl"
          />
        </div>
      </div>

      {/* 数据库选择 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4">
          <DatabaseSelector
            databases={databases}
            selectedDb={selectedDb}
            onSelect={setSelectedDb}
            label="选择数据库："
          />
          {loading && <span className="text-sm text-slate-500">加载中...</span>}
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className="glass-card p-6 hover:scale-105 transition-transform duration-200">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-r ${stat.color} flex items-center justify-center shadow-lg`}>
                  <Icon size={24} className="text-white" />
                </div>
              </div>
              <p className="text-3xl font-bold text-slate-800 mb-1">{stat.value.toLocaleString()}</p>
              <p className="text-sm text-slate-600">{stat.label}</p>
            </div>
          )
        })}
      </div>

      {/* 功能特性 */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800 mb-6">核心功能</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div key={index} className="glass-card p-6 hover:scale-105 transition-transform duration-200">
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-r ${feature.gradient} flex items-center justify-center shadow-lg mb-4`}>
                  <Icon size={28} className="text-white" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800 mb-2">{feature.title}</h3>
                <p className="text-slate-600">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
