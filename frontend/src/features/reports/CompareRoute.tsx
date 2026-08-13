import ComparePage from '@/features/reports/ComparePage'
import { useCompletedRuns } from '@/features/reports/hooks'

/** Route wrapper: loads the workspace's runs for the pickers. */
export default function CompareRoute() {
  const { data: runs = [] } = useCompletedRuns()

  const completed = runs
    .filter(
      (r) =>
        (r.status === 'completed' || r.status === 'dead') &&
        (r.mode === 'monte_carlo' || r.mode === 'stress'),
    )
    .map((r) => ({
      id: r.id,
      label: `${r.mode} · seed ${r.seed} · ${new Date(r.created_at).toLocaleDateString()}`,
    }))

  return <ComparePage runs={completed} />
}
