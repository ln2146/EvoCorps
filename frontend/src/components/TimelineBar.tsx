import { useCallback, useEffect, useRef, useState } from 'react'
import { Pause, Play, RotateCcw } from 'lucide-react'
import { setPauseFlag, getSnapshots, restoreSnapshot, type SnapshotInfo } from '../services/api'

interface TimelineBarProps {
  isRunning: boolean
  currentTick: number
  totalTicks: number
  paused: boolean
  onPausedChange: (paused: boolean) => void
  onTickChange: (tick: number) => void
}

export default function TimelineBar({
  isRunning,
  currentTick,
  totalTicks,
  paused,
  onPausedChange,
  onTickChange,
}: TimelineBarProps) {
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([])
  const [restoring, setRestoring] = useState(false)
  const [hoveredTick, setHoveredTick] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Fetch snapshots periodically while running
  useEffect(() => {
    if (!isRunning) return
    let cancelled = false
    const fetch = async () => {
      const data = await getSnapshots()
      if (!cancelled) setSnapshots(data.snapshots)
    }
    fetch()
    const id = setInterval(fetch, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [isRunning])

  // Auto-scroll to keep current tick visible
  useEffect(() => {
    if (!scrollRef.current) return
    const dot = scrollRef.current.querySelector(`[data-tick="${currentTick}"]`) as HTMLElement | null
    if (dot) dot.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [currentTick])

  const handlePauseToggle = useCallback(async () => {
    try {
      const result = await setPauseFlag(!paused)
      onPausedChange(result.paused)
    } catch {
      console.error('Failed to toggle pause')
    }
  }, [paused, onPausedChange])

  const handleRestore = useCallback(async (tick: number) => {
    if (restoring) return
    if (!confirm(`回退到 Tick ${tick} 将从该时间步继续，确认？`)) return
    setRestoring(true)
    try {
      const result = await restoreSnapshot(tick)
      if (result.success) {
        onTickChange(tick)
        onPausedChange(false)
      } else {
        alert('回退失败')
      }
    } catch {
      alert('回退请求失败')
    } finally {
      setRestoring(false)
    }
  }, [restoring, onTickChange, onPausedChange])

  const snapshotSet = new Set(snapshots.map(s => s.tick))

  const getTooltip = (tick: number): string | undefined => {
    const snap = snapshots.find(s => s.tick === tick)
    if (!snap) return undefined
    const t = snap.timestamp ? new Date(snap.timestamp).toLocaleTimeString() : ''
    return `Tick ${tick}${t ? ` · ${t}` : ''}\n点击回退到此时间步`
  }

  if (!isRunning && totalTicks === 0) return null

  const displayTotal = totalTicks || currentTick || 1

  return (
    <div className="glass-card px-5 py-4 flex items-center gap-4">
      {/* Pause / Resume button */}
      <button
        disabled={!isRunning || restoring}
        onClick={handlePauseToggle}
        className={`
          flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold
          transition-all duration-200 min-w-[90px]
          ${!isRunning || restoring
            ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
            : paused
              ? 'bg-gradient-to-r from-emerald-500 to-green-500 text-white hover:shadow-lg'
              : 'bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:shadow-lg'
          }
        `}
      >
        {paused ? <Play size={16} /> : <Pause size={16} />}
        {paused ? '继续' : '暂停'}
      </button>

      {/* Tick label */}
      <div className="flex flex-col items-center min-w-[80px]">
        <span className="text-xs text-slate-500 leading-tight">时间步</span>
        <span className="text-lg font-bold text-slate-800 leading-tight">
          {currentTick} <span className="text-sm font-normal text-slate-400">/ {displayTotal}</span>
        </span>
      </div>

      {/* Timeline dots */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-x-auto scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent"
      >
        <div className="flex items-center gap-0 py-2 min-w-min">
          {Array.from({ length: displayTotal }, (_, i) => {
            const tick = i + 1
            const isCurrent = tick === currentTick
            const isCompleted = tick < currentTick
            const hasSnapshot = snapshotSet.has(tick)
            const isHovered = hoveredTick === tick
            const canClick = isCompleted && hasSnapshot && isRunning && !restoring

            return (
              <div key={tick} className="flex items-center" data-tick={tick}>
                {/* Connector line */}
                {i > 0 && (
                  <div
                    className={`h-[2px] transition-all duration-300 ${
                      isCompleted || isCurrent
                        ? 'w-3 sm:w-4 md:w-5 bg-blue-400'
                        : 'w-3 sm:w-4 md:w-5 bg-slate-200'
                    }`}
                  />
                )}

                {/* Dot */}
                <div className="relative group">
                  <button
                    disabled={!canClick}
                    onClick={() => canClick && handleRestore(tick)}
                    onMouseEnter={() => setHoveredTick(tick)}
                    onMouseLeave={() => setHoveredTick(null)}
                    title={canClick ? getTooltip(tick) : `Tick ${tick}`}
                    className={`
                      rounded-full transition-all duration-200 flex items-center justify-center
                      ${isCurrent
                        ? 'w-5 h-5 bg-blue-500 ring-4 ring-blue-200 shadow-md'
                        : isCompleted && hasSnapshot
                          ? `w-3.5 h-3.5 bg-blue-500 cursor-pointer hover:w-4.5 hover:h-4.5 hover:ring-2 hover:ring-blue-300 hover:shadow ${isHovered ? 'ring-2 ring-blue-300' : ''}`
                          : isCompleted
                            ? 'w-3 h-3 bg-blue-300'
                            : 'w-3 h-3 bg-slate-200 border border-slate-300'
                      }
                    `}
                  >
                    {isCurrent && paused && (
                      <Pause size={10} className="text-white" />
                    )}
                    {canClick && isHovered && !isCurrent && (
                      <RotateCcw size={8} className="text-white" />
                    )}
                  </button>

                  {/* Tick number label — show for first, last, current, and every 5th */}
                  {(tick === 1 || tick === displayTotal || isCurrent || tick % 5 === 0) && (
                    <span
                      className={`absolute -bottom-4 left-1/2 -translate-x-1/2 text-[10px] leading-none whitespace-nowrap ${
                        isCurrent ? 'text-blue-600 font-bold' : 'text-slate-400'
                      }`}
                    >
                      {tick}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Status badge */}
      {isRunning && (
        <div className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full ${
          restoring
            ? 'bg-purple-100 text-purple-700'
            : paused
              ? 'bg-amber-100 text-amber-700'
              : 'bg-emerald-100 text-emerald-700'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            restoring ? 'bg-purple-500' : paused ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'
          }`} />
          {restoring ? '回退中...' : paused ? '已暂停' : '运行中'}
        </div>
      )}
    </div>
  )
}
