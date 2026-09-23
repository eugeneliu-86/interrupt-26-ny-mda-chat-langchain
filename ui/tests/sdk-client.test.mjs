/**
 * The path the BROWSER takes (ph. 06 §3).
 *
 * WHY THIS FILE EXISTS. Every other test here drives the proxy over raw
 * HTTP — correct, and it proved the server side was right while the app was
 * completely broken in a browser. The SDK builds requests with
 * `new URL(`${apiUrl}${path}`)`, one argument and no base, so the relative
 * `apiUrl: "/api/lg"` the spec sketched threw `Invalid URL` on the first
 * request and every run reported "Run failed: Failed to construct 'URL'".
 *
 * A raw-HTTP suite can never catch that, because it never constructs a
 * client. This one does: it builds the real SDK `Client` with the exact URL
 * the components pass and makes it talk to the running proxy.
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

import { PROXY_PATH, proxyUrl } from "../lib/apiUrl.ts";

const ROOT = new URL("..", import.meta.url).pathname;
const BASE = (process.env.PROXY_TEST_BASE ?? "http://127.0.0.1:3000").replace(/\/$/, "");

function configured() {
  if (!existsSync(ROOT + ".env.local")) return false;
  const t = readFileSync(ROOT + ".env.local", "utf8");
  return /^LANGSMITH_API_KEY=.+/m.test(t) && /^MDA_API_URL=.+/m.test(t);
}
const skip = configured() ? false : "set ui/.env.local and run the dev server";

// --- the bug, pinned directly ----------------------------------------------

test("the proxy URL is absolute, because the SDK cannot parse a relative one", () => {
  const original = globalThis.window;
  globalThis.window = { location: { origin: "http://localhost:3000" } };
  try {
    const url = proxyUrl();
    assert.equal(url, "http://localhost:3000/api/lg");
    // THE EXACT OPERATION THE SDK PERFORMS. `new URL("/api/lg/threads")`
    // throws; this must not.
    assert.doesNotThrow(() => new URL(`${url}/threads`));
    assert.equal(new URL(`${url}/threads`).pathname, "/api/lg/threads");
  } finally {
    globalThis.window = original;
  }
});

test("a relative apiUrl would still break the SDK — the reason is real", () => {
  assert.throws(() => new URL(`${PROXY_PATH}/threads`), /Invalid URL/);
});

test("the SSR placeholder parses too", () => {
  const original = globalThis.window;
  // @ts-expect-error - simulating the server
  delete globalThis.window;
  try {
    assert.doesNotThrow(() => new URL(`${proxyUrl()}/threads`));
  } finally {
    globalThis.window = original;
  }
});

// --- the real client against the real proxy ---------------------------------

test("the SDK client reaches the deployment through the proxy", { skip }, async () => {
  const { Client } = await import("@langchain/langgraph-sdk");

  const res = await fetch(`${BASE}/api/identity`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ role: "employee" }),
  });
  assert.equal(res.status, 200, "identity route unreachable — is the server up?");
  const cookie = (res.headers.getSetCookie?.() ?? [])
    .map((c) => c.split(";")[0])
    .join("; ");

  // Exactly what the components construct, with the browser's origin.
  const client = new Client({
    apiUrl: `${BASE}${PROXY_PATH}`,
    defaultHeaders: { cookie },
  });

  const thread = await client.threads.create();
  assert.ok(thread.thread_id, "the SDK could not create a thread");

  const found = await client.assistants.search({ limit: 10 });
  assert.ok(
    found.some((a) => a.name === "role-aware-docs-assistant"),
    "the SDK could not see the canonical assistant through the proxy",
  );
});

test("the SDK can stream a run, and the role still comes from the cookie", {
  skip,
  timeout: 600_000,
}, async () => {
  const { Client } = await import("@langchain/langgraph-sdk");

  const res = await fetch(`${BASE}/api/identity`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ role: "employee" }),
  });
  const cookie = (res.headers.getSetCookie?.() ?? [])
    .map((c) => c.split(";")[0])
    .join("; ");

  const client = new Client({
    apiUrl: `${BASE}${PROXY_PATH}`,
    defaultHeaders: { cookie },
  });
  const thread = await client.threads.create();

  const corpora = new Set();
  let chunks = 0;
  for await (const ev of client.runs.stream(
    thread.thread_id,
    "role-aware-docs-assistant",
    {
      input: { messages: [{ type: "human", content: "What is our on-call escalation path?" }] },
      streamMode: ["updates", "messages-tuple"],
    },
  )) {
    chunks++;
    for (const update of Object.values(ev.data ?? {})) {
      for (const m of update?.messages ?? []) {
        if (m?.type === "tool" && typeof m.name === "string" && m.name.includes("__")) {
          corpora.add(m.name.split("__")[0]);
        }
      }
    }
  }

  assert.ok(chunks > 2, `the stream produced only ${chunks} event(s)`);
  // Beat 2, through the browser's own code path.
  assert.ok(!corpora.has("engineeringDocs"), `employee reached ${[...corpora]}`);
});
