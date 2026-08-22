/* eslint-disable */
"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useWorkspace } from "@/components/providers/workspace-provider"
import { conversations as convApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Send,
  Plus,
  MessageSquare,
  Loader2,
  MoreVertical,
  Pencil,
  Trash2,
  X,
  CheckSquare,
  Square,
  AlertTriangle,
} from "lucide-react"

type Conversation = {
  id: string
  title: string
  updated_at?: string
}

type Message = {
  id?: string
  role: "user" | "assistant"
  content: string
  citations?: any[]
}

// ── Utility: format relative time ──────────────────────────────────────────
function relativeTime(dateStr?: string) {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000)
  if (diffDays === 0) return "Today"
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString()
}

// ── Confirmation Dialog ─────────────────────────────────────────────────────
function ConfirmDialog({
  title,
  description,
  onConfirm,
  onCancel,
  loading,
}: {
  title: string
  description: string
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}) {
  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" onClick={onCancel} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-xl border bg-card shadow-2xl">
          <div className="p-5 space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-sm">{title}</p>
                <p className="text-xs text-muted-foreground mt-1">{description}</p>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={onCancel} className="flex-1">Cancel</Button>
              <Button variant="destructive" size="sm" onClick={onConfirm} disabled={loading} className="flex-1">
                {loading && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                Delete
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// ── Rename Input ────────────────────────────────────────────────────────────
function RenameInput({
  initial,
  onSave,
  onCancel,
}: {
  initial: string
  onSave: (title: string) => void
  onCancel: () => void
}) {
  const [value, setValue] = React.useState(initial)
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); if (value.trim()) onSave(value.trim()) }}
      className="flex items-center gap-1 flex-1 min-w-0"
    >
      <Input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-6 text-xs px-2 flex-1"
        maxLength={80}
      />
      <button type="submit" className="text-primary hover:text-primary/80 p-0.5"><Pencil className="h-3 w-3" /></button>
      <button type="button" onClick={onCancel} className="text-muted-foreground hover:text-foreground p-0.5"><X className="h-3 w-3" /></button>
    </form>
  )
}

