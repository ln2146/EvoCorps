export function parsePostContent(
  raw: string,
  opts?: { previewChars?: number },
): {
  full: string
  tag?: string
  title?: string
  preview: string
} {
  const rawFull = raw ?? ''
  // Strip internal scaffolding that should not be shown in the UI:
  // - "[OFFICIAL EXPLANATION] ..." appended by simulation
  // - trailing "Please analyze ..." prompt used by agents
  const full = (() => {
    const lines = rawFull.split(/\r?\n/)
    const idxOfficial = lines.findIndex((l) => /\[OFFICIAL EXPLANATION\]/i.test(l))
    const idxPrompt = lines.findIndex((l) =>
      /^\s*Please analyze the opinion tendency of this post and whether intervention is needed\.\s*$/i.test(l),
    )
    const cut = [idxOfficial, idxPrompt].filter((n) => n >= 0).sort((a, b) => a - b)[0]
    const kept = (cut == null ? lines : lines.slice(0, cut)).join('\n')
    return kept.replace(/\s+$/g, '').trimEnd()
  })()
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
