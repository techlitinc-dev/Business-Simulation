import { fireEvent, render, screen } from '@testing-library/react'

import { CopilotPanel } from '@/features/copilot/CopilotPanel'

const { sendCopilotMessageMock } = vi.hoisted(() => ({
  sendCopilotMessageMock: vi.fn(),
}))

vi.mock('@/features/copilot/api', () => ({
  sendCopilotMessage: (...args: unknown[]) => sendCopilotMessageMock(...args),
}))

beforeEach(() => {
  sendCopilotMessageMock.mockReset()
  // jsdom doesn't implement scrollIntoView; the panel calls it on new messages.
  Element.prototype.scrollIntoView = vi.fn()
})

it('CopilotPanel renders chat bubble icon when closed', () => {
  render(<CopilotPanel runId="run_1" />)

  expect(screen.getByRole('button', { name: '💬' })).toBeInTheDocument()
  expect(screen.queryByText('Ask About This Run')).not.toBeInTheDocument()
})

it('CopilotPanel opens on click, shows empty state', () => {
  render(<CopilotPanel runId="run_1" />)

  fireEvent.click(screen.getByRole('button', { name: '💬' }))

  expect(screen.getByText('Ask About This Run')).toBeInTheDocument()
  expect(screen.getByText(/Ask anything about this simulation/)).toBeInTheDocument()
})

it('CopilotPanel sends message and shows response', async () => {
  sendCopilotMessageMock.mockResolvedValue({
    answer: 'The survival rate is 68 percent.',
    sources_used: ['mc_aggregates'],
    confidence: 'HIGH',
    grounded: true,
    flagged_claims: [],
  })
  render(<CopilotPanel runId="run_7" />)
  fireEvent.click(screen.getByRole('button', { name: '💬' }))

  const input = screen.getByPlaceholderText('Ask a question…')
  fireEvent.change(input, { target: { value: 'What was the survival rate?' } })
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

  expect(sendCopilotMessageMock).toHaveBeenCalledWith(
    'run_7',
    'What was the survival rate?',
    [],
  )
  expect(
    await screen.findByText('The survival rate is 68 percent.'),
  ).toBeInTheDocument()
  expect(screen.getByText('✅ Grounded in data')).toBeInTheDocument()
})