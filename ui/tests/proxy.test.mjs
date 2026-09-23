/**
 * The trust boundary, tested against a real server (ph. 06 §1, §2).
 *
 *     pnpm build && node --test tests/proxy.test.mjs
 *
 * Needs `.env.local` with a working `MDA_API_URL` and `LANGSMITH_API_KEY`,
 * and makes real runs against the deployment. Skipped when unconfigured, so
 * `node --test tests/` stays runnable offline.
 *
 * THE TEST THAT MATTERS is "a hand-crafted context is ignored". Everything
 * else here is hygiene; that one is the architecture. If a browser can put a
 * role in the body and have it honoured, then the role is a value the client
 * sets, and the demo's central sentence — *swap the dropdown for a verified
 * JWT claim and nothing downstream changes* — becomes false.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { after, before, test } from "node:test";

const ROOT = new URL("..", import.meta.url).pathname;

function env() {
  const out = {};
  if (!existsSync(ROOT + ".env.local")) return out;
  for (const line of readFileSync(ROOT + ".env.local", "utf8").split("\n")) {
    const m = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (m && m[2]) out[m[1]] = m[2];
  }
  return out;
}

const ENV = env();
const CONFIGURED = Boolean(ENV.MDA_API_URL && ENV.LANGSMITH_API_KEY);
const skip = CONFIGURED ? false : "set ui/.env.local to run";

/** Beat 2. An employee must never reach the runbooks, whatever it sends. */
const ENGINEERING_ONLY = "What is our on-call escalation path?";

let server;
let base;

before(async () => {
  if (!CONFIGURED) return;

  // Reuse a server that is already up. Starting one per run is fine in CI and
  // wasteful while iterating, and an already-warm server removes cold start
  // from the streaming and latency measurements below.
  if (process.env.PROXY_TEST_BASE) {
    base = process.env.PROXY_TEST_BASE.replace(/\/$/, "");
    return;
  }

  const port = 3100 + Math.floor(Math.random() * 400);
  base = `http://127.0.0.1:${port}`;
  server = spawn("node_modules/.bin/next", ["start", "-p", String(port)], {
    cwd: ROOT,
    env: { ...process.env, ...ENV },
    stdio: ["ignore", "pipe", "pipe"],
  });
  server.stdout.setEncoding("utf8");
  server.stderr.setEncoding("utf8");
  // Keep the server's own output: when the proxy 500s, its message is the
  // whole diagnosis, and a test that discards it makes you re-run to learn
  // anything.
  server.stdout.on("data", (d) => process.stdout.write(`    [next] ${d}`));
  server.stderr.on("data", (d) => process.stdout.write(`    [next!] ${d}`));
  // Wait for readiness rather than sleeping: a fixed sleep either wastes time
  // or races, and a racing test gets marked flaky and then ignored.
  const deadline = Date.now() + 60_000;
  for (;;) {
    if (Date.now() > deadline) throw new Error("next start never became ready");
    try {
      const res = await fetch(base, { signal: AbortSignal.timeout(2000) });
      if (res.status < 500) break;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
}, { timeout: 90_000 });

after(() => server?.kill("SIGTERM"));

// Each live test makes a real run against a shared deployment. 300s was not
// enough when the deployment was already busy, and a timeout there reads as a
// proxy bug rather than as queueing.
const LIVE = { skip, timeout: 600_000 };

/** Pick an identity and return the raw cookie header to reuse. */
async function pick(role) {
  const res = await fetch(`${base}/api/identity`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ role }),
  });
  const setCookie = res.headers.getSetCookie?.() ?? [];
  return { res, setCookie, cookie: setCookie.map((c) => c.split(";")[0]).join("; ") };
}

async function newThread(cookie) {
  const res = await fetch(`${base}/api/lg/threads`, {
    method: "POST",
    headers: { "content-type": "application/json", cookie },
    body: "{}",
  });
  if (res.status !== 200) {
    throw new Error(`thread create failed: ${res.status} ${await res.text()}`);
  }
  return (await res.json()).thread_id;
}

function corporaUsed(state) {
  const msgs = state.messages ?? [];
  return new Set(
    msgs
      .filter((m) => m.type === "tool" && typeof m.name === "string" && m.name.includes("__"))
      .map((m) => m.name.split("__")[0]),
  );
}

// --- §1 rule 1: the key stays server-side ----------------------------------

test("the browser only ever talks to this origin", { skip }, async () => {
  const html = await (await fetch(base, { headers: { cookie: "" } })).text();
  assert.ok(!html.includes(ENV.LANGSMITH_API_KEY), "the key is in the served HTML");
  assert.ok(!html.includes(ENV.MDA_API_URL), "the deployment URL is in the served HTML");

  // Every script the page pulls must be same-origin, and at least one of them
  // must name the proxy path — that is what proves the client calls `/api/lg`
  // rather than the deployment.
  //
  // Checked in the CHUNKS, not the HTML: `apiUrl: "/api/lg"` is a value in
  // compiled client code, and asserting on the HTML only tested that Next
  // does not inline the bundle. The earlier version of this test did exactly
  // that and failed for a reason unrelated to the property.
  const srcs = [...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(srcs.length > 0, "the page loaded no scripts at all");
  for (const src of srcs) {
    assert.ok(
      src.startsWith("/") || src.startsWith(base),
      `the page loads a cross-origin script: ${src}`,
    );
  }

  for (const src of srcs) {
    const js = await (await fetch(new URL(src, base))).text();
    assert.ok(!js.includes(ENV.LANGSMITH_API_KEY), `the key is in ${src}`);
    assert.ok(!js.includes(ENV.MDA_API_URL), `the deployment URL is in ${src}`);
  }

  // `/api/lg` lives in a LAZILY-LOADED chunk, so it is not in any script the
  // first document references. Scanning only those chunks made this assertion
  // depend on Turbopack's splitting decisions, which changed between builds
  // and failed for a reason unrelated to the property. Scan what was built.
  const { readdirSync, readFileSync, statSync } = await import("node:fs");
  const { join } = await import("node:path");
  const walk = (d) => readdirSync(d).flatMap((n) => {
    const f = join(d, n);
    return statSync(f).isDirectory() ? walk(f) : f.endsWith(".js") ? [f] : [];
  });
  const chunks = walk(join(ROOT, ".next/static"));
  assert.ok(
    chunks.some((f) => readFileSync(f, "utf8").includes("/api/lg")),
    "no client chunk points at the same-origin proxy",
  );
});

// --- §1 rule 2: THE test ---------------------------------------------------

test(
  "a hand-crafted context is IGNORED — the cookie decides",
  LIVE,
  async () => {
    const { cookie } = await pick("employee");
    const thread = await newThread(cookie);

    const res = await fetch(`${base}/api/lg/threads/${thread}/runs/wait`, {
      method: "POST",
      headers: { "content-type": "application/json", cookie },
      body: JSON.stringify({
        assistant_id: "role-aware-docs-assistant",
        input: { messages: [{ type: "human", content: ENGINEERING_ONLY }] },
        // A client claiming to be the engineer. This must have no effect.
        context: { role: "engineer", display_name: "forged" },
      }),
    });
    assert.equal(res.status, 200);
    const state = await res.json();
    assert.ok(!state.__error__, `run died: ${JSON.stringify(state.__error__)}`);

    const used = corporaUsed(state);
    assert.ok(
      !used.has("engineeringDocs"),
      `FORGERY SUCCEEDED — the run reached ${[...used].join(", ")}`,
    );
    assert.ok(used.has("productDocs"), "the run used no corpus at all");
  },
);

test("a run with no identity is refused before it reaches MDA", { skip }, async () => {
  const thread = await newThread("");
  const res = await fetch(`${base}/api/lg/threads/${thread}/runs/wait`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      assistant_id: "role-aware-docs-assistant",
      input: { messages: [{ type: "human", content: "hi" }] },
    }),
  });
  assert.equal(res.status, 400);
  assert.match((await res.json()).error, /no identity selected/);
});

