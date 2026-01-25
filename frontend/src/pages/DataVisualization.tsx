import { BarChart3, TrendingUp, Users, MessageSquare } from 'lucide-react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'

export default function DataVisualization() {
  // 用户情绪分布
  const sentimentDistribution = [
    { name: '非常负面', value: 15, color: '#ef4444' },
    { name: '负面', value: 25, color: '#f97316' },
    { name: '中性', value: 35, color: '#64748b' },
    { name: '正面', value: 20, color: '#22c55e' },
    { name: '非常正面', value: 5, color: '#14b8a6' },
  ]

  // 内容类型分布
  const contentTypes = [
    { type: '新闻', count: 450 },
    { type: '评论', count: 1200 },
    { type: '转发', count: 800 },
    { type: '点赞', count: 2500 },
  ]

  // 干预效果对比
  const interventionEffect = [
    { metric: '情绪稳定性', before: 45, after: 78 },
    { metric: '理性程度', before: 52, after: 85 },
    { metric: '极端内容', before: 85, after: 25 },
    { metric: '用户参与', before: 60, after: 72 },
    { metric: '内容质量', before: 55, after: 82 },
  ]

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-500 flex items-center justify-center shadow-lg">
            <BarChart3 size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">数据可视化</h1>
            <p className="text-slate-600">深度分析舆论数据和系统效果</p>
          </div>
        </div>
      </div>

      {/* 关键指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: '总帖子数', value: '5,678', icon: MessageSquare, color: 'from-blue-500 to-cyan-500' },
          { label: '活跃用户', value: '1,234', icon: Users, color: 'from-purple-500 to-blue-500' },
          { label: '干预次数', value: '89', icon: TrendingUp, color: 'from-cyan-500 to-green-500' },
          { label: '平均情绪', value: '+0.32', icon: TrendingUp, color: 'from-green-500 to-emerald-500' },
        ].map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className="glass-card p-6">
              <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg mb-3`}>
                <Icon size={20} className="text-white" />
              </div>
              <p className="text-2xl font-bold text-slate-800 mb-1">{stat.value}</p>
              <p className="text-sm text-slate-600">{stat.label}</p>
            </div>
          )
        })}
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 用户情绪分布 */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-4">用户情绪分布</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={sentimentDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {sentimentDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 内容类型统计 */}
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-4">内容类型统计</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={contentTypes}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="type" stroke="#64748b" />
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
              <Bar dataKey="count" fill="url(#colorBar)" radius={[10, 10, 0, 0]} />
              <defs>
                <linearGradient id="colorBar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0.3}/>
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 干预效果对比 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">干预效果对比分析</h2>
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={interventionEffect}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="metric" stroke="#64748b" />
            <PolarRadiusAxis stroke="#64748b" />
            <Radar name="干预前" dataKey="before" stroke="#f97316" fill="#f97316" fillOpacity={0.3} />
            <Radar name="干预后" dataKey="after" stroke="#3b82f6" fill="#22c55e" fillOpacity={0.3} />
            <Legend />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.9)', 
                backdropFilter: 'blur(10px)',
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)'
              }} 
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* 数据导出 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">数据导出</h2>
        <div className="flex gap-3">
          <button className="btn-primary">导出 CSV</button>
          <button className="btn-secondary">导出 JSON</button>
          <button className="btn-secondary">生成报告</button>
        </div>
      </div>
    </div>
  )
}
