import Link from "next/link";
import { Workflow } from "lucide-react";
import { docsNav } from "./nav";

export function DocsSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-border/50 bg-sidebar px-6 py-8 lg:block">
      <div className="mb-8">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <Workflow className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-base font-semibold tracking-tight">
            airflow-unfactor
          </span>
        </Link>
        <p className="mt-1 text-xs text-muted-foreground">
          DAG to Flow Migration
        </p>
      </div>
      <nav className="space-y-6">
        {docsNav.map((section) => (
          <div key={section.title}>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="block rounded-md px-2.5 py-1.5 text-sm text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  >
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
