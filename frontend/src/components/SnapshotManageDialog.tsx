import { useState, useEffect } from 'react'
import { Trash2, Database, Clock, AlertTriangle, RefreshCw } from 'lucide-react'
import { getSavedSnapshots, deleteSnapshot, deleteAllSnapshots, type SavedSnapshot } from '../services/api'

interface SnapshotManageDialogProps {
  open: boolean
  onClose: () => void
  onDeleted?: () => void
}

export default function SnapshotManageDialog({ open, onClose, onDeleted }: SnapshotManageDialogProps) {
  const [snapshots, setSnapshots] = useState<SavedSnapshot[]>([])
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deleteAllConfirm, setDeleteAllConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 加载快照列表
  const loadSnapshots = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getSavedSnapshots()
      setSnapshots(result)
    } catch (err) {
      setError('加载快照列表失败')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // 对话框打开时加载快照
  useEffect(() => {
    if (open) {
      loadSnapshots()
      setDeleteAllConfirm(false)
    }
  }, [open])

  // 删除单个快照
  const handleDelete = async (sessionId: string) => {
    if (!confirm('确定要删除这个快照吗？此操作不可撤销。')) {
      return
    }

    setDeleting(sessionId)
    try {
      const result = await deleteSnapshot(sessionId)
      if (result.success) {
        setSnapshots(prev => prev.filter(s => s.id !== sessionId))
        onDeleted?.()
      } else {
        alert(`删除失败: ${result.message}`)
      }
    } catch (err) {
      alert('删除失败')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  // 删除所有快照
  const handleDeleteAll = async () => {
    if (!deleteAllConfirm) {
      setDeleteAllConfirm(true)
      return
    }

    setDeleting('all')
    try {
      const result = await deleteAllSnapshots()
      if (result.success) {
        setSnapshots([])
        setDeleteAllConfirm(false)
        onDeleted?.()
        alert(`成功删除 ${result.deleted_count} 个快照`)
      } else {
        alert(`删除失败: ${result.message}`)
      }
    } catch (err) {
      alert('删除失败')
      console.error(err)
    } finally {
      setDeleting(null)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[99999] bg-slate-700/22 backdrop-blur-[2px] flex items-start justify-center pt-10 px-6 pb-6">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200/85 bg-gradient-to-br from-slate-100/97 via-slate-50/96 to-blue-50/94 shadow-[0_28px_90px_rgba(15,23,42,0.18)] max-h-[80vh] flex flex-col">
        {/* 标题 */}
        <div className="p-6 border-b border-slate-200/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="text-blue-500" size={24} />
              <div>
                <h3 className="text-2xl font-bold text-slate-800">快照管理</h3>
                <p className="text-sm text-slate-600 mt-1">
                  管理已保存的仿真快照
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
            >
              关闭
            </button>
          </div>
        </div>

        {/* 操作栏 */}
        <div className="px-6 py-3 border-b border-slate-200/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>共 {snapshots.length} 个快照</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadSnapshots}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              刷新
            </button>
            {snapshots.length > 0 && (
              <button
                onClick={handleDeleteAll}
                disabled={deleting === 'all'}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50 ${
                  deleteAllConfirm
                    ? 'bg-red-500 text-white hover:bg-red-600'
                    : 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100'
                }`}
              >
                <Trash2 size={14} />
                {deleteAllConfirm ? '确认删除全部？' : '删除全部'}
              </button>
            )}
          </div>
        </div>

        {/* 快照列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw size={24} className="animate-spin text-slate-400" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <AlertTriangle size={32} className="text-red-400" />
              <p className="text-red-600">{error}</p>
              <button
                onClick={loadSnapshots}
                className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              >
                重试
              </button>
            </div>
          ) : snapshots.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Database size={32} className="text-slate-300" />
              <p className="text-slate-500">暂无已保存的快照</p>
              <p className="text-sm text-slate-400">结束演示时可保存快照</p>
            </div>
          ) : (
            <div className="space-y-3">
              {snapshots.map((snapshot) => (
                <div
                  key={snapshot.id}
                  className="bg-white/70 rounded-2xl p-4 border border-white/40 shadow-sm hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-slate-800 truncate">
                          {snapshot.name || `快照 ${snapshot.id}`}
                        </h4>
                        {snapshot.name && snapshot.name !== `快照 ${snapshot.id}` && (
                          <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-600 text-xs font-medium">
                            已命名
                          </span>
                        )}
                      </div>
                      {snapshot.description && (
                        <p className="text-sm text-slate-600 mb-2 line-clamp-2">
                          {snapshot.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <div className="flex items-center gap-1">
                          <Clock size={12} />
                          <span>
                            {new Date(snapshot.created_at).toLocaleString('zh-CN', {
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                        <span>{snapshot.tick_count} 个时间步</span>
                        {snapshot.total_users !== undefined && (
                          <span>{snapshot.total_users} 用户</span>
                        )}
                        {snapshot.total_posts !== undefined && (
                          <span>{snapshot.total_posts} 帖子</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(snapshot.id)}
                      disabled={deleting === snapshot.id}
                      className="ml-3 p-2 rounded-lg text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
                      title="删除快照"
                    >
                      {deleting === snapshot.id ? (
                        <RefreshCw size={16} className="animate-spin" />
                      ) : (
                        <Trash2 size={16} />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
