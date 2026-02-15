import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Zap,
  GitBranch,
  Layers,
  Code2,
  Workflow,
  Shield,
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Workflow className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold tracking-tight">
              airflow-unfactor
            </span>
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link
              href="/docs"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Docs
            </Link>
            <Link
              href="/docs/mcp"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              MCP Guide
            </Link>
            <Link
              href="https://github.com/gabcoyne/airflow-unfactor"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              GitHub
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="gradient-glow pointer-events-none absolute inset-0 h-[600px]" />
        <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-16 md:pb-32 md:pt-24">
          <div className="mx-auto max-w-4xl text-center">
            <div className="mb-6 flex items-center justify-center gap-3">
              <Badge
                variant="outline"
                className="border-primary/30 bg-primary/5"
              >
                <Zap className="mr-1 h-3 w-3" />
                MCP Native
              </Badge>
              <Badge variant="secondary">v0.1.0</Badge>
            </div>

            <h1 className="text-4xl font-bold tracking-tight md:text-6xl lg:text-7xl">
              Transform{" "}
              <span className="text-gradient">Airflow DAGs</span>
              <br />
              into Prefect Flows
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              AI-powered migration tooling that analyzes your DAGs, generates
              clean Prefect code with educational comments, and validates
              behavioral equivalence.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2">
                <Link href="/docs">
                  Get Started
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/docs/mcp">MCP Integration</Link>
              </Button>
            </div>
          </div>

          {/* Code Preview */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl shadow-primary/5">
              <div className="flex items-center gap-2 border-b border-border bg-muted/30 px-4 py-3">
                <div className="h-3 w-3 rounded-full bg-destructive/60" />
                <div className="h-3 w-3 rounded-full bg-accent/60" />
                <div className="h-3 w-3 rounded-full bg-chart-3/60" />
                <span className="ml-2 text-xs text-muted-foreground">
                  conversion_example.py
                </span>
              </div>
              <pre className="overflow-x-auto p-6 text-sm">
                <code className="text-muted-foreground">
                  <span className="text-chart-5"># Before: Airflow DAG</span>
                  {"\n"}
                  <span className="text-chart-4">@dag</span>(dag_id=
                  <span className="text-chart-2">&quot;etl_pipeline&quot;</span>)
                  {"\n"}
                  <span className="text-primary">def</span>{" "}
                  <span className="text-foreground">etl_pipeline</span>():
                  {"\n"}
                  {"    "}extract_task = PythonOperator(...)
                  {"\n\n"}
                  <span className="text-chart-5"># After: Prefect Flow</span>
                  {"\n"}
                  <span className="text-chart-4">@flow</span>(name=
                  <span className="text-chart-2">&quot;etl_pipeline&quot;</span>)
                  {"\n"}
                  <span className="text-primary">def</span>{" "}
                  <span className="text-foreground">etl_pipeline</span>():
                  {"\n"}
                  {"    "}
                  <span className="text-chart-5">
                    # Prefect handles retries, logging, and observability
                  </span>
                  {"\n"}
                  {"    "}result = extract_task()
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="border-t border-border bg-muted/30 py-20 md:py-32">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
              Intelligent Migration
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              More than a transpiler. Understand, convert, and validate your
              workflow migrations.
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Code2 className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>Deep Analysis</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Detect Airflow versions (2.x/3.x), identify TaskFlow API,
                Datasets, Sensors, and 50+ operator types with full context.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                  <Layers className="h-5 w-5 text-accent-foreground" />
                </div>
                <CardTitle>Smart Conversion</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Generate idiomatic Prefect flows with educational comments
                explaining each transformation and Prefect best practices.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-chart-3/10">
                  <Shield className="h-5 w-5 text-chart-3" />
                </div>
                <CardTitle>Validation</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Behavioral equivalence checking compares task graphs, data flow,
                and dependencies between original and converted code.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-chart-4/10">
                  <GitBranch className="h-5 w-5 text-chart-4" />
                </div>
                <CardTitle>TaskFlow Support</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Seamless conversion from @dag/@task decorators to @flow/@task,
                preserving function signatures and data dependencies.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-chart-5/10">
                  <Workflow className="h-5 w-5 text-chart-5" />
                </div>
                <CardTitle>Datasets to Events</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Convert Airflow Datasets to Prefect Events with deployment
                triggers and automation scaffolding.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>MCP Native</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Built for AI-assisted workflows. Tool schemas follow MCP
                conventions for Claude, Cursor, and other AI tools.
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="border-t border-border py-20 md:py-32">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
              Ready to migrate?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Start converting your Airflow DAGs to Prefect flows in minutes.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2">
                <Link href="/docs">
                  Read the Docs
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="https://github.com/gabcoyne/airflow-unfactor">
                  View on GitHub
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-muted/30 py-12">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-primary">
                <Workflow className="h-3 w-3 text-primary-foreground" />
              </div>
              <span className="text-sm font-medium">airflow-unfactor</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="/docs" className="hover:text-foreground">
                Docs
              </Link>
              <Link
                href="https://github.com/gabcoyne/airflow-unfactor"
                className="hover:text-foreground"
              >
                GitHub
              </Link>
              <span>MIT License</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
