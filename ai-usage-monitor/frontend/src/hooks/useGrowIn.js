import { useEffect, useState } from 'react'

/**
 * Returns 0 on first render, then the real value a tick later -- paired
 * with a CSS transition on the consumer, this is what makes bars/rings
 * grow in on mount instead of snapping straight to their final size.
 * Safe in any environment (no requestAnimationFrame dependency), so it
 * doesn't need the jsdom fallback the count-up hook needs.
 */
export function useGrowIn(target) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const id = setTimeout(() => setValue(target), 30)
    return () => clearTimeout(id)
  }, [target])

  return value
}
