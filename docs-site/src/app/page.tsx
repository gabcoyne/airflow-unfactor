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
              MCP Tools
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
                LLM-Native
              </Badge>
              <Badge variant="secondary">MCP Server</Badge>
            </div>

            <h1 className="text-4xl font-bold tracking-tight md:text-6xl lg:text-7xl">
              Analyze{" "}
              <span className="text-gradient">Airflow DAGs</span>
              <br />
              for LLM Conversion
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              Rich analysis payloads that enable LLMs to generate complete,
              functional Prefect flows. We analyze. The LLM generates. We validate.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" asChild className="gap-2">
                <Link href="/docs">
                  Get Started
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/docs/mcp">MCP Tools</Link>
              </Button>
            </div>
          </div>

          {/* Workflow Preview */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl shadow-primary/5">
              <div className="flex items-center gap-2 border-b border-border bg-muted/30 px-4 py-3">
                <div className="h-3 w-3 rounded-full bg-destructive/60" />
                <div className="h-3 w-3 rounded-full bg-accent/60" />
                <div className="h-3 w-3 rounded-full bg-chart-3/60" />
                <span className="ml-2 text-xs text-muted-foreground">
                  workflow
                </span>
              </div>
              <pre className="overflow-x-auto p-6 text-sm">
                <code className="text-muted-foreground">
                  <span className="text-chart-5"># 1. Analyze your DAG</span>
                  {"\n"}
                  analysis = <span className="text-primary">analyze</span>(
                  <span className="text-chart-2">&quot;dags/etl.py&quot;</span>)
                  {"\n\n"}
                  <span className="text-chart-5"># 2. Get Prefect context</span>
                  {"\n"}
                  context = <span className="text-primary">get_context</span>(
                  {"\n"}
                  {"    "}features=analysis.patterns
                  {"\n"}
                  )
                  {"\n\n"}
                  <span className="text-chart-5"># 3. LLM generates Prefect flow using analysis + context</span>
                  {"\n"}
                  <span className="text-chart-5"># 4. Validate the result</span>
                  {"\n"}
                  result = <span className="text-primary">validate</span>(
                  {"\n"}
                  {"    "}original=dag_code,
                  {"\n"}
                  {"    "}generated=prefect_flow
                  {"\n"}
                  )
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
              LLM-Assisted Migration
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Deterministic templating is brittle. We provide rich payloads
              that let LLMs generate idiomatic Prefect code.
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Code2 className="h-5 w-5 text-primary" />
                </div>
                <CardTitle>Rich Analysis</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Comprehensive DAG payloads with structure, patterns, configuration,
                complexity metrics, and migration notes.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                  <Layers className="h-5 w-5 text-accent-foreground" />
                </div>
                <CardTitle>Prefect Context</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Fetch relevant Prefect documentation, operator mappings,
                and deployment templates based on detected features.
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
                Verify generated code matches original structure—task coverage,
                dependency graphs, and configuration completeness.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-chart-4/10">
                  <GitBranch className="h-5 w-5 text-chart-4" />
                </div>
                <CardTitle>Pattern Detection</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Detect XCom usage, sensors, trigger rules, dynamic mapping,
                connections, variables, and custom operators.
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-chart-5/10">
                  <Workflow className="h-5 w-5 text-chart-5" />
                </div>
                <CardTitle>Operator Mappings</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                50+ Airflow→Prefect operator mappings with example code
                and migration guidance for each.
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
                Built with FastMCP for AI-assisted workflows. Works with
                Claude, Cursor, and other MCP-compatible tools.
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
              Let your LLM generate clean Prefect flows from comprehensive DAG analysis.
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
