import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { InvestorToolkitPage } from '../InvestorToolkitPage'

const { generateTeaserMock, generatePitchDeckMock, downloadBlobMock } = vi.hoisted(() => ({
  generateTeaserMock: vi.fn(),
  generatePitchDeckMock: vi.fn(),
  downloadBlobMock: vi.fn(),
}))

vi.mock('../api', () => ({
  generateTeaser: (...args: unknown[]) => generateTeaserMock(...args),
  generatePitchDeck: (...args: unknown[]) => generatePitchDeckMock(...args),
  downloadBlob: (...args: unknown[]) => downloadBlobMock(...args),
}))

beforeEach(() => {
  generateTeaserMock.mockReset()
  generatePitchDeckMock.mockReset()
  downloadBlobMock.mockReset()
})

describe('InvestorToolkitPage', () => {
  it('renders 2 action cards', () => {
    render(<InvestorToolkitPage runId="run_1" />)

    expect(
      screen.getByRole('button', { name: /Generate Investment Teaser/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Generate Pitch Deck Outline/ }),
    ).toBeInTheDocument()
  })

  it('generates teaser on click and triggers download', async () => {
    generateTeaserMock.mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }))
    render(<InvestorToolkitPage runId="run_1" />)

    fireEvent.click(screen.getByRole('button', { name: /Generate Investment Teaser/ }))

    await waitFor(() => expect(generateTeaserMock).toHaveBeenCalledWith('run_1'))
    expect(downloadBlobMock).toHaveBeenCalledWith(expect.any(Blob), 'teaser_run_1.pdf')
  })
})