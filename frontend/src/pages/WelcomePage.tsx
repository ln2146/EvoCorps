import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Activity, ArrowRight } from 'lucide-react'

export default function WelcomePage() {
  const navigate = useNavigate()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isLoaded, setIsLoaded] = useState(false)
  const [particles, setParticles] = useState<Array<{ id: number; x: number; y: number; angle: number }>>([])
  const logoRef = useRef<HTMLDivElement>(null)
  const particleIdRef = useRef(0)

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

  // 页面加载动画
  useEffect(() => {
    setIsLoaded(true)
  }, [])

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

  // Logo 点击特效
  const handleLogoClick = () => {
    if (!logoRef.current) return

    const rect = logoRef.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    // 生成粒子
    const newParticles = Array.from({ length: 12 }, (_, i) => ({
      id: particleIdRef.current++,
      x: centerX,
      y: centerY,
      angle: (i / 12) * Math.PI * 2,
    }))

    setParticles(prev => [...prev, ...newParticles])

    // 3 秒后移除粒子
    setTimeout(() => {
      setParticles(prev => prev.filter(p => !newParticles.find(np => np.id === p.id)))
    }, 1000)
  }

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedIndex])

  return (
    <div className="min-h-screen flex items-center justify-between overflow-hidden bg-gradient-to-r from-blue-50 via-cyan-50 to-green-50">
      {/* 粒子效果容器 */}
      <div className="fixed inset-0 pointer-events-none">
        {particles.map(particle => (
          <Particle key={particle.id} particle={particle} />
        ))}
      </div>

      {/* 左侧 Logo */}
      <div 
        className="w-1/2 flex items-center justify-end pr-32"
        ref={logoRef}
      >
        <div
          className={`transition-all duration-1000 ease-out transform ${
            isLoaded 
              ? 'opacity-100 scale-100' 
              : 'opacity-0 scale-75'
          }`}
          onClick={handleLogoClick}
          style={{
            cursor: 'pointer',
            filter: isLoaded ? 'drop-shadow(0 20px 25px rgba(0, 0, 0, 0.1))' : 'drop-shadow(0 0 0 rgba(0, 0, 0, 0))',
          }}
        >
          <img 
            src="/logo.png" 
            alt="EvoCorps Logo" 
            className="w-full max-w-md hover:scale-105 transition-transform duration-300"
          />
        </div>
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
              const cardDelay = index * 200

              return (
                <div
                  key={mode.id}
                  className="absolute transition-all duration-500 ease-out cursor-pointer"
                  style={{
                    transform: `translateY(${offset}px) scale(${scale})`,
                    opacity: isLoaded ? opacity : 0,
                    filter: `blur(${blur}px)`,
                    pointerEvents: isSelected ? 'auto' : 'none',
                    transitionDelay: isLoaded ? '0ms' : `${cardDelay}ms`,
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

// 粒子组件
function Particle({ particle }: { particle: { id: number; x: number; y: number; angle: number } }) {
  const distance = 150
  const endX = particle.x + Math.cos(particle.angle) * distance
  const endY = particle.y + Math.sin(particle.angle) * distance

  return (
    <div
      className="fixed w-2 h-2 rounded-full pointer-events-none"
      style={{
        left: particle.x,
        top: particle.y,
        background: `hsl(${Math.random() * 60 + 180}, 100%, 50%)`,
        animation: `particleExplode 1s ease-out forwards`,
        '--end-x': `${endX - particle.x}px`,
        '--end-y': `${endY - particle.y}px`,
      } as React.CSSProperties & { '--end-x': string; '--end-y': string }}
    />
  )
}
