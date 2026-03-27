import { createFileRoute } from '@tanstack/react-router'
import { BarChart3 } from 'lucide-react'

export const Route = createFileRoute('/_app/reports')({
  component: ReportsPage,
})

function ReportsPage() {
  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6">
        <div>
          <h1 className="text-xl font-bold text-white">Reports</h1>
          <p className="text-sm text-slate-400">Compliance and analytics reports</p>
        </div>
        <div className="flex-1 flex items-center justify-center bg-[#1e293b] border border-slate-700/50 rounded-xl p-16">
          <div className="text-center">
            <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 font-medium">Advanced reports coming soon</p>
            <p className="text-slate-600 text-sm mt-1">Export, scheduled reports, and deep analytics</p>
          </div>
        </div>
      </div>
    </div>
  )
}
