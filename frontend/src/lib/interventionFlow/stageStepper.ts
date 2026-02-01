import type { Role } from './logRouter'
import { formatRoleStagesTooltip, getRoleStages } from './roleStages'

export function buildStageStepperModel(
  role: Role,
  input: {
    current: number
    max: number
    order: number[]
  },
) {
  const canonical = getRoleStages(role)

  // Option A: only render stages that actually appeared in the current round,
  // and keep their order as the first time they appeared in the log stream.
  const order = Array.isArray(input.order) ? input.order : []
  const stages = order
    .map((idx) => canonical[idx])
    .filter((label) => typeof label === 'string' && label.trim().length > 0)

  const currentPos = order.indexOf(input.current)
  const maxPos = order.indexOf(input.max)
  const currentLabel = currentPos >= 0 ? stages[currentPos] : ''

  return {
    stages,
    currentPos,
    maxPos,
    currentLabel,
    // Denominator should stay stable (e.g. 1/5) even if only 1 stage has shown up so far.
    total: canonical.length,
    seenCount: stages.length,
    tooltip: formatRoleStagesTooltip(role),
  }
}
