import * as React from "react"
import { type LucideIcon } from "lucide-react"
import { Link, useLocation } from "@tanstack/react-router"

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function NavMain({
  items,
  ...props
}: {
  items: {
    title: string
    url: string
    icon?: LucideIcon
    activePattern?: string  // Optional: custom pattern for matching active state
  }[]
} & React.ComponentPropsWithoutRef<typeof SidebarGroup>) {
  const location = useLocation()
  const url = location.pathname

  return (
    <SidebarGroup {...props}>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            // Determine active state based on URL matching
            // Some pages need exact match, others match if URL starts with their pattern
            let isActive = false

            if (item.activePattern) {
              // Use custom pattern if provided (supports regex)
              const pattern = new RegExp(item.activePattern)
              isActive = pattern.test(url)
            } else if (item.url === '/') {
              // Exact match for home/dashboard
              isActive = url === item.url
            } else {
              // Other pages should be active if URL starts with their pattern
              isActive = url.startsWith(item.url)
            }

            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild tooltip={item.title} isActive={isActive}>
                  <Link to={item.url}>
                    {item.icon && <item.icon />}
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
