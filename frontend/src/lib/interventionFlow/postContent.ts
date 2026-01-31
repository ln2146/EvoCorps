export function parsePostContent(
  raw: string,
  opts?: { previewChars?: number },
): {
  full: string
  tag?: string
  title?: string
  preview: string
} {
  const full = raw ?? ''
  const previewChars = Math.max(0, opts?.previewChars ?? 220)

  const firstLine = full.split(/\r?\n/, 1)[0]?.trim() ?? ''
  let tag: string | undefined
  let title: string | undefined

  let bodyForPreview = full
  const tagMatch = firstLine.match(/^\[([^\]]+)\]\s*(.*)$/)
  if (tagMatch) {
    tag = tagMatch[1].trim() || undefined
    title = tagMatch[2].trim() || undefined
    // Only strip the leading tag; keep the rest unchanged for full rendering.
    bodyForPreview = full.replace(/^\[[^\]]+\]\s*/, '')
  } else {
    title = firstLine || undefined
  }

  const compact = bodyForPreview.replace(/\s+/g, ' ').trim()
  const preview =
    compact.length <= previewChars ? compact : `${compact.slice(0, previewChars)}…`

  return { full, tag, title, preview }
}

