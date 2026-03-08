import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { Server, Settings, Play, Square, Shield, Save, Bug, Sparkles, Eye } from 'lucide-react'
import axios from 'axios'
import { setAttackFlag, setAttackMode, setAftercareFlag, setModerationFlag, saveSnapshot, getSavedSnapshots } from '../services/api'
import { resolveAttackToggleAction, getAttackModeLabel, type AttackMode } from '../lib/attackModeToggle'
import { startDynamicDemoWithPreset } from '../lib/dynamicDemo/startDemo'
import { useSimulation } from '../contexts/SimulationContext'
import SaveSnapshotDialog from '../components/SaveSnapshotDialog'
import SnapshotSelectDialog from '../components/SnapshotSelectDialog'

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
  const navigate = useNavigate()
  const simulation = useSimulation()
  const [activeTab, setActiveTab] = useState<'service' | 'config'>('config')
  
  // 服务管理状态
  const [status, setStatus] = useState<ServiceStatus>({
    database: 'stopped',
    platform: 'stopped',
    balance: 'stopped'
  })
  const [condaEnv, setCondaEnv] = useState<string>('')
  const [isEnvSaved, setIsEnvSaved] = useState<boolean>(false)

  // 演示启停状态
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)

  // 控制开关状态
  const [enableAttack, setEnableAttack] = useState(false)
  const [attackMode, setAttackModeState] = useState<AttackMode | null>(null)
  const [attackModeDialogOpen, setAttackModeDialogOpen] = useState(false)
  const [enableAftercare, setEnableAftercare] = useState(false)
  const [enableModeration, setEnableModeration] = useState(false)
  const [enableEvoCorps, setEnableEvoCorps] = useState(false)

  // 快照对话框状态
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [showSnapshotSelect, setShowSnapshotSelect] = useState(false)

  // 配置状态
  const [config, setConfig] = useState<ExperimentConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(false)

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

  const platformRunning = status.platform === 'running'
  const dbRunning = status.database === 'running'
  const isRunning = dbRunning && platformRunning

  const handleStartDemo = async (snapshotId?: string, startTick?: number) => {
    if (isRunning || isStarting) return
    setIsStarting(true)
    simulation.setIsStarting(true)
    try {
      const data = await startDynamicDemoWithPreset({
        enableAttack,
        attackMode,
        enableAftercare,
        enableModeration,
        enableEvoCorps,
        snapshotId,
        startTick,
      })

      if (data.success) {
        setStatus(prev => ({ ...prev, database: 'running', platform: 'running' }))
        simulation.setIsRunning(true)
        simulation.setDatabaseRunning(true)
        simulation.setMainRunning(true)
        simulation.setEnableAttack(enableAttack)
        simulation.setAttackMode(attackMode)
        simulation.setEnableAftercare(enableAftercare)
        simulation.setEnableModeration(enableModeration)
        simulation.setEnableEvoCorps(enableEvoCorps)
        navigate('/dynamic')
      } else {
        alert(`启动失败：${data.message || '未知错误'}`)
      }
    } catch (error) {
      alert(`启动失败：${error instanceof Error ? error.message : '网络错误'}`)
    } finally {
      setIsStarting(false)
      simulation.setIsStarting(false)
    }
  }

  const handleStartClick = async () => {
    if (isRunning || isStarting) return
    // 检查是否有已保存的快照
    try {
      const snapshots = await getSavedSnapshots()
      if (snapshots.length > 0) {
        setShowSnapshotSelect(true)
      } else {
        await handleStartDemo()
      }
    } catch {
      await handleStartDemo()
    }
  }

  const handleStopDemo = async () => {
    if (isStopping) return
    // 显示保存快照对话框
    setShowSaveDialog(true)
  }

  const handleSaveAndStop = async (name: string, description: string) => {
    setShowSaveDialog(false)
    setIsStopping(true)
    try {
      // 先保存快照
      await saveSnapshot(name, description)
      // 然后停止演示
      const response = await axios.post('/api/dynamic/stop', {}, { timeout: 10000, validateStatus: () => true })
      if (!response.data.success) {
        alert(`停止失败：${response.data.message || '未知错误'}`)
      }
    } catch (error: any) {
      const msg = error.message || '网络错误'
      if (msg.includes('Network Error') || msg.includes('ECONNREFUSED')) {
        alert('后端服务未响应，已重置前端状态')
      } else {
        alert(`停止失败：${msg}`)
      }
    } finally {
      setIsStopping(false)
    }
  }

  const handleSkipSave = async () => {
    setShowSaveDialog(false)
    setIsStopping(true)
    try {
      const response = await axios.post('/api/dynamic/stop', {}, { timeout: 10000, validateStatus: () => true })
      if (!response.data.success) {
        alert(`停止失败：${response.data.message || '未知错误'}`)
      }
    } catch (error: any) {
      const msg = error.message || '网络错误'
      if (msg.includes('Network Error') || msg.includes('ECONNREFUSED')) {
        alert('后端服务未响应，已重置前端状态')
      } else {
        alert(`停止失败：${msg}`)
      }
    } finally {
      setIsStopping(false)
    }
  }

  const handleSelectSnapshot = async (snapshotId: string, startTick: number) => {
    setShowSnapshotSelect(false)
    await handleStartDemo(snapshotId, startTick)
  }

  const handleStartFresh = async () => {
    setShowSnapshotSelect(false)
    await handleStartDemo()
  }

  const handleToggleAttack = async () => {
    const action = resolveAttackToggleAction({
      enabled: enableAttack,
      selectedMode: attackMode,
    })

    if (action.type === 'open_mode_dialog' || action.type === 'enable') {
      setAttackModeDialogOpen(true)
      return
    }

    // disable
    if (!confirm('是否确认关闭恶意攻击模式？')) return

    if (!platformRunning) {
      setEnableAttack(false)
      setAttackModeState(null)
      return
    }

    setEnableAttack(false)
    try {
      const data = await setAttackFlag(false)
      setEnableAttack(data.attack_enabled)
      if (!data.attack_enabled) setAttackModeState(null)
    } catch {
      setEnableAttack(true)
    }
  }

  const handleSelectAttackMode = async (mode: AttackMode) => {
    setAttackModeState(mode)
    setAttackModeDialogOpen(false)

    if (!platformRunning) {
      setEnableAttack(true)
      return
    }

    setEnableAttack(true)
    try {
      await setAttackMode(mode)
      const data = await setAttackFlag(true)
      setEnableAttack(Boolean(data.attack_enabled))
    } catch {
      setEnableAttack(false)
    }
  }

  const handleToggleAftercare = async () => {
    const next = !enableAftercare
    setEnableAftercare(next)
    if (!platformRunning) return
    try {
      const data = await setAftercareFlag(next)
      setEnableAftercare(data.aftercare_enabled)
    } catch {
      setEnableAftercare(!next)
    }
  }

  const handleToggleModeration = async () => {
    const next = !enableModeration
    setEnableModeration(next)
    if (!platformRunning) {
      fetch('/api/config/moderation', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_moderation: next }),
      }).catch(() => {})
      return
    }
    try {
      const data = await setModerationFlag(next)
      setEnableModeration(data.moderation_enabled)
    } catch {
      setEnableModeration(!next)
    }
  }

  const handleToggleEvoCorps = () => {
    setEnableEvoCorps(!enableEvoCorps)
  }

  const toggles = [
    {
      id: 'attack',
      name: '恶意攻击',
      description: `开启后将模拟恶意水军的协同攻击行为，包括蜂群式、分散式、链式三种攻击模式。${attackMode ? `当前模式：${getAttackModeLabel(attackMode)}` : ''}`,
      icon: Bug,
      color: 'from-red-500 to-orange-500',
      enabled: enableAttack,
      onToggle: handleToggleAttack,
    },
    {
      id: 'aftercare',
      name: '事后干预',
      description: '开启后系统将在攻击行为发生后进行智能干预，降低恶意内容的传播影响。',
      icon: Sparkles,
      color: 'from-purple-500 to-pink-500',
      enabled: enableAftercare,
      onToggle: handleToggleAftercare,
    },
    {
      id: 'moderation',
      name: '内容审核',
      description: '开启后系统将对平台内容进行实时审核，识别并标记违规内容。',
      icon: Eye,
      color: 'from-indigo-500 to-blue-500',
      enabled: enableModeration,
      onToggle: handleToggleModeration,
    },
    {
      id: 'evocorps',
      name: '舆论平衡',
      description: '智能监控平台舆论走向，识别极端言论和极化趋势，自动进行干预平衡。仅在场景4中需要，需要配置梯子。',
      icon: Shield,
      color: 'from-orange-500 to-red-500',
      enabled: enableEvoCorps,
      onToggle: handleToggleEvoCorps,
    },
  ]

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
                      普通用户数量
                    </label>
                    <input
                      type="number"
                      value={config.num_users}
                      onChange={(e) => updateConfig('num_users', parseInt(e.target.value))}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      min="1"
                    />
                    <p className="text-xs text-slate-500 mt-1">模拟的普通用户总数</p>
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
                  <p>• 普通用户数量和时间步数会直接影响实验运行时间</p>
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

          {/* 开启/停止演示 */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-4">
              <button
                onClick={handleStartClick}
                disabled={isRunning || isStarting || isStopping}
                className="btn-primary inline-flex items-center justify-center gap-2 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex-1"
              >
                <Play size={18} />
                {isStarting ? '启动中...' : isRunning ? '运行中' : '开启演示'}
              </button>
              <button
                onClick={handleStopDemo}
                disabled={isStopping}
                className="btn-secondary inline-flex items-center justify-center gap-2 bg-gradient-to-r from-red-500 to-rose-500 text-white border-transparent hover:shadow-xl text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex-1"
              >
                <Square size={18} />
                {isStopping ? '结束中...' : '结束演示'}
              </button>
            </div>
          </div>

          {/* 功能开关列表 */}
          <div className="grid gap-6">
            {toggles.map((toggle) => {
              const Icon = toggle.icon
              return (
                <div key={toggle.id} className="glass-card p-6">
                  <div className="flex items-start gap-4">
                    <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${toggle.color} flex items-center justify-center shadow-lg flex-shrink-0`}>
                      <Icon size={32} className="text-white" />
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-bold text-slate-800">{toggle.name}</h3>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          toggle.enabled
                            ? 'bg-green-100 text-green-700'
                            : 'bg-slate-100 text-slate-600'
                        }`}>
                          {toggle.enabled ? '已开启' : '已关闭'}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed mb-3">{toggle.description}</p>
                    </div>

                    <div className="flex flex-col gap-2">
                      <button
                        onClick={toggle.onToggle}
                        className={`btn-primary inline-flex items-center justify-center gap-2 text-lg font-medium ${toggle.enabled ? '!bg-gradient-to-r !from-red-500 !to-rose-500' : ''}`}
                      >
                        {toggle.enabled ? <Square size={18} /> : <Play size={18} />}
                        {toggle.enabled ? '关闭' : '开启'}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

        </>
      )}


      {attackModeDialogOpen && (
        <AttackModeDialog
          onSelect={handleSelectAttackMode}
          onClose={() => setAttackModeDialogOpen(false)}
        />
      )}

      {/* 保存快照对话框 */}
      <SaveSnapshotDialog
        open={showSaveDialog}
        onSave={handleSaveAndStop}
        onSkip={handleSkipSave}
        onCancel={() => setShowSaveDialog(false)}
      />

      {/* 快照选择对话框 */}
      <SnapshotSelectDialog
        open={showSnapshotSelect}
        onSelect={handleSelectSnapshot}
        onStartFresh={handleStartFresh}
        onCancel={() => setShowSnapshotSelect(false)}
      />
    </div>
  )
}

