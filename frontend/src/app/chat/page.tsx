/* eslint-disable */
"use client"

import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { useWorkspace } from "@/components/providers/workspace-provider"
import { conversations as convApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Plus, MessageSquare, Loader2 } from "lucide-react"

type Conversation = {
  id: string
  title: string
}

type Message = {
  id?: string
  role: "user" | "assistant"
  content: string
  citations?: any[]
}

export default function ChatPage() {
  const { activeWorkspace } = useWorkspace()
  const [conversations, setConversations] = React.useState<Conversation[]>([])
  const [activeConvId, setActiveConvId] = React.useState<string | null>(null)
  const [messages, setMessages] = React.useState<Message[]>([])
  const [inputValue, setInputValue] = React.useState("")
  const [isLoadingList, setIsLoadingList] = React.useState(true)
  const [isStreaming, setIsStreaming] = React.useState(false)

  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming])

  React.useEffect(() => {
    if (activeWorkspace) {
      loadConversations()
    }
  }, [activeWorkspace])

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
    setActiveConvId(id)
    setMessages([])
    try {
      const res: any = await convApi.getMessages(id)
      const items = res?.data?.items || res?.items || (Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : []))
      if (Array.isArray(items)) {
        setMessages(items.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
        })))
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
      if (newConv && newConv.id) {
        setConversations(prev => [newConv, ...prev.filter(c => c && c.id !== newConv.id)])
        setActiveConvId(newConv.id)
      }
      setMessages([])
    } catch (error) {
      console.error(error)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    let currentConvId = activeConvId
    if (!currentConvId) {
      if (!activeWorkspace) return
      try {
        const res: any = await convApi.create(activeWorkspace.id, { title: inputValue.slice(0, 30) + "..." })
        const newConv = res?.data || res
        if (newConv && newConv.id) {
          setConversations(prev => [newConv, ...prev.filter(c => c && c.id !== newConv.id)])
          currentConvId = newConv.id
          setActiveConvId(currentConvId)
        }
      } catch (err) {
        console.error("Failed to create conversation on send:", err)
      }
    }

    const userMsg = inputValue
    setInputValue("")
    setMessages(prev => [...prev, { role: "user", content: userMsg }])
    
    setIsStreaming(true)
    let aiContent = ""
    let aiCitations: any[] = []
    
    try {
      if (!currentConvId) throw new Error("Conversation ID is null");
      const response = await convApi.sendMessage(currentConvId, { content: userMsg })
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      setMessages(prev => [...prev, { role: "assistant", content: "" }])

      if (reader) {
        let buffer = ""
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ""

          for (const rawLine of lines) {
            const line = rawLine.trim()
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6).trim()
              if (dataStr === "[DONE]") break
              try {
                const data = JSON.parse(dataStr)
                if (data.delta) {
                  aiContent += data.delta
                }
                if (data.citations) {
                  aiCitations = data.citations
                }
                
                setMessages(prev => {
                  const newMsgs = [...prev]
                  newMsgs[newMsgs.length - 1] = {
                    role: "assistant",
                    content: aiContent,
                    citations: aiCitations.length ? aiCitations : undefined,
                  }
                  return newMsgs
                })
              } catch (e) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err)
      setMessages(prev => {
        const newMsgs = [...prev]
        if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === "assistant" && !newMsgs[newMsgs.length - 1].content) {
          newMsgs[newMsgs.length - 1] = {
            role: "assistant",
            content: "Sorry, I encountered an error while retrieving knowledge. Please try sending your question again."
          }
        }
        return newMsgs
      })
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="flex h-full overflow-hidden rounded-xl border bg-card">
        {/* Sidebar */}
        <div className="w-64 border-r flex flex-col bg-muted/20">
          <div className="p-4 border-b">
            <Button onClick={handleNewConversation} className="w-full" variant="outline">
              <Plus className="mr-2 h-4 w-4" />
              New Chat
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {isLoadingList ? (
              <div className="flex justify-center p-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : conversations.filter(c => Boolean(c && c.id)).map(c => (
              <button
                key={c.id}
                onClick={() => handleSelectConversation(c.id)}
                className={`w-full text-left px-3 py-2 text-sm rounded-lg flex items-center space-x-2 transition-colors ${activeConvId === c.id ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'}`}
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <span className="truncate">{c.title || "Untitled Conversation"}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col h-full bg-background relative">
          {!activeConvId && messages.length === 0 ? (
             <div className="flex-1 flex items-center justify-center text-muted-foreground">
               <p>Select a conversation or start a new chat.</p>
             </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((msg, i) => (
                <div key={i} className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}>
                  <div className={`px-4 py-3 rounded-2xl ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content || (isStreaming && i === messages.length -1 ? "..." : "")}</p>
                    
                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-border/50">
                        <p className="text-xs font-semibold mb-2 opacity-80">Sources</p>
                        <div className="flex flex-wrap gap-2">
                          {msg.citations.map((cite, idx) => {
                            const name = cite.source?.source_filename || cite.filename || "Resume Document";
                            const page = cite.source?.page_number || cite.page_number || 1;
                            const marker = cite.citation_id || `[${idx + 1}]`;
                            return (
                              <div key={idx} className="bg-background/80 border rounded-lg px-2.5 py-1.5 flex flex-col text-xs max-w-[220px] shadow-sm">
                                <span className="font-semibold truncate text-primary" title={name}>{marker} {name}</span>
                                <span className="text-muted-foreground text-[10px]">Page {page}</span>
                              </div>
                            );
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
              <Button type="submit" disabled={!inputValue.trim() || isStreaming || !activeWorkspace}>
                <Send className="h-4 w-4" />
                <span className="sr-only">Send message</span>
              </Button>
            </form>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

