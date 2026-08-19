/* eslint-disable */
"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Moon, Sun, UserCircle, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/components/providers/auth-provider"

export function Header() {
  const { setTheme, theme } = useTheme()
  const { user, logout } = useAuth()

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center">
        {/* Mobile menu toggle could go here */}
        <h2 className="text-lg font-semibold md:hidden">Aurenix AI</h2>
      </div>
      <div className="flex items-center space-x-4">
        {user && (
          <span className="text-sm font-medium hidden md:inline-block">
            {user.full_name || user.email}
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
        <Button variant="ghost" size="icon" onClick={logout} title="Log out">
          <LogOut className="h-5 w-5" />
          <span className="sr-only">Log out</span>
        </Button>
      </div>
    </header>
  )
}

