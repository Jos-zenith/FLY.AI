import { useGrowIn } from '../../hooks/useGrowIn.js'

/**
 * A single premium horizontal bar. Optionally stacked with a second
 * "accent" segment (e.g. how much of this bar's volume was flagged PII)
 * drawn on top of the base segment, plus a small numeric chip -- so
 * composition reads visually, with no supporting sentence needed.
 */
export function Bar({ label, value, max, accentValue = 0, accentLabel, unit = '' }) {
  const safeMax = Math.max(max, 1)
  const basePct = Math.min(100, (value / safeMax) * 100)
  const accentPct = Math.min(100, (accentValue / safeMax) * 100)
  const grownBase = useGrowIn(basePct)
  const grownAccent = useGrowIn(accentPct)

  return (
    <div className="bar-row">
      <div className="bar-row-top">
        <span className="bar-row-label">{label}</span>
        <span className="bar-row-values">
          {accentValue > 0 && (
            <span className="bar-row-chip accent" title={accentLabel}>
              {accentValue}
            </span>
          )}
          <span className="bar-row-value">
            {value}
            {unit}
          </span>
        </span>
      </div>
      <div className="bar-track">
        <div className="bar-fill base" style={{ width: `${grownBase}%` }} />
        {accentValue > 0 && <div className="bar-fill accent" style={{ width: `${grownAccent}%` }} />}
      </div>
    </div>
  )
}
