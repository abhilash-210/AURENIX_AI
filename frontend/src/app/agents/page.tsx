import { DashboardLayout } from "@/components/layout/dashboard-layout"

export default function AgentsPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">Configure and deploy intelligent agents.</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border bg-card p-6 shadow-sm">
            <h3 className="font-semibold">Research Agent</h3>
            <p className="mt-2 text-sm text-muted-foreground">Analyses uploaded documents and summarizes findings.</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
