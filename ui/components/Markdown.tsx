"use client";

/**
 * Rendering the assistant's answer (ph. 06 §5).
 *
 * The answers are Markdown, and substantially so — measured over the 32
 * recorded runs in `agent/tests/question_selection.json`: bold in 25, inline
 * code in 26, links in 18, lists in 18, headings in 4, and **tables in 3**.
 * The spare demo question ("What environments do we have?") answers with a
 * four-row table, which is unreadable as raw pipes on a projector.
 *
 * `remark-gfm` is therefore required rather than optional: tables are a GFM
 * extension that base CommonMark does not parse.
 *
 * NO RAW HTML. `react-markdown` ignores embedded HTML unless `rehype-raw` is
 * added, and it is deliberately not added. This text is model output derived
 * from corpus documents — one of which is a repo any engineer can edit — so
 * it is untrusted by construction. Markdown gives the formatting the demo
 * needs without giving a document the ability to inject markup into the page.
 *
 * The element map lives in `lib/markdown.ts` so it can be tested without a
 * JSX transform; see the note there.
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { components } from "@/lib/markdown";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
