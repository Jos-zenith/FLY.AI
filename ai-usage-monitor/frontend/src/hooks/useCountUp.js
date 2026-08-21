import { useEffect, useRef, useState } from 'react'

/**
 * Animates a number from its previous value up (or down) to the next one.
 * Purely a "the dashboard feels alive" touch -- if requestAnimationFrame
 * isn't available (older browsers, jsdom in unit tests) it just snaps to
 * the target value instead of throwing, the same fallback pattern used for
 * the WebGL particle orb elsewhere in this app.
 */
export function useCountUp(value, duration = 700) {
  const numeric = Number(value) || 0
  const [display, setDisplay] = useState(numeric)
  const fromRef = useRef(numeric)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.requestAnimationFrame !== 'function') {
      setDisplay(numeric)
      fromRef.current = numeric
      return undefined
    }

    const from = fromRef.current
    const to = numeric
    if (from === to) return undefined

    const start = performance.now()
    let raf

    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(from + (to - from) * eased))
      if (progress < 1) {
        raf = window.requestAnimationFrame(tick)
      } else {
        fromRef.current = to
      }
    }

    raf = window.requestAnimationFrame(tick)
    return () => raf && window.cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numeric, duration])

  return display
}
