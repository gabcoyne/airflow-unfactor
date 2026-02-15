import { DocsSidebar } from "@/components/docs/sidebar";
import { DocsTopbar } from "@/components/docs/topbar";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      <DocsTopbar />
      <div className="mx-auto flex max-w-7xl">
        <DocsSidebar />
        <main className="flex-1 px-6 py-10 lg:px-12">
          <article className="mx-auto max-w-4xl">{children}</article>
        </main>
      </div>
    </div>
  );
}
