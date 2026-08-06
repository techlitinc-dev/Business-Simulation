import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Flame } from 'lucide-react'

import { EmptyState } from '../empty-state'

describe('EmptyState', () => {
  it('renders title, description and icon', () => {
    render(
      <EmptyState
        icon={Flame}
        title="No blueprints yet"
        description="Build your first blueprint to get started."
      />,
    )
    expect(screen.getByText('No blueprints yet')).toBeInTheDocument()
    expect(
      screen.getByText('Build your first blueprint to get started.'),
    ).toBeInTheDocument()
  })

  it('renders a CTA button and fires onClick', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()
    render(
      <EmptyState
        title="Nothing here"
        ctaLabel="Create one"
        onCtaClick={onClick}
      />,
    )
    const cta = screen.getByRole('button', { name: 'Create one' })
    expect(cta).toBeInTheDocument()
    await user.click(cta)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('does not render a CTA when no label is provided', () => {
    render(<EmptyState title="Just a title" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
