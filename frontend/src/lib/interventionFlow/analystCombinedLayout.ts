export function getAnalystCombinedCardClassName() {
  // Single "channel": post + milestones share ONE scrollbar to avoid the "two cards" feeling.
  // Always show scrollbar space so width stays stable while streaming.
  return 'mt-4 bg-white/60 border border-white/40 rounded-2xl p-4 min-h-0 flex-1 overflow-y-scroll overflow-x-hidden pr-1 space-y-3'
}

export function getAnalystCombinedPostBodyClassName() {
  // Always show the full post content; the outer Analyst card provides the single scrollbar.
  return 'text-sm text-slate-700 leading-relaxed break-all whitespace-pre-wrap'
}

export function getAnalystCombinedStreamClassName() {
  // Stream list wrapper (no scrolling here; the outer card scrolls).
  return 'space-y-2'
}
