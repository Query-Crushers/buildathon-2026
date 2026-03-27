import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, ShieldAlert } from 'lucide-react'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/aml-checks')({
  component: AMLChecksPage,
})

interface AMLCheck {
  id: number
  transaction: {
    id: number
    reference_id: string
    account_name: string
    account_number: string
    amount: string
    currency: string
    status: string
  }
  matched_name: string
  match_score: string
  sanctions_list: string
  is_pep: boolean
  match_type: string
  narrative: string
  checked_at: string
  checked_by: { email: string } | null
}

const SCORE_BG = (score: number) => {
  if (score >= 80) return 'bg-red-500/15 text-red-400 border-red-500/30'
  if (score >= 50) return 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
}

function AMLChecksPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['aml-checks', page],
    queryFn: () => api.get<{ results: AMLCheck[]; count: number; next: string | null }>(`/aml/checks/?page=${page}`),
  })

  const filtered = data?.results.filter((c) =>
    !search ||
    c.transaction.reference_id.toLowerCase().includes(search.toLowerCase()) ||
    c.transaction.account_name.toLowerCase().includes(search.toLowerCase()) ||
    c.matched_name.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  const totalPages = data ? Math.ceil(data.count / 25) : 1

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">AML Checks</h1>
            <p className="text-sm text-slate-400">
              {data ? `${data.count} total checks performed` : 'Loading…'}
            </p>
          </div>
        </div>

        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search by reference or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#f97316]"
          />
        </div>

        <div className="bg-[#1e293b] border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[700px]">
              <thead>
                <tr className="border-b border-slate-700/50 bg-slate-800/30">
                  {['Transaction', 'Account', 'Matched Name', 'Score', 'Sanctions List', 'PEP', 'Checked At', 'By'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-800">
                      <td colSpan={8} className="px-4 py-3">
                        <Skeleton className="h-4 bg-slate-800" />
                      </td>
                    </tr>
                  ))
                  : filtered.map((check) => {
                    const score = parseFloat(check.match_score)
                    return (
                      <tr key={check.id} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">
                          {check.transaction.reference_id}
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-white text-xs font-medium">{check.transaction.account_name}</p>
                          <p className="text-slate-500 text-xs">{check.transaction.account_number}</p>
                        </td>
                        <td className="px-4 py-3 text-xs text-white">{check.matched_name || '—'}</td>
                        <td className="px-4 py-3">
                          <span className={cn('text-xs px-2 py-0.5 rounded-full border font-bold', SCORE_BG(score))}>
                            {score.toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-300">{check.sanctions_list || '—'}</td>
                        <td className="px-4 py-3">
                          {check.is_pep ? (
                            <span className="text-xs text-red-400 font-semibold flex items-center gap-1">
                              <ShieldAlert className="w-3 h-3" /> Yes
                            </span>
                          ) : (
                            <span className="text-xs text-slate-500">No</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {new Date(check.checked_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {check.checked_by?.email ?? 'System'}
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>

          {data && totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
              <p className="text-xs text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button
                  className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-3 py-1.5 rounded border border-slate-600 hover:border-slate-500 transition-colors"
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </button>
                <button
                  className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-3 py-1.5 rounded border border-slate-600 hover:border-slate-500 transition-colors"
                  disabled={page === totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
