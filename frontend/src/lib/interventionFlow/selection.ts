import type { Role } from './logRouter'

export function computeEffectiveRole(selectedRole: Role | null, activeRole: Role | null): Role {
  return selectedRole ?? activeRole ?? 'Analyst'
}

export function nextSelectedRoleOnTabClick(
  selectedRole: Role | null,
  clickedRole: Role,
  activeRole: Role | null,
): Role | null {
  // Enter review mode.
  if (!selectedRole) return clickedRole

  // If user clicks the currently active role while reviewing, return to follow mode.
  if (clickedRole === activeRole) return null

  // Otherwise switch review selection to the clicked role.
  return clickedRole
}
