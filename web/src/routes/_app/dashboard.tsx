import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  ArrowLeftRight, AlertTriangle, Search, Gavel,
  TrendingUp, ArrowRight, RefreshCw,
} from 'lucide-react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/dashboard')({
  component: DashboardPage,
})

interface DashboardStats {
  kpis: {
    total_transactions: number
    flagged_transactions: number
    flagged_pct: number
    aml_hits: number
    liens_placed: number
  }
  volume_chart: { date: string; transactions: number }[]
  risk_distribution: { clean: number; flagged: number; under_review: number; lien_placed: number }
}

interface Transaction {
  id: number
  reference_id: string
  date: string
  amount: string
  currency: string
  account_name: string
  account_number: string
  status: string
  risk_level: string
  has_aml_check: boolean
}

const STATUS_BADGE: Record<string, string> = {
  clean: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  flagged: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  under_review: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  lien_placed: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const RISK_BADGE: Record<string, string> = {
  low: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  high: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  critical: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const PIE_COLORS = ['#22c55e', '#f59e0b', '#3b82f6', '#ef4444']

function KpiCard({
  title, value, sub, icon: Icon, accent,
}: {
  title: string
  value: string | number
  sub?: string
  icon: React.ElementType
  accent: string
}) {
  return (
    <Card className="bg-[#1e293b] border-slate-700/50 text-white">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
          </div>
          <div className={cn('p-2.5 rounded-lg', accent)}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get<DashboardStats>('/sg-dashboard/stats/'),
    refetchInterval: 60_000,
  })

  const { data: txns, isLoading: txnsLoading } = useQuery({
    queryKey: ['transactions', { page: 1 }],
    queryFn: () => api.get<{ results: Transaction[]; count: number }>('/transactions/?page_size=10'),
  })

  const kpis = stats?.kpis
  const riskDist = stats?.risk_distribution

  const pieData = riskDist ? [
    { name: 'Clean', value: riskDist.clean },
    { name: 'Flagged', value: riskDist.flagged },
    { name: 'Under Review', value: riskDist.under_review },
    { name: 'Lien Placed', value: riskDist.lien_placed },
  ] : []

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Dashboard</h1>
            <p className="text-sm text-slate-400">Last 30 days • Transaction monitoring overview</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent"
            onClick={() => window.location.reload()}
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {statsLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 bg-slate-800" />
            ))
          ) : (
            <>
              <KpiCard
                title="Total Transactions"
                value={kpis?.total_transactions.toLocaleString() ?? '—'}
                sub="Past 30 days"
                icon={ArrowLeftRight}
                accent="bg-blue-500/15 text-blue-400"
              />
              <KpiCard
                title="Flagged Transactions"
                value={kpis?.flagged_transactions.toLocaleString() ?? '—'}
                sub={kpis ? `${kpis.flagged_pct}% of total` : undefined}
                icon={AlertTriangle}
                accent="bg-amber-500/15 text-amber-400"
              />
              <KpiCard
                title="AML Hits"
                value={kpis?.aml_hits.toLocaleString() ?? '—'}
                sub="Sanctions / PEP matches"
                icon={Search}
                accent="bg-orange-500/15 text-orange-400"
              />
              <KpiCard
                title="Liens Placed"
                value={kpis?.liens_placed.toLocaleString() ?? '—'}
                sub="Lien actions"
                icon={Gavel}
                accent="bg-red-500/15 text-red-400"
              />
            </>
          )}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Volume Bar Chart */}
          <Card className="lg:col-span-2 bg-[#1e293b] border-slate-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#f97316]" />
                7-Day Transaction Volume
              </CardTitle>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <Skeleton className="h-48 bg-slate-800" />
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={stats?.volume_chart ?? []}>
                    <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                      cursor={{ fill: 'rgba(249,115,22,0.08)' }}
                    />
                    <Bar dataKey="transactions" fill="#f97316" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Risk Distribution Pie */}
          <Card className="bg-[#1e293b] border-slate-700/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-slate-300">Risk Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <Skeleton className="h-48 bg-slate-800" />
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="45%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((_, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Legend
                      iconType="circle"
                      iconSize={8}
                      formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>}
                    />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Transactions Table */}
        <Card className="bg-[#1e293b] border-slate-700/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="text-sm font-semibold text-slate-300">Recent Transactions</CardTitle>
              <Link to="/_app/transactions">
                <Button variant="ghost" size="sm" className="text-[#f97316] hover:text-[#f97316] hover:bg-[#f97316]/10 text-xs h-7">
                  View all <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[640px]">
                <thead>
                  <tr className="border-b border-slate-700/50">
                    {['Reference ID', 'Account', 'Amount', 'Status', 'Risk', 'Action'].map((h) => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wide">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {txnsLoading
                    ? Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i} className="border-b border-slate-800">
                        <td colSpan={6} className="px-4 py-3">
                          <Skeleton className="h-4 bg-slate-800" />
                        </td>
                      </tr>
                    ))
                    : txns?.results.map((txn) => (
                      <tr key={txn.id} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">{txn.reference_id}</td>
                        <td className="px-4 py-3">
                          <p className="text-white text-xs font-medium">{txn.account_name}</p>
                          <p className="text-slate-500 text-xs">{txn.account_number}</p>
                        </td>
                        <td className="px-4 py-3 text-white text-xs font-medium">
                          {txn.currency} {Number(txn.amount).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium', STATUS_BADGE[txn.status] ?? '')}>
                            {txn.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium', RISK_BADGE[txn.risk_level] ?? '')}>
                            {txn.risk_level}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {(txn.status === 'flagged' || txn.status === 'under_review') && (
                            <Link to="/_app/transactions">
                              <Button size="sm" variant="ghost" className="text-[#f97316] hover:bg-[#f97316]/10 text-xs h-6 px-2">
                                Review →
                              </Button>
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
