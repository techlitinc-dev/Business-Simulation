import { motion } from 'framer-motion'

import { revealVariants } from './motion'

const STEPS = [
  {
    n: '01',
    title: 'Build your blueprint',
    desc: 'Model your business — costs, pricing, team, funnel — in minutes.',
  },
  {
    n: '02',
    title: 'Baseline run',
    desc: 'The deterministic engine simulates 24+ months of operations.',
  },
  {
    n: '03',
    title: 'Stress test',
    desc: 'The AI Game Master injects bespoke, narratively coherent crises.',
  },
  {
    n: '04',
    title: 'Resilience audit',
    desc: 'Get a Monte-Carlo-driven audit with prescriptive optimizations.',
  },
]

export default function HowItWorks() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <motion.h2
        variants={revealVariants(0)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.4 }}
        className="text-center text-3xl font-semibold"
      >
        How it works
      </motion.h2>
      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step, i) => (
          <motion.div
            key={step.n}
            variants={revealVariants(i * 0.08)}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            className="rounded-lg border border-border bg-card p-5"
          >
            <span className="font-display text-2xl font-bold text-primary">
              {step.n}
            </span>
            <h3 className="mt-3 font-semibold">{step.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{step.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
