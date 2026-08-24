import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ActualsUploadPage } from '@/features/actuals/ActualsUploadPage'

const { uploadActualsMock } = vi.hoisted(() => ({
  uploadActualsMock: vi.fn(),
}))

vi.mock('@/features/actuals/api', () => ({
  uploadActuals: (...args: unknown[]) => uploadActualsMock(...args),
}))

const RESULT = {
  records_created: 2,
  records_updated: 1,
  validation_warnings: [],
  unmapped_columns: [],
}

const CSV = [
  'month,revenue,costs,cash,churn_rate,notes',
  '1,12000,14000,86000,0.05,"hello"',
  '2,15000,14200,91000,0.04,"world"',
].join('\n')

function renderPage() {
  return render(<ActualsUploadPage blueprintId="bp_1" onSuccess={vi.fn()} />)
}

/** Mapping row: [column name span, select]. The select has no accessible
 *  label, so pair each column with its select via the row structure. */
function getMappingRows(container: HTMLElement) {
  return Array.from(container.querySelectorAll('div.flex.items-center.gap-3')).map(
    (row) => {
      const col = row.querySelector('span')?.textContent ?? ''
      const select = row.querySelector('select') as HTMLSelectElement | null
      return { col, select }
    },
  )
}

describe('ActualsUploadPage', () => {
  beforeEach(() => {
    uploadActualsMock.mockReset()
  })

  it('shows paste step initially', () => {
    renderPage()

    expect(screen.getByText(/Paste your CSV/)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Parse Headers/ }),
    ).toBeInTheDocument()
    // Mapping step is not shown yet.
    expect(screen.queryByText(/Map CSV columns/)).not.toBeInTheDocument()
  })

  it('parses headers and shows mapping step', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), CSV)
    await user.click(screen.getByRole('button', { name: /Parse Headers/ }))

    expect(screen.getByText(/Map CSV columns/)).toBeInTheDocument()
    // One dropdown per CSV column.
    const selects = screen.getAllByRole('combobox')
    expect(selects).toHaveLength(6)
    expect(screen.getByRole('button', { name: 'Upload Actuals' })).toBeInTheDocument()
  })

  it('auto-maps known columns', async () => {
    const user = userEvent.setup()
    const { container } = renderPage()

    await user.type(screen.getByRole('textbox'), CSV)
    await user.click(screen.getByRole('button', { name: /Parse Headers/ }))

    const rows = getMappingRows(container)
    // Known columns are pre-selected to their field.
    for (const col of ['month', 'revenue', 'costs', 'cash', 'churn_rate']) {
      const row = rows.find((r) => r.col === col)
      expect(row?.select?.value).toBe(col)
    }
    // Unknown column defaults to "-- skip --".
    const notes = rows.find((r) => r.col === 'notes')
    expect(notes?.select?.value).toBe('')
  })

  it('calls uploadActuals with correct params', async () => {
    const user = userEvent.setup()
    uploadActualsMock.mockResolvedValue(RESULT)
    renderPage()

    await user.type(screen.getByRole('textbox'), CSV)
    await user.click(screen.getByRole('button', { name: /Parse Headers/ }))
    await user.click(screen.getByRole('button', { name: 'Upload Actuals' }))

    expect(uploadActualsMock).toHaveBeenCalledWith(
      'bp_1',
      CSV,
      {
        month: 'month',
        revenue: 'revenue',
        costs: 'costs',
        cash: 'cash',
        churn_rate: 'churn_rate',
      },
    )
  })

  it('shows success message after upload', async () => {
    const user = userEvent.setup()
    uploadActualsMock.mockResolvedValue(RESULT)
    renderPage()

    await user.type(screen.getByRole('textbox'), CSV)
    await user.click(screen.getByRole('button', { name: /Parse Headers/ }))
    await user.click(screen.getByRole('button', { name: 'Upload Actuals' }))

    expect(await screen.findByText(/Upload complete/)).toBeInTheDocument()
    expect(screen.getByText(/2 created · 1 updated/)).toBeInTheDocument()
  })
})
