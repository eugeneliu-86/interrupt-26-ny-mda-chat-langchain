/**
 * How assistant Markdown is rendered (ph. 06 §5).
 *
 * WHY THIS IS `.ts` AND USES `createElement` INSTEAD OF JSX. Node runs
 * TypeScript directly but does not transform JSX, so anything written as
 * `.tsx` cannot be imported by `node --test` without adding a build step to
 * the test run. Keeping the element map here makes the rendering rules —
 * which are the part with actual decisions in them — testable against real
 * rendered HTML. `Markdown.tsx` is then a thin wrapper with nothing to test.
 */
import { createElement, type ReactNode } from "react";
import type { Components } from "react-markdown";

/**
 * Is this link somewhere a browser can actually go?
 *
 * The model cites sources as `[middleware.md](middleware.md)` — a corpus
 * page key, not a URL. Rendered as an anchor it resolves against this app's
 * origin and 404s, so the demo would show inviting links that all break, in
 * front of an audience specifically invited to check the evidence.
 */
export function isExternalLink(href: unknown): href is string {
  return typeof href === "string" && /^https?:\/\//i.test(href);
}

export const components: Components = {
  a({ href, children, node: _node, ...rest }) {
    if (isExternalLink(href)) {
      return createElement(
        "a",
        { href, target: "_blank", rel: "noreferrer noopener", ...rest },
        children as ReactNode,
      );
    }
    // A citation, not a destination. Styled to read as a source reference,
    // with the page key in the tooltip, and deliberately not clickable.
    return createElement(
      "span",
      {
        className: "cite",
        title: typeof href === "string" ? `corpus page: ${href}` : undefined,
      },
      children as ReactNode,
    );
  },

  // A wide table must scroll inside the message. Without the wrapper it
  // widens the column and the whole page scrolls sideways at projection
  // size — and the demo's spare question answers with a four-column table.
  table({ children, node: _node, ...rest }) {
    return createElement(
      "div",
      { className: "tablewrap" },
      createElement("table", rest, children as ReactNode),
    );
  },
};
