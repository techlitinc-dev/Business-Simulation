import type { Variants } from 'framer-motion'

/** Shared scroll-reveal animation config that respects prefers-reduced-motion. */
export function reducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function revealVariants(delay = 0): Variants {
  const disable = reducedMotion()
  return {
    hidden: { opacity: 0, y: disable ? 0 : 24 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: 'easeOut', delay },
    },
  }
}
