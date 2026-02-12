import { DocsSidebar } from "@/components/docs/sidebar";
import { DocsTopbar } from "@/components/docs/topbar";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <DocsTopbar />
      <div className="mx-auto flex max-w-6xl">
        <DocsSidebar />
        <main className="flex-1 px-6 py-10">
          <article className="max-w-3xl space-y-6 leading-7">
            {children}
          </article>
        </main>
      </div>
    </div>
  );
}
