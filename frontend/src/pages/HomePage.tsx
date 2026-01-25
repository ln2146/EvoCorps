import { Activity, Users, MessageSquare, TrendingUp, Shield, Zap } from 'lucide-react'

export default function HomePage() {
  const stats = [
    { label: '活跃用户', value: '1,234', icon: Users, color: 'from-blue-500 to-cyan-500' },
    { label: '监控帖子', value: '5,678', icon: MessageSquare, color: 'from-purple-500 to-blue-500' },
    { label: '干预次数', value: '89', icon: Shield, color: 'from-cyan-500 to-green-500' },
    { label: '系统效率', value: '94%', icon: TrendingUp, color: 'from-green-500 to-emerald-500' },
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
      title: '数据可视化',
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
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-2xl">
            <Activity size={48} className="text-white" />
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className="glass-card p-6 hover:scale-105 transition-transform duration-200">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg`}>
                  <Icon size={24} className="text-white" />
                </div>
              </div>
              <p className="text-3xl font-bold text-slate-800 mb-1">{stat.value}</p>
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
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center shadow-lg mb-4`}>
                  <Icon size={28} className="text-white" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800 mb-2">{feature.title}</h3>
                <p className="text-slate-600">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* 系统状态 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">系统状态</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-slate-600">数据库服务</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">运行中</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">监控服务</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">运行中</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">AI 引擎</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">就绪</span>
          </div>
        </div>
      </div>
    </div>
  )
}
