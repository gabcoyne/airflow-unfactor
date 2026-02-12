import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">airflow-unfactor</div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link href="/docs">Docs</Link>
            <Link href="https://github.com/prefect/airflow-unfactor">GitHub</Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section className="grid gap-10 md:grid-cols-2">
          <div>
            <div className="mb-4 flex items-center gap-2">
              <Badge variant="outline">MCP</Badge>
              <Badge variant="secondary">Prefect-aligned</Badge>
            </div>
            <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
              Modernize Airflow DAGs with MCP-native conversions.
            </h1>
            <p className="mt-4 text-lg text-muted-foreground">
              airflow-unfactor converts Airflow DAGs to Prefect flows with rich analysis, clear
              warnings, and MCP-ready tooling. Built with shadcn/ui and FastMCP.
            </p>
            <div className="mt-6 flex gap-3">
              <Button asChild>
                <Link href="/docs">Read the docs</Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/docs/mcp">MCP guide</Link>
              </Button>
            </div>
          </div>

          <div className="grid gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Analysis</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Detect Airflow versions, identify TaskFlow, Datasets, Sensors, and operator usage.
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Conversion</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Generate Prefect flows with educational comments and conversion notes.
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>MCP-native</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Tool schemas and responses align with Prefect MCP guidance.
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="mt-16 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>TaskFlow</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Clean conversion from @dag/@task to @flow/@task.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Datasets</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Convert Datasets to Prefect Events and Automations.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Sensors</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Polling tasks + event-driven alternatives.
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
