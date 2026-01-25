import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Server, Activity, FlaskConical, BarChart3, Settings, ChevronLeft, ChevronRight } from 'lucide-react'

interface LayoutProps {
  children: ReactNode
}

const navItems = [
  { path: '/', label: '主页', icon: Home },
  { path: '/service', label: '服务管理', icon: Server },
  { path: '/monitoring', label: '数据监控', icon: Activity },
  { path: '/experiment', label: '实验管理', icon: FlaskConical },
  { path: '/visualization', label: '数据可视化', icon: BarChart3 },
  { path: '/config', label: '配置', icon: Settings },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 侧边栏 */}
      <aside 
        className={`glass-sidebar flex flex-col transition-all duration-300 ease-in-out relative ${
          isCollapsed ? 'w-20' : 'w-64'
        } m-4 rounded-3xl shadow-2xl`}
      >
        {/* 折叠按钮 - 放在右侧边框中间 */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-12 bg-white/80 backdrop-blur-xl rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center border border-white/30 hover:scale-110 z-10"
        >
          {isCollapsed ? (
            <ChevronRight size={16} className="text-slate-700" />
          ) : (
            <ChevronLeft size={16} className="text-slate-700" />
          )}
        </button>

        {/* Logo */}
        <div className="p-6 border-b border-white/20 flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-xl">E</span>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
                  EvoCorps
                </h1>
                <p className="text-xs text-slate-500">舆论平衡系统</p>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg mx-auto">
              <span className="text-white font-bold text-xl">E</span>
            </div>
          )}
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${isActive ? 'active' : 'text-slate-700'} ${
                  isCollapsed ? 'justify-center' : ''
                }`}
                title={isCollapsed ? item.label : ''}
              >
                <Icon size={20} />
                {!isCollapsed && <span className="font-medium">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* 底部信息 */}
        {!isCollapsed && (
          <div className="p-4 border-t border-white/20">
            <div className="glass-card p-4">
              <p className="text-xs text-slate-600 mb-1">系统版本</p>
              <p className="text-sm font-semibold text-slate-800">v1.0.0</p>
            </div>
          </div>
        )}
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
