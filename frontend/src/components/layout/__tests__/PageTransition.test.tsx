import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import PageTransition from '../PageTransition'

describe('PageTransition', () => {
  it('renders the active route children', () => {
    render(
      <MemoryRouter initialEntries={['/one']}>
        <Routes>
          <Route path="/one" element={<PageTransition />}>
            <Route index element={<div>Page One</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Page One')).toBeInTheDocument()
  })

  it('renders children when nested under a route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<PageTransition />}>
            <Route index element={<div>Home</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Home')).toBeInTheDocument()
  })
})
