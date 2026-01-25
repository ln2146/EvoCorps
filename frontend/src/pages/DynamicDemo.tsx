import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Rocket, Construction } from 'lucide-react'

export default function DynamicDemo() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl text-center space-y-8">
        {/* 图标 */}
        <div className="flex justify-center">
          <div className="w-32 h-32 rounded-3xl bg-gradient-to-r from-cyan-500 to-green-500 flex items-center justify-center shadow-2xl">
            <Rocket size={64} className="text-white" />
          </div>
        </div>

        {/* 标题 */}
        <div>
          <h1 className="text-4xl font-bold text-slate-800 mb-4">动态演示模式</h1>
          <p className="text-xl text-slate-600">实时运行模拟和监控系统</p>
        </div>

        {/* 功能说明 */}
        <div className="glass-card p-8 text-left">
          <div className="flex items-start gap-4 mb-6">
            <Construction size={24} className="text-cyan-500 flex-shrink-0 mt-1" />
            <div>
              <h3 className="text-lg font-semibold text-slate-800 mb-2">功能开发中</h3>
              <p className="text-slate-600">
                动态演示模式正在开发中，将提供以下功能：
              </p>
            </div>
          </div>

          <ul className="space-y-3 ml-10">
            <li className="flex items-start gap-3">
              <span className="text-cyan-500 font-bold">•</span>
              <span className="text-slate-700">实时启动和控制模拟实验</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-500 font-bold">•</span>
              <span className="text-slate-700">动态监控舆论变化和系统干预</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-500 font-bold">•</span>
              <span className="text-slate-700">实时调整参数和策略</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-500 font-bold">•</span>
              <span className="text-slate-700">WebSocket 实时数据推送</span>
            </li>
          </ul>
        </div>

        {/* 返回按钮 */}
        <button
          onClick={() => navigate('/')}
          className="btn-primary inline-flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          返回首页
        </button>
      </div>
    </div>
  )
}
