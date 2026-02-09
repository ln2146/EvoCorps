import { Database } from 'lucide-react'

interface DatabaseSelectorProps {
  databases: string[]
  selectedDb: string
  onSelect: (db: string) => void
  label?: string
}

export default function DatabaseSelector({
  databases,
  selectedDb,
  onSelect,
  label = '选择数据库：'
}: DatabaseSelectorProps) {
  return (
    <div className="flex items-center gap-4">
      <Database size={20} className="text-slate-600" />
      <label className="text-lg font-medium text-slate-700">{label}</label>
      <select
        value={selectedDb}
        onChange={(e) => onSelect(e.target.value)}
        className="glass-card px-6 py-2 rounded-2xl border border-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white/70 backdrop-blur-xl text-slate-700 font-medium transition-all duration-300 hover:bg-white/80 cursor-pointer"
      >
        {databases.map(db => (
          <option key={db} value={db}>{db}</option>
        ))}
      </select>
    </div>
  )
}
