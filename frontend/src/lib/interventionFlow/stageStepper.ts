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

  // Always render canonical stages so the stepper stays stable and the step number
  // matches the meaning of each stage (even if the log stream is sparse or interleaved).
  const stages = canonical
  const total = canonical.length

  const inRange = (n: number) => Number.isFinite(n) && n >= 0 && n < total

  const order = Array.isArray(input.order) ? input.order : []
  const seen = Array.from(new Set(order.filter((idx) => inRange(idx))))
  const seenCount = seen.length

  const currentPos = inRange(input.current) ? input.current : -1
  const maxPos = inRange(input.max) ? input.max : -1
  const currentLabel = currentPos >= 0 ? stages[currentPos] : ''
  const currentStep = currentPos >= 0 ? currentPos + 1 : 0

  return {
    stages,
    currentPos,
    maxPos,
    currentLabel,
    currentStep,
    total,
    seenCount,
    tooltip: formatRoleStagesTooltip(role),
  }
}
