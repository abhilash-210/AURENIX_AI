/* eslint-disable */
"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useWorkspace } from "@/components/providers/workspace-provider"
import { workspaces as workspacesApi, apiKeys, audit } from "@/lib/api"

export default function SettingsPage() {
  const { activeWorkspace } = useWorkspace()
  const [activeTab, setActiveTab] = useState("general")

  const tabs = [
    { id: "general", label: "General" },
    { id: "members", label: "Members" },
    { id: "apikeys", label: "API Keys" },
    { id: "audit", label: "Audit Logs" },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Manage your workspace settings and preferences.</p>
        </div>
        
        <div className="flex border-b">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id 
                  ? "border-primary text-foreground" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="pt-4">
          {activeTab === "general" && <GeneralTab workspaceId={activeWorkspace?.id} />}
          {activeTab === "members" && <MembersTab workspaceId={activeWorkspace?.id} />}
          {activeTab === "apikeys" && <ApiKeysTab workspaceId={activeWorkspace?.id} />}
          {activeTab === "audit" && <AuditTab workspaceId={activeWorkspace?.id} />}
        </div>
      </div>
    </DashboardLayout>
  )
}

function GeneralTab({ workspaceId }: { workspaceId?: string }) {
  if (!workspaceId) return null
  return (
    <div className="max-w-2xl space-y-6">
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold">Workspace Settings</h3>
        <p className="text-sm text-muted-foreground mb-4">Usage limits are enforced based on these settings.</p>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Max Documents</label>
            <div className="mt-1 h-10 w-full rounded-md border bg-muted/50 px-3 py-2 text-sm text-muted-foreground flex items-center">
              100 (Default)
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">Max Messages</label>
            <div className="mt-1 h-10 w-full rounded-md border bg-muted/50 px-3 py-2 text-sm text-muted-foreground flex items-center">
              1000 (Default)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function MembersTab({ workspaceId }: { workspaceId?: string }) {
  const [members, setMembers] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId) return
    workspacesApi.getMembers(workspaceId)
      .then(res => setMembers(res.data))
      .catch(err => setError(err.response?.status === 403 ? "You do not have permission to view members." : "Failed to load members"))
  }, [workspaceId])

  if (error) return <div className="text-red-500 bg-red-500/10 p-4 rounded-md">{error}</div>

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <table className="w-full text-sm text-left">
        <thead className="bg-muted/50 text-muted-foreground text-xs uppercase font-medium">
          <tr>
            <th className="px-6 py-3">Name</th>
            <th className="px-6 py-3">Email</th>
            <th className="px-6 py-3">Role</th>
            <th className="px-6 py-3">Joined</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {members.map((m) => (
            <tr key={m.user_id}>
              <td className="px-6 py-4 font-medium">{m.full_name}</td>
              <td className="px-6 py-4 text-muted-foreground">{m.email}</td>
              <td className="px-6 py-4 capitalize">{m.role}</td>
              <td className="px-6 py-4 text-muted-foreground">{new Date(m.joined_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ApiKeysTab({ workspaceId }: { workspaceId?: string }) {
  const [keys, setKeys] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [newKey, setNewKey] = useState<string | null>(null)

  const loadKeys = () => {
    if (!workspaceId) return
    apiKeys.list(workspaceId)
      .then(res => setKeys(res.data))
      .catch(err => setError(err.response?.status === 403 ? "You do not have permission to manage API keys." : "Failed to load API keys"))
  }

  useEffect(() => {
    loadKeys()
  }, [workspaceId])

  const createKey = async () => {
    if (!workspaceId) return
    try {
      const res = await apiKeys.create(workspaceId, { name: "New API Key" })
      setNewKey(res.data.raw_key)
      loadKeys()
    } catch (e) {
      console.error(e)
    }
  }

  const revokeKey = async (id: string) => {
    if (!workspaceId) return
    try {
      await apiKeys.revoke(workspaceId, id)
      loadKeys()
    } catch (e) {
      console.error(e)
    }
  }

  if (error) return <div className="text-red-500 bg-red-500/10 p-4 rounded-md">{error}</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">Manage programmatic access to this workspace.</p>
        <button onClick={createKey} className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium">
          Generate New Key
        </button>
      </div>

      {newKey && (
        <div className="bg-green-500/10 border border-green-500/20 p-4 rounded-md">
          <p className="text-green-600 font-medium mb-2">Save this key, it will not be shown again!</p>
          <code className="bg-background px-3 py-2 rounded-md text-sm select-all">{newKey}</code>
        </div>
      )}

      <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 text-muted-foreground text-xs uppercase font-medium">
            <tr>
              <th className="px-6 py-3">Name</th>
              <th className="px-6 py-3">Key</th>
              <th className="px-6 py-3">Created</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {keys.map((k) => (
              <tr key={k.id}>
                <td className="px-6 py-4 font-medium">{k.name}</td>
                <td className="px-6 py-4 font-mono text-muted-foreground">{k.prefix}</td>
                <td className="px-6 py-4 text-muted-foreground">{new Date(k.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => revokeKey(k.id)} className="text-red-500 hover:text-red-600 font-medium">Revoke</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AuditTab({ workspaceId }: { workspaceId?: string }) {
  const [logs, setLogs] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId) return
    audit.list(workspaceId)
      .then(res => setLogs(res.data))
      .catch(err => setError(err.response?.status === 403 ? "You do not have permission to view audit logs." : "Failed to load audit logs"))
  }, [workspaceId])

  if (error) return <div className="text-red-500 bg-red-500/10 p-4 rounded-md">{error}</div>

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <table className="w-full text-sm text-left">
        <thead className="bg-muted/50 text-muted-foreground text-xs uppercase font-medium">
          <tr>
            <th className="px-6 py-3">Timestamp</th>
            <th className="px-6 py-3">Action</th>
            <th className="px-6 py-3">Resource</th>
            <th className="px-6 py-3">Details</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {logs.map((log) => (
            <tr key={log.id}>
              <td className="px-6 py-4 whitespace-nowrap text-muted-foreground">{new Date(log.created_at).toLocaleString()}</td>
              <td className="px-6 py-4 font-medium">{log.action}</td>
              <td className="px-6 py-4 text-muted-foreground">{log.resource_type || "-"}</td>
              <td className="px-6 py-4 text-muted-foreground font-mono text-xs">{JSON.stringify(log.details)}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">No audit logs found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
