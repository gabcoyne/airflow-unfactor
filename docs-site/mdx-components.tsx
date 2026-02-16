import type { MDXComponents } from "mdx/types";

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    // Headings
    h1: ({ children }) => (
      <h1 className="mb-6 text-3xl font-bold tracking-tight text-foreground">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="mb-4 mt-10 text-2xl font-semibold tracking-tight text-foreground">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="mb-3 mt-8 text-xl font-semibold text-foreground">
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="mb-2 mt-6 text-lg font-semibold text-foreground">
        {children}
      </h4>
    ),

    // Paragraphs
    p: ({ children }) => (
      <p className="mb-4 leading-7 text-foreground/90">{children}</p>
    ),

    // Links
    a: ({ href, children }) => (
      <a
        href={href}
        className="font-medium text-primary underline decoration-primary/30 underline-offset-4 transition-colors hover:decoration-primary"
      >
        {children}
      </a>
    ),

    // Lists
    ul: ({ children }) => (
      <ul className="mb-4 ml-6 list-disc space-y-2 text-foreground/90">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="mb-4 ml-6 list-decimal space-y-2 text-foreground/90">
        {children}
      </ol>
    ),
    li: ({ children }) => <li className="leading-7">{children}</li>,

    // Code - inline code only (code blocks use pre > code)
    code: ({ children, className }) => {
      // If className exists, it's likely a code block (has language class)
      // In that case, don't add the inline styling
      if (className) {
        return <code className={`${className} font-mono text-sm`}>{children}</code>;
      }
      // Inline code styling
      return (
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm text-foreground">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="mb-4 overflow-x-auto rounded-lg border border-border bg-muted/50 p-4 text-sm">
        {children}
      </pre>
    ),

    // Blockquote
    blockquote: ({ children }) => (
      <blockquote className="mb-4 border-l-4 border-primary/50 pl-4 italic text-muted-foreground">
        {children}
      </blockquote>
    ),

    // Table - improved styling
    table: ({ children }) => (
      <div className="my-6 w-full overflow-x-auto">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="border-b border-border bg-muted/50">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-border">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="border-b border-border transition-colors hover:bg-muted/30">
        {children}
      </tr>
    ),
    th: ({ children }) => (
      <th className="border border-border bg-muted/50 px-4 py-3 text-left font-semibold text-foreground">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border border-border px-4 py-3 text-foreground/90 align-top">
        {children}
      </td>
    ),

    // Horizontal rule
    hr: () => <hr className="my-8 border-border" />,

    // Strong and emphasis
    strong: ({ children }) => (
      <strong className="font-semibold text-foreground">{children}</strong>
    ),
    em: ({ children }) => <em className="italic">{children}</em>,

    ...components,
  };
}
