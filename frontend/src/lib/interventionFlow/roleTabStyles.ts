export function getRoleTabButtonClassName(isSelected: boolean) {
  const base =
    'w-full rounded-2xl border shadow-sm transition-colors duration-200 px-3 py-2 text-left min-w-0 box-border'

  if (isSelected) {
    // Keep visual emphasis without changing perceived size (no bigger shadow).
    return [
      base,
      'bg-white/80 border-emerald-200 ring-2 ring-inset ring-emerald-100',
    ].join(' ')
  }

  return [base, 'bg-white/60 border-white/40 hover:bg-white/75'].join(' ')
}

