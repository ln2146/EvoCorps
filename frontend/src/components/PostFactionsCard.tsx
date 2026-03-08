export default function PostFactionsCard({ postId }: { postId: string | null }) {
  return (
    <div className="glass-card p-6">
      <h2 className="text-2xl font-bold text-slate-800">帖子派系分析</h2>
      <p className="text-sm text-slate-500">{postId ? `当前帖子: ${postId}` : '请选择帖子'}</p>
    </div>
  )
}
