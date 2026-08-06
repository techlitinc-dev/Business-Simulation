import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { revealVariants } from './motion'

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Ember glow background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(60% 50% at 50% 0%, hsl(var(--forge) / 0.18), transparent 70%)',
        }}
      />
      <motion.div
        className="relative mx-auto max-w-4xl px-4 py-24 text-center"
        initial="hidden"
        animate="visible"
      >
        <motion.h1
          variants={revealVariants(0)}
          className="font-display text-4xl font-bold leading-tight sm:text-6xl"
        >
          The digital wind tunnel{' '}
          <span className="text-primary">for your business</span>
        </motion.h1>
        <motion.p
          variants={revealVariants(0.1)}
          className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground"
        >
          A deterministic engine that can't be overridden, plus an AI Game
          Master that stress-tests your model with bespoke crises. Simulate 24+
          months before you spend a dollar.
        </motion.p>
        <motion.div
          variants={revealVariants(0.2)}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Button size="lg" asChild>
            <Link to="/register">
              Start simulating free <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/pricing">See pricing</Link>
          </Button>
        </motion.div>
      </motion.div>
    </section>
  )
}
