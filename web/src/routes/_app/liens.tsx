import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { getUser } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/liens')({
  component: LiensPage,
})

interface LienRequest {
  id: number
  transaction: {
    reference_id: string
    account_name: string
    account_number: string
    amount: string
    currency: string
  }
  requested_by: { email: string; first_name: string; last_name: string }
  approved_by: { email: string; first_name: string; last_name: string } | null
  notes: string
  supervisor_notes: string
  status: string
  requested_at: string
  resolved_at: string | null
}

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  approved: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  rejected: 'bg-red-500/15 text-red-400 border-red-500/30',
  executed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
}

function ActionModal({
  lien,
  action,
  onClose,
}: {
  lien: LienRequest
  action: 'approve' | 'reject' | 'execute'
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [notes, setNotes] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/liens/${lien.id}/${action}/`, { supervisor_notes: notes }),
    onSuccess: () => {
      const msgs = { approve: 'Lien request approved.', reject: 'Lien request rejected.', execute: 'Lien executed successfully.' }
      toast.success(msgs[action])
      queryClient.invalidateQueries({ queryKey: ['liens'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      onClose()
    },
    onError: (err: any) => toast.error(err?.data?.detail ?? 'Action failed.'),
  })

  const titles = { approve: 'Approve Lien Request', reject: 'Reject Lien Request', execute: 'Execute Lien' }
  const colors = { approve: 'bg-blue-600 hover:bg-blue-700', reject: 'bg-red-600 hover:bg-red-700', execute: 'bg-emerald-600 hover:bg-emerald-700' }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="bg-[#1e293b] border-slate-700 text-white max-w-[95vw] md:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white">{titles[action]}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="bg-slate-800/50 rounded-lg p-4 space-y-2 text-sm">
            <p><span className="text-slate-400">Reference: </span><span className="text-white font-mono">{lien.transaction.reference_id}</span></p>
            <p><span className="text-slate-400">Account: </span><span className="text-white">{lien.transaction.account_name} ({lien.transaction.account_number})</span></p>
            <p><span className="text-slate-400">Amount: </span><span className="text-white">{lien.transaction.currency} {Number(lien.transaction.amount).toLocaleString()}</span></p>
            <p><span className="text-slate-400">Analyst notes: </span><span className="text-slate-300">{lien.notes}</span></p>
          </div>
          <div>
            <Label className="text-slate-300 text-sm">Supervisor notes (optional)</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes for the record..."
              className="mt-1.5 bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 resize-none"
              rows={3}
            />
          </div>
          <div className="flex gap-3 justify-end">
            <Button
              variant="outline"
              className="border-slate-600 text-slate-300 bg-transparent hover:bg-slate-700"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className={cn('text-white', colors[action])}
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Processing…' : titles[action]}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function LiensPage() {
  const user = getUser()
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [activeAction, setActiveAction] = useState<{ lien: LienRequest; action: 'approve' | 'reject' | 'execute' } | null>(null)

  const params = new URLSearchParams({ page: String(page) })
  if (statusFilter !== 'all') params.set('status', statusFilter)

  const { data, isLoading } = useQuery({
    queryKey: ['liens', page, statusFilter],
    queryFn: () => api.get<{ results: LienRequest[]; count: number }>(`/liens/?${params}`),
  })

  const canAct = user?.role === 'supervisor' || user?.role === 'admin'
  const totalPages = data ? Math.ceil(data.count / 25) : 1

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Lien Management</h1>
            <p className="text-sm text-slate-400">
              {data ? `${data.count} lien records` : 'Loading…'}
            </p>
          </div>
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
            <SelectTrigger className="w-[160px] bg-slate-800/60 border-slate-600 text-slate-300">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="all" className="text-slate-300">All Statuses</SelectItem>
              <SelectItem value="pending" className="text-amber-400">Pending</SelectItem>
              <SelectItem value="approved" className="text-blue-400">Approved</SelectItem>
              <SelectItem value="rejected" className="text-red-400">Rejected</SelectItem>
              <SelectItem value="executed" className="text-emerald-400">Executed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="bg-[#1e293b] border border-slate-700/50 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="border-b border-slate-700/50 bg-slate-800/30">
                  {['Transaction Ref', 'Account', 'Amount', 'Requested By', 'Approved By', 'Date', 'Status', canAct ? 'Actions' : ''].filter(Boolean).map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-800">
                      <td colSpan={8} className="px-4 py-3">
                        <Skeleton className="h-4 bg-slate-800" />
                      </td>
                    </tr>
                  ))
                  : data?.results.map((lien) => (
                    <tr key={lien.id} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-slate-300">
                        {lien.transaction.reference_id}
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-white text-xs font-medium">{lien.transaction.account_name}</p>
                        <p className="text-slate-500 text-xs">{lien.transaction.account_number}</p>
                      </td>
                      <td className="px-4 py-3 text-white text-xs font-medium">
                        {lien.transaction.currency} {Number(lien.transaction.amount).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300">
                        {lien.requested_by?.first_name
                          ? `${lien.requested_by.first_name} ${lien.requested_by.last_name}`
                          : lien.requested_by?.email}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">
                        {lien.approved_by
                          ? lien.approved_by.first_name
                            ? `${lien.approved_by.first_name} ${lien.approved_by.last_name}`
                            : lien.approved_by.email
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">
                        {new Date(lien.requested_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium capitalize', STATUS_BADGE[lien.status] ?? '')}>
                          {lien.status}
                        </span>
                      </td>
                      {canAct && (
                        <td className="px-4 py-3">
                          <div className="flex gap-2 flex-wrap">
                            {lien.status === 'pending' && (
                              <>
                                <Button
                                  size="sm"
                                  className="bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 text-xs h-7 px-2"
                                  onClick={() => setActiveAction({ lien, action: 'approve' })}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="sm"
                                  className="bg-red-600/20 text-red-400 hover:bg-red-600/30 border border-red-500/30 text-xs h-7 px-2"
                                  onClick={() => setActiveAction({ lien, action: 'reject' })}
                                >
                                  Reject
                                </Button>
                              </>
                            )}
                            {lien.status === 'approved' && (
                              <Button
                                size="sm"
                                className="bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 border border-emerald-500/30 text-xs h-7 px-2"
                                onClick={() => setActiveAction({ lien, action: 'execute' })}
                              >
                                Execute Lien
                              </Button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {data && totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
              <p className="text-xs text-slate-400">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button
                  className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-3 py-1.5 rounded border border-slate-600 transition-colors"
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </button>
                <button
                  className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-3 py-1.5 rounded border border-slate-600 transition-colors"
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

      {activeAction && (
        <ActionModal
          lien={activeAction.lien}
          action={activeAction.action}
          onClose={() => setActiveAction(null)}
        />
      )}
    </div>
  )
}
