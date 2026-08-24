import { render, screen } from '@testing-library/react'

import { ChatBubble } from '@/features/copilot/ChatBubble'

it('ChatBubble shows grounded badge for assistant messages', () => {
  render(<ChatBubble role="assistant" content="Answer here." grounded />)

  expect(screen.getByText('✅ Grounded in data')).toBeInTheDocument()
  expect(screen.queryByText('⚠️ Unverified claim')).not.toBeInTheDocument()
})

it('ChatBubble shows flagged claim warning', () => {
  render(
    <ChatBubble
      role="assistant"
      content="Revenue hit 999999 dollars."
      grounded={false}
      flaggedClaims={['999999']}
    />,
  )

  expect(screen.getByText('⚠️ Unverified claim')).toBeInTheDocument()
  expect(screen.getByText('Flagged: 999999')).toBeInTheDocument()
})