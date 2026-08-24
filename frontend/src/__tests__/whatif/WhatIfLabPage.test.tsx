import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { WhatIfLabPage } from '@/features/whatif/WhatIfLabPage'
import { useWorkspaceStore } from '@/stores/workspace-store'
import type { BreakevenResult, SweepResult } from '@/features/whatif/api'

const { runSweepMock, findBreakevenMock, saveVersionMock } = vi.hoisted(() => ({
  runSweepMock: vi.fn(),
  findBreakevenMock: vi.fn(),
  saveVersionMock: vi.fn(),
}))

vi.mock('@/features/whatif/api', () => ({
  runSweep: (...args: unknown[]) => runSweepMock(...args),
  findBreakeven: (...args: unknown[]) => findBreakevenMock(...args),
  saveVersion: (...args: unknown[]) => saveVersionMock(...args),
}))

const SWEEP: SweepResult = {
  blueprint_id: 'bp_1',
  param: 'revenue_engine.streams.0.churn_monthly',
  grid: [
    {
      param_value: 0.02,
      survival_rate: 0.9,
      median_runway: 24,
      p25_runway: 22,
      p75_runway: 24,
    },
    {
      param_value: 0.05,
      survival_rate: 0.65,
      median_runway: 20,
      p25_runway: 16,
      p75_runway: 24,
    },
    {
      param_value: 0.08,
      survival_rate: 0.4,
      median_runway: 15,
      p25_runway: 10,
      p75_runway: 20,
    },
  ],
}

const BREAKEVEN: BreakevenResult = {
  blueprint_id: 'bp_1',
  param: 'revenue_engine.streams.0.churn_monthly',
  breakeven_value: 0.0616,
  survival_at_breakeven: 0.5,
  message:
    'Your model maintains ≥50% survival only if revenue_engine.streams.0.churn_monthly stays below 0.0616',
}

function setPlanTier(tier: string) {
  useWorkspaceStore.getState().setWorkspaces([
    { id: 'ws_1', name: 'Test WS', slug: 'test-ws', plan_tier: tier, role: 'owner', benchmark_opt_in: true },
  ])
  useWorkspaceStore.getState().setActive('ws_1')
}

function renderPage(blueprintId = 'bp_1') {
  return render(<WhatIfLabPage blueprintId={blueprintId} />)
}

describe('WhatIfLabPage', () => {
  beforeEach(() => {
    runSweepMock.mockReset()
    findBreakevenMock.mockReset()
    saveVersionMock.mockReset()
  })

  it('shows paywall for free plan', () => {
    setPlanTier('free')
    renderPage()

    expect(screen.getByText('What-If Lab')).toBeInTheDocument()
    expect(
      screen.getByText('Run sensitivity sweeps and find break-even thresholds. Pro+ required.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Run Sweep' })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('shows parameter selector and Run button for pro plan', () => {
    setPlanTier('pro')
    renderPage()

    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run Sweep' })).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Upgrade to Pro' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/Range:/)).toBeInTheDocument()
  })

  it('calls runSweep and findBreakeven on button click', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    runSweepMock.mockResolvedValue(SWEEP)
    findBreakevenMock.mockResolvedValue(BREAKEVEN)
    renderPage('bp_abc')

    await user.click(screen.getByRole('button', { name: 'Run Sweep' }))

    expect(runSweepMock).toHaveBeenCalledWith(
      'bp_abc',
      'revenue_engine.streams.0.churn_monthly',
      0.01,
      0.2,
    )
    expect(findBreakevenMock).toHaveBeenCalledWith(
      'bp_abc',
      'revenue_engine.streams.0.churn_monthly',
      0.01,
      0.2,
    )
  })

  it('shows heatmap after successful sweep', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    runSweepMock.mockResolvedValue(SWEEP)
    findBreakevenMock.mockResolvedValue(BREAKEVEN)
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Run Sweep' }))

    expect(await screen.findByText(/Survival Rate vs/)).toBeInTheDocument()
    // Three grid points → three heatmap cells (percentage labels).
    for (const pt of SWEEP.grid) {
      expect(screen.getByText(`${(pt.survival_rate * 100).toFixed(0)}%`)).toBeInTheDocument()
    }
  })

  it('shows break-even card after sweep', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    runSweepMock.mockResolvedValue(SWEEP)
    findBreakevenMock.mockResolvedValue(BREAKEVEN)
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Run Sweep' }))

    expect(await screen.findByText('⚠️ Break-Even Threshold')).toBeInTheDocument()
    expect(
      screen.getByText('revenue engine.streams.0.churn monthly = 0.0616'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/stays below 0\.0616/),
    ).toBeInTheDocument()
  })

  it('calls saveVersion with correct params on grid point click', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    runSweepMock.mockResolvedValue(SWEEP)
    findBreakevenMock.mockResolvedValue(BREAKEVEN)
    saveVersionMock.mockResolvedValue({ id: 'bpv_1', version: 3 })
    renderPage('bp_save')

    await user.click(screen.getByRole('button', { name: 'Run Sweep' }))
    const saveBtn = await screen.findByRole('button', { name: '0.050 (65%)' })
    await user.click(saveBtn)

    expect(saveVersionMock).toHaveBeenCalledWith(
      'bp_save',
      'revenue_engine.streams.0.churn_monthly',
      0.05,
      'Monthly Churn = 0.0500 (What-If)',
    )
    expect(await screen.findByText('✅ Saved as version: 3')).toBeInTheDocument()
  })
})
