import { useState } from 'react'
import { FlaskConical, Play, Pause, RotateCcw, Download } from 'lucide-react'

interface Experiment {
  id: string
  name: string
  status: 'running' | 'completed' | 'paused'
  progress: number
  startTime: string
  config: {
    users: number
    timeSteps: number
    maliciousBots: boolean
    opinionBalance: boolean
  }
}

export default function ExperimentManagement() {
  const [experiments, setExperiments] = useState<Experiment[]>([
    {
      id: '1',
      name: '基线实验 - 无干预',
      status: 'completed',
      progress: 100,
      startTime: '2024-01-20 10:00',
      config: {
        users: 100,
        timeSteps: 50,
        maliciousBots: false,
        opinionBalance: false,
      },
    },
    {
      id: '2',
      name: '恶意攻击场景',
      status: 'running',
      progress: 65,
      startTime: '2024-01-20 14:30',
      config: {
        users: 100,
        timeSteps: 50,
        maliciousBots: true,
        opinionBalance: false,
      },
    },
    {
      id: '3',
      name: '完整干预实验',
      status: 'paused',
      progress: 30,
      startTime: '2024-01-20 16:00',
      config: {
        users: 100,
        timeSteps: 50,
        maliciousBots: true,
        opinionBalance: true,
      },
    },
  ])

  const [showNewExperiment, setShowNewExperiment] = useState(false)

  const getStatusColor = (status: Experiment['status']) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-700'
      case 'completed':
        return 'bg-blue-100 text-blue-700'
      case 'paused':
        return 'bg-orange-100 text-orange-700'
    }
  }

  const getStatusText = (status: Experiment['status']) => {
    switch (status) {
      case 'running':
        return '运行中'
      case 'completed':
        return '已完成'
      case 'paused':
        return '已暂停'
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-cyan-500 to-green-500 flex items-center justify-center shadow-lg">
              <FlaskConical size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-800">实验管理</h1>
              <p className="text-slate-600">创建和管理模拟实验</p>
            </div>
          </div>
          <button 
            onClick={() => setShowNewExperiment(true)}
            className="btn-primary"
          >
            + 新建实验
          </button>
        </div>
      </div>

      {/* 新建实验表单 */}
      {showNewExperiment && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-4">新建实验</h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">实验名称</label>
              <input 
                type="text" 
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="输入实验名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">用户数量</label>
              <input 
                type="number" 
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">时间步数</label>
              <input 
                type="number" 
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">AI 引擎</label>
              <select className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                <option>GPT-4</option>
                <option>GPT-3.5</option>
                <option>Claude</option>
              </select>
            </div>
          </div>
          <div className="space-y-2 mb-4">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-slate-700">启用恶意机器人系统</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-slate-700">启用舆论平衡系统</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm text-slate-700">启用事实核查</span>
            </label>
          </div>
          <div className="flex gap-3">
            <button className="btn-primary">创建并启动</button>
            <button 
              onClick={() => setShowNewExperiment(false)}
              className="btn-secondary"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* 实验列表 */}
      <div className="space-y-4">
        {experiments.map((exp) => (
          <div key={exp.id} className="glass-card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold text-slate-800">{exp.name}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(exp.status)}`}>
                    {getStatusText(exp.status)}
                  </span>
                </div>
                <p className="text-sm text-slate-600">开始时间: {exp.startTime}</p>
              </div>
              <div className="flex gap-2">
                {exp.status === 'running' && (
                  <button className="p-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors">
                    <Pause size={20} />
                  </button>
                )}
                {exp.status === 'paused' && (
                  <button className="p-2 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors">
                    <Play size={20} />
                  </button>
                )}
                {exp.status === 'completed' && (
                  <button className="p-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors">
                    <Download size={20} />
                  </button>
                )}
                <button className="p-2 bg-slate-500 text-white rounded-xl hover:bg-slate-600 transition-colors">
                  <RotateCcw size={20} />
                </button>
              </div>
            </div>

            {/* 进度条 */}
            <div className="mb-4">
              <div className="flex justify-between text-sm text-slate-600 mb-2">
                <span>进度</span>
                <span>{exp.progress}%</span>
              </div>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300"
                  style={{ width: `${exp.progress}%` }}
                />
              </div>
            </div>

            {/* 配置信息 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white/50 p-3 rounded-xl">
                <p className="text-xs text-slate-600 mb-1">用户数</p>
                <p className="text-lg font-semibold text-slate-800">{exp.config.users}</p>
              </div>
              <div className="bg-white/50 p-3 rounded-xl">
                <p className="text-xs text-slate-600 mb-1">时间步</p>
                <p className="text-lg font-semibold text-slate-800">{exp.config.timeSteps}</p>
              </div>
              <div className="bg-white/50 p-3 rounded-xl">
                <p className="text-xs text-slate-600 mb-1">恶意机器人</p>
                <p className="text-lg font-semibold text-slate-800">{exp.config.maliciousBots ? '✓' : '✗'}</p>
              </div>
              <div className="bg-white/50 p-3 rounded-xl">
                <p className="text-xs text-slate-600 mb-1">舆论平衡</p>
                <p className="text-lg font-semibold text-slate-800">{exp.config.opinionBalance ? '✓' : '✗'}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
