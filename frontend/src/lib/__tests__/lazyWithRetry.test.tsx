import { Suspense, useEffect } from 'react'
import { render, screen } from '@testing-library/react'

import { lazyWithRetry } from '../lazyWithRetry'

describe('lazyWithRetry', () => {
  const originalReload = window.location.reload

  afterEach(() => {
    window.location.reload = originalReload
  })

  it('reloads once when the dynamic import fails', async () => {
    const reload = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { reload },
      writable: true,
    })

    const LazyComp = lazyWithRetry(() => Promise.reject(new Error('chunk 404')))

    render(
      <Suspense fallback={<div>loading</div>}>
        <LazyComp />
      </Suspense>,
    )

    // The rejected import triggers the reload as soon as React settles it.
    await screen.findByText('loading')
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('renders the lazy component when the import succeeds', async () => {
    function Loaded() {
      useEffect(() => {
        // effect not strictly needed; keeps the component non-trivial
      }, [])
      return <div>loaded page</div>
    }
    const LazyComp = lazyWithRetry(() => Promise.resolve({ default: Loaded }))

    render(
      <Suspense fallback={<div>loading</div>}>
        <LazyComp />
      </Suspense>,
    )

    expect(await screen.findByText('loaded page')).toBeInTheDocument()
  })
})
