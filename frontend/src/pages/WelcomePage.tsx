import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Activity, ArrowRight } from 'lucide-react'

export default function WelcomePage() {
  const navigate = useNavigate()
  const [selectedIndex, setSelectedIndex] = useState(0)

  const modes = [
    {
      id: 'static',
      title: '静态演示',
      description: '查看系统数据和可视化分析',
      icon: BarChart3,
      gradient: 'from-blue-500 to-cyan-500',
      path: '/dashboard',
    },
    {
      id: 'dynamic',
      title: '动态演示',
      description: '实时运行模拟和监控系统',
      icon: Activity,
      gradient: 'from-cyan-500 to-green-500',
      path: '/dynamic',
    },
  ]

  const handleWheel = (e: React.WheelEvent) => {
    if (e.deltaY > 0 && selectedIndex < modes.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    } else if (e.deltaY < 0 && selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown' && selectedIndex < modes.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    } else if (e.key === 'ArrowUp' && selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1)
    } else if (e.key === 'Enter') {
      navigate(modes[selectedIndex].path)
    }
  }

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedIndex])

  return (
    <div className="min-h-screen flex items-center justify-between overflow-hidden">
      {/* 左侧 Logo */}
      <div className="w-1/2 flex items-center justify-end pr-32">
        <img 
          src="/logo.png" 
          alt="EvoCorps Logo" 
          className="w-full max-w-md drop-shadow-2xl"
        />
      </div>

      {/* 右侧选择区域 */}
      <div className="w-1/2 h-screen relative flex items-center justify-start pl-16">
        {/* 左侧半圆 + 右侧长方形背景 */}
        <div className="absolute inset-0 overflow-hidden">
          <div 
            className="absolute top-0 bottom-0 right-0 bg-white/60 backdrop-blur-3xl"
            style={{
              left: '0',
              width: '100%',
              borderTopLeftRadius: '50%',
              borderBottomLeftRadius: '50%',
              boxShadow: 'inset 2px 0 4px rgba(0, 0, 0, 0.05)',
            }}
          />
        </div>

        {/* 滑动选择器容器 */}
        <div 
          className="relative z-10 w-full max-w-xl"
          onWheel={handleWheel}
        >
          {/* 卡片容器 */}
          <div className="relative h-[400px] flex items-center justify-center">
            {modes.map((mode, index) => {
              const Icon = mode.icon
              const offset = (index - selectedIndex) * 120
              const isSelected = index === selectedIndex
              const scale = isSelected ? 1 : 0.85
              const opacity = isSelected ? 1 : 0.3
              const blur = isSelected ? 0 : 4

              return (
                <div
                  key={mode.id}
                  className="absolute transition-all duration-500 ease-out cursor-pointer"
                  style={{
                    transform: `translateY(${offset}px) scale(${scale})`,
                    opacity: opacity,
                    filter: `blur(${blur}px)`,
                    pointerEvents: isSelected ? 'auto' : 'none',
                  }}
                  onClick={() => isSelected && navigate(mode.path)}
                >
                  <div className="glass-card p-8 w-[480px] hover:shadow-2xl transition-shadow">
                    <div className="flex items-center gap-6">
                      <div className={`w-20 h-20 rounded-2xl bg-gradient-to-r ${mode.gradient} flex items-center justify-center shadow-lg flex-shrink-0`}>
                        <Icon size={40} className="text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-3xl font-bold text-slate-800 mb-2">
                          {mode.title}
                        </h3>
                        <p className="text-slate-600 text-lg">{mode.description}</p>
                      </div>
                      {isSelected && (
                        <ArrowRight 
                          size={32} 
                          className="text-slate-400 animate-pulse flex-shrink-0" 
                        />
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
