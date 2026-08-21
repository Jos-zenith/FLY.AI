import { useState } from 'react'
import { motion } from 'framer-motion'

export function AnimatedPenguin({ width = 128, height = 128 }) {
  const [isWaving, setIsWaving] = useState(false)

  return (
    <div
      className="animated-penguin"
      style={{ width, height }}
      onMouseEnter={() => setIsWaving(true)}
      onMouseLeave={() => setIsWaving(false)}
      onClick={() => setIsWaving((current) => !current)}
      role="img"
      aria-label="Animated penguin"
    >
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="40" cy="88" r="6" strokeWidth="2.5" />
          <circle cx="60" cy="88" r="6" strokeWidth="2.5" />
          <ellipse cx="50" cy="55" rx="25" ry="32" strokeWidth="2.5" />
          <ellipse cx="50" cy="58" rx="18" ry="24" strokeWidth="1.8" />
          <circle cx="43" cy="38" r="2.5" fill="currentColor" stroke="none" />
          <circle cx="57" cy="38" r="2.5" fill="currentColor" stroke="none" />
          <path d="M46,42 L54,42 L50,48 Z" strokeWidth="2" />
            <path d="M28,48 C17,50 15,62 25,69 C29,62 30,54 28,48" strokeWidth="2.5" />
            <motion.path
              d="M72,48 C83,50 85,62 75,69 C71,62 70,54 72,48"
              strokeWidth="2.5"
              style={{ transformOrigin: '72px 48px' }}
              animate={isWaving ? { rotate: [0, -28, -8, -28, -8, 0] } : { rotate: 0 }}
              transition={isWaving ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 }}
            />
        </g>
      </svg>
    </div>
  )
}
