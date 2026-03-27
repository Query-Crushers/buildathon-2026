import { Outlet, createRootRoute } from '@tanstack/react-router'
import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from '@/components/ui/sonner'

export const Route = createRootRoute({
  component: () => (
    <ThemeProvider defaultTheme="system" storageKey="cayuUiTheme">
      <div className="flex flex-col h-full bg-background">
        <Outlet />
      </div>
      <Toaster position="top-right" />
    </ThemeProvider>
  ),
})
