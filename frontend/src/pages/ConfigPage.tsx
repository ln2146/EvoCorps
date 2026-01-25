import { Settings, Save, RotateCcw } from 'lucide-react'

export default function ConfigPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center shadow-lg">
            <Settings size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-800">系统配置</h1>
            <p className="text-slate-600">管理系统参数和运行配置</p>
          </div>
        </div>
      </div>

      {/* 基础配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">基础配置</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">默认用户数量</label>
            <input 
              type="number" 
              defaultValue={100}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">默认时间步数</label>
            <input 
              type="number" 
              defaultValue={50}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">AI 引擎</label>
            <select className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
              <option>GPT-4</option>
              <option>GPT-3.5-Turbo</option>
              <option>Claude-3</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Temperature</label>
            <input 
              type="number" 
              step="0.1"
              defaultValue={0.7}
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* 恶意机器人系统配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">恶意机器人系统</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input type="checkbox" className="w-5 h-5 rounded" defaultChecked />
            <span className="text-slate-700">启用恶意机器人系统</span>
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">集群大小</label>
              <input 
                type="number" 
                defaultValue={10}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">攻击概率</label>
              <input 
                type="number" 
                step="0.1"
                defaultValue={0.3}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">初始攻击阈值</label>
              <input 
                type="number" 
                defaultValue={15}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">后续攻击间隔</label>
              <input 
                type="number" 
                defaultValue={30}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 舆论平衡系统配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">舆论平衡系统</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input type="checkbox" className="w-5 h-5 rounded" defaultChecked />
            <span className="text-slate-700">启用舆论平衡系统</span>
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">干预阈值</label>
              <input 
                type="number" 
                step="0.1"
                defaultValue={0.7}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">响应延迟（分钟）</label>
              <input 
                type="number" 
                defaultValue={5}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">监控间隔（分钟）</label>
              <select className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                <option value="1">1 分钟（超高频）</option>
                <option value="5">5 分钟（高频）</option>
                <option value="10">10 分钟（中高频）</option>
                <option value="30" selected>30 分钟（标准）</option>
                <option value="60">60 分钟（低频）</option>
              </select>
            </div>
          </div>
          <label className="flex items-center gap-3">
            <input type="checkbox" className="w-5 h-5 rounded" defaultChecked />
            <span className="text-slate-700">启用反馈迭代系统</span>
          </label>
        </div>
      </div>

      {/* 事实核查配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">事实核查系统</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input type="checkbox" className="w-5 h-5 rounded" />
            <span className="text-slate-700">启用第三方事实核查</span>
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">每步核查数量</label>
              <input 
                type="number" 
                defaultValue={10}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">核查 Temperature</label>
              <input 
                type="number" 
                step="0.1"
                defaultValue={0.3}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Prebunking 系统配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">Prebunking 系统</h2>
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input type="checkbox" className="w-5 h-5 rounded" />
            <span className="text-slate-700">启用 Prebunking 系统</span>
          </label>
          <p className="text-sm text-slate-600">
            在用户查看潜在误导性内容前，提前插入安全提示和背景知识
          </p>
        </div>
      </div>

      {/* API 配置 */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-slate-800 mb-4">API 配置</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">OpenAI API Key</label>
            <input 
              type="password" 
              placeholder="sk-..."
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Base URL</label>
            <input 
              type="text" 
              placeholder="https://api.openai.com/v1"
              className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3">
        <button className="btn-primary flex items-center gap-2">
          <Save size={20} />
          保存配置
        </button>
        <button className="btn-secondary flex items-center gap-2">
          <RotateCcw size={20} />
          重置为默认
        </button>
      </div>
    </div>
  )
}
