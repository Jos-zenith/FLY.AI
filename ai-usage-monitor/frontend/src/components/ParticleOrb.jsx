import { useMemo, useRef, Component } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'

/**
 * Small decorative "activity" orb — a rotating dotted sphere with a glowing
 * core, adapted from the reference design's particle visualization.
 *
 * Real WebGL rendering only happens in browsers that support it. In any
 * environment without WebGL (older browsers, some CI/test runners, jsdom in
 * unit tests) this quietly falls back to a static CSS glow instead of
 * throwing — a real dashboard shouldn't go blank because a decorative
 * element couldn't get a GL context.
 */

function supportsWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    )
  } catch {
    return false
  }
}

function DottedSphere({ radius = 1.1, dotCount = 260, dotSize = 0.032 }) {
  const groupRef = useRef(null)

  const dots = useMemo(() => {
    const positions = []
    const phi = Math.PI * (3 - Math.sqrt(5)) // golden angle for even distribution

    for (let i = 0; i < dotCount; i++) {
      const y = 1 - (i / (dotCount - 1)) * 2
      const radiusAtY = Math.sqrt(1 - y * y)
      const theta = phi * i

      const x = Math.cos(theta) * radiusAtY * radius
      const z = Math.sin(theta) * radiusAtY * radius
      positions.push([x, y * radius, z])
    }
    return positions
  }, [radius, dotCount])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.15
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.08) * 0.12
    }
  })

  return (
    <group ref={groupRef}>
      {dots.map((pos, i) => (
        <mesh key={i} position={pos}>
          <sphereGeometry args={[dotSize, 6, 6]} />
          <meshStandardMaterial
            color="#e8e4db"
            emissive="#e8e4db"
            emissiveIntensity={0.55}
            metalness={0.75}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  )
}

function GlowingCore() {
  const meshRef = useRef(null)

  useFrame((state) => {
    if (meshRef.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 1.6) * 0.05
      meshRef.current.scale.set(scale, scale, scale)
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.16, 24, 24]} />
      <meshStandardMaterial color="#faf8f3" emissive="#e8e4db" emissiveIntensity={1.8} metalness={0.35} roughness={0.2} />
    </mesh>
  )
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.7} />
      <pointLight position={[4, 4, 4]} intensity={2} color="#ffffff" />
      <pointLight position={[-4, -3, -3]} intensity={1} color="#c9c4b6" />
      <GlowingCore />
      <DottedSphere />
    </>
  )
}

class OrbErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch() {
    // Decorative element only -- swallow and fall back, nothing to surface.
  }

  render() {
    if (this.state.failed) return this.props.fallback
    return this.props.children
  }
}

function OrbGlowFallback({ size }) {
  return <div className="orb-glow-fallback" style={{ width: size, height: size }} aria-hidden="true" />
}

export function ParticleOrb({ size = 48 }) {
  const fallback = <OrbGlowFallback size={size} />

  if (typeof window === 'undefined' || !supportsWebGL()) {
    return fallback
  }

  return (
    <div className="particle-orb" style={{ width: size, height: size }} aria-hidden="true">
      <OrbErrorBoundary fallback={fallback}>
        <Canvas
          camera={{ position: [0, 0, 3.2], fov: 45 }}
          style={{ background: 'transparent' }}
          gl={{ alpha: true, antialias: true }}
          dpr={[1, 1.5]}
        >
          <Scene />
        </Canvas>
      </OrbErrorBoundary>
    </div>
  )
}
