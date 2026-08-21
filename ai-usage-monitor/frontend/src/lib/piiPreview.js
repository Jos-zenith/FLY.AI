/**
 * Client-side mirror of the backend's regex PII patterns (see
 * backend/app/services/pii.py), used ONLY for instant as-you-type
 * feedback on the hero screen -- never sent anywhere, never trusted for
 * the real detection record. The backend's redact() call is still the
 * source of truth for what actually gets stored; this is a preview.
 */
const PREVIEW_PATTERNS = [
  { label: 'EMAIL', pattern: /\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b/g },
  { label: 'PHONE', pattern: /\b(?:\+?\d{1,3}[-\s]?)?(?:\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4})\b/g },
  { label: 'CREDIT_CARD', pattern: /\b(?:\d[ -]*?){13,16}\b/g },
  { label: 'PAN', pattern: /\b[A-Z]{5}[0-9]{4}[A-Z]\b/g },
  { label: 'AADHAAR', pattern: /\b\d{4}\s?\d{4}\s?\d{4}\b/g },
]

export function previewPiiCounts(text) {
  const counts = {}
  if (!text) return counts
  for (const { label, pattern } of PREVIEW_PATTERNS) {
    const matches = text.match(pattern)
    if (matches?.length) counts[label] = matches.length
  }
  return counts
}

/**
 * Splits already-sanitized text like "Contact <EMAIL> or <PHONE>" into
 * plain-text and token segments, so the UI can render the redaction
 * markers as visually distinct badges instead of plain angle-bracket text.
 */
export function splitSanitizedText(text) {
  if (!text) return []
  const parts = []
  const tokenPattern = /<([A-Z_]+)>/g
  let lastIndex = 0
  let match
  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'token', value: match[1] })
    lastIndex = tokenPattern.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }
  return parts
}
