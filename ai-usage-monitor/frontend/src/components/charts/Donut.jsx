import { useGrowIn } from '../../hooks/useGrowIn.js'

const PALETTE = ['var(--danger)', '#c99a68', 'var(--text)', 'var(--text-muted)', '#8a7a5c', 'var(--text-faint)']

/**
 * A composition donut -- what share of detections is each PII type,
 * at a glance, with a legend for the exact counts. No prose needed:
 * the ring segments and the number in the middle carry the meaning.
 */
export function Donut({ segments, centerLabel, size = 140 }) {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1
  const stroke = 16
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const grown = useGrowIn(100)

  let cumulative = 0

  return (
    <div className="donut">
      <div className="donut-chart" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(242, 239, 232, 0.06)" strokeWidth={stroke} />
          {segments.map((segment, i) => {
            const fraction = segment.value / total
            const dash = fraction * circumference * (grown / 100)
            const gap = circumference - dash
            const offset = -((cumulative / total) * circumference)
            cumulative += segment.value
            return (
              <circle
                key={segment.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={PALETTE[i % PALETTE.length]}
                strokeWidth={stroke}
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={offset}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
                style={{ transition: 'stroke-dasharray 0.7s cubic-bezier(0.4, 0, 0.2, 1)' }}
                strokeLinecap="butt"
              />
            )
          })}
        </svg>
        <div className="donut-center">
          <strong>{total}</strong>
          <span>{centerLabel}</span>
        </div>
      </div>
      <ul className="donut-legend">
        {segments.map((segment, i) => (
          <li key={segment.label}>
            <span className="donut-legend-dot" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="donut-legend-label">{segment.label}</span>
            <span className="donut-legend-value">{segment.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
