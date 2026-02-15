import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Workflow, Zap } from "lucide-react";

export function DocsTopbar() {
  return (
    <div className="sticky top-0 z-10 border-b border-border/50 bg-background/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <Workflow className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <span className="font-semibold tracking-tight">
              airflow-unfactor
            </span>
          </Link>
          <Badge
            variant="outline"
            className="hidden border-primary/30 bg-primary/5 sm:inline-flex"
          >
            <Zap className="mr-1 h-3 w-3" />
            MCP
          </Badge>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <Link
            href="/docs"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            Docs
          </Link>
          <Link
            href="https://github.com/gabcoyne/airflow-unfactor"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            GitHub
          </Link>
        </div>
      </div>
    </div>
  );
}