// ── Main Chat Page ──────────────────────────────────────────────────────────
export default function ChatPage() {
  const { activeWorkspace } = useWorkspace()
  const [conversations, setConversations] = React.useState<Conversation[]>([])
  const [activeConvId, setActiveConvId] = React.useState<string | null>(null)
  const [messages, setMessages] = React.useState<Message[]>([])
  const [inputValue, setInputValue] = React.useState("")
  const [isLoadingList, setIsLoadingList] = React.useState(true)
  const [isStreaming, setIsStreaming] = React.useState(false)

  // Conversation management state
  const [menuOpenId, setMenuOpenId] = React.useState<string | null>(null)
  const [renamingId, setRenamingId] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = React.useState(false)

  // Multi-select state
  const [selectMode, setSelectMode] = React.useState(false)
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = React.useState(false)
  const [bulkDeleteLoading, setBulkDeleteLoading] = React.useState(false)

  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })

  React.useEffect(() => { scrollToBottom() }, [messages, isStreaming])

  // Reload conversations when workspace changes
  React.useEffect(() => {
    if (activeWorkspace) {
      setActiveConvId(null)
      setMessages([])
      setSelectedIds(new Set())
      setSelectMode(false)
      loadConversations()
    }
  }, [activeWorkspace?.id])

  const loadConversations = async () => {
    if (!activeWorkspace) return
    try {
      setIsLoadingList(true)
      const res: any = await convApi.list(activeWorkspace.id)
      const items = res?.data?.items || res?.items || (Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : []))
      setConversations(Array.isArray(items) ? items : [])
    } catch (error) {
      console.error(error)
    } finally {
      setIsLoadingList(false)
    }
  }

  const handleSelectConversation = async (id: string) => {
    if (selectMode) {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.has(id) ? next.delete(id) : next.add(id)
        return next
      })
      return
    }
    setActiveConvId(id)
    setMessages([])
    try {
      const res: any = await convApi.getMessages(id)
      const items = res?.data?.items || res?.items || (Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : []))
      if (Array.isArray(items)) {
        setMessages(items.map((m: any) => ({ id: m.id, role: m.role, content: m.content, citations: m.citations })))
      }
    } catch (error) {
      console.error(error)
    }
  }

  const handleNewConversation = async () => {
    if (!activeWorkspace) return
    try {
      const res: any = await convApi.create(activeWorkspace.id, { title: "New Conversation" })
      const newConv = res?.data || res
      if (newConv?.id) {
        setConversations((prev) => [newConv, ...prev.filter((c) => c?.id !== newConv.id)])
        setActiveConvId(newConv.id)
        setMessages([])
      }
    } catch (error) {
      console.error(error)
    }
  }

  // ── Rename conversation ───────────────────────────────────────────────────
  const handleRename = async (id: string, newTitle: string) => {
    try {
      const res: any = await convApi.rename(id, newTitle)
      const updated = res?.data || res
      setConversations((prev) => prev.map((c) => c.id === id ? { ...c, title: updated?.title || newTitle } : c))
    } catch (err) {
      console.error(err)
    } finally {
      setRenamingId(null)
    }
  }

  // ── Delete single conversation ────────────────────────────────────────────
  const handleDelete = async (id: string) => {
    try {
      setDeleteLoading(true)
      await convApi.delete(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConvId === id) { setActiveConvId(null); setMessages([]) }
    } catch (err) {
      console.error(err)
    } finally {
      setDeleteLoading(false)
      setDeletingId(null)
    }
  }

  // ── Bulk delete ───────────────────────────────────────────────────────────
  const handleBulkDelete = async () => {
    try {
      setBulkDeleteLoading(true)
      await Promise.all(Array.from(selectedIds).map((id) => convApi.delete(id)))
      setConversations((prev) => prev.filter((c) => !selectedIds.has(c.id)))
      if (selectedIds.has(activeConvId ?? "")) { setActiveConvId(null); setMessages([]) }
      setSelectedIds(new Set())
      setSelectMode(false)
    } catch (err) {
      console.error(err)
    } finally {
      setBulkDeleteLoading(false)
      setBulkDeleteConfirm(false)
    }
  }

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    let currentConvId = activeConvId
    if (!currentConvId) {
      if (!activeWorkspace) return
      try {
        const res: any = await convApi.create(activeWorkspace.id, { title: inputValue.slice(0, 40) })
        const newConv = res?.data || res
        if (newConv?.id) {
          setConversations((prev) => [newConv, ...prev.filter((c) => c?.id !== newConv.id)])
          currentConvId = newConv.id
          setActiveConvId(currentConvId)
        }
      } catch (err) {
        console.error("Failed to create conversation:", err)
        return
      }
    }

    const userMsg = inputValue
    setInputValue("")
    setMessages((prev) => [...prev, { role: "user", content: userMsg }])
    setIsStreaming(true)
    let aiContent = ""
    let aiCitations: any[] = []

    try {
      if (!currentConvId) throw new Error("No conversation ID")
      const response = await convApi.sendMessage(currentConvId, { content: userMsg })
      const reader = (response as any).body?.getReader()
      const decoder = new TextDecoder()

      setMessages((prev) => [...prev, { role: "assistant", content: "" }])

      if (reader) {
        let buffer = ""
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() || ""
          for (const rawLine of lines) {
            const line = rawLine.trim()
            if (!line.startsWith("data: ")) continue
            const dataStr = line.slice(6).trim()
            if (dataStr === "[DONE]") break
            try {
              const data = JSON.parse(dataStr)
              if (data.delta) aiContent += data.delta
              if (data.citations?.length) aiCitations = data.citations
              if (data.error) aiContent = data.error
              setMessages((prev) => {
                const msgs = [...prev]
                msgs[msgs.length - 1] = { role: "assistant", content: aiContent, citations: aiCitations.length ? aiCitations : undefined }
                return msgs
              })
            } catch { /* ignore partial json */ }
          }
        }
      }
    } catch (err: any) {
      console.error(err)
      setMessages((prev) => {
        const msgs = [...prev]
        if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant" && !msgs[msgs.length - 1].content) {
          msgs[msgs.length - 1] = { role: "assistant", content: "Sorry, something went wrong. Please try again." }
        }
        return msgs
      })
    } finally {
      setIsStreaming(false)
    }
  }

  // ── Group conversations by date ───────────────────────────────────────────
  const grouped = React.useMemo(() => {
    const groups: Record<string, Conversation[]> = {}
    conversations.filter((c) => c?.id).forEach((c) => {
      const label = relativeTime(c.updated_at) || "Older"
      ;(groups[label] = groups[label] || []).push(c)
    })
    return groups
  }, [conversations])

  const groupOrder = ["Today", "Yesterday", ...Object.keys(grouped).filter((k) => !["Today", "Yesterday"].includes(k))]

  return (
    <DashboardLayout>
      <div className="flex h-full overflow-hidden rounded-xl border bg-card">

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <div className="w-64 border-r flex flex-col bg-muted/20 shrink-0">
          {/* Top actions */}
          <div className="p-3 border-b space-y-2">
            <Button onClick={handleNewConversation} className="w-full" variant="outline" size="sm">
              <Plus className="mr-2 h-3.5 w-3.5" /> New Chat
            </Button>
            {conversations.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-muted-foreground"
                onClick={() => { setSelectMode((s) => !s); setSelectedIds(new Set()) }}
              >
                {selectMode ? <><X className="mr-2 h-3.5 w-3.5" /> Cancel</> : <><CheckSquare className="mr-2 h-3.5 w-3.5" /> Select</>}
              </Button>
            )}
            {selectMode && selectedIds.size > 0 && (
              <Button
                variant="destructive"
                size="sm"
                className="w-full"
                onClick={() => setBulkDeleteConfirm(true)}
              >
                <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete {selectedIds.size} selected
              </Button>
            )}
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto py-2">
            {isLoadingList ? (
              <div className="flex justify-center p-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : conversations.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center pt-6 px-4">No conversations yet. Start a new chat!</p>
            ) : (
              groupOrder.filter((g) => grouped[g]).map((groupLabel) => (
                <div key={groupLabel}>
                  <p className="text-[10px] font-semibold uppercase text-muted-foreground px-3 pt-3 pb-1 tracking-wider">{groupLabel}</p>
                  {grouped[groupLabel].map((c) => (
                    <div
                      key={c.id}
                      className={`group relative flex items-center px-3 py-2 mx-1 rounded-lg cursor-pointer transition-colors ${
                        activeConvId === c.id
                          ? "bg-primary/10 text-primary"
                          : selectedIds.has(c.id)
                          ? "bg-primary/5 text-foreground"
                          : "hover:bg-muted text-muted-foreground"
                      }`}
                      onClick={() => handleSelectConversation(c.id)}
                    >
                      {/* Select checkbox */}
                      {selectMode && (
                        <span className="mr-2 shrink-0">
                          {selectedIds.has(c.id)
                            ? <CheckSquare className="h-4 w-4 text-primary" />
                            : <Square className="h-4 w-4 text-muted-foreground" />}
                        </span>
                      )}

                      {!selectMode && <MessageSquare className="h-3.5 w-3.5 mr-2 shrink-0" />}

                      {/* Title or rename input */}
                      {renamingId === c.id ? (
                        <RenameInput
                          initial={c.title}
                          onSave={(t) => handleRename(c.id, t)}
                          onCancel={() => setRenamingId(null)}
                        />
                      ) : (
                        <span className="truncate text-sm flex-1">{c.title || "Untitled"}</span>
                      )}

                      {/* ⋮ Menu button */}
                      {!selectMode && renamingId !== c.id && (
                        <button
                          className="ml-1 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground transition-all shrink-0"
                          onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === c.id ? null : c.id) }}
                        >
                          <MoreVertical className="h-3.5 w-3.5" />
                        </button>
                      )}

                      {/* Dropdown menu */}
                      {menuOpenId === c.id && (
                        <div
                          className="absolute right-2 top-full mt-1 z-20 w-36 rounded-lg border bg-card shadow-lg overflow-hidden"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                            onClick={() => { setRenamingId(c.id); setMenuOpenId(null) }}
                          >
                            <Pencil className="h-3.5 w-3.5" /> Rename
                          </button>
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                            onClick={() => { setDeletingId(c.id); setMenuOpenId(null) }}
                          >
                            <Trash2 className="h-3.5 w-3.5" /> Delete
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Chat Area ───────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col h-full bg-background relative">
          {!activeConvId && messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <MessageSquare className="h-10 w-10 opacity-20" />
              <p className="text-sm">Select a conversation or start a new chat.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex flex-col max-w-[85%] ${msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"}`}
                >
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed text-sm">
                      {msg.content || (isStreaming && i === messages.length - 1 ? "▋" : "")}
                    </p>

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-border/50">
                        <p className="text-xs font-semibold mb-2 opacity-70">Sources</p>
                        <div className="flex flex-wrap gap-2">
                          {msg.citations.map((cite, idx) => {
                            const name = cite.source?.source_filename || cite.filename || "Document"
                            const page = cite.source?.page_number || cite.page_number || 1
                            const marker = cite.citation_id || `[${idx + 1}]`
                            return (
                              <div
                                key={idx}
                                className="bg-background/80 border rounded-lg px-2.5 py-1.5 flex flex-col text-xs max-w-[220px] shadow-sm"
                              >
                                <span className="font-semibold truncate text-primary" title={name}>{marker} {name}</span>
                                <span className="text-muted-foreground text-[10px]">Page {page}</span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Input Area */}
          <div className="p-4 border-t bg-card mt-auto">
            <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Message Aurenix AI..."
                className="flex-1"
                disabled={isStreaming}
              />
              <Button type="submit" disabled={!inputValue.trim() || isStreaming || !activeWorkspace} size="icon">
                {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* ── Single delete confirm ─────────────────────────────────────────── */}
      {deletingId && (
        <ConfirmDialog
          title="Delete this conversation?"
          description="This will permanently remove the conversation and all its messages. This cannot be undone."
          onConfirm={() => handleDelete(deletingId)}
          onCancel={() => setDeletingId(null)}
          loading={deleteLoading}
        />
      )}

      {/* ── Bulk delete confirm ───────────────────────────────────────────── */}
      {bulkDeleteConfirm && (
        <ConfirmDialog
          title={`Delete ${selectedIds.size} conversation${selectedIds.size > 1 ? "s" : ""}?`}
          description="All selected conversations and their messages will be permanently deleted."
          onConfirm={handleBulkDelete}
          onCancel={() => setBulkDeleteConfirm(false)}
          loading={bulkDeleteLoading}
        />
      )}

      {/* Close menus on outside click */}
      {menuOpenId && (
        <div className="fixed inset-0 z-10" onClick={() => setMenuOpenId(null)} />
      )}
    </DashboardLayout>
  )
}
