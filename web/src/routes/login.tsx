import { createFileRoute } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { Shield, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { api } from '@/lib/api'
import { setAuth, type AuthUser } from '@/lib/auth'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

function LoginPage() {
  const [showPw, setShowPw] = useState(false)

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      api.post<{ access: string; refresh: string; user: AuthUser }>('/auth/login/', data),
    onSuccess: (data) => {
      setAuth(data.access, data.refresh, data.user)
      // Hard navigation ensures beforeLoad auth guard re-evaluates with fresh tokens
      window.location.replace('/dashboard')
    },
    onError: () => {
      toast.error('Invalid email or password.')
    },
  })

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-[#0f1729] min-h-0 overflow-auto py-8">
      <div className="w-full max-w-md px-4">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="bg-[#f97316] rounded-xl p-2.5">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">SwitchGuard</h1>
            <p className="text-xs text-slate-400 tracking-widest uppercase">Analytics Platform</p>
          </div>
        </div>

        {/* Card */}
        <div className="bg-[#1e293b] border border-slate-700/50 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white mb-1">Sign in</h2>
          <p className="text-sm text-slate-400 mb-6">Access the transaction monitoring dashboard</p>

          <Form {...form}>
            <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-300 text-sm">Email address</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="email"
                        placeholder="analyst@switchguard.com"
                        className="bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#f97316] focus-visible:border-[#f97316]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-300 text-sm">Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          {...field}
                          type={showPw ? 'text' : 'password'}
                          placeholder="••••••••"
                          className="bg-slate-800/60 border-slate-600 text-white placeholder:text-slate-500 pr-10 focus-visible:ring-[#f97316] focus-visible:border-[#f97316]"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPw(!showPw)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                        >
                          {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                className="w-full bg-[#f97316] hover:bg-[#ea6c0d] text-white font-semibold mt-2"
                disabled={mutation.isPending}
              >
                {mutation.isPending ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </Form>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          Powered by Interswitch · Transaction Monitoring System
        </p>
      </div>
    </div>
  )
}
