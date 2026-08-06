import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

import { Button } from '@/components/ui/button'
import { revealVariants } from './motion'

export default function FinalCta() {
  return (
    <section className="border-t border-border/60">
      <motion.div
        variants={revealVariants(0)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="mx-auto max-w-4xl px-4 py-24 text-center"
      >
        <h2 className="font-display text-3xl font-semibold sm:text-4xl">
          Find out if your business survives — before it has to
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          Build a blueprint, face the Game Master, and walk away with a
          resilience audit you can act on.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" asChild>
            <Link to="/register">Start simulating free</Link>
          </Button>
        </div>
      </motion.div>
      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row">
          <span className="text-sm text-muted-foreground">
            © 2026 The Forge. All rights reserved.
          </span>
          <nav className="flex gap-4 text-sm text-muted-foreground">
            <a href="#" className="hover:text-foreground">
              Docs
            </a>
            <a href="#" className="hover:text-foreground">
              GitHub
            </a>
            <a href="#" className="hover:text-foreground">
              Privacy
            </a>
          </nav>
        </div>
      </footer>
    </section>
  )
}
