import { Outlet } from 'react-router-dom'
import { Toaster } from 'sonner'

import PaywallModal from '@/features/billing/PaywallModal'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppShell() {
  return (
    <div className="app-canvas flex min-h-screen">
      {/* Sibling 1: fixed-width side navigation */}
      <Sidebar />

      {/* Sibling 2: main content — flows to the right of the sidebar */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>

      <Toaster
        theme="dark"
        position="top-right"
        richColors
        toastOptions={{
          style: {
            background: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            color: 'hsl(var(--foreground))',
          },
        }}
      />
      <PaywallModal />
    </div>
  )
}
