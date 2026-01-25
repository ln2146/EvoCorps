import { useState } from 'react'
import { Server, Play, Square, RefreshCw, CheckCircle, XCircle } from 'lucide-react'

interface Service {
  id: string
  name: string
  description: string
  status: 'running' | 'stopped' | 'error'
  port?: number
}

export default function ServiceManagement() {
  const [services, setServices] = useState<Service[]>([
    {
      id: 'database',
      name: '数据库服务',
      description: 'SQLite 数据库服务，管理用户、帖子和评论数据',
      status: 'running',
      port: 5000,
    },
    {
      id: 'simulation',
      name: '模拟服务',
      description: '社交媒体模拟主程序',
      status: 'stopped',
    },
    {
      id: 'opinion-balance',
      name: '舆论平衡系统',
      description: '监控和干预极端内容',
      status: 'stopped',
    },
    {
      id: 'malicious-bot',
      name: '恶意机器人系统',
      description: '模拟恶意攻击和极端言论',
      status: 'stopped',
    },
  ])

  const handleStart = (id: string) => {
    setServices(services.map(s => 
      s.id === id ? { ...s, status: 'running' as const } : s
    ))
  }

  const handleStop = (id: string) => {
    setServices(services.map(s => 
      s.id === id ? { ...s, status: 'stopped' as const } : s
    ))
  }

  const handleRestart = (id: string) => {
    handleStop(id)
    setTimeout(() => handleStart(id), 500)
  }

  const getStatusColor = (status: Service['status']) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-700'
      case 'stopped':
        return 'bg-slate-100 text-slate-700'
      case 'error':
        return 'bg-red-100 text-red-700'
    }
  }

  const getStatusIcon = (status: Service['status']) => {
    switch (status) {
      case 'running':
        return <CheckCircle size={16} />
      case 'stopped':
        return <Square size={16} />
      case 'error':
        return <XCircle size={16} />
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
            <Server size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">服务管理</h1>
            <p className="text-slate-600">管理和监控系统服务状态</p>
          </div>
        </div>
      </div>

      {/* 服务列表 */}
      <div className="grid gap-4">
        {services.map((service) => (
          <div key={service.id} className="glass-card p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold text-slate-800">{service.name}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1 ${getStatusColor(service.status)}`}>
                    {getStatusIcon(service.status)}
                    {service.status === 'running' ? '运行中' : service.status === 'stopped' ? '已停止' : '错误'}
                  </span>
                </div>
                <p className="text-slate-600 mb-2">{service.description}</p>
                {service.port && (
                  <p className="text-sm text-slate-500">端口: {service.port}</p>
                )}
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2">
                {service.status === 'stopped' ? (
                  <button
                    onClick={() => handleStart(service.id)}
                    className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2"
                  >
                    <Play size={16} />
                    启动
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleStop(service.id)}
                      className="px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2"
                    >
                      <Square size={16} />
                      停止
                    </button>
                    <button
                      onClick={() => handleRestart(service.id)}
                      className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2"
                    >
                      <RefreshCw size={16} />
                      重启
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 快速操作 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">快速操作</h2>
        <div className="flex gap-3">
          <button className="btn-primary">启动所有服务</button>
          <button className="btn-secondary">停止所有服务</button>
          <button className="btn-secondary">重启所有服务</button>
        </div>
      </div>
    </div>
  )
}
