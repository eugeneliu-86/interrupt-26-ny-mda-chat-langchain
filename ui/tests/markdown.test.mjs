/**
 * The assistant's answers render as Markdown, not as raw text (ph. 06 §5).
 *
 *     node --test tests/markdown.test.mjs
 *
 * Offline. Renders the real element map against REAL RECORDED ANSWERS from
 * `agent/tests/question_selection.json`, so the fixtures are what the model
 * actually produced rather than markdown someone invented for a test.
 *
 * This layer had no coverage at all until the UI shipped and the answers
 * arrived as literal `**bold**` and pipe-delimited table rows on screen.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { components, isExternalLink } from "../lib/markdown.ts";

const render = (md) =>
  renderToStaticMarkup(
    createElement(ReactMarkdown, { remarkPlugins: [remarkGfm], components }, md),
  );

const RECORDED = JSON.parse(
  readFileSync(new URL("../../agent/tests/question_selection.json", import.meta.url), "utf8"),
);

function everyRecordedAnswer() {
  const out = [];
  for (const c of Object.values(RECORDED.candidates)) {
    for (const role of ["engineer", "employee"]) {
      for (const r of c[role]) if (r.text?.trim()) out.push(r.text);
    }
  }
  for (const role of ["engineer", "employee"]) {
    const t = RECORDED.beat_two[role]?.text;
    if (t?.trim()) out.push(t);
  }
  return out;
}

// --- the shapes the model actually emits -----------------------------------

test("bold becomes <strong>, not asterisks", () => {
  const html = render("Retry middleware is **required** on every model call.");
  assert.match(html, /<strong>required<\/strong>/);
  assert.ok(!html.includes("**"), html);
});

test("inline code becomes <code>", () => {
  const html = render("The rotation is `platform-agents-oncall`.");
  assert.match(html, /<code>platform-agents-oncall<\/code>/);
  assert.ok(!html.includes("`"), html);
});

test("GFM tables render — base CommonMark would not", () => {
  const html = render(
    "| Environment | Purpose |\n|---|---|\n| `prod-us` | US production |\n",
  );
  assert.match(html, /<table>/);
  assert.match(html, /<th[^>]*>Environment<\/th>/);
  assert.match(html, /<td[^>]*><code>prod-us<\/code><\/td>/);
  // Wrapped, so a wide table scrolls inside the message instead of widening
  // the page at projection size.
  assert.match(html, /<div class="tablewrap"><table>/);
  assert.ok(!html.includes("|---"), html);
});

test("lists render as lists", () => {
  const ul = render("- primary\n- secondary\n");
  assert.match(ul, /<ul>\s*<li>primary<\/li>/);
  const ol = render("1. open a ticket\n2. pass the eval gate\n");
  assert.match(ol, /<ol>\s*<li>open a ticket<\/li>/);
});

test("headings render", () => {
  assert.match(render("### Escalation path\n"), /<h3>Escalation path<\/h3>/);
});

// --- citations are not destinations ----------------------------------------

test("a corpus citation is NOT a link", () => {
  const html = render("Source: [`middleware.md`](middleware.md).");
  assert.ok(!html.includes("<a "), `citation became an anchor: ${html}`);
  assert.match(html, /<span class="cite"[^>]*>/);
  assert.match(html, /title="corpus page: middleware\.md"/);
  assert.match(html, /<code>middleware\.md<\/code>/);
});

test("a real external link still works, and opens in a new tab", () => {
  const html = render("See [the docs](https://docs.langchain.com/x).");
  assert.match(html, /<a href="https:\/\/docs\.langchain\.com\/x"/);
  assert.match(html, /target="_blank"/);
  assert.match(html, /rel="noreferrer noopener"/);
});

test("isExternalLink is strict about what counts", () => {
  for (const yes of ["https://x.dev", "http://x.dev", "HTTPS://X.DEV"]) {
    assert.equal(isExternalLink(yes), true, yes);
  }
  for (const no of ["middleware.md", "/middleware.md", "./a.md", "", undefined, null, 42]) {
    assert.equal(isExternalLink(no), false, String(no));
  }
});

// --- no raw HTML -----------------------------------------------------------

test("embedded HTML is escaped, not executed — the corpus is untrusted input", () => {
  const html = render('Hello <img src=x onerror="alert(1)"> and <script>alert(2)</script>.');

  // The property is that the markup is INERT, not that the characters are
  // gone. Showing the literal text `<img …>` is correct — it is what the
  // document said. An earlier version of this test asserted the substring
  // "onerror" was absent and failed on correct output, which would have
  // pushed someone toward "fixing" safe behaviour.
  assert.ok(!/<img[\s>]/i.test(html), `a real <img> element was emitted: ${html}`);
  assert.ok(!/<script[\s>]/i.test(html), `a real <script> element was emitted: ${html}`);
  assert.match(html, /&lt;img/, "the tag was not escaped");
  assert.match(html, /&lt;script/, "the tag was not escaped");
  // The attribute is inert text inside a <p>, never a live attribute.
  assert.ok(!/<[a-z]+[^>]*\sonerror=/i.test(html), `a live handler survived: ${html}`);
});

// --- against every answer the deployment actually gave ---------------------

test("no recorded answer renders with leftover markdown syntax", () => {
  const answers = everyRecordedAnswer();
  assert.ok(answers.length >= 30, `only ${answers.length} fixtures`);

  const leftovers = [];
  for (const md of answers) {
    const html = render(md);
    // Strip the one place literal markdown is legitimate: inside code.
    const outsideCode = html.replace(/<code>[\s\S]*?<\/code>/g, "").replace(/<pre>[\s\S]*?<\/pre>/g, "");
    if (/\*\*/.test(outsideCode)) leftovers.push(["bold", md.slice(0, 70)]);
    if (/^\|.*\|/m.test(outsideCode)) leftovers.push(["table row", md.slice(0, 70)]);
    if (/^#{1,6} /m.test(outsideCode)) leftovers.push(["heading", md.slice(0, 70)]);
  }
  assert.deepEqual(leftovers, [], `unrendered markdown in ${leftovers.length} answer(s)`);
});

test("the table answer really does produce a table", () => {
  // The spare demo question. If this stops being a table the spare is still
  // correct but loses the thing that makes it legible in fifteen seconds.
  const withTable = everyRecordedAnswer().filter((t) => /^\|.*\|/m.test(t));
  assert.ok(withTable.length > 0, "no recorded answer contains a table any more");
  for (const md of withTable) assert.match(render(md), /<table>/);
});
