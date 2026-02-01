export function getDynamicDemoGridClassName() {
  // Use minmax(0, ...) to prevent any child from widening the grid column (common when stage/header text is long).
  return 'grid grid-cols-1 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_minmax(0,1fr)] gap-6'
}

