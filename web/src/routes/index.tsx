import { createFileRoute, Navigate } from '@tanstack/react-router'
import { isAuthenticated } from '@/lib/auth'

export const Route = createFileRoute('/')({
  component: RootRedirect,
})

function RootRedirect() {
  return <Navigate to={isAuthenticated() ? '/_app/dashboard' : '/login'} />
}
