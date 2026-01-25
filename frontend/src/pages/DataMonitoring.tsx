import { Activity, TrendingUp, AlertTriangle, Users } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function DataMonitoring() {
  // 模拟情绪数据
  const sentimentData = [
    { time: '00:00', sentiment: 0.2, interventions: 0 },
    { time: '04:00', sentiment: 0.1, interventions: 2 },
    { time: '08:00', sentiment: -0.3, interventions: 5 },
    { time: '12:00', sentiment: -0.5, interventions: 8 },
    { time: '16:00', sentiment: -0.2, interventions: 12 },
    { time: '20:00', sentiment: 0.1, interventions: 15 },
    { time: '24:00', sentiment: 0.3, interventions: 18 },
  ]

  const realtimeMetrics = [
    { label: '当前情绪值', value: '+0.32', trend: 'up', color: 'from-green-500 to-emerald-500' },
    { label: '极端内容数', value: '12', trend: 'down', color: 'from-cyan-500 to-green-500' },
    { label: '干预成功率', value: '94%', trend: 'up', color: 'from-blue-500 to-cyan-500' },
    { label: '活跃用户', value: '1,234', trend: 'up', color: 'from-purple-500 to-blue-500' },
  ]

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
            <Activity size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">数据监控</h1>
            <p className="text-slate-600">实时监控舆论动态和系统运行状态</p>
          </div>
        </div>
      </div>

      {/* 实时指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {realtimeMetrics.map((metric, index) => (
          <div key={index} className="glass-card p-6">
            <p className="text-sm text-slate-600 mb-2">{metric.label}</p>
            <div className="flex items-end justify-between">
              <p className="text-3xl font-bold text-slate-800">{metric.value}</p>
              <div className={`px-2 py-1 rounded-lg bg-gradient-to-r ${metric.color} text-white text-xs font-medium flex items-center gap-1`}>
                <TrendingUp size={12} className={metric.trend === 'down' ? 'rotate-180' : ''} />
                {metric.trend === 'up' ? '↑' : '↓'}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 情绪趋势图 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">情绪趋势分析</h2>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={sentimentData}>
            <defs>
              <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="time" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.9)', 
                backdropFilter: 'blur(10px)',
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
              }} 
            />
            <Area 
              type="monotone" 
              dataKey="sentiment" 
              stroke="#3b82f6" 
              strokeWidth={3}
              fill="url(#colorSentiment)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 干预次数统计 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">干预次数统计</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={sentimentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="time" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.9)', 
                backdropFilter: 'blur(10px)',
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
              }} 
            />
            <Line 
              type="monotone" 
              dataKey="interventions" 
              stroke="#3b82f6" 
              strokeWidth={3}
              dot={{ fill: '#3b82f6', r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 警报列表 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          <AlertTriangle size={20} className="text-orange-500" />
          实时警报
        </h2>
        <div className="space-y-3">
          {[
            { time: '14:32', message: '检测到极端内容，已触发干预', level: 'warning' },
            { time: '14:28', message: '用户情绪波动较大，持续监控中', level: 'info' },
            { time: '14:15', message: '恶意机器人活动增加', level: 'error' },
          ].map((alert, index) => (
            <div key={index} className="flex items-center gap-3 p-3 bg-white/50 rounded-xl">
              <div className={`w-2 h-2 rounded-full ${
                alert.level === 'error' ? 'bg-red-500' : 
                alert.level === 'warning' ? 'bg-orange-500' : 
                'bg-blue-500'
              }`} />
              <span className="text-sm text-slate-600">{alert.time}</span>
              <span className="text-sm text-slate-800 flex-1">{alert.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
