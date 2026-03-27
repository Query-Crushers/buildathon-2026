import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Filter, RefreshCw, AlertTriangle, CheckCircle, X } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { getUser } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/transactions')({
  component: TransactionsPage,
})

interface AMLCheck {
  id: number
  matched_name: string
  match_score: string
  sanctions_list: string
  is_pep: boolean
  match_type: string
  narrative: string
  checked_at: string
}

interface Transaction {
  id: number
  reference_id: string
  date: string
  amount: string
  currency: string
  account_name: string
  account_number: string
  originating_bank: string
  status: string
  risk_level: string
  has_aml_check: boolean
  aml_check?: AMLCheck
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

const SCORE_COLOR = (score: number) => {
  if (score >= 80) return 'text-red-400'
  if (score >= 50) return 'text-amber-400'
  return 'text-emerald-400'
}

function AMLReviewModal({
  transaction,
  onClose,
}: {
  transaction: Transaction
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const user = getUser()
  const [notes, setNotes] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)

  const amlQuery = useQuery({
    queryKey: ['aml-check', transaction.id],
    queryFn: () => api.post<AMLCheck>(`/aml/check/${transaction.id}/`, {}),
    enabled: true,
    staleTime: Infinity,
  })

  const dismissMutation = useMutation({
    mutationFn: () => api.post(`/transactions/${transaction.id}/flag/`, { status: 'clean' }),
    onSuccess: () => {
      toast.success('Flag dismissed — transaction marked clean.')
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      onClose()
    },
    onError: () => toast.error('Failed to dismiss flag.'),
  })

  const lienMutation = useMutation({
    mutationFn: () =>
      api.post('/liens/request/', {
        transaction_id: transaction.id,
        notes,
      }),
    onSuccess: () => {
      toast.success(
        user?.role === 'analyst'
          ? 'Lien request submitted for supervisor approval.'
          : 'Lien placed successfully.'
      )
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['liens'] })
      onClose()
    },
    onError: (err: any) => {
      toast.error(err?.data?.detail ?? 'Failed to submit lien request.')
    },
  })

  const aml = amlQuery.data
  const score = aml ? parseFloat(aml.match_score) : 0
  const isHighRisk = score >= 60 || aml?.is_pep

  return (
    <>
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="bg-[#1e293b] border-slate-700 text-white max-w-[95vw] md:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              AML Review — {transaction.reference_id}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-5">
            {/* Transaction Details */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Transaction Details</h3>
              <div className="grid grid-cols-2 gap-3 bg-slate-800/50 rounded-lg p-4">
                {[
                  ['Reference ID', transaction.reference_id],
                  ['Date', new Date(transaction.date).toLocaleString()],
                  ['Amount', `${transaction.currency} ${Number(transaction.amount).toLocaleString()}`],
                  ['Account Name', transaction.account_name],
                  ['Account Number', transaction.account_number],
                  ['Originating Bank', transaction.originating_bank || '—'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-xs text-slate-500">{label}</p>
                    <p className="text-sm text-white font-medium mt-0.5">{value}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* AML Check Result */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">AML Check Result</h3>
              {amlQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 bg-slate-700" />
                  <Skeleton className="h-4 bg-slate-700 w-3/4" />
                </div>
              ) : aml ? (
                <div className="bg-slate-800/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Match Score</span>
                    <span className={cn('text-2xl font-bold', SCORE_COLOR(score))}>
                      {score.toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      ['Matched Name', aml.matched_name || '—'],
                      ['Sanctions List', aml.sanctions_list || 'None'],
                      ['Match Type', aml.match_type || '—'],
                      ['PEP Flag', aml.is_pep ? 'Yes — PEP detected' : 'No'],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-xs text-slate-500">{label}</p>
                        <p className={cn(
                          'text-sm font-medium mt-0.5',
                          label === 'PEP Flag' && aml.is_pep ? 'text-red-400' : 'text-white'
                        )}>{value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-400">No AML check available.</p>
              )}
            </section>

            {/* Risk Assessment */}
            {aml && (
              <section>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Risk Assessment</h3>
                <div className={cn(
                  'rounded-lg p-4 border',
                  isHighRisk
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-amber-500/10 border-amber-500/30'
                )}>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className={cn('w-4 h-4', isHighRisk ? 'text-red-400' : 'text-amber-400')} />
                    <span className={cn('text-sm font-semibold', isHighRisk ? 'text-red-300' : 'text-amber-300')}>
                      {isHighRisk ? 'High Risk' : 'Medium Risk'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed">{aml.narrative}</p>
                </div>
              </section>
            )}

            {/* Analyst Action */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Analyst Action</h3>
              <div className="space-y-3">
                <div>
                  <Label className="text-slate-300 text-sm">
                    Notes <span className="text-slate-500">(min. 20 characters, required)</span>
                  </Label>
                  <Textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Provide justification for your action..."
                    className="mt-1.5 bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 resize-none"
                    rows={3}
                  />
                  {notes.length > 0 && notes.length < 20 && (
                    <p className="text-xs text-amber-400 mt-1">{20 - notes.length} more characters required</p>
                  )}
                </div>

                <div className="flex gap-3 flex-wrap">
                  <Button
                    variant="outline"
                    className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 bg-transparent"
                    onClick={() => dismissMutation.mutate()}
                    disabled={dismissMutation.isPending}
                  >
                    <CheckCircle className="w-4 h-4 mr-1.5" />
                    Dismiss Flag
                  </Button>
                  <Button
                    className="bg-red-600 hover:bg-red-700 text-white"
                    onClick={() => setShowConfirm(true)}
                    disabled={notes.length < 20 || lienMutation.isPending}
                  >
                    {user?.role === 'analyst' ? 'Submit for Lien Approval' : 'Place Lien'}
                  </Button>
                </div>
              </div>
            </section>
          </div>
        </DialogContent>
      </Dialog>

      {/* Lien Confirmation Dialog */}
      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent className="bg-[#1e293b] border-slate-700 text-white">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Confirm Lien Action</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">
              You are about to place a lien on account{' '}
              <span className="text-white font-medium">{transaction.account_number}</span>.
              This action will be logged and emailed to compliance. Confirm?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-slate-600 text-slate-300 hover:bg-slate-700">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={() => {
                setShowConfirm(false)
                lienMutation.mutate()
              }}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function TransactionsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [riskFilter, setRiskFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [reviewTxn, setReviewTxn] = useState<Transaction | null>(null)

  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (search) params.set('search', search)
  if (statusFilter !== 'all') params.set('status', statusFilter)
  if (riskFilter !== 'all') params.set('risk_level', riskFilter)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['transactions', page, search, statusFilter, riskFilter],
    queryFn: () => api.get<{ results: Transaction[]; count: number; next: string | null; previous: string | null }>(`/transactions/?${params}`),
  })

  const totalPages = data ? Math.ceil(data.count / 25) : 1

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Transactions</h1>
            <p className="text-sm text-slate-400">
              {data ? `${data.count.toLocaleString()} total transactions` : 'Loading…'}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent"
            onClick={() => refetch()}
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search reference, account name..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              className="pl-9 bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#f97316]"
            />
          </div>
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[160px] bg-slate-800/60 border-slate-600 text-slate-300">
              <Filter className="w-3.5 h-3.5 mr-2 text-slate-400" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="all" className="text-slate-300">All Statuses</SelectItem>
              <SelectItem value="clean" className="text-emerald-400">Clean</SelectItem>
              <SelectItem value="flagged" className="text-amber-400">Flagged</SelectItem>
              <SelectItem value="under_review" className="text-blue-400">Under Review</SelectItem>
              <SelectItem value="lien_placed" className="text-red-400">Lien Placed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={riskFilter} onValueChange={(v) => { setRiskFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[150px] bg-slate-800/60 border-slate-600 text-slate-300">
              <SelectValue placeholder="Risk Level" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="all" className="text-slate-300">All Risk Levels</SelectItem>
              <SelectItem value="low" className="text-slate-400">Low</SelectItem>
              <SelectItem value="medium" className="text-amber-400">Medium</SelectItem>
              <SelectItem value="high" className="text-orange-400">High</SelectItem>
              <SelectItem value="critical" className="text-red-400">Critical</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        <div className="bg-[#1e293b] border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
              <thead>
                <tr className="border-b border-slate-700/50 bg-slate-800/30">
                  {['Reference ID', 'Date/Time', 'Amount', 'Account', 'Status', 'Risk Level', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-800">
                      <td colSpan={7} className="px-4 py-3">
                        <Skeleton className="h-4 bg-slate-800" />
                      </td>
                    </tr>
                  ))
                  : data?.results.map((txn) => (
                    <tr
                      key={txn.id}
                      className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-300">{txn.reference_id}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">
                        {new Date(txn.date).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-white font-medium text-xs">
                        {txn.currency} {Number(txn.amount).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-white text-xs font-medium">{txn.account_name}</p>
                        <p className="text-slate-500 text-xs">{txn.account_number}</p>
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
                          <Button
                            size="sm"
                            className="bg-amber-500/15 text-amber-400 hover:bg-amber-500/25 border border-amber-500/30 text-xs h-7 px-3"
                            onClick={() => setReviewTxn(txn)}
                          >
                            Review →
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
              <p className="text-xs text-slate-400">
                Page {page} of {totalPages} · {data.count} total
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-slate-600 text-slate-300 bg-transparent hover:bg-slate-700 h-7 text-xs"
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-slate-600 text-slate-300 bg-transparent hover:bg-slate-700 h-7 text-xs"
                  disabled={page === totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {reviewTxn && (
        <AMLReviewModal transaction={reviewTxn} onClose={() => setReviewTxn(null)} />
      )}
    </div>
  )
}
