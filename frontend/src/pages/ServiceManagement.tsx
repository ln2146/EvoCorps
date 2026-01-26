import { useState, useEffect } from 'react'
import { Server, Play, Square, Database, Users, Shield, Trash2 } from 'lucide-react'
import axios from 'axios'

interface ServiceStatus {
  database: 'running' | 'stopped'
  platform: 'running' | 'stopped'
  balance: 'running' | 'stopped'
}

export default function ServiceManagement() {
  const [status, setStatus] = useState<ServiceStatus>({
    database: 'stopped',
    platform: 'stopped',
    balance: 'stopped'
  })
  const [loading, setLoading] = useState<string | null>(null)

  const services = [
    {
      id: 'database',
      name: '数据库服务器',
      description: '核心数据存储服务，负责用户数据、帖子分享、评论互动等所有数据的持久化存储。这是系统的基础服务，必须最先启动。',
      icon: Database,
      color: 'from-blue-500 to-cyan-500',
      script: 'src/start_database_service.py'
    },
    {
      id: 'platform',
      name: '社交平台模拟',
      description: '模拟真实的社交媒体环境，生成用户行为、内容发布、互动评论等。支持多样化场景，包括正常用户行为和极端内容传播。',
      icon: Users,
      color: 'from-purple-500 to-pink-500',
      script: 'src/main.py'
    },
    {
      id: 'balance',
      name: '舆论平衡系统',
      description: '智能监控平台内容，识别极端言论和极化趋势，自动进行干预平衡。仅在场景4中需要开启，需要配置梯子。使用时需在社交平台启动前开启，不使用时记得关闭。',
      icon: Shield,
      color: 'from-orange-500 to-red-500',
      script: 'src/opinion_balance_launcher.py'
    }
  ]

  // 加载服务状态
  const loadStatus = async () => {
    try {
      const response = await axios.get('/api/services/status')
      setStatus(response.data.services)
    } catch (error) {
      console.error('Failed to load service status:', error)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 3000) // 每3秒刷新一次状态
    return () => clearInterval(interval)
  }, [])

  const handleStart = async (serviceId: string) => {
    setLoading(serviceId)
    try {
      console.log(`Starting service: ${serviceId}`)
      const response = await axios.post(`/api/services/${serviceId}/start`)
      console.log('Start response:', response.data)
      await loadStatus()
      alert(`服务启动成功！请查看新打开的CMD窗口。`)
    } catch (error: any) {
      console.error('Start error:', error)
      alert(`启动失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(null)
    }
  }

  const handleStop = async (serviceId: string) => {
    setLoading(serviceId)
    try {
      console.log(`Stopping service: ${serviceId}`)
      const response = await axios.post(`/api/services/${serviceId}/stop`)
      console.log('Stop response:', response.data)
      await loadStatus()
      alert(`服务已停止！`)
    } catch (error: any) {
      console.error('Stop error:', error)
      alert(`停止失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(null)
    }
  }

  const handleCleanup = async () => {
    if (!confirm('确定要清理所有服务进程吗？这将强制终止所有正在运行的服务。')) {
      return
    }
    
    setLoading('cleanup')
    try {
      const response = await axios.post('/api/services/cleanup')
      console.log('Cleanup response:', response.data)
      await loadStatus()
      const cleaned = response.data.cleaned || []
      if (cleaned.length > 0) {
        alert(`清理完成！已终止 ${cleaned.length} 个进程:\n${cleaned.join('\n')}`)
      } else {
        alert('清理完成！没有发现需要清理的进程。')
      }
    } catch (error: any) {
      console.error('Cleanup error:', error)
      alert(`清理失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
              <Server size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-800">服务管理</h1>
              <p className="text-slate-600">管理和监控系统服务状态</p>
            </div>
          </div>
          <button
            onClick={handleCleanup}
            disabled={loading === 'cleanup'}
            className="px-6 py-3 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 size={18} />
            {loading === 'cleanup' ? '清理中...' : '清理所有服务'}
          </button>
        </div>
      </div>

      <div className="grid gap-6">
        {services.map((service) => {
          const Icon = service.icon
          const isRunning = status[service.id as keyof ServiceStatus] === 'running'
          const isLoading = loading === service.id

          return (
            <div key={service.id} className="glass-card p-6">
              <div className="flex items-start gap-4">
                <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${service.color} flex items-center justify-center shadow-lg flex-shrink-0`}>
                  <Icon size={32} className="text-white" />
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold text-slate-800">{service.name}</h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      isRunning 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      {isRunning ? '● 运行中' : '○ 已停止'}
                    </span>
                  </div>
                  <p className="text-slate-600 leading-relaxed mb-3">{service.description}</p>
                  <p className="text-xs text-slate-500 font-mono bg-slate-50 px-2 py-1 rounded inline-block">
                    {service.script}
                  </p>
                </div>

                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => handleStart(service.id)}
                    disabled={isLoading || isRunning}
                    className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play size={18} />
                    {isLoading && !isRunning ? '启动中...' : '启动服务'}
                  </button>
                  <button
                    onClick={() => handleStop(service.id)}
                    disabled={isLoading || !isRunning}
                    className="px-6 py-3 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Square size={18} />
                    {isLoading && isRunning ? '停止中...' : '停止服务'}
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="glass-card p-6 bg-blue-50/50">
        <h3 className="text-lg font-bold text-slate-800 mb-3">使用说明</h3>
        <div className="space-y-2 text-sm text-slate-700">
          <p>1. <strong>数据库服务器</strong>必须最先启动，这是所有服务的基础</p>
          <p>2. <strong>社交平台模拟</strong>在数据库服务启动后启动</p>
          <p>3. <strong>舆论平衡系统</strong>仅在场景4中需要，且需要在社交平台启动前开启</p>
          <p>4. 舆论平衡系统需要配置梯子才能正常工作</p>
          <p>5. 不使用舆论平衡系统时请及时关闭以节省资源</p>
          <p className="text-red-600 font-medium mt-3">⚠️ 如果服务无法启动或出现端口占用错误，请点击右上角的"清理所有服务"按钮</p>
        </div>
      </div>
    </div>
  )
}
