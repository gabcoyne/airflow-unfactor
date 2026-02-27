import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Sparkles,
  GitBranch,
  Layers,
  Code2,
  Shield,
  Cpu,
  Zap,
} from "lucide-react";

function TransformLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Airflow-inspired shape morphing into Prefect shape */}
      <defs>
        <linearGradient id="transform-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="oklch(0.78 0.20 45)" />
          <stop offset="40%" stopColor="oklch(0.82 0.18 85)" />
          <stop offset="100%" stopColor="oklch(0.68 0.18 255)" />
        </linearGradient>
      </defs>
      <path
        d="M20 4L32 12V28L20 36L8 28V12L20 4Z"
        fill="url(#transform-gradient)"
      />
      <path
        d="M20 10L26 14V26L20 30L14 26V14L20 10Z"
        fill="currentColor"
        className="text-background"
      />
      <circle cx="20" cy="20" r="4" fill="url(#transform-gradient)" />
    </svg>
  );
}

function FloatingOrb({ className = "", delay = "0s" }: { className?: string; delay?: string }) {
  return (
    <div
      className={`absolute rounded-full blur-3xl animate-float ${className}`}
      style={{ animationDelay: delay }}
    />
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/40 bg-background/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="group flex items-center gap-3">
            <div className="relative">
              <TransformLogo className="h-9 w-9 transition-transform duration-300 group-hover:scale-110" />
              <div className="absolute inset-0 blur-lg opacity-50 group-hover:opacity-75 transition-opacity">
                <TransformLogo className="h-9 w-9" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
                airflow-unfactor
              </span>
              <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
                DAG Migration
              </span>
            </div>
          </Link>
          <nav className="flex items-center gap-8 text-sm">
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
            <Button size="sm" asChild className="gap-2 rounded-full">
              <Link href="/docs/getting-started/quick-start">
                Get Started
                <ArrowRight className="h-3 w-3" />
              </Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Animated background orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <FloatingOrb
            className="left-1/4 top-20 h-96 w-96 bg-chart-1/20"
            delay="0s"
          />
          <FloatingOrb
            className="right-1/4 top-40 h-80 w-80 bg-chart-2/20"
            delay="2s"
          />
          <FloatingOrb
            className="left-1/2 top-60 h-64 w-64 bg-chart-3/15"
            delay="4s"
          />
        </div>

        <div className="gradient-glow pointer-events-none absolute inset-0 h-[700px]" />

        <div className="relative mx-auto max-w-7xl px-6 pb-24 pt-20 md:pb-40 md:pt-32">
          <div className="mx-auto max-w-4xl text-center">
            {/* Badges */}
            <div className="mb-8 flex items-center justify-center gap-3 animate-stagger">
              <Badge
                variant="outline"
                className="badge-airflow gap-1.5 rounded-full px-3 py-1"
              >
                <span className="h-2 w-2 rounded-full bg-chart-1 animate-pulse" />
                Airflow
              </Badge>
              <div className="flex items-center gap-1 text-muted-foreground">
                <ArrowRight className="h-4 w-4" />
              </div>
              <Badge
                variant="outline"
                className="badge-prefect gap-1.5 rounded-full px-3 py-1"
              >
                <span className="h-2 w-2 rounded-full bg-chart-2 animate-pulse" style={{ animationDelay: '0.5s' }} />
                Prefect
              </Badge>
            </div>

            {/* Main headline */}
            <h1
              className="text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              <span className="block">Transform</span>
              <span className="text-gradient">DAGs to Flows</span>
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-lg text-muted-foreground md:text-xl leading-relaxed">
              Point it at an Airflow DAG and get idiomatic Prefect code back.
              Raw source in, working flow out. Thirty seconds, not thirty hours.
            </p>

            {/* CTA buttons */}
            <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button
                size="lg"
                asChild
                className="group gap-2 rounded-full bg-gradient-to-r from-chart-1 via-chart-3 to-chart-2 px-8 text-white shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all duration-300"
              >
                <Link href="/docs">
                  Begin Transformation
                  <Sparkles className="h-4 w-4 transition-transform group-hover:rotate-12" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                asChild
                className="gap-2 rounded-full border-border/60 backdrop-blur"
              >
                <Link href="/docs/mcp">
                  <Cpu className="h-4 w-4" />
                  Explore MCP Tools
                </Link>
              </Button>
            </div>

            {/* Stats */}
            <div className="mt-16 flex items-center justify-center gap-12 text-center">
              <div>
                <div className="text-3xl font-bold text-gradient" style={{ fontFamily: 'var(--font-display)' }}>50+</div>
                <div className="text-sm text-muted-foreground">Operator Mappings</div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <div className="text-3xl font-bold text-gradient" style={{ fontFamily: 'var(--font-display)' }}>78</div>
                <div className="text-sm text-muted-foreground">Translation Entries</div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div>
                <div className="text-3xl font-bold text-gradient" style={{ fontFamily: 'var(--font-display)' }}>100%</div>
                <div className="text-sm text-muted-foreground">LLM-Native</div>
              </div>
            </div>
          </div>

          {/* Code Preview */}
          <div className="mx-auto mt-20 max-w-4xl">
            <div className="code-block overflow-hidden shadow-2xl shadow-primary/10">
              <div className="terminal-dots">
                <div className="terminal-dot terminal-dot-red" />
                <div className="terminal-dot terminal-dot-yellow" />
                <div className="terminal-dot terminal-dot-green" />
                <span className="ml-3 text-xs text-muted-foreground font-mono">
                  transformation.py
                </span>
              </div>
              <pre className="overflow-x-auto p-6 text-sm leading-relaxed">
                <code>
                  <span className="text-chart-4"># 1. Read the DAG source code</span>
                  {"\n"}
                  dag = <span className="text-chart-2">read_dag</span>(
                  <span className="text-chart-3">&quot;dags/etl_pipeline.py&quot;</span>)
                  {"\n\n"}
                  <span className="text-chart-4"># 2. Look up Airflow→Prefect translation knowledge</span>
                  {"\n"}
                  mapping = <span className="text-chart-2">lookup_concept</span>(
                  <span className="text-chart-3">&quot;PythonOperator&quot;</span>)
                  {"\n"}
                  docs = <span className="text-chart-2">search_prefect_docs</span>(
                  <span className="text-chart-3">&quot;task retries&quot;</span>)
                  {"\n\n"}
                  <span className="text-chart-4"># 3. LLM generates idiomatic Prefect code</span>
                  {"\n"}
                  <span className="text-chart-4"># 4. Validate the generated flow</span>
                  {"\n"}
                  result = <span className="text-chart-2">validate</span>(
                  {"\n"}
                  {"    "}original_dag=dag_path,
                  {"\n"}
                  {"    "}converted_flow=prefect_code
                  {"\n"}
                  )
                  {"\n"}
                  <span className="text-chart-4"># ✓ Syntax valid</span>
                  {"\n"}
                  <span className="text-chart-4"># ✓ Both sources returned for comparison</span>
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Philosophy Section */}
      <section className="relative border-t border-border/40 bg-muted/20 py-24 md:py-32">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <Badge variant="secondary" className="mb-6 rounded-full">
              <Zap className="mr-1 h-3 w-3" />
              Philosophy
            </Badge>
            <h2
              className="text-3xl font-bold tracking-tight md:text-5xl"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              Templates are brittle.
              <br />
              <span className="text-muted-foreground">LLMs are adaptive.</span>
            </h2>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
              Traditional conversion tools rely on rigid templates that break on edge cases.
              We provide rich, structured payloads that enable LLMs to generate
              idiomatic, context-aware Prefect code that actually works.
            </p>
          </div>

          {/* Comparison */}
          <div className="mx-auto mt-16 grid max-w-4xl gap-8 md:grid-cols-2">
            <Card className="border-destructive/20 bg-destructive/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive/20 text-xs">✗</span>
                  Template-Based
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-2">
                <p>• Rigid pattern matching breaks on variations</p>
                <p>• Non-idiomatic output requires manual fixes</p>
                <p>• Cannot handle custom operators well</p>
                <p>• Template maintenance burden</p>
              </CardContent>
            </Card>

            <Card className="card-glow border-chart-2/30 bg-chart-2/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-chart-2/20 text-xs">✓</span>
                  LLM-Assisted
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-2">
                <p>• Rich context enables adaptive generation</p>
                <p>• Idiomatic code tailored to each DAG</p>
                <p>• Handles complex patterns naturally</p>
                <p>• Continuous improvement with model updates</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative border-t border-border/40 py-24 md:py-32 noise">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <Badge variant="secondary" className="mb-6 rounded-full">
              <Layers className="mr-1 h-3 w-3" />
              Capabilities
            </Badge>
            <h2
              className="text-3xl font-bold tracking-tight md:text-5xl"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              Everything you need
              <br />
              <span className="text-gradient">for transformation</span>
            </h2>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3 animate-stagger">
            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-chart-1/10">
                  <Code2 className="h-6 w-6 text-chart-1" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>DAG Reading</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Read raw Airflow DAG source code directly. The LLM analyzes
                the code — no brittle AST intermediary.
              </CardContent>
            </Card>

            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-chart-2/10">
                  <Layers className="h-6 w-6 text-chart-2" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>Translation Knowledge</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                78 pre-compiled Airflow→Prefect mappings via Colin, plus live
                Prefect doc search for anything not covered.
              </CardContent>
            </Card>

            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-chart-3/10">
                  <Shield className="h-6 w-6 text-chart-3" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>Validation</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Syntax-check generated flows and return both sources
                side-by-side for the LLM to verify structural fidelity.
              </CardContent>
            </Card>

            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-chart-4/10">
                  <GitBranch className="h-6 w-6 text-chart-4" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>Pattern Detection</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Detect XCom usage, sensors, trigger rules, dynamic mapping,
                connections, variables, and custom operators.
              </CardContent>
            </Card>

            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-chart-5/10">
                  <ArrowRight className="h-6 w-6 text-chart-5" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>Operator Mappings</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                50+ Airflow→Prefect operator mappings with example code
                and migration guidance for each pattern.
              </CardContent>
            </Card>

            <Card className="card-glow border-border/40 bg-card/60 backdrop-blur">
              <CardHeader>
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                  <Cpu className="h-6 w-6 text-primary" />
                </div>
                <CardTitle style={{ fontFamily: 'var(--font-display)' }}>MCP Native</CardTitle>
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
      <section className="relative border-t border-border/40 py-24 md:py-32">
        <div className="gradient-glow pointer-events-none absolute inset-0 rotate-180 opacity-50" />
        <div className="relative mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2
              className="text-3xl font-bold tracking-tight md:text-5xl"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              Ready to{" "}
              <span className="text-gradient">migrate</span>?
            </h2>
            <p className="mt-6 text-lg text-muted-foreground">
              Let your LLM generate clean Prefect flows from comprehensive DAG analysis.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button
                size="lg"
                asChild
                className="group gap-2 rounded-full px-8 shadow-lg shadow-primary/20"
              >
                <Link href="/docs">
                  Read the Docs
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="rounded-full">
                <Link href="https://github.com/gabcoyne/airflow-unfactor">
                  View on GitHub
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-muted/20 py-16">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-center justify-between gap-8 md:flex-row">
            <div className="flex items-center gap-3">
              <TransformLogo className="h-8 w-8" />
              <div>
                <span className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
                  airflow-unfactor
                </span>
                <p className="text-xs text-muted-foreground">
                  LLM-native DAG transformation
                </p>
              </div>
            </div>
            <div className="flex items-center gap-8 text-sm text-muted-foreground">
              <Link href="/docs" className="transition-colors hover:text-foreground">
                Docs
              </Link>
              <Link href="/docs/mcp" className="transition-colors hover:text-foreground">
                MCP Tools
              </Link>
              <Link
                href="https://github.com/gabcoyne/airflow-unfactor"
                className="transition-colors hover:text-foreground"
              >
                GitHub
              </Link>
              <span className="text-muted-foreground/60">MIT License</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
