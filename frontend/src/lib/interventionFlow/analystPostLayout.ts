export function getAnalystPostCardClassName() {
  // Keep this compact so the streaming area remains dominant.
  // Fixed height prevents layout shifts when expanding/collapsing.
  return 'mt-4 bg-white/60 border border-white/40 rounded-2xl p-4 h-28 flex flex-col min-h-0'
}

export function getAnalystPostBodyClassName(expanded: boolean) {
  const base = 'text-sm text-slate-700 leading-relaxed break-all'
  if (!expanded) return `${base} line-clamp-3`
  return `${base} whitespace-pre-wrap min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1`
}

