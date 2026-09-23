# Role-aware documentation assistant — UI

**You only need this directory.** The agent is already deployed and shared;
this is a local client that points at it. You are not deploying anything.

```bash
cp .env.example .env.local     # paste YOUR LangSmith key into it
pnpm install
pnpm dev                       # → http://localhost:3000
```

Your key must be issued in the shared **Demo Workspace**
(`a3866f07-2cf5-4e9c-a287-59ed817c2ecd`). A key from a different workspace
returns 403, which reads like a broken URL rather than a wrong key.

Full context, the demo script, and what not to say on stage:
[`../docs/DE-onboarding.md`](../docs/DE-onboarding.md).

---

## The identity is simulated

Nobody logs in. There is no authentication and no authorization in this demo.
A person picks a name from a menu, the server writes it into an httpOnly
cookie, and the server injects it into the run. The screen says so
permanently, and so should you.

What *is* real is the provenance: the role is established server-side and the
browser cannot set it. Swapping the cookie for a verified JWT claim would
change nothing downstream — which is the point of the arrangement, and is
only true because of the overwrite described below.

## Threads are shared

Everyone runs their own UI against **one** deployment. Threads are per
browser, so you will not see anyone else's conversation, but you share the
deployment's rate limits, and every run lands in the same LangSmith project.

---

## How it fits together

```text
browser                    Next.js server                  MDA deployment
───────                    ──────────────                  ──────────────
pick identity ──POST /api/identity──→ httpOnly cookie
                                        role = "engineer"

useStream ──────/api/lg/** ─────────→ proxy route
  (no key, no context)                  + x-api-key         ──→ /threads/…/runs/stream
                                        + context OVERWRITTEN
                                          from the cookie
```

Two rules hold this up:

1. **The LangSmith key never reaches the browser.** No `NEXT_PUBLIC_` prefix,
   no client component reads it. `pnpm check` asserts this against the built
   output, not the source.
2. **The proxy overwrites `context`. It does not merge and it does not
   trust.** A client that sends its own `context` has it replaced. There is a
   test for exactly this, and it is the most important test here.

## Layout

```text
app/
  page.tsx                     server component: reads the cookie, renders the rails
  api/identity/route.ts        the only writer of the identity cookie
  api/lg/[..._path]/route.ts   the proxy — the trust boundary lives here
components/
  IdentityPicker.tsx           choose who is asking; switching clears the thread
  GrantsPanel.tsx              the ordered list and the ✗ row
  Console.tsx                  useStream, pointed at /api/lg
  Compare.tsx                  both identities side by side (opt-in, see below)
  Transcript.tsx               messages, tool-call chips, error rows
lib/
  grants.ts                    reads ../agent/contracts/grants.json — the single source
  identity.ts                  cookie read/write
  content.ts                   content blocks, tool-call args, dead-run detection
  runCreate.ts                 which paths start a run (shared with the test)
```

### Nothing here decides a grant

`lib/grants.ts` imports `../agent/contracts/grants.json`, which is generated
from `agent/contracts/grants.py`. No role name, corpus name, or grant list is
written in `ui/`. If this UI and the agent ever disagreed about who can reach
what, the screen would be lying about a deployment whose traces are in the
room.

Regenerate after changing the agent's grants:

```bash
cd ../agent && uv run python -m contracts.emit_grants_json
```

---

## Compare mode (opt-in)

```bash
echo 'DEMO_COMPARE_MODE=true' >> .env.local
```

Adds a **Side by side** view: one question, both identities, two threads, two
traces.

It is off by default because it **relaxes rule 2**. Each pane pins its role
with an `x-demo-role` header, which the server validates against the closed
set in `grants.json` — so the browser chooses the role for that request. That
is acceptable only because the page is already displaying both roles at once,
and it means the strict property ("a client cannot change who it runs as")
holds in the default build and not in this one. Don't enable it and then
claim otherwise.

An unrecognised header value is ignored rather than honoured, so a bad header
falls back to the cookie instead of running as something unexpected.

---

## Tests

```bash
node --test tests/                 # offline: the run-create shapes
pnpm build && pnpm check           # no key, no deployment URL in any chunk
PROXY_TEST_BASE=http://127.0.0.1:3000 node --test tests/   # live, needs a running server
```

The live suite makes real runs against the deployment. It is skipped unless
`.env.local` is configured. Point `PROXY_TEST_BASE` at a server you already
have running, or omit it and the suite starts its own.

## Three things that will waste your afternoon

- **An empty assistant bubble.** `gpt-5.6-luna` returns `content` as a list of
  blocks — `reasoning`, `function_call`, then `text`. Reading it as a string
  gives `""`, which renders as an empty bubble and reads as "the agent said
  nothing" rather than as a parsing bug. `lib/content.ts` handles it.
- **A dead run answers HTTP 200.** `/runs/wait` returns `{"__error__": …}`
  with no messages when a run dies. Checking the status code is not enough.
- **`pkill -f "next start"` does not stop the server.** Next renames its
  process to `next-server (v16.x)` once it is up, so the pattern misses and
  you go on testing against a build from an hour ago. This cost real time
  during the build — a rebuilt page kept reporting the previous
  `demo_version` and the tests agreed with it. Use
  `lsof -ti:3000 | xargs kill -9`, or `pkill -f next-server`.
