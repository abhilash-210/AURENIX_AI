/* eslint-disable */
"use client"

import * as React from "react"
import { useWorkspace, Workspace } from "@/components/providers/workspace-provider"
import {
  ChevronDown,
  Plus,
  Check,
  Building2,
  Pencil,
  Trash2,
  X,
  Loader2,
  AlertTriangle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// ── Small modal primitives ──────────────────────────────────────────────────

function Overlay({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    />
  )
}

function Modal({ children, title, onClose }: { children: React.ReactNode; title: string; onClose: () => void }) {
  return (
    <>
      <Overlay onClose={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-xl border bg-card shadow-2xl">
          <div className="flex items-center justify-between border-b px-5 py-4">
            <h3 className="text-base font-semibold">{title}</h3>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </div>
      </div>
    </>
  )
}

// ── Create workspace modal ──────────────────────────────────────────────────

function CreateWorkspaceModal({ onClose }: { onClose: () => void }) {
  const { createWorkspace } = useWorkspace()
  const [name, setName] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    try {
      setLoading(true)
      setError("")
      await createWorkspace(name.trim(), description.trim() || undefined)
      onClose()
    } catch (err: any) {
      setError(err?.message || "Failed to create workspace.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="Create Workspace" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground mb-1 block">Name</label>
          <Input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Company HR, College Project..."
            maxLength={80}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground mb-1 block">Description <span className="text-muted-foreground font-normal">(optional)</span></label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this workspace for?"
            maxLength={200}
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
          <Button type="submit" disabled={!name.trim() || loading} className="flex-1">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Create Workspace
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ── Rename workspace modal ──────────────────────────────────────────────────

function RenameWorkspaceModal({ workspace, onClose }: { workspace: Workspace; onClose: () => void }) {
  const { renameWorkspace } = useWorkspace()
  const [name, setName] = React.useState(workspace.name)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || name.trim() === workspace.name) { onClose(); return }
    try {
      setLoading(true)
      await renameWorkspace(workspace.id, name.trim())
      onClose()
    } catch (err: any) {
      setError(err?.message || "Failed to rename workspace.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="Rename Workspace" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
          <Button type="submit" disabled={!name.trim() || loading} className="flex-1">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Save
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ── Delete workspace confirmation modal ────────────────────────────────────

function DeleteWorkspaceModal({ workspace, onClose }: { workspace: Workspace; onClose: () => void }) {
  const { deleteWorkspace } = useWorkspace()
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const handleDelete = async () => {
    try {
      setLoading(true)
      await deleteWorkspace(workspace.id)
      onClose()
    } catch (err: any) {
      setError(err?.message || "Failed to delete workspace.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title={`Delete "${workspace.name}"?`} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-lg bg-destructive/10 border border-destructive/20 p-4">
          <AlertTriangle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          <div className="text-sm text-destructive">
            <p className="font-semibold mb-1">This action is permanent.</p>
            <p>All documents, conversations, messages, AI memories, and vector embeddings in this workspace will be <strong>permanently deleted</strong>.</p>
          </div>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={loading}
            className="flex-1"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
            Delete Workspace
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Main WorkspaceSwitcher ──────────────────────────────────────────────────

export function WorkspaceSwitcher() {
  const { activeWorkspace, workspaces } = useWorkspace()
  const [open, setOpen] = React.useState(false)
  const [showCreate, setShowCreate] = React.useState(false)
  const [renaming, setRenaming] = React.useState<Workspace | null>(null)
  const [deleting, setDeleting] = React.useState<Workspace | null>(null)
  const { setActiveWorkspace } = useWorkspace()
  const ref = React.useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [open])

  const handleSelect = (w: Workspace) => {
    setActiveWorkspace(w)
    setOpen(false)
  }

  return (
    <>
      <div className="relative" ref={ref}>
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border bg-muted/40 hover:bg-muted transition-colors text-left"
        >
          <Building2 className="h-4 w-4 text-primary shrink-0" />
          <span className="flex-1 text-sm font-semibold truncate text-foreground">
            {activeWorkspace?.name ?? "Select workspace"}
          </span>
          <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="absolute left-0 right-0 top-full mt-1 z-30 rounded-xl border bg-card shadow-xl overflow-hidden">
            {/* Workspace list */}
            <div className="max-h-52 overflow-y-auto">
              {workspaces.map((w) => (
                <div
                  key={w.id}
                  className={`flex items-center gap-2 px-3 py-2.5 text-sm group ${
                    activeWorkspace?.id === w.id
                      ? "bg-primary/10 text-primary"
                      : "hover:bg-muted text-foreground"
                  }`}
                >
                  <button
                    className="flex-1 flex items-center gap-2 min-w-0 text-left"
                    onClick={() => handleSelect(w)}
                  >
                    {activeWorkspace?.id === w.id && <Check className="h-3.5 w-3.5 shrink-0" />}
                    {activeWorkspace?.id !== w.id && <span className="h-3.5 w-3.5 shrink-0" />}
                    <span className="truncate font-medium">{w.name}</span>
                  </button>
                  {/* Per-workspace actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); setOpen(false); setRenaming(w) }}
                      className="p-1 rounded hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground"
                      title="Rename"
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setOpen(false); setDeleting(w) }}
                      className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Divider */}
            <div className="border-t" />

            {/* Create new */}
            <button
              onClick={() => { setOpen(false); setShowCreate(true) }}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-primary hover:bg-primary/5 transition-colors font-medium"
            >
              <Plus className="h-4 w-4" />
              New Workspace
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && <CreateWorkspaceModal onClose={() => setShowCreate(false)} />}
      {renaming && <RenameWorkspaceModal workspace={renaming} onClose={() => setRenaming(null)} />}
      {deleting && <DeleteWorkspaceModal workspace={deleting} onClose={() => setDeleting(null)} />}
    </>
  )
}
