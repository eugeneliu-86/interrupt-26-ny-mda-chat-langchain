/**
 * Same-origin passthrough to the MDA Agent Server (ph. 06 §1, §2).
 *
 * Two jobs, and the second is the architecture:
 *
 *   1. attach `x-api-key` server-side, so the key never reaches a browser;
 *   2. OVERWRITE `context` on run-create bodies from the identity cookie.
 *
 * "Overwrite" is exact. Not merge, not default, not trust-if-absent. A client
 * that posts its own `context` has it replaced. If the browser could
 * contribute any part of the role, the role would be a value the browser
 * sets, and the demo's best sentence — *swap the dropdown for a verified JWT
 * claim and nothing downstream changes* — would be false.
 *
 * WHY THIS IS HAND-WRITTEN rather than `langgraph-nextjs-api-passthrough`.
 * The entire purpose of this route is to rewrite the body. A generic
 * passthrough forwards it untouched, which would hand the browser control of
 * the role — the one thing this file exists to prevent.
 */
import { GRANTS, isRole } from "@/lib/grants";
import { RUN_CREATE } from "@/lib/runCreate";
import { readIdentity } from "@/lib/identity";

// Streaming an SSE body through requires the Node runtime here. Chosen, not
// inherited: buffering the stream turns a live-feeling demo into a ten-second
// pause followed by a wall of text.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";


type Ctx = { params: Promise<{ _path: string[] }> };

/**
 * The header compare mode uses to pin a pane to one role (§6).
 *
 * THIS WEAKENS RULE 2 ON PURPOSE, AND ONLY WHEN TURNED ON. Normally the
 * cookie is the sole source of the role and the browser cannot influence it.
 * Compare mode needs two roles in flight from one page, so it sends this
 * header and the server validates it against the closed set in
 * `grants.json` — a client-chosen role, but only ever one of the two the
 * page is already displaying side by side.
 *
 * It is therefore OFF unless `DEMO_COMPARE_MODE=true`, so the default build
 * keeps the strict property that §1's acceptance test checks: a hand-crafted
 * request cannot change who it runs as. Do not turn this on and then claim
 * the browser has no say in the role.
 */
const ROLE_HEADER = "x-demo-role";
export const compareModeEnabled = () => process.env.DEMO_COMPARE_MODE === "true";

function upstream(): string {
  const base = process.env.MDA_API_URL;
  if (!base) throw new Error("MDA_API_URL is not set — see ui/.env.example");
  return base.replace(/\/$/, "");
}

function key(): string {
  const k = process.env.LANGSMITH_API_KEY;
  if (!k) throw new Error("LANGSMITH_API_KEY is not set — see ui/.env.example");
  return k;
}

async function forward(req: Request, ctx: Ctx, rewriteBody: boolean) {
  const { _path } = await ctx.params;
  const path = "/" + _path.join("/");
  const search = new URL(req.url).search;

  let base: string;
  let apiKey: string;
  try {
    base = upstream();
    apiKey = key();
  } catch (e) {
    // A missing env var must say so, not 500 into a blank screen (§7).
    return Response.json({ error: (e as Error).message }, { status: 500 });
  }

  const headers: Record<string, string> = { "x-api-key": apiKey };
  let body: string | undefined;

  if (req.method !== "GET" && req.method !== "DELETE") {
    body = await req.text();
    headers["content-type"] = "application/json";
  }

  if (rewriteBody && RUN_CREATE.test(path)) {
    const identity = await readIdentity();

    // Compare mode: a per-request role, validated here against the emitted
    // set. An unknown value is IGNORED rather than honoured, so a bad header
    // degrades to the cookie instead of running as something unexpected.
    const asked = req.headers.get(ROLE_HEADER);
    const pinned = compareModeEnabled() && isRole(asked) ? asked : null;

    if (!pinned && (!identity || !isRole(identity.role))) {
      // Refuse BEFORE the deployment. The agent would also refuse (C1), but
      // this message can say what to do about it and costs no model call.
      return Response.json(
        { error: "no identity selected — pick one before asking a question" },
        { status: 400 },
      );
    }
    let parsed: Record<string, unknown>;
    try {
      parsed = body ? (JSON.parse(body) as Record<string, unknown>) : {};
    } catch {
      return Response.json({ error: "run body was not JSON" }, { status: 400 });
    }
    // THE OVERWRITE. Whatever the client sent is discarded.
    const role = pinned ?? identity!.role;
    const displayName = pinned ? GRANTS[pinned].label : identity!.displayName;
    parsed.context = { role, display_name: displayName };
    parsed.metadata = {
      ...(parsed.metadata as Record<string, unknown> | undefined),
      ui: pinned ? "interrupt-26-demo-compare" : "interrupt-26-demo",
    };
    body = JSON.stringify(parsed);
  }

  const res = await fetch(base + path + search, {
    method: req.method,
    headers,
    body,
    // Node's fetch refuses a streaming request body without this; harmless
    // for the buffered bodies used here, and required if one ever streams.
    // @ts-expect-error -- `duplex` is not in the DOM lib types yet.
    duplex: "half",
  });

  // Return the upstream body UNBUFFERED. `res.body` is a ReadableStream, and
  // passing it straight through is what makes tokens appear progressively.
  const out = new Headers();
  for (const h of ["content-type", "cache-control", "transfer-encoding"]) {
    const v = res.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(res.body, { status: res.status, headers: out });
}

export const GET = (req: Request, ctx: Ctx) => forward(req, ctx, false);
export const POST = (req: Request, ctx: Ctx) => forward(req, ctx, true);
export const PUT = (req: Request, ctx: Ctx) => forward(req, ctx, true);
export const PATCH = (req: Request, ctx: Ctx) => forward(req, ctx, true);
export const DELETE = (req: Request, ctx: Ctx) => forward(req, ctx, false);
