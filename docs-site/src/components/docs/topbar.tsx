import Link from "next/link";
import { Badge } from "@/components/ui/badge";

export function DocsTopbar() {
  return (
    <div className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-semibold">
            airflow-unfactor
          </Link>
          <Badge variant="outline">MCP</Badge>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <Link href="/docs">Docs</Link>
          <Link href="https://github.com/prefect/airflow-unfactor">GitHub</Link>
        </div>
      </div>
    </div>
  );
}
