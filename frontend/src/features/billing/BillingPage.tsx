import { Link } from 'react-router-dom'
import { CreditCard } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import UsageMeters from './UsageMeters'

export default function BillingPage() {
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Your plan, usage, and limits.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Usage</CardTitle>
          <CardDescription>
            Consumption against your current plan limits.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UsageMeters />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <CreditCard className="h-4 w-4" /> Manage plan
          </CardTitle>
          <CardDescription>
            Compare tiers or upgrade to lift your monthly limits.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/pricing">View pricing</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
