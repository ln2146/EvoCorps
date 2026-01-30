import type { Role } from './logRouter'

export function computeRoleFlexGrow(activeRole: Role | null, role: Role) {
  if (!activeRole) return 1
  return role === activeRole ? 6 : 1
}

