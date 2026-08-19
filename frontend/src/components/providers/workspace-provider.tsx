"use client"

import React, { createContext, useContext, useEffect, useState } from "react"
import { workspaces as workspacesApi } from "@/lib/api"
import { useAuth } from "./auth-provider"

type Workspace = {
  id: string
  name: string
  slug: string
}

type WorkspaceContextType = {
  activeWorkspace: Workspace | null
  workspaces: Workspace[]
  isLoading: boolean
  setActiveWorkspace: (workspace: Workspace) => void
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined)

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    async function loadWorkspaces() {
      if (!user) {
        setWorkspaces([])
        setActiveWorkspace(null)
        return
      }

      try {
        setIsLoading(true)
        const res = await workspacesApi.list()
        setWorkspaces(res.data)
        if (res.data.length > 0) {
          // Default to the first workspace
          setActiveWorkspace(res.data[0])
        }
      } catch (error) {
        console.error("Failed to load workspaces:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadWorkspaces()
  }, [user])

  return (
    <WorkspaceContext.Provider value={{ activeWorkspace, workspaces, isLoading, setActiveWorkspace }}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (context === undefined) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider")
  }
  return context
}
