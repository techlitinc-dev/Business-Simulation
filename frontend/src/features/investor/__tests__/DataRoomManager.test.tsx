import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { DataRoomManager } from '../DataRoomManager'

const { createDataRoomMock, revokeDataRoomMock } = vi.hoisted(() => ({
  createDataRoomMock: vi.fn(),
  revokeDataRoomMock: vi.fn(),
}))

vi.mock('../api', () => ({
  createDataRoom: (...args: unknown[]) => createDataRoomMock(...args),
  revokeDataRoom: (...args: unknown[]) => revokeDataRoomMock(...args),
}))

const ROOM = {
  token: 'tok_abc',
  download_url: '/api/v1/dataroom/tok_abc/download',
  expires_at: '2026-09-01T00:00:00Z',
  label: 'Investor Data Room',
}

beforeEach(() => {
  createDataRoomMock.mockReset()
  revokeDataRoomMock.mockReset()
})

describe('DataRoomManager', () => {
  it('shows Create Data Room button', () => {
    render(<DataRoomManager runId="run_1" />)

    expect(
      screen.getByRole('button', { name: /Create Data Room Link/ }),
    ).toBeInTheDocument()
  })

  it('shows room card after creation', async () => {
    createDataRoomMock.mockResolvedValue(ROOM)
    render(<DataRoomManager runId="run_1" />)

    fireEvent.click(screen.getByRole('button', { name: /Create Data Room Link/ }))

    expect(await screen.findByText('Investor Data Room')).toBeInTheDocument()
    expect(createDataRoomMock).toHaveBeenCalledWith('run_1', 'Investor Data Room')
  })

  it('removes room after revoke', async () => {
    createDataRoomMock.mockResolvedValue(ROOM)
    render(<DataRoomManager runId="run_1" />)

    fireEvent.click(screen.getByRole('button', { name: /Create Data Room Link/ }))
    await screen.findByText('Investor Data Room')

    fireEvent.click(screen.getByText('Revoke'))

    await waitFor(() => expect(revokeDataRoomMock).toHaveBeenCalledWith('tok_abc'))
    expect(screen.queryByText('Investor Data Room')).not.toBeInTheDocument()
  })
})