import { useState, useEffect } from 'react'
import { Layers } from 'lucide-react'
import DatabaseSelector from '../components/DatabaseSelector'
import {
  getDatabases,
  getFilterBubbleGlobalStats,
  getAllUsersBubbleMetrics,
  getUserBubbleMetrics,
  FilterBubbleGlobalStats,
  FilterBubbleUserMetrics,
} from '../services/api'

// 严重程度颜色映射
const severityColors = {
  none: 'bg-green-100 text-green-700 border-green-300',
  mild: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  moderate: 'bg-orange-100 text-orange-700 border-orange-300',
  severe: 'bg-red-100 text-red-700 border-red-300'
}

const severityLabels = {
  none: '无茧房',
  mild: '轻度',
  moderate: '中度',
  severe: '严重'
}

// 仪表盘组件
function MetricGauge({ value, label, color }: { value: number; label: string; color: string }) {
  const percentage = Math.min(100, Math.max(0, value * 100))

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full transform -rotate-90">
          {/* 背景圆 */}
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="12"
          />
          {/* 进度圆 */}
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeDasharray={`${percentage * 3.52} 352`}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-slate-800">{(value * 100).toFixed(0)}%</span>
        </div>
      </div>
      <p className="mt-2 text-sm font-medium text-slate-600">{label}</p>
    </div>
  )
}

