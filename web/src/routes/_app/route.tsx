import { createFileRoute, Outlet, Link, useNavigate, useLocation, redirect } from '@tanstack/react-router'
import { useEffect } from 'react'
import {
  LayoutDashboard, ArrowLeftRight, Search, Gavel, BarChart3,
  Settings, Shield, LogOut, ChevronRight,
} from 'lucide-react'
import { isAuthenticated, getUser, clearAuth } from '@/lib/auth'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    if (!isAuthenticated()) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
})

const NAV_ITEMS = [
  { to: '/_app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/_app/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/_app/aml-checks', label: 'AML Checks', icon: Search },
  { to: '/_app/liens', label: 'Lien Management', icon: Gavel },
  { to: '/_app/reports', label: 'Reports', icon: BarChart3 },
]

const ROLE_BADGE_COLOR: Record<string, string> = {
  admin: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  supervisor: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  analyst: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
}

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = getUser()

  // Reactive auth guard — catches token expiry mid-session
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate({ to: '/login' })
    }
  }, [navigate])

  const handleLogout = () => {
    clearAuth()
    navigate({ to: '/login' })
  }

  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase() || user.email[0].toUpperCase()
    : '?'

  const roleBadgeColor = ROLE_BADGE_COLOR[user?.role ?? 'analyst']

  return (
    <div className="flex h-full overflow-hidden bg-slate-950">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 flex flex-col bg-[#1e293b] border-r border-slate-700/50">
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-700/50">
          <div className="bg-[#f97316] rounded-lg p-1.5">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-none">SwitchGuard</p>
            <p className="text-[10px] text-slate-400 tracking-wider uppercase mt-0.5">Analytics</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
            const urlPath = to.replace('/_app', '')
            const active = location.pathname === urlPath
              || location.pathname.startsWith(urlPath + '/')
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                  active
                    ? 'bg-[#f97316]/15 text-[#f97316] border border-[#f97316]/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                )}
              >
                <Icon className={cn('w-4 h-4 flex-shrink-0', active ? 'text-[#f97316]' : '')} />
                <span className="flex-1">{label}</span>
                {active && <ChevronRight className="w-3 h-3 opacity-60" />}
              </Link>
            )
          })}

          {user?.role === 'admin' && (
            <Link
              to="/_app/settings"
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                location.pathname === '/settings'
                  ? 'bg-[#f97316]/15 text-[#f97316] border border-[#f97316]/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              )}
            >
              <Settings className="w-4 h-4 flex-shrink-0" />
              <span>Settings</span>
            </Link>
          )}
        </nav>

        {/* User section */}
        <div className="px-3 pb-4 border-t border-slate-700/50 pt-3">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-800/50">
            <Avatar className="w-8 h-8 flex-shrink-0">
              <AvatarFallback className="bg-[#f97316]/20 text-[#f97316] text-xs font-bold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.email}
              </p>
              <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded-full border', roleBadgeColor)}>
                {user?.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-500 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-950">
        <Outlet />
      </main>
    </div>
  )
}