test("the identity cookie is httpOnly and sameSite=lax", { skip }, async () => {
  const { setCookie } = await pick("engineer");
  assert.equal(setCookie.length, 1, "expected exactly one cookie");
  const raw = setCookie[0];
  assert.match(raw, /HttpOnly/i, raw);
  assert.match(raw, /SameSite=lax/i, raw);
  assert.match(raw, /Path=\//i, raw);
});

test("an unknown role never becomes a cookie", { skip }, async () => {
  const { res, setCookie } = await pick("admin");
  assert.equal(res.status, 400);
  assert.match((await res.json()).error, /unknown role/);
  assert.equal(setCookie.length, 0);
});

// --- §2: streaming and error passthrough -----------------------------------

test(
  "the stream arrives incrementally, not as one buffered blob",
  LIVE,
  async () => {
    const { cookie } = await pick("engineer");
    const thread = await newThread(cookie);
    const res = await fetch(`${base}/api/lg/threads/${thread}/runs/stream`, {
      method: "POST",
      headers: { "content-type": "application/json", cookie },
      body: JSON.stringify({
        assistant_id: "role-aware-docs-assistant",
        input: { messages: [{ type: "human", content: ENGINEERING_ONLY }] },
        stream_mode: ["messages-tuple", "updates"],
      }),
    });
    assert.equal(res.status, 200);
    assert.match(res.headers.get("content-type") ?? "", /event-stream/);

    const started = Date.now();
    const arrivals = [];
    const reader = res.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value?.length) arrivals.push(Date.now() - started);
    }
    // Buffered would mean every chunk lands at effectively the same instant.
    assert.ok(arrivals.length > 2, `only ${arrivals.length} chunk(s)`);
    const spread = arrivals.at(-1) - arrivals[0];
    assert.ok(spread > 250, `all chunks landed within ${spread}ms — buffered`);
  },
);

test("a 4xx from MDA reaches the client with its message", { skip }, async () => {
  const { cookie } = await pick("engineer");
  const thread = await newThread(cookie);
  const res = await fetch(`${base}/api/lg/threads/${thread}/runs/wait`, {
    method: "POST",
    headers: { "content-type": "application/json", cookie },
    body: JSON.stringify({
      assistant_id: "no-such-assistant",
      input: { messages: [{ type: "human", content: "hi" }] },
    }),
  });
  assert.ok(res.status >= 400, `expected an error, got ${res.status}`);
  const text = await res.text();
  assert.ok(text.trim().length > 0, "the error body was swallowed");
});

test("GET requests pass through with the key attached", { skip }, async () => {
  const { cookie } = await pick("engineer");
  const res = await fetch(`${base}/api/lg/assistants/search`, {
    method: "POST",
    headers: { "content-type": "application/json", cookie },
    body: JSON.stringify({ limit: 5 }),
  });
  assert.equal(res.status, 200);
  const found = await res.json();
  assert.ok(
    found.some((a) => a.name === "role-aware-docs-assistant"),
    "the canonical assistant was not reachable through the proxy",
  );
});

test("the proxy costs one hop, not two", LIVE, async () => {
  const { cookie } = await pick("engineer");
  const direct = Date.now();
  await fetch(`${ENV.MDA_API_URL}/assistants/search`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-api-key": ENV.LANGSMITH_API_KEY },
    body: JSON.stringify({ limit: 5 }),
  });
  const directMs = Date.now() - direct;

  const viaStart = Date.now();
  await fetch(`${base}/api/lg/assistants/search`, {
    method: "POST",
    headers: { "content-type": "application/json", cookie },
    body: JSON.stringify({ limit: 5 }),
  });
  const viaMs = Date.now() - viaStart;

  console.log(`    direct ${directMs}ms · via proxy ${viaMs}ms · overhead ${viaMs - directMs}ms`);
  // Measured, not assumed. Generous because a conference network is not a lab.
  assert.ok(viaMs < directMs + 1500, `proxy added ${viaMs - directMs}ms`);
});

// --- §6: compare mode relaxes the boundary, and only when switched on ------

