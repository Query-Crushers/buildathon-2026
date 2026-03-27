import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'

interface User {
  id: number
  name: string
  email: string
}

interface AppLayoutProps {
  user: User
  children: React.ReactNode
}

/**
 * Optional layout wrapper for apps that want a sidebar.
 *
 * Usage:
 * ```tsx
 * import { AppLayout } from '@/layouts/app-layout'
 *
 * function MyPage() {
 *   const user = { id: 1, name: "User", email: "user@example.com" }
 *
 *   return (
 *     <AppLayout user={user}>
 *       <div className="p-6">
 *         <h1>My Page</h1>
 *       </div>
 *     </AppLayout>
 *   )
 * }
 * ```
 */
export function AppLayout({ user, children }: AppLayoutProps) {
  return (
    <SidebarProvider>
      <AppSidebar user={user} />
      <SidebarInset>
        {children}
      </SidebarInset>
    </SidebarProvider>
  )
}
