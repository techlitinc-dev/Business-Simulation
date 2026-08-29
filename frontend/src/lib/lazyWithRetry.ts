import { lazy } from 'react'

/**
 * Route-level `lazy()` wrapper that self-heals when a dynamically imported
 * chunk is missing. Hashed asset filenames change on every deploy, so a user
 * who has an old `index.html` cached (nginx sets no-cache on the HTML, but a
 * browser tab opened before the deploy keeps the old module graph) will try to
 * fetch a chunk URL that 404s after the new build replaces it.
 *
 * The first failure triggers a full reload, which re-fetches the latest
 * `index.html` and its matching hashed chunks. A reload flag guards against an
 * infinite reload loop if the chunk is genuinely broken.
 */
export function lazyWithRetry(
  importFn: () => Promise<{ default: React.ComponentType<unknown> }>,
) {
  let hasReloaded = false

  return lazy(() =>
    importFn().catch((err: unknown) => {
      if (!hasReloaded) {
        hasReloaded = true
        window.location.reload()
      }
      // The reload tears down the page; the rejected promise only matters if
      // it was somehow still consumed (it will surface in the error boundary).
      throw err
    }),
  )
}
