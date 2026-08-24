import { fireEvent, render, screen } from '@testing-library/react'

import { DecisionCoach } from '@/features/warroom/DecisionCoach'

const { sendCopilotMessageMock } = vi.hoisted(() => ({
  sendCopilotMessageMock: vi.fn(),
}))

vi.mock('@/features/copilot/api', () => ({
  sendCopilotMessage: (...args: unknown[]) => sendCopilotMessageMock(...args),
}))

beforeEach(() => {
  sendCopilotMessageMock.mockReset()
})

it('DecisionCoach shows second opinion button', () => {
  render(<DecisionCoach runId="run_1" optionLabel="Option A" />)

  expect(
    screen.getByRole('button', { name: '🤔 Get Second Opinion' }),
  ).toBeInTheDocument()
})

it('DecisionCoach calls sendCopilotMessage with option label', async () => {
  sendCopilotMessageMock.mockResolvedValue({
    answer: 'This option raises burn risk.',
    sources_used: [],
    confidence: 'MEDIUM',
    grounded: true,
    flagged_claims: [],
  })
  render(<DecisionCoach runId="run_9" optionLabel="Defend the base" />)

  fireEvent.click(screen.getByRole('button', { name: '🤔 Get Second Opinion' }))

  expect(sendCopilotMessageMock).toHaveBeenCalledWith(
    'run_9',
    expect.stringContaining('Defend the base'),
  )
  expect(
    await screen.findByText('This option raises burn risk.'),
  ).toBeInTheDocument()
})