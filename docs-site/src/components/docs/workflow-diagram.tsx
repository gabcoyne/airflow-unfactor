"use client";

import { cn } from "@/lib/utils";

interface WorkflowDiagramProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export function WorkflowDiagram({ children, className, title }: WorkflowDiagramProps) {
  return (
    <div className={cn("my-6", className)}>
      {title && (
        <div className="mb-2 text-sm font-medium text-muted-foreground">
          {title}
        </div>
      )}
      <div className="relative rounded-lg border border-border bg-muted/30 overflow-hidden">
        {/* Terminal-style header */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/50">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-400/80" />
            <div className="w-3 h-3 rounded-full bg-yellow-400/80" />
            <div className="w-3 h-3 rounded-full bg-green-400/80" />
          </div>
          <span className="ml-2 text-xs text-muted-foreground font-mono">workflow</span>
        </div>
        {/* Scrollable content area with visible scrollbar */}
        <div
          className="overflow-x-auto overflow-y-hidden scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: 'var(--border) transparent'
          }}
        >
          <pre className="p-4 text-sm font-mono leading-relaxed whitespace-pre min-w-max">
            {children}
          </pre>
        </div>
      </div>
    </div>
  );
}
