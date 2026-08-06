import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Users, Building2, DollarSign, Play, Cpu } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { apiFetch } from '@/lib/api-client'

export interface AdminStats {
  total_users: number
  users_last_30d: number
  total_workspaces: number
  workspaces_last_30d: number
  subscriptions_by_tier: Record<string, number>
  mrr_estimate_usd: number
  runs_this_month: number
  monte_carlo_ticks_this_month: number
  llm_tokens_this_month: number
}

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => apiFetch<AdminStats>('/api/v1/admin/stats'),
  })
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Users
  label: string
  value: string
  sub?: string
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <Icon className="h-4 w-4" /> {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  )
}

export default function AdminDashboardPage() {
  const { data, isLoading, isError } = useAdminStats()

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-3 h-8 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return <p className="text-sm text-destructive">Could not load admin stats.</p>
  }

  const tierData = Object.entries(data.subscriptions_by_tier).map(([tier, count]) => ({
    tier,
    count,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Admin dashboard</h1>
        <p className="text-sm text-muted-foreground">Platform-wide analytics.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Users}
          label="Users"
          value={String(data.total_users)}
          sub={`+${data.users_last_30d} in 30d`}
        />
        <StatCard
          icon={Building2}
          label="Workspaces"
          value={String(data.total_workspaces)}
          sub={`+${data.workspaces_last_30d} in 30d`}
        />
        <StatCard
          icon={DollarSign}
          label="MRR (est.)"
          value={`$${data.mrr_estimate_usd.toLocaleString()}`}
        />
        <StatCard
          icon={Play}
          label="Runs this month"
          value={String(data.runs_this_month)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          icon={Cpu}
          label="Monte Carlo ticks"
          value={String(data.monte_carlo_ticks_this_month)}
        />
        <StatCard
          icon={Cpu}
          label="LLM tokens"
          value={data.llm_tokens_this_month.toLocaleString()}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Subscriptions by tier</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={tierData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="tier" tick={{ fill: 'var(--muted-foreground)' }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: 'var(--background)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="count" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
