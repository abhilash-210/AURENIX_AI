/* eslint-disable */
"use client"

import React, { createContext, useContext, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { auth as authApi } from "@/lib/api"

type User = {
  id: string
  email: string
  full_name: string | null
  role: string
}

type AuthContextType = {
  user: User | null
  isLoading: boolean
  login: (token: string, user: User) => void
  logout: () => void
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const login = (token: string, userData: User) => {
    localStorage.setItem("access_token", token)
    setUser(userData)
    router.push("/dashboard")
  }

  const logout = () => {
    localStorage.removeItem("access_token")
    setUser(null)
    router.push("/login")
  }

  const checkAuth = async () => {
    try {
      setIsLoading(true)
      const token = localStorage.getItem("access_token")
      if (!token) {
        setUser(null)
        return
      }
      
      const res = await authApi.me()
      setUser(res.data)
    } catch (error) {
      console.error("Auth check failed:", error)
      localStorage.removeItem("access_token")
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    checkAuth()
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

