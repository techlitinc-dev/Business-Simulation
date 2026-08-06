import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/lib/utils'

const SETTINGS_TABS = [
  { label: 'Profile', to: '/app/settings/profile' },
  { label: 'Workspace', to: '/app/settings/workspace' },
  { label: 'Members', to: '/app/settings/members' },
  { label: 'Security', to: '/app/settings/security' },
  { label: 'API keys', to: '/app/settings/api-keys' },
]

export default function SettingsLayout() {
  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <aside className="lg:w-52 lg:shrink-0">
        <nav className="flex gap-1 overflow-x-auto lg:flex-col">
          {SETTINGS_TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === '/app/settings/profile'}
              className={({ isActive }) =>
                cn(
                  'whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  )
}
