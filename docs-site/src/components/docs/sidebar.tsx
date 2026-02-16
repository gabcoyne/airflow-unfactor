import Link from "next/link";
import { docsNav } from "./nav";

function TransformLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="sidebar-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="oklch(0.78 0.20 45)" />
          <stop offset="40%" stopColor="oklch(0.82 0.18 85)" />
          <stop offset="100%" stopColor="oklch(0.68 0.18 255)" />
        </linearGradient>
      </defs>
      <path
        d="M20 4L32 12V28L20 36L8 28V12L20 4Z"
        fill="url(#sidebar-gradient)"
      />
      <path
        d="M20 10L26 14V26L20 30L14 26V14L20 10Z"
        fill="currentColor"
        className="text-sidebar"
      />
      <circle cx="20" cy="20" r="4" fill="url(#sidebar-gradient)" />
    </svg>
  );
}

export function DocsSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-sidebar-border/50 bg-sidebar px-5 py-6 lg:block">
      {/* Logo */}
      <div className="mb-8 px-2">
        <Link href="/" className="group flex items-center gap-2.5">
          <div className="relative">
            <TransformLogo className="h-8 w-8 transition-transform duration-300 group-hover:scale-105" />
          </div>
          <div className="flex flex-col">
            <span
              className="text-[15px] font-semibold tracking-tight"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              airflow-unfactor
            </span>
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Documentation
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="space-y-6">
        {docsNav.map((section) => (
          <div key={section.title}>
            <p className="mb-2.5 px-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground/70">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="group flex items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] text-sidebar-foreground/75 transition-all duration-200 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  >
                    <span className="h-1 w-1 rounded-full bg-current opacity-0 transition-opacity group-hover:opacity-100" />
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="mt-8 border-t border-sidebar-border/50 pt-6">
        <div className="rounded-lg bg-gradient-to-br from-chart-1/10 via-chart-3/10 to-chart-2/10 p-4">
          <p className="text-xs font-medium text-foreground/80">Need help?</p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Check out our{" "}
            <Link href="/docs/guides/enterprise-migration" className="text-primary hover:underline">
              enterprise guide
            </Link>{" "}
            or open an issue on GitHub.
          </p>
        </div>
      </div>
    </aside>
  );
}
