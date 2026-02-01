import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Activity, FlaskConical, BarChart3, Settings, ChevronLeft, ChevronRight, ArrowLeft, MessageSquare, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface DashboardLayoutProps {
  children: ReactNode
}

const navItems = [
  { path: '/dashboard', label: '主页', icon: Home },
  { path: '/dashboard/service', label: '实验设置', icon: Settings },
  { path: '/dashboard/monitoring', label: '数据监控', icon: Activity },
  { path: '/dashboard/experiment', label: '实验管理', icon: FlaskConical },
  { path: '/dashboard/visualization', label: '关系图谱', icon: BarChart3 },
  { path: '/dashboard/interview', label: '采访功能', icon: MessageSquare },
]

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
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
        <div className="p-6 border-b border-white/20">
          {!isCollapsed && (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg">
                <Zap size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
                  EvoCorps
                </h1>
                <p className="text-sm text-slate-500">静态演示</p>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-r from-blue-500 to-green-500 flex items-center justify-center shadow-lg mx-auto">
              <Zap size={24} className="text-white" />
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
                {!isCollapsed && <span className="font-medium text-lg">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* 底部按钮区 */}
        {!isCollapsed && (
          <div className="p-4 border-t border-white/20 space-y-2">
            <button
              onClick={() => navigate('/dynamic')}
              className="btn-apple w-full flex items-center justify-center gap-2 text-slate-700 font-medium text-base"
            >
              <span>进入动态演示</span>
            </button>
            <button
              onClick={() => navigate('/')}
              className="btn-apple w-full flex items-center justify-center gap-2 text-slate-700 font-medium text-base"
            >
              <ArrowLeft size={18} />
              <span>返回首页</span>
            </button>
          </div>
        )}
        {isCollapsed && (
          <div className="p-4 border-t border-white/20 space-y-2">
            <button
              onClick={() => navigate('/dynamic')}
              className="btn-apple w-full flex items-center justify-center text-slate-700"
              title="进入动态演示"
            >
              <span className="text-xs">动态</span>
            </button>
            <button
              onClick={() => navigate('/')}
              className="btn-apple w-full flex items-center justify-center text-slate-700"
              title="返回首页"
            >
              <ArrowLeft size={18} />
            </button>
          </div>
        )}
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 pb-4">
          {children}
        </div>
      </main>
    </div>
  )
}
