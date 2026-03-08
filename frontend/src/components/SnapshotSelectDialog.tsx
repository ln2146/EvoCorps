import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Play, RotateCcw, Clock, Users, FileText, ChevronRight, Settings } from 'lucide-react'
import { getSavedSnapshots, type SavedSnapshot } from '../services/api'

interface SnapshotSelectDialogProps {
  open: boolean
  onSelect: (snapshotId: string, startTick: number) => Promise<void>
  onStartFresh: () => Promise<void>
  onCancel: () => void
  onManageSnapshots?: () => void
}

export default function SnapshotSelectDialog({ open, onSelect, onStartFresh, onCancel, onManageSnapshots }: SnapshotSelectDialogProps) {
  const [snapshots, setSnapshots] = useState<SavedSnapshot[]>([])
  const [selectedSnapshot, setSelectedSnapshot] = useState<SavedSnapshot | null>(null)
  const [selectedTick, setSelectedTick] = useState(1)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    if (open) {
      loadSnapshots()
    }
  }, [open])

  const loadSnapshots = async () => {
    setLoading(true)
    try {
      const data = await getSavedSnapshots()
      setSnapshots(data)
      if (data.length > 0) {
        // 默认选择最新的快照
        setSelectedSnapshot(data[0])
        const lastTick = data[0].ticks[data[0].ticks.length - 1]?.tick || 1
        setSelectedTick(lastTick)
      }
    } catch (error) {
      console.error('Failed to load snapshots:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = async () => {
    if (!selectedSnapshot) return

    setStarting(true)
    try {
      await onSelect(selectedSnapshot.id, selectedTick)
    } catch (error) {
      alert('启动失败')
      console.error(error)
    } finally {
      setStarting(false)
    }
  }

  const handleStartFresh = async () => {
    setStarting(true)
    try {
      await onStartFresh()
    } catch (error) {
      alert('启动失败')
      console.error(error)
    } finally {
      setStarting(false)
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-[99999] bg-slate-700/50 backdrop-blur-sm flex items-start justify-center pt-10 px-6 pb-6 overflow-y-auto">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
              <RotateCcw size={20} className="text-white" />
            </div>
            <h2 className="text-xl font-bold text-slate-800">选择快照</h2>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
            <span className="ml-3 text-slate-600">加载快照列表...</span>
          </div>
        ) : snapshots.length === 0 ? (
          <div className="text-center py-12">
            <FileText size={48} className="mx-auto text-slate-300 mb-3" />
            <p className="text-slate-600">没有已保存的快照</p>
            <p className="text-sm text-slate-500 mt-2">直接点击下方"重新开始"按钮启动新演示</p>
          </div>
        ) : (
          <div className="flex flex-1 min-h-[400px]">
            {/* 左侧： 快照列表 */}
            <div className="w-1/2 border-r border-slate-200 p-4 overflow-y-auto">
              <div className="space-y-2">
                {snapshots.map((snapshot) => (
                  <div
                    key={snapshot.id}
                    onClick={() => {
                      setSelectedSnapshot(snapshot)
                      const lastTick = snapshot.ticks[snapshot.ticks.length - 1]?.tick || 1
                      setSelectedTick(lastTick)
                    }}
                    className={`
                      p-4 rounded-xl cursor-pointer transition-all
                      ${selectedSnapshot?.id === snapshot.id
                        ? 'bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-400'
                        : 'bg-slate-50 border-2 border-transparent hover:border-slate-200'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-slate-800">{snapshot.name}</h3>
                        {snapshot.description && (
                          <p className="text-sm text-slate-600 mt-1">{snapshot.description}</p>
                        )}
                      </div>
                      <span className="text-xs text-slate-500">
                        {snapshot.tick_count} ticks
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Users size={12} />
                        {snapshot.total_users}
                      </span>
                      <span className="flex items-center gap-1">
                        <FileText size={12} />
                        {snapshot.total_posts}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {formatDate(snapshot.saved_at || snapshot.created_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 右侧: Tick 时间轴 */}
            {selectedSnapshot && (
              <div className="w-1/2 p-4 overflow-y-auto">
                <h4 className="text-sm font-medium text-slate-700 mb-3">选择起始时间步</h4>
                <div className="space-y-1 max-h-[300px] overflow-y-auto pr-2">
                  {selectedSnapshot.ticks.map((tickInfo) => (
                    <div
                      key={tickInfo.tick}
                      onClick={() => setSelectedTick(tickInfo.tick)}
                      className={`
                        flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all
                        ${selectedTick === tickInfo.tick
                          ? 'bg-blue-100 border border-blue-400'
                          : 'hover:bg-slate-100'
                        }
                      `}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`
                          w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                          ${selectedTick === tickInfo.tick
                            ? 'bg-blue-500 text-white'
                            : 'bg-slate-200 text-slate-700'
                          }
                        `}>
                          {tickInfo.tick}
                        </span>
                        <div>
                          <div className="text-sm font-medium text-slate-700">Tick {tickInfo.tick}</div>
                          <div className="text-xs text-slate-500">
                            {tickInfo.user_count} 用户 · {tickInfo.post_count} 帖子
                          </div>
                        </div>
                      </div>
                      {selectedTick === tickInfo.tick && (
                        <ChevronRight size={16} className="text-blue-500" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 底部按钮 */}
        <div className="flex gap-3 justify-between p-6 border-t border-slate-200">
          <div>
            {onManageSnapshots && (
              <button
                onClick={() => {
                  onCancel()
                  onManageSnapshots()
                }}
                className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors flex items-center gap-2"
              >
                <Settings size={16} />
                管理快照
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleStartFresh}
              disabled={starting}
              className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <Play size={16} />
              重新开始
            </button>
            <button
              onClick={handleSelect}
              disabled={!selectedSnapshot || starting}
              className="px-6 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 text-white font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {starting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  启动中...
                </>
              ) : (
                <>
                  <RotateCcw size={16} />
                  从 Tick {selectedTick} 继续
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
