export function getHeatLeaderboardCardClassName() {
  // Match the right-side InterventionFlowPanel height so the two columns align.
  return 'glass-card p-6 h-[645px] flex flex-col min-h-0'
}

export function getHeatLeaderboardListClassName() {
  // Scroll within the card, never grow the outer card.
  return 'space-y-3 min-h-0 flex-1 overflow-y-scroll pr-2'
}
