export function getInterventionFlowPanelClassName() {
  // Fixed-height panel; clip overflow to avoid visual growth when inner content is long.
  // min-w-0 is important in CSS grid/flex contexts to prevent long content from forcing the column wider.
  return 'glass-card p-6 h-[645px] flex flex-col min-h-0 min-w-0 w-full overflow-hidden'
}

export function getLeaderCommentsContainerClassName() {
  // Keep the container height stable; scroll within for long comment bodies.
  return 'space-y-3 max-h-56 overflow-y-scroll overflow-x-hidden pr-1'
}