function AttackModeDialog({
  onSelect,
  onClose,
}: {
  onSelect: (mode: AttackMode) => void
  onClose: () => void
}) {
  if (typeof document === 'undefined') return null

  return createPortal(
    <div className="fixed inset-0 z-[99999] bg-slate-700/22 backdrop-blur-[2px] flex items-start justify-center pt-10 px-6 pb-6">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200/85 bg-gradient-to-br from-slate-100/97 via-slate-50/96 to-blue-50/94 shadow-[0_28px_90px_rgba(15,23,42,0.18)] p-10">
        <h3 className="text-3xl font-bold text-slate-800">选择恶意攻击模式</h3>
        <p className="text-base text-slate-600 mt-2">请选择本次开启时使用的攻击协同模式。</p>

        <div className="mt-6 grid grid-cols-1 gap-4">
          <button
            type="button"
            onClick={() => onSelect('swarm')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">蜂群式</div>
            <div className="text-sm text-slate-600 mt-1">集中攻击同一目标，放大互动信号。</div>
          </button>
          <button
            type="button"
            onClick={() => onSelect('dispersed')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">游离式</div>
            <div className="text-sm text-slate-600 mt-1">分散到多条帖子，降低集中痕迹。</div>
          </button>
          <button
            type="button"
            onClick={() => onSelect('chain')}
            className="w-full text-left rounded-2xl border border-slate-200/90 bg-white/72 p-5 hover:border-blue-300 hover:bg-white/92 transition-all duration-200 hover:shadow-lg"
          >
            <div className="font-semibold text-xl text-slate-800">链式传播</div>
            <div className="text-sm text-slate-600 mt-1">主导账号→扩散账号→控评账号的三层协同攻击。</div>
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
