import type { RoleStatus } from './logRouter'

export function shouldShowDetailStatusLabel(status: RoleStatus) {
  // Users don't benefit from seeing "IDLE" in the detail header.
  return status !== 'idle'
}

