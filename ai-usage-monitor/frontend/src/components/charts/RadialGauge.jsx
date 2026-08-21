import { useGrowIn } from '../../hooks/useGrowIn.js'

const TONE_VARS = {
  neutral: 'var(--text)',
  danger: 'var(--danger)',
  ok: 'var(--ok)',
}

/**
 * A circular progress ring. `percent` drives how much of the ring is
 * filled; `displayValue`/`label` are the only text on the chart -- the
 * fill itself is meant to communicate "how much" without a sentence.
 */
export function RadialGauge({ percent, displayValue, label, tone = 'neutral', size = 108 }) {
  const clamped = Math.max(0, Math.min(100, percent))
  const grown = useGrowIn(clamped)
  const stroke = 10
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (grown / 100) * circumference

  return (
    <div className="radial-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(242, 239, 232, 0.08)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={TONE_VARS[tone]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 0.7s cubic-bezier(0.4, 0, 0.2, 1)' }}
        />
      </svg>
      <div className="radial-gauge-center">
        <strong>{displayValue}</strong>
        <span>{label}</span>
      </div>
    </div>
  )
}