export default function FilterBubbleObservation() {
  const [databases, setDatabases] = useState<string[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [globalStats, setGlobalStats] = useState<FilterBubbleGlobalStats | null>(null)
  const [userMetrics, setUserMetrics] = useState<FilterBubbleUserMetrics[]>([])
  const [selectedUser, setSelectedUser] = useState<FilterBubbleUserMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'overview' | 'user-detail'>('overview')

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

  // 加载数据
  useEffect(() => {
    if (selectedDb) {
      loadData()
    }
  }, [selectedDb])

  const loadData = async () => {
    setLoading(true)
    try {
      const [stats, metrics] = await Promise.all([
        getFilterBubbleGlobalStats(selectedDb),
        getAllUsersBubbleMetrics(selectedDb, 100)
      ])
      setGlobalStats(stats)
      setUserMetrics(metrics)
      if (metrics.length > 0) {
        setSelectedUser(metrics[0])
      }
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUserSelect = async (userId: string) => {
    const metrics = await getUserBubbleMetrics(selectedDb, userId)
    if (metrics) {
      setSelectedUser(metrics)
      setViewMode('user-detail')
    }
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
            <Layers size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-slate-800">信息茧房观测</h1>
            <p className="text-lg text-slate-600">监测与分析用户群体的信息茧房效应</p>
          </div>
        </div>
      </div>

      {/* 数据库选择 */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <DatabaseSelector
            databases={databases}
            selectedDb={selectedDb}
            onSelect={setSelectedDb}
            label="选择数据库："
          />
          {loading && <span className="text-sm text-slate-500">分析中...</span>}
        </div>
      </div>

      {viewMode === 'overview' && globalStats && (
        <>
          {/* 全局统计 */}
          <div className="glass-card p-6">
            <h2 className="text-2xl font-bold text-slate-800 mb-6">全局信息茧房统计</h2>

            {/* 关键指标卡片 */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-600 to-blue-400 text-white">
                <p className="text-3xl font-bold mb-1">{globalStats.total_users}</p>
                <p className="text-base opacity-90">总用户数</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 text-white">
                <p className="text-3xl font-bold mb-1">{globalStats.severe_bubble_users}</p>
                <p className="text-base opacity-90">严重茧房用户</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-500 text-white">
                <p className="text-3xl font-bold mb-1">{globalStats.moderate_bubble_users}</p>
                <p className="text-base opacity-90">中度茧房用户</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 text-white">
                <p className="text-3xl font-bold mb-1">{globalStats.mild_bubble_users}</p>
                <p className="text-base opacity-90">轻度茧房用户</p>
              </div>
            </div>

            {/* 平均指标 */}
            <div className="grid grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">平均同质化指数</p>
                <p className="text-2xl font-bold text-slate-800">
                  {(globalStats.avg_homogeneity * 100).toFixed(1)}%
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">平均活跃广度</p>
                <p className="text-2xl font-bold text-slate-800">
                  {(userMetrics.length > 0 ? (userMetrics.reduce((sum: number, m: FilterBubbleUserMetrics) => sum + (m.activity_breadth || 0), 0) / userMetrics.length) * 100 : 0).toFixed(1)}%
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">平均回声室指数</p>
                <p className="text-2xl font-bold text-slate-800">
                  {(globalStats.avg_echo_index * 100).toFixed(1)}%
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">网络密度</p>
                <p className="text-2xl font-bold text-slate-800">
                  {(globalStats.network_density * 100).toFixed(3)}%
                </p>
              </div>
            </div>
          </div>

          {/* 用户列表 */}
          <div className="glass-card p-6">
            <h2 className="text-2xl font-bold text-slate-800 mb-4">用户信息茧房指数</h2>

            <div className="max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b border-slate-200">
                    <th className="text-left p-3 text-sm font-medium text-slate-600">用户ID</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">同质化</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">活跃广度</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">茧房指数</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">严重程度</th>
                    <th className="text-left p-3 text-sm font-medium text-slate-600">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {userMetrics.map((user) => (
                    <tr
                      key={user.user_id}
                      className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                    >
                      <td className="p-3 text-sm text-slate-800 font-mono">{user.user_id}</td>
                      <td className="p-3 text-sm text-slate-600">
                        {((user.homogeneity_index ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="p-3 text-sm text-slate-600">
                        {((user.activity_breadth ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="p-3 text-sm text-slate-600">
                        {((user.echo_chamber_index ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${severityColors[user.bubble_severity]}`}>
                          {severityLabels[user.bubble_severity]}
                        </span>
                      </td>
                      <td className="p-3">
                        <button
                          onClick={() => handleUserSelect(user.user_id)}
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                        >
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {viewMode === 'user-detail' && selectedUser && (
        <>
          {/* 返回按钮 */}
          <div className="glass-card p-4">
            <button
              onClick={() => setViewMode('overview')}
              className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-2"
            >
              ← 返回全局概览
            </button>
          </div>

          {/* 用户详情 */}
          <div className="glass-card p-6">
            <h2 className="text-2xl font-bold text-slate-800 mb-6">
              用户详情: {selectedUser.user_id}
            </h2>

            {/* 严重程度标签 */}
            <div className="mb-6">
              <span className={`px-4 py-2 rounded-lg text-base font-medium border ${severityColors[selectedUser.bubble_severity]}`}>
                信息茧房等级: {severityLabels[selectedUser.bubble_severity]}
              </span>
            </div>

            {/* 主指数仪表盘 */}
            <div className="mb-8">
              <h3 className="text-xl font-bold text-slate-800 mb-4">信息茧房总指数</h3>
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-6 rounded-xl border border-purple-200">
                <div className="flex items-center justify-center">
                  <MetricGauge
                    value={selectedUser.echo_chamber_index}
                    label="茧房指数"
                    color="#a855f7"
                  />
                </div>
                <div className="mt-4 text-center">
                  <p className="text-sm text-slate-600">
                    基于同质化、活跃广度和社区多样性综合计算
                  </p>
                </div>
              </div>
            </div>

            {/* 基础指标仪表盘 */}
            <div className="mb-8">
              <h3 className="text-xl font-bold text-slate-800 mb-4">基础指标</h3>
              <div className="grid grid-cols-2 gap-6">
                <MetricGauge
                  value={selectedUser.homogeneity_index ?? 0}
                  label="同质化指数"
                  color="#ef4444"
                />
                <MetricGauge
                  value={selectedUser.activity_breadth ?? 0}
                  label="活跃广度"
                  color="#22c55e"
                />
              </div>
            </div>

            {/* 指标说明 */}
            <div className="mb-8">
              <h3 className="text-xl font-bold text-slate-800 mb-4">指标说明</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-sm font-medium text-slate-700 mb-2">同质化指数</p>
                  <p className="text-xs text-slate-500">
                    衡量用户关注人群的相似程度，值越高表示关注的人群越相似，圈子越封闭
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <p className="text-sm font-medium text-slate-700 mb-2">活跃广度</p>
                  <p className="text-xs text-slate-500">
                    衡量用户在不同类型活动上的参与程度，值越高表示用户越活跃
                  </p>
                </div>
              </div>
            </div>

            {/* 详细数值 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">同质化指数</p>
                <p className="text-lg text-slate-800 mb-2">
                  {((selectedUser.homogeneity_index ?? 0) * 100).toFixed(2)}%
                </p>
                <p className="text-xs text-slate-500">
                  衡量用户关注人群的相似程度，值越高表示关注的人群越相似
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm text-slate-600 mb-2">活跃广度</p>
                <p className="text-lg text-slate-800 mb-2">
                  {((selectedUser.activity_breadth ?? 0) * 100).toFixed(2)}%
                </p>
                <p className="text-xs text-slate-500">
                  衡量用户在不同类型活动上的参与程度，值越高表示用户越活跃
                </p>
              </div>
            </div>

            {/* 回声室指数解释 */}
            <div className="mt-6 p-4 rounded-xl bg-blue-50 border border-blue-200">
              <h4 className="text-sm font-bold text-blue-800 mb-2">信息茧房指数解释</h4>
              <p className="text-sm text-blue-700">
                信息茧房指数通过多维度综合分析，评估用户的信息接触模式和社交网络特征。
                指数越高，表示用户越可能处于信息茧房中，接触到的信息越单一。
              </p>
              <p className="text-sm text-blue-700 mt-2">
                当前茧房指数: <strong>{((selectedUser.echo_chamber_index ?? 0) * 100).toFixed(2)}%</strong>
              </p>
            </div>
          </div>
        </>
      )}

    </div>
  )
}

