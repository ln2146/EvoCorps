import { useState, useEffect } from 'react'
import { Server, Settings, Play, Square, Database, Users, Shield, Trash2, Save } from 'lucide-react'
import axios from 'axios'

interface ServiceStatus {
  database: 'running' | 'stopped'
  platform: 'running' | 'stopped'
  balance: 'running' | 'stopped'
}

interface ExperimentConfig {
  num_users: number
  num_time_steps: number
  engine: string
  temperature: number
  reset_db: boolean
  [key: string]: any
}

export default function ExperimentSettings() {
  const [activeTab, setActiveTab] = useState<'service' | 'config'>('config')
  
  // 服务管理状态
  const [status, setStatus] = useState<ServiceStatus>({
    database: 'stopped',
    platform: 'stopped',
    balance: 'stopped'
  })
  const [loading, setLoading] = useState<string | null>(null)
  const [condaEnv, setCondaEnv] = useState<string>('')
  const [isEnvSaved, setIsEnvSaved] = useState<boolean>(false)

  // 配置状态
  const [config, setConfig] = useState<ExperimentConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(false)

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
      color: 'from-blue-500 to-green-500',
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

  // 从localStorage加载conda环境名称
  useEffect(() => {
    const savedEnv = localStorage.getItem('condaEnv')
    if (savedEnv) {
      setCondaEnv(savedEnv)
      setIsEnvSaved(true)
    }
  }, [])

  // 加载服务状态
  const loadStatus = async () => {
    try {
      const response = await axios.get('/api/services/status')
      setStatus(response.data.services)
    } catch (error) {
      console.error('Failed to load service status:', error)
    }
  }

  // 加载配置
  const loadConfig = async () => {
    setConfigLoading(true)
    try {
      const response = await axios.get('/api/config/experiment')
      setConfig(response.data)
    } catch (error) {
      console.error('Failed to load config:', error)
      alert('加载配置失败')
    } finally {
      setConfigLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    loadConfig()
  }, [])

  // 保存conda环境名称
  const saveCondaEnv = () => {
    if (condaEnv.trim()) {
      localStorage.setItem('condaEnv', condaEnv.trim())
      setIsEnvSaved(true)
      alert('Conda环境名称已保存！')
    } else {
      alert('请输入有效的环境名称')
    }
  }

  // 清除conda环境名称
  const clearCondaEnv = () => {
    localStorage.removeItem('condaEnv')
    setCondaEnv('')
    setIsEnvSaved(false)
    alert('Conda环境名称已清除！')
  }

  const handleStart = async (serviceId: string) => {
    setLoading(serviceId)
    try {
      const payload = condaEnv.trim() ? { conda_env: condaEnv.trim() } : {}
      await axios.post(`/api/services/${serviceId}/start`, payload)
      await loadStatus()
      alert(`服务启动成功！请查看新打开的CMD窗口。`)
    } catch (error: any) {
      alert(`启动失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(null)
    }
  }

  const handleStop = async (serviceId: string) => {
    setLoading(serviceId)
    try {
      await axios.post(`/api/services/${serviceId}/stop`)
      await loadStatus()
      alert(`服务已停止！`)
    } catch (error: any) {
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
      await loadStatus()
      const cleaned = response.data.cleaned || []
      if (cleaned.length > 0) {
        alert(`清理完成！已终止 ${cleaned.length} 个进程\n${cleaned.join('\n')}`)
      } else {
        alert('清理完成！没有发现需要清理的进程。')
      }
    } catch (error: any) {
      alert(`清理失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(null)
    }
  }

  const handleSaveConfig = async () => {
    if (!config) return
    
    setConfigLoading(true)
    try {
      // 只发送需要修改的字段
      const updateData = {
        num_users: config.num_users,
        num_time_steps: config.num_time_steps,
        temperature: config.temperature,
        reset_db: config.reset_db
      }
      await axios.post('/api/config/experiment', updateData)
      alert('配置保存成功！')
    } catch (error: any) {
      alert(`保存失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setConfigLoading(false)
    }
  }

  const updateConfig = (key: string, value: any) => {
    if (!config) return
    setConfig({ ...config, [key]: value })
  }

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center shadow-lg">
            <Settings size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-slate-800">实验设置</h1>
            <p className="text-lg text-slate-600">管理服务和配置实验参数</p>
          </div>
        </div>
      </div>

      {/* 标签页切换*/}
      <div className="glass-card p-2">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('config')}
            className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              activeTab === 'config'
                ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white shadow-lg'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Settings size={20} />
            参数设置
          </button>
          <button
            onClick={() => setActiveTab('service')}
            className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              activeTab === 'service'
                ? 'bg-gradient-to-r from-blue-500 to-green-500 text-white shadow-lg'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Server size={20} />
            启动服务
          </button>
        </div>
      </div>

      {/* 实验配置内容 */}
      {activeTab === 'config' && (
        <>
          {configLoading ? (
            <div className="glass-card p-12 text-center">
              <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-slate-600">加载配置中...</p>
            </div>
          ) : config ? (
            <>
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold text-slate-800">基础配置</h2>
                  <button
                    onClick={handleSaveConfig}
                    disabled={configLoading}
                    className="px-6 py-3 bg-gradient-to-r from-blue-500 to-green-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50"
                  >
                    <Save size={18} />
                    保存配置
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      用户数量
                    </label>
                    <input
                      type="number"
                      value={config.num_users}
                      onChange={(e) => updateConfig('num_users', parseInt(e.target.value))}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="1"
                    />
                    <p className="text-xs text-slate-500 mt-1">模拟的用户总数</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      时间步数
                    </label>
                    <input
                      type="number"
                      value={config.num_time_steps}
                      onChange={(e) => updateConfig('num_time_steps', parseInt(e.target.value))}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="1"
                    />
                    <p className="text-xs text-slate-500 mt-1">模拟运行的时间步数</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Temperature
                    </label>
                    <input
                      type="number"
                      value={config.temperature}
                      onChange={(e) => updateConfig('temperature', parseFloat(e.target.value))}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="0"
                      max="2"
                      step="0.1"
                    />
                    <p className="text-xs text-slate-500 mt-1">AI生成的随机性(0-2)</p>
                  </div>

                  <div className="col-span-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={config.reset_db}
                        onChange={(e) => updateConfig('reset_db', e.target.checked)}
                        className="w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
                      />
                      <span className="text-sm font-medium text-slate-700">启动时重置数据库</span>
                    </label>
                    <p className="text-xs text-slate-500 mt-1 ml-6">勾选后每次启动会清空之前的数据</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6 bg-yellow-50/50">
                <h3 className="text-lg font-bold text-slate-800 mb-3">⚠️ 注意事项</h3>
                <div className="space-y-2 text-sm text-slate-700">
                  <p>• 修改配置后需要点击"保存配置"按钮才会生效</p>
                  <p>• 配置保存后需要重启服务才能应用新配置</p>
                  <p>• 用户数量和时间步数会直接影响实验运行时间</p>
                  <p>• Temperature值越高，AI生成的内容越随机和多样化</p>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card p-12 text-center">
              <p className="text-slate-600">无法加载配置文件</p>
            </div>
          )}
        </>
      )}

      {/* 服务管理内容 */}
      {activeTab === 'service' && (
        <>
          {/* Conda环境配置 */}
          <div className="glass-card p-6 bg-gradient-to-br from-green-50 to-emerald-50">
            <h3 className="text-lg font-bold text-slate-800 mb-3 flex items-center gap-2">
              <span className="text-2xl">🐍</span>
              Conda环境配置
            </h3>
            <div className="space-y-3">
              <p className="text-sm text-slate-700">
                如果您使用conda虚拟环境，请在此输入环境名称。启动服务时会自动执行<code className="bg-slate-200 px-2 py-0.5 rounded text-xs">conda run -n 环境名称</code>
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={condaEnv}
                  onChange={(e) => setCondaEnv(e.target.value)}
                  placeholder="例如: EvoCrops 或 base"
                  className="flex-1 px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
                  disabled={isEnvSaved}
                />
                {!isEnvSaved ? (
                  <button
                    onClick={saveCondaEnv}
                    className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
                  >
                    保存
                  </button>
                ) : (
                  <button
                    onClick={clearCondaEnv}
                    className="px-6 py-2 bg-gradient-to-r from-slate-500 to-slate-600 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
                  >
                    修改
                  </button>
                )}
              </div>
              {isEnvSaved && (
                <p className="text-sm text-green-700 font-medium">
                  ✓ 已配置环境: <code className="bg-green-100 px-2 py-0.5 rounded">{condaEnv}</code>
                </p>
              )}
              <p className="text-xs text-slate-500">
                💡 提示: 环境名称区分大小写。可以运行<code className="bg-slate-200 px-1 rounded">conda info --envs</code> 查看所有环境。
              </p>
            </div>
          </div>

          {/* 服务列表 */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-800">服务列表</h2>
            <button
              onClick={handleCleanup}
              disabled={loading === 'cleanup'}
              className="px-6 py-3 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 size={18} />
              {loading === 'cleanup' ? '清理中...' : '清理所有服务'}
            </button>
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
                          {isRunning ? '运行中' : '已停止'}
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
              <p className="text-red-600 font-medium mt-3">⚠️ 如果服务无法启动或出现端口占用错误，请点击右上角的清理所有服务按钮</p>
            </div>
          </div>
        </>
      )}


    </div>
  )
}
