import { useId, useMemo } from 'react'

/**
 * A premium area/line trend chart. Pure SVG, no charting library --
 * intentionally minimal-text: the shape of the line is the message, with
 * only a start/end date label to anchor it in time.
 */
export function Sparkline({ points, height = 120, formatLabel = (p) => p.label }) {
  const gradientId = useId()
  const width = 480

  const { path, areaPath, dots } = useMemo(() => {
    if (!points.length) return { path: '', areaPath: '', dots: [] }
    const values = points.map((p) => p.value)
    const max = Math.max(...values, 1)
    const min = Math.min(...values, 0)
    const range = max - min || 1
    const stepX = points.length > 1 ? width / (points.length - 1) : 0
    let coords = points.map((p, i) => {
      const x = points.length > 1 ? i * stepX : width / 2
      const y = height - ((p.value - min) / range) * (height - 16) - 8
      return [x, y]
    })
    // A single day of data has nothing to trace a shape through -- draw a
    // flat reference line across the full width instead of a lone dot.
    if (coords.length === 1) {
      coords = [
        [0, coords[0][1]],
        [width, coords[0][1]],
      ]
    }
    const linePath = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
    const area = `${linePath} L ${coords[coords.length - 1][0].toFixed(1)} ${height} L ${coords[0][0].toFixed(1)} ${height} Z`
    return { path: linePath, areaPath: area, dots: coords }
  }, [points, height])

  if (!points.length) return null

  const last = points[points.length - 1]
  const first = points[0]

  return (
    <div className="sparkline">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="sparkline-svg" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--text)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--text)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
        <path d={path} fill="none" stroke="var(--text)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {dots.length > 0 && <circle cx={dots[dots.length - 1][0]} cy={dots[dots.length - 1][1]} r="4" fill="var(--text)" />}
      </svg>
      <div className="sparkline-axis">
        <span>{formatLabel(first)}</span>
        <span>{formatLabel(last)}</span>
      </div>
    </div>
  )
}
