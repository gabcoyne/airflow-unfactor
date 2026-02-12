import Link from "next/link";
import { docsNav } from "./nav";

export function DocsSidebar() {
  return (
    <aside className="hidden lg:block w-64 shrink-0 border-r border-border/60 px-6 py-10">
      <div className="mb-6">
        <Link href="/" className="text-lg font-semibold">
          airflow-unfactor
        </Link>
        <p className="text-sm text-muted-foreground">Modern MCP docs</p>
      </div>
      <nav className="space-y-6">
        {docsNav.map((section) => (
          <div key={section.title}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {section.title}
            </p>
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="block rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
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
