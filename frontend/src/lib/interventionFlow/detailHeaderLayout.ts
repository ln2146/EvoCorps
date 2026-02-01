export function getLiveBadgeClassName() {
  // Prevent the two Chinese characters from wrapping vertically (looks like a circle badge).
  return 'text-xs font-semibold text-emerald-700 px-2 py-1 rounded-full bg-emerald-50 border border-emerald-100 whitespace-nowrap inline-flex items-center'
}

export function getStageHeaderContainerClassName() {
  // Fixed width avoids reflow; keep it reasonably compact so the role label doesn't truncate.
  return 'shrink-0 w-[260px] text-right'
}

export function getStageHeaderTextClassName() {
  // Slightly bigger than pills; never truncate so text is fully visible.
  // Allow wrapping so long labels don't force the whole panel wider.
  return 'text-sm font-semibold text-slate-800 whitespace-normal break-words leading-snug'
}

export function getStageSegmentClassName(tone: 'done' | 'current' | 'todo') {
  const base = 'h-2 w-5 rounded-full'
  if (tone === 'current') return `${base} bg-emerald-600`
  if (tone === 'done') return `${base} bg-emerald-300`
  return `${base} bg-white/60 border border-white/50`
}
