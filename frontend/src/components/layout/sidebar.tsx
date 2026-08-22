"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { WorkspaceSwitcher } from "./workspace-switcher"
import {
  MessageSquare,
  LayoutDashboard,
  FileText,
  Bot,
  Settings,
} from "lucide-react"

const sidebarItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "AI Chat", href: "/chat", icon: MessageSquare },
  { name: "Knowledge base", href: "/documents", icon: FileText },
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card px-3 py-4">
      {/* Logo */}
      <div className="mb-4 px-3 text-lg font-bold tracking-tight">Aurenix AI</div>

      {/* Workspace Switcher */}
      <div className="mb-4 px-1">
        <WorkspaceSwitcher />
      </div>

      <div className="border-b mb-3" />

      {/* Navigation */}
      <nav className="flex flex-1 flex-col space-y-1">
        {sidebarItems.map((item) => {
          const isActive = pathname?.startsWith(item.href)
          return (
            <Link key={item.href} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn("w-full justify-start", isActive ? "font-semibold" : "font-normal")}
              >
                <item.icon className="mr-3 h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </nav>

      {/* Enterprise badge */}
      <div className="mt-auto px-3 pb-4">
        <div className="rounded-md bg-muted p-4">
          <p className="text-sm font-medium">Enterprise Plan</p>
          <p className="text-xs text-muted-foreground">All features enabled</p>
        </div>
      </div>
    </div>
  )
}
