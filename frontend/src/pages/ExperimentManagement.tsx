import { useState, useEffect } from 'react'
import { Save, FolderOpen, Trash2, Database, Clock, Tag } from 'lucide-react'
import { getExperiments, saveExperiment, loadExperiment, deleteExperiment, getDatabases, type Experiment } from '../services/api'

export default function ExperimentManagement() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [databases, setDatabases] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  
  // 保存实验表单
  const [showSaveForm, setShowSaveForm] = useState(false)
  const [saveForm, setSaveForm] = useState({
    experiment_name: '',
    scenario_type: 'scenario_1',
    database_name: 'simulation.db'
  })

  // 加载实验列表
  const loadExperiments = async () => {
    const data = await getExperiments()
    setExperiments(data)
  }

  // 加载数据库列表
  const loadDatabases = async () => {
    const dbs = await getDatabases()
    setDatabases(dbs)
    if (dbs.length > 0 && !saveForm.database_name) {
      setSaveForm(prev => ({ ...prev, database_name: dbs[0] }))
    }
  }

  useEffect(() => {
    loadExperiments()
    loadDatabases()
  }, [])

  // 保存当前实验
  const handleSave = async () => {
    if (!saveForm.experiment_name.trim()) {
      alert('请输入实验名称')
      return
    }

    setLoading(true)
    try {
      await saveExperiment(saveForm)
      alert('实验保存成功！')
      setShowSaveForm(false)
      setSaveForm({
        experiment_name: '',
        scenario_type: 'scenario_1',
        database_name: databases[0] || 'simulation.db'
      })
      await loadExperiments()
    } catch (error: any) {
      alert(`保存失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 加载历史实验
  const handleLoad = async (experimentId: string, experimentName: string) => {
    if (!confirm(`确定要加载实验 "${experimentName}" 吗？\n\n当前数据库将被备份，然后恢复到该实验的状态。`)) {
      return
    }

    setLoading(true)
    try {
      await loadExperiment(experimentId)
      alert('实验加载成功！当前数据库已恢复到该实验状态。')
      // 刷新页面以显示新数据
      window.location.reload()
    } catch (error: any) {
      alert(`加载失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 删除实验
  const handleDelete = async (experimentId: string, experimentName: string) => {
    if (!confirm(`确定要删除实验 "${experimentName}" 吗？\n\n此操作不可恢复！`)) {
      return
    }

    setLoading(true)
    try {
      await deleteExperiment(experimentId)
      alert('实验删除成功！')
      await loadExperiments()
    } catch (error: any) {
      alert(`删除失败: ${error.response?.data?.error || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 格式化时间戳
  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return ''
    // timestamp format: YYYYMMDD_HHMMSS
    const year = timestamp.substring(0, 4)
    const month = timestamp.substring(4, 6)
    const day = timestamp.substring(6, 8)
    const hour = timestamp.substring(9, 11)
    const minute = timestamp.substring(11, 13)
    const second = timestamp.substring(13, 15)
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`
  }

  // 场景类型映射
  const scenarioNames: Record<string, string> = {
    'scenario_1': '场景1 - 基线模拟',
    'scenario_2': '场景2 - 恶意攻击',
    'scenario_3': '场景3 - 极端内容',
    'scenario_4': '场景4 - 舆论平衡'
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
            <Database size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">实验管理</h1>
            <p className="text-slate-600">保存和加载模拟实验快照</p>
          </div>
        </div>
      </div>

      {/* 保存当前实验 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Save size={24} className="text-blue-600" />
          <h2 className="text-xl font-bold text-slate-800">保存当前实验</h2>
        </div>

        {!showSaveForm ? (
          <button
            onClick={() => setShowSaveForm(true)}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
          >
            保存为新实验
          </button>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                实验名称
              </label>
              <input
                type="text"
                value={saveForm.experiment_name}
                onChange={(e) => setSaveForm({ ...saveForm, experiment_name: e.target.value })}
                placeholder="例如: experiment_20260110_193906"
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  场景类型
                </label>
                <select
                  value={saveForm.scenario_type}
                  onChange={(e) => setSaveForm({ ...saveForm, scenario_type: e.target.value })}
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="scenario_1">场景1 - 基线模拟</option>
                  <option value="scenario_2">场景2 - 恶意攻击</option>
                  <option value="scenario_3">场景3 - 极端内容</option>
                  <option value="scenario_4">场景4 - 舆论平衡</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  数据库
                </label>
                <select
                  value={saveForm.database_name}
                  onChange={(e) => setSaveForm({ ...saveForm, database_name: e.target.value })}
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {databases.map(db => (
                    <option key={db} value={db}>{db}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '保存中...' : '保存实验'}
              </button>
              <button
                onClick={() => setShowSaveForm(false)}
                disabled={loading}
                className="px-6 py-3 bg-slate-200 text-slate-700 rounded-xl font-medium hover:bg-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 已保存的实验 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <FolderOpen size={24} className="text-orange-600" />
          <h2 className="text-xl font-bold text-slate-800">已保存的实验</h2>
          <span className="text-sm text-slate-500">({experiments.length})</span>
        </div>

        {experiments.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Database size={48} className="mx-auto mb-4 opacity-50" />
            <p>暂无保存的实验</p>
            <p className="text-sm mt-2">完成模拟后，可以保存实验快照以便后续分析</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">#</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">实验名称</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">场景类型</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">保存时间</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">数据库</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">情绪数据</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-600">操作</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp, index) => (
                  <tr key={exp.experiment_id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 text-slate-600">{index + 1}</td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-800">{exp.experiment_name}</div>
                      <div className="text-xs text-slate-500 font-mono">{exp.experiment_id}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        <Tag size={12} />
                        {scenarioNames[exp.scenario_type] || exp.scenario_type}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Clock size={14} />
                        {formatTimestamp(exp.timestamp)}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
                        exp.database_saved ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {exp.database_saved ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
                        exp.emotion_data_saved ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {exp.emotion_data_saved ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleLoad(exp.experiment_id, exp.experiment_name)}
                          disabled={loading}
                          className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg text-sm font-medium hover:shadow-lg transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="加载实验数据"
                        >
                          加载实验
                        </button>
                        <button
                          onClick={() => handleDelete(exp.experiment_id, exp.experiment_name)}
                          disabled={loading}
                          className="px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-lg text-sm font-medium hover:shadow-lg transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="删除实验"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 使用说明 */}
      <div className="glass-card p-6 bg-blue-50/50">
        <h3 className="text-lg font-bold text-slate-800 mb-3">使用说明</h3>
        <div className="space-y-2 text-sm text-slate-700">
          <p>1. <strong>保存实验</strong>：完成模拟后，点击"保存为新实验"按钮，系统会保存当前数据库快照和情绪数据</p>
          <p>2. <strong>加载实验</strong>：点击"加载实验"按钮可恢复历史实验状态，当前数据库会自动备份</p>
          <p>3. <strong>删除实验</strong>：点击删除按钮可永久删除实验快照，此操作不可恢复</p>
          <p>4. <strong>数据包含</strong>：每个实验快照包含完整的数据库文件、情绪数据和实验元信息</p>
          <p className="text-orange-600 font-medium mt-3">⚠️ 加载实验会覆盖当前数据库，请确保已保存当前实验或不再需要当前数据</p>
        </div>
      </div>
    </div>
  )
}
