import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Users } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { getUser } from '@/lib/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/settings')({
  component: SettingsPage,
})

interface UserRecord {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
}

const ROLE_BADGE: Record<string, string> = {
  admin: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  supervisor: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  analyst: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
}

function SettingsPage() {
  const currentUser = getUser()
  const queryClient = useQueryClient()

  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', role: 'analyst' })

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<UserRecord[]>('/users/'),
    enabled: currentUser?.role === 'admin',
  })

  const createMutation = useMutation({
    mutationFn: () => api.post('/users/', form),
    onSuccess: () => {
      toast.success('User created successfully.')
      setForm({ email: '', password: '', first_name: '', last_name: '', role: 'analyst' })
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: any) => toast.error(err?.data?.detail ?? 'Failed to create user.'),
  })

  if (currentUser?.role !== 'admin') {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-slate-400">Admin access required.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      <div className="flex flex-col gap-5 p-5 md:p-6 max-w-4xl">
        <div>
          <h1 className="text-xl font-bold text-white">Settings</h1>
          <p className="text-sm text-slate-400">User management and system configuration</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Create User */}
          <Card className="bg-[#1e293b] border-slate-700/50">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-[#f97316]" />
                Create User
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-slate-400 text-xs">First Name</Label>
                  <Input
                    value={form.first_name}
                    onChange={(e) => setForm(f => ({ ...f, first_name: e.target.value }))}
                    className="mt-1 bg-slate-800/60 border-slate-600 text-white text-sm h-8"
                  />
                </div>
                <div>
                  <Label className="text-slate-400 text-xs">Last Name</Label>
                  <Input
                    value={form.last_name}
                    onChange={(e) => setForm(f => ({ ...f, last_name: e.target.value }))}
                    className="mt-1 bg-slate-800/60 border-slate-600 text-white text-sm h-8"
                  />
                </div>
              </div>
              <div>
                <Label className="text-slate-400 text-xs">Email</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                  className="mt-1 bg-slate-800/60 border-slate-600 text-white text-sm h-8"
                />
              </div>
              <div>
                <Label className="text-slate-400 text-xs">Password</Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                  className="mt-1 bg-slate-800/60 border-slate-600 text-white text-sm h-8"
                />
              </div>
              <div>
                <Label className="text-slate-400 text-xs">Role</Label>
                <Select value={form.role} onValueChange={(v) => setForm(f => ({ ...f, role: v }))}>
                  <SelectTrigger className="mt-1 bg-slate-800/60 border-slate-600 text-slate-300 h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="analyst" className="text-slate-300">Analyst</SelectItem>
                    <SelectItem value="supervisor" className="text-slate-300">Supervisor</SelectItem>
                    <SelectItem value="admin" className="text-slate-300">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                className="w-full bg-[#f97316] hover:bg-[#ea6c0d] text-white text-sm h-8"
                onClick={() => createMutation.mutate()}
                disabled={!form.email || !form.password || createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating…' : 'Create User'}
              </Button>
            </CardContent>
          </Card>

          {/* User List */}
          <Card className="bg-[#1e293b] border-slate-700/50">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Users className="w-4 h-4 text-[#f97316]" />
                All Users ({users?.length ?? 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {isLoading
                ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-10 bg-slate-800" />)
                : users?.map((u) => (
                  <div key={u.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-800/50">
                    <div className="w-7 h-7 rounded-full bg-[#f97316]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-[#f97316]">
                        {(u.first_name?.[0] ?? u.email[0]).toUpperCase()}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-white truncate">
                        {u.first_name ? `${u.first_name} ${u.last_name}` : u.email}
                      </p>
                      <p className="text-xs text-slate-500 truncate">{u.email}</p>
                    </div>
                    <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', ROLE_BADGE[u.role] ?? '')}>
                      {u.role}
                    </span>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
