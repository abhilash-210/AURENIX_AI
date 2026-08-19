/* eslint-disable */
"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { useWorkspace } from "@/components/providers/workspace-provider"
import { documents as documentsApi } from "@/lib/api"
import { UploadCloud, FileText, Loader2, AlertCircle } from "lucide-react"

type Document = {
  id: string
  filename: string
  file_type: string
  status: string
  created_at: string
}

export default function DocumentsPage() {
  const { activeWorkspace } = useWorkspace()
  const [documents, setDocuments] = React.useState<Document[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [isUploading, setIsUploading] = React.useState(false)
  const [error, setError] = React.useState("")
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const fetchDocuments = React.useCallback(async () => {
    if (!activeWorkspace) return
    try {
      setError("")
      const res = await documentsApi.list(activeWorkspace.id)
      setDocuments(res.data)
    } catch (err: any) {
      console.error(err)
      setError("Failed to load documents.")
    } finally {
      setIsLoading(false)
    }
  }, [activeWorkspace])

  React.useEffect(() => {
    if (activeWorkspace) {
      fetchDocuments()
      const interval = setInterval(fetchDocuments, 5000)
      return () => clearInterval(interval)
    }
  }, [activeWorkspace, fetchDocuments])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !activeWorkspace) return

    const formData = new FormData()
    formData.append("file", file)

    setIsUploading(true)
    setError("")
    try {
      await documentsApi.upload(activeWorkspace.id, formData)
      await fetchDocuments()
    } catch (err: any) {
      console.error(err)
      setError("Failed to upload document.")
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
            <p className="text-muted-foreground">Manage your documents and data sources.</p>
          </div>
          <div>
            <input 
              type="file" 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              accept=".pdf,.txt,.csv,.docx" 
            />
            <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading || !activeWorkspace}>
              {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UploadCloud className="mr-2 h-4 w-4" />}
              Upload Document
            </Button>
          </div>
        </div>

        {error && (
          <div className="flex items-center space-x-2 rounded border border-destructive/50 bg-destructive/10 p-4 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : documents.length === 0 ? (
          <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground">
            No documents found. Upload a document to get started.
          </div>
        ) : (
          <div className="rounded-xl border bg-card">
            <div className="divide-y">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center space-x-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      doc.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                      doc.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                      'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                    }`}>
                      {doc.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

