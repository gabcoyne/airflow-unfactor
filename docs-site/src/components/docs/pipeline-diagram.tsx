"use client";

import { cn } from "@/lib/utils";

const steps = [
  {
    num: "1",
    tool: "read_dag",
    label: "Read DAG",
    desc: "Raw source code",
    color: "from-amber-500/20 to-amber-500/5",
    border: "border-amber-500/40",
    dot: "bg-amber-500",
  },
  {
    num: "2",
    tool: "lookup_concept",
    label: "Lookup",
    desc: "Translation rules",
    color: "from-blue-500/20 to-blue-500/5",
    border: "border-blue-500/40",
    dot: "bg-blue-500",
  },
  {
    num: "3",
    tool: "search_prefect_docs",
    label: "Search Docs",
    desc: "Live Prefect docs",
    color: "from-violet-500/20 to-violet-500/5",
    border: "border-violet-500/40",
    dot: "bg-violet-500",
    optional: true,
  },
  {
    num: "4",
    tool: null,
    label: "LLM Generates",
    desc: "Complete Prefect flow",
    color: "from-emerald-500/20 to-emerald-500/5",
    border: "border-emerald-500/40",
    dot: "bg-emerald-500",
    highlight: true,
  },
  {
    num: "5",
    tool: "validate",
    label: "Validate",
    desc: "Syntax + comparison",
    color: "from-rose-500/20 to-rose-500/5",
    border: "border-rose-500/40",
    dot: "bg-rose-500",
  },
];

export function PipelineDiagram({ className }: { className?: string }) {
  return (
    <div className={cn("my-8", className)}>
      {/* Desktop: horizontal pipeline */}
      <div className="hidden md:block">
        <div className="flex items-stretch gap-0">
          {steps.map((step, i) => (
            <div key={step.num} className="flex items-stretch flex-1 min-w-0">
              {/* Step node */}
              <div
                className={cn(
                  "relative flex flex-col items-center justify-start rounded-xl border px-3 py-4 w-full",
                  "bg-gradient-to-b",
                  step.color,
                  step.border,
                  step.highlight && "ring-1 ring-emerald-500/30"
                )}
              >
                {/* Number badge */}
                <div
                  className={cn(
                    "flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold mb-2",
                    step.dot,
                    "text-black"
                  )}
                >
                  {step.num}
                </div>

                {/* Label */}
                <div className="text-sm font-semibold text-foreground text-center leading-tight">
                  {step.label}
                </div>

                {/* Tool name */}
                {step.tool && (
                  <code className="mt-1.5 text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded">
                    {step.tool}
                  </code>
                )}

                {/* Description */}
                <div className="mt-1.5 text-[11px] text-muted-foreground text-center leading-snug">
                  {step.desc}
                </div>

                {/* Optional badge */}
                {step.optional && (
                  <span className="mt-1.5 text-[9px] uppercase tracking-wider text-muted-foreground/60 font-medium">
                    optional
                  </span>
                )}
              </div>

              {/* Arrow connector */}
              {i < steps.length - 1 && (
                <div className="flex items-center px-1 shrink-0">
                  <svg width="20" height="20" viewBox="0 0 20 20" className="text-muted-foreground/40">
                    <path
                      d="M4 10 L14 10 M11 6 L15 10 L11 14"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Mobile: vertical pipeline */}
      <div className="md:hidden flex flex-col gap-0">
        {steps.map((step, i) => (
          <div key={step.num}>
            <div
              className={cn(
                "relative flex items-center gap-3 rounded-lg border px-4 py-3",
                "bg-gradient-to-r",
                step.color,
                step.border,
                step.highlight && "ring-1 ring-emerald-500/30"
              )}
            >
              {/* Number badge */}
              <div
                className={cn(
                  "flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold shrink-0",
                  step.dot,
                  "text-black"
                )}
              >
                {step.num}
              </div>

              <div className="min-w-0">
                <div className="text-sm font-semibold text-foreground">
                  {step.label}
                  {step.optional && (
                    <span className="ml-2 text-[9px] uppercase tracking-wider text-muted-foreground/60 font-medium">
                      optional
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">{step.desc}</div>
              </div>

              {step.tool && (
                <code className="ml-auto text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded shrink-0">
                  {step.tool}
                </code>
              )}
            </div>

            {/* Vertical connector */}
            {i < steps.length - 1 && (
              <div className="flex justify-center py-1">
                <svg width="12" height="16" viewBox="0 0 12 16" className="text-muted-foreground/40">
                  <path
                    d="M6 2 L6 12 M3 9 L6 13 L9 9"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
