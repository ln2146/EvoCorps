import { useState } from 'react'
import { createPortal } from 'react-dom'
import { Save } from 'lucide-react'

interface SaveSnapshotDialogProps {
  open: boolean
  onSave: (name: string, description: string) => Promise<void>
  onSkip: () => Promise<void>
  onCancel: () => void
}

export default function SaveSnapshotDialog({ open, onSave, onSkip, onCancel }: SaveSnapshotDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim()) {
      alert('请输入快照名称')
      return
    }

    setSaving(true)
    try {
      await onSave(name.trim(), description.trim())
    } catch (error) {
      alert('保存快照失败')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const handleSkip = async () => {
    await onSkip()
  }

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-[99999] bg-slate-700/50 backdrop-blur-sm flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
            <Save size={20} className="text-white" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">保存快照</h2>
        </div>

        <p className="text-slate-600 mb-4">
          是否保存当前演示的快照？输入名称和描述以便下次使用。
        </p>

        {/* Name input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            快照名称 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如: 实验1_恶意攻击测试"
            className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
            disabled={saving}
          />
        </div>

        {/* Description input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            描述（可选）
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="描述这个快照的内容..."
            className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
            rows={3}
            disabled={saving}
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSkip}
            disabled={saving}
            className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            直接结束
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            className="px-6 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 text-white font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              </>
            ) : (
              <Save size={16} />
            )}
            {saving ? '保存中...' : '保存并结束'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
