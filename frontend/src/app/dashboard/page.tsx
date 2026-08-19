"use client"
/* eslint-disable */
import * as React from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useWorkspace } from "@/components/providers/workspace-provider"
import { analytics as analyticsApi, system as systemApi } from "@/lib/api"
import { Activity, Database, MessageSquare, Files, AlertCircle, Loader2, Server, Clock, Search, Bot } from "lucide-react"

export default function DashboardPage() {
  const { activeWorkspace } = useWorkspace()
  const [metrics, setMetrics] = React.useState<any>(null)
  const [activity, setActivity] = React.useState<any>(null)
  const [systemHealth, setSystemHealth] = React.useState<any>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState("")

  React.useEffect(() => {
    if (activeWorkspace) {
      loadDashboardData()
    }
  }, [activeWorkspace])

  const loadDashboardData = async () => {
    if (!activeWorkspace) return
    setIsLoading(true)
    setError("")
    try {
      const [overviewRes, activityRes, healthRes] = await Promise.all([
        analyticsApi.overview(activeWorkspace.id),
        analyticsApi.activity(activeWorkspace.id),
        systemApi.health().catch(() => ({ status: "down" }))
      ])
      
      setMetrics(overviewRes.data)
      setActivity(activityRes.data)
      setSystemHealth(healthRes)
    } catch (err) {
      console.error(err)
      setError("Failed to load analytics data. Please try again later.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
          <p className="text-muted-foreground">Monitor system usage and intelligence operations.</p>
        </div>

        {error && (
          <div className="flex items-center space-x-2 rounded border border-destructive/50 bg-destructive/10 p-4 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="flex h-64 items-center justify-center rounded-xl border bg-card">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Primary Metrics */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                  <Files className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.documents || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">Indexed in workspace</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Conversations</CardTitle>
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.conversations || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">Active chat sessions</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">AI Requests</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.ai_requests || 0}</div>
                  <p className="text-xs text-muted-foreground mt-1">Total assistant responses</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">System Health</CardTitle>
                  <Server className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center space-x-2">
                    <div className={`h-2.5 w-2.5 rounded-full ${systemHealth?.status === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <div className="text-2xl font-bold capitalize">{systemHealth?.status || 'Unknown'}</div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Backend API Status</p>
                </CardContent>
              </Card>
            </div>

            {/* Unavailable / Coming Soon Metrics */}
            <div>
              <h3 className="mb-4 text-lg font-medium tracking-tight">Advanced Metrics <span className="ml-2 text-xs font-normal text-muted-foreground rounded-full bg-muted px-2 py-0.5">Coming Soon</span></h3>
              <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5 opacity-60 pointer-events-none">
                <Card className="bg-muted/30">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">Token Usage</CardTitle>
                    <Database className="h-3 w-3 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold text-muted-foreground">--</div>
                  </CardContent>
                </Card>
                <Card className="bg-muted/30">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">Response Latency</CardTitle>
                    <Clock className="h-3 w-3 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold text-muted-foreground">-- ms</div>
                  </CardContent>
                </Card>
                <Card className="bg-muted/30">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">Retrieval Ops</CardTitle>
                    <Search className="h-3 w-3 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold text-muted-foreground">--</div>
                  </CardContent>
                </Card>
                <Card className="bg-muted/30">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">Agent Executions</CardTitle>
                    <Bot className="h-3 w-3 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold text-muted-foreground">--</div>
                  </CardContent>
                </Card>
                <Card className="bg-muted/30">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">Error Rate</CardTitle>
                    <AlertCircle className="h-3 w-3 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold text-muted-foreground">-- %</div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Activity Feeds */}
            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Documents</CardTitle>
                  <CardDescription>Latest files ingested into your knowledge base.</CardDescription>
                </CardHeader>
                <CardContent>
                  {!activity?.recent_documents?.length ? (
                    <p className="text-sm text-muted-foreground">No recent documents.</p>
                  ) : (
                    <div className="space-y-4">
                      {activity.recent_documents.map((doc: any) => (
                        <div key={doc.id} className="flex items-center space-x-4">
                          <div className="rounded-md bg-primary/10 p-2">
                            <Files className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1 space-y-1">
                            <p className="text-sm font-medium leading-none">{doc.filename}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(doc.created_at).toLocaleString()}
                            </p>
                          </div>
                          <div className="text-xs font-medium text-muted-foreground capitalize">
                            {doc.status}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Recent Conversations</CardTitle>
                  <CardDescription>Latest chat sessions with Aurenix AI.</CardDescription>
                </CardHeader>
                <CardContent>
                  {!activity?.recent_conversations?.length ? (
                    <p className="text-sm text-muted-foreground">No recent conversations.</p>
                  ) : (
                    <div className="space-y-4">
                      {activity.recent_conversations.map((conv: any) => (
                        <div key={conv.id} className="flex items-center space-x-4">
                          <div className="rounded-md bg-primary/10 p-2">
                            <MessageSquare className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1 space-y-1">
                            <p className="text-sm font-medium leading-none truncate max-w-[200px]">{conv.title}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(conv.updated_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
