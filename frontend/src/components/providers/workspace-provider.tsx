"use client"

import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { workspaces as workspacesApi } from "@/lib/api"
import { useAuth } from "./auth-provider"

export type Workspace = {
  id: string
  name: string
  slug: string
  description?: string
}

type WorkspaceContextType = {
  activeWorkspace: Workspace | null
  workspaces: Workspace[]
  isLoading: boolean
  setActiveWorkspace: (workspace: Workspace) => void
  createWorkspace: (name: string, description?: string) => Promise<Workspace>
  renameWorkspace: (id: string, name: string) => Promise<void>
  deleteWorkspace: (id: string) => Promise<void>
  refreshWorkspaces: () => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined)

const ACTIVE_WORKSPACE_KEY = "aurenix_active_workspace_id"

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeWorkspace, setActiveWorkspaceState] = useState<Workspace | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadWorkspaces = useCallback(async () => {
    if (!user) {
      setWorkspaces([])
      setActiveWorkspaceState(null)
      return
    }
    try {
      setIsLoading(true)
      const res: any = await workspacesApi.list()
      const list: Workspace[] = res?.data ?? res ?? []
      setWorkspaces(list)

      // Restore persisted active workspace if still valid
      const savedId = typeof window !== "undefined" ? localStorage.getItem(ACTIVE_WORKSPACE_KEY) : null
      const saved = savedId ? list.find((w) => w.id === savedId) : null
      setActiveWorkspaceState(saved ?? list[0] ?? null)
    } catch (error) {
      console.error("Failed to load workspaces:", error)
    } finally {
      setIsLoading(false)
    }
  }, [user])

  useEffect(() => {
    loadWorkspaces()
  }, [loadWorkspaces])

  const setActiveWorkspace = useCallback((workspace: Workspace) => {
    setActiveWorkspaceState(workspace)
    if (typeof window !== "undefined") {
      localStorage.setItem(ACTIVE_WORKSPACE_KEY, workspace.id)
    }
  }, [])

  const createWorkspace = useCallback(async (name: string, description?: string): Promise<Workspace> => {
    const res: any = await workspacesApi.create({ name, description })
    const created: Workspace = res?.data ?? res
    setWorkspaces((prev) => [...prev, created])
    setActiveWorkspace(created)
    return created
  }, [setActiveWorkspace])

  const renameWorkspace = useCallback(async (id: string, name: string): Promise<void> => {
    const res: any = await workspacesApi.rename(id, { name })
    const updated: Workspace = res?.data ?? res
    setWorkspaces((prev) => prev.map((w) => (w.id === id ? { ...w, name: updated.name } : w)))
    setActiveWorkspaceState((prev) => (prev?.id === id ? { ...prev, name: updated.name } : prev))
  }, [])

  const deleteWorkspace = useCallback(async (id: string): Promise<void> => {
    await workspacesApi.delete(id)
    const remaining = workspaces.filter((w) => w.id !== id)
    setWorkspaces(remaining)
    if (activeWorkspace?.id === id) {
      const next = remaining[0] ?? null
      setActiveWorkspaceState(next)
      if (next && typeof window !== "undefined") {
        localStorage.setItem(ACTIVE_WORKSPACE_KEY, next.id)
      } else if (typeof window !== "undefined") {
        localStorage.removeItem(ACTIVE_WORKSPACE_KEY)
      }
    }
  }, [workspaces, activeWorkspace])

  const refreshWorkspaces = useCallback(loadWorkspaces, [loadWorkspaces])

  return (
    <WorkspaceContext.Provider
      value={{
        activeWorkspace,
        workspaces,
        isLoading,
        setActiveWorkspace,
        createWorkspace,
        renameWorkspace,
        deleteWorkspace,
        refreshWorkspaces,
      }}
    >
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
