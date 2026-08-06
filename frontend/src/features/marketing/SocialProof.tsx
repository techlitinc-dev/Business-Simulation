import { motion } from 'framer-motion'

import { revealVariants } from './motion'

const TESTIMONIALS = [
  {
    quote: 'Placeholder testimonial — swap in a real founder quote.',
    name: 'Founder Name',
    role: 'Company, Stage',
  },
  {
    quote: 'Placeholder testimonial — swap in a real founder quote.',
    name: 'Founder Name',
    role: 'Company, Stage',
  },
  {
    quote: 'Placeholder testimonial — swap in a real founder quote.',
    name: 'Founder Name',
    role: 'Company, Stage',
  },
]

const LOGOS = ['Acme Co', 'Globex', 'Initech', 'Stark', 'Wayne', 'Umbrella']

/** Placeholder social proof — clearly marked swap-ready (T39). */
export default function SocialProof() {
  return (
    <section
      className="mx-auto max-w-6xl px-4 py-20"
      data-testid="social-proof-placeholder"
    >
      <motion.p
        variants={revealVariants(0)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="text-center text-xs font-medium uppercase tracking-widest text-muted-foreground"
      >
        Trusted by founders at
      </motion.p>
      <motion.div
        variants={revealVariants(0.1)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        className="mt-6 flex flex-wrap items-center justify-center gap-4 opacity-70"
      >
        {LOGOS.map((logo) => (
          <span
            key={logo}
            className="flex h-10 w-32 items-center justify-center rounded-md border border-dashed border-border bg-muted/30 text-sm font-semibold text-muted-foreground"
          >
            {logo}
          </span>
        ))}
      </motion.div>

      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {TESTIMONIALS.map((t, i) => (
          <motion.figure
            key={i}
            variants={revealVariants(i * 0.08)}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            className="rounded-lg border border-dashed border-border bg-card/50 p-5"
          >
            <blockquote className="text-sm text-muted-foreground">
              “{t.quote}”
            </blockquote>
            <figcaption className="mt-3 text-sm">
              <span className="font-semibold">{t.name}</span>
              <span className="text-muted-foreground"> — {t.role}</span>
            </figcaption>
          </motion.figure>
        ))}
      </div>
    </section>
  )
}