test(
  "the compare-mode header is IGNORED unless DEMO_COMPARE_MODE is on",
  LIVE,
  async () => {
    if (ENV.DEMO_COMPARE_MODE === "true" || process.env.DEMO_COMPARE_MODE === "true") {
      console.log("    compare mode is ON for this server — see the next test");
      return;
    }
    const { cookie } = await pick("employee");
    const thread = await newThread(cookie);
    const res = await fetch(`${base}/api/lg/threads/${thread}/runs/wait`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        cookie,
        // Compare mode's own header, sent by a client that should not have it.
        "x-demo-role": "engineer",
      },
      body: JSON.stringify({
        assistant_id: "role-aware-docs-assistant",
        input: { messages: [{ type: "human", content: ENGINEERING_ONLY }] },
      }),
    });
    assert.equal(res.status, 200);
    const state = await res.json();
    assert.ok(!state.__error__, `run died: ${JSON.stringify(state.__error__)}`);
    const used = corporaUsed(state);
    assert.ok(
      !used.has("engineeringDocs"),
      `the header was honoured with compare mode OFF — reached ${[...used].join(", ")}`,
    );
  },
);

// --- the page renders the things the demo depends on -----------------------

test("the page shows the mechanism, not just a chat box", { skip }, async () => {
  const { cookie } = await pick("employee");
  const html = await (await fetch(base, { headers: { cookie } })).text();

  // C5: the simulated-identity label, always, without scrolling.
  assert.match(html, /Simulated identity/i, "no simulated-identity banner");

  // The ✗ row — the only place the ENFORCED difference is visible before a
  // question is asked. The employee must have exactly one.
  //
  // Counted as rendered <li> elements, NOT as occurrences of "✗": the RSC
  // flight payload at the bottom of the document repeats the whole tree as
  // serialized JSON, so every glyph appears twice and a naive count is
  // always double. Matching the element is both exact and what the audience
  // actually sees.
  const withheldRows = (html.match(/<li class="withheld"/g) ?? []).length;
  assert.equal(withheldRows, 1, `employee should show exactly one ✗ row, saw ${withheldRows}`);
  assert.match(html, /internal engineering runbooks/i, "the withheld corpus is unnamed");
  assert.match(html, /no tool/i, "the ✗ row does not say why");

  // …and the engineer must have none.
  const { cookie: engCookie } = await pick("engineer");
  const engHtml = await (await fetch(base, { headers: { cookie: engCookie } })).text();
  const engWithheld = (engHtml.match(/<li class="withheld"/g) ?? []).length;
  assert.equal(engWithheld, 0, `engineer should show no ✗ row, saw ${engWithheld}`);

  // If both panels looked the same, nesting would have been rendered as if
  // it were disjoint and the UI would be lying about which half is enforced.
  assert.notEqual(withheldRows, engWithheld);

  // Nesting rendered as nesting: the engineer's list is ordered 1..2.
  assert.match(engHtml, /preferred/i, "the engineer's preference is not shown");
});

test("the demo script is on screen as one-click chips", { skip }, async () => {
  const { cookie } = await pick("engineer");
  const html = await (await fetch(base, { headers: { cookie } })).text();
  for (const q of [
    "Do we require retry middleware on model calls?",
    "What is our on-call escalation path?",
  ]) {
    assert.ok(html.includes(q), `missing suggestion: ${q}`);
  }
});

test("the UI reports the same build the agent does", { skip }, async () => {
  // One value, `agent/contracts/version.py`, reaching the UI through
  // grants.json and the trace through define_deep_agent(metadata=…). They
  // drifted once: the v4 -> v5 bump left grants.json stale, so the UI would
  // have shown v4 for a v5 deployment. Nothing else would have noticed.
  const { readFileSync } = await import("node:fs");
  const grants = JSON.parse(
    readFileSync(new URL("../../agent/contracts/grants.json", import.meta.url), "utf8"),
  );
  const { cookie } = await pick("engineer");
  const html = await (await fetch(base, { headers: { cookie } })).text();
  assert.ok(
    html.includes(grants.demo_version),
    `the page does not show ${grants.demo_version}`,
  );
});
