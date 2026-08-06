import { motion } from 'framer-motion'
import { Bot, Gauge, GitBranch, ShieldCheck } from 'lucide-react'

import { revealVariants } from './motion'

const FEATURES = [
  {
    icon: ShieldCheck,
    title: 'Deterministic Engine',
    desc: 'Physics that can\u2019t be overridden — cash, payroll, churn, demand are math, not vibes.',
  },
  {
    icon: Bot,
    title: 'AI Game Master',
    desc: 'Bespoke, narratively coherent crises that hit exactly where your model is weak.',
  },
  {
    icon: Gauge,
    title: 'Monte Carlo',
    desc: '100 runs in seconds to see your real survival odds — not one lucky trace.',
  },
  {
    icon: GitBranch,
    title: 'War Room',
    desc: 'Branching strategic decisions with 12-month projections for every option.',
  },
]

export default function Features() {
  return (
    <section className="border-y border-border/60 bg-card/40">
      <div className="mx-auto max-w-6xl px-4 py-20">
        <motion.h2
          variants={revealVariants(0)}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.4 }}
          className="text-center text-3xl font-semibold"
        >
          Built for the way failure actually happens
        </motion.h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              variants={revealVariants(i * 0.08)}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              className="rounded-lg border border-border bg-card p-5"
            >
              <f.icon className="h-6 w-6 text-primary" />
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
