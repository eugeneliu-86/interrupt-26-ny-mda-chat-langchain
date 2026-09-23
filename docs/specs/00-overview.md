# Phase 00 — Overview and Contracts

> **Status:** draft · **Depends on:** nothing · **Owns:** the invariants every
> other phase is measured against.
>
> One canonical Managed Deep Agent in the shared Demo workspace answers
> documentation questions. Two simulated identities — `engineer` and
> `employee` — ask the *same question* and get *different correct answers*,
> because middleware deterministically exposes a different tool surface to each.

## The one-sentence demo

> Ask **"Do we require retry middleware on model calls?"**
>
> as **employee** → *"**No.** The public documentation does not state that
> retry middleware is required. It is one possible use case, not a
> requirement — so it is optional unless your own application needs it."*
> (cites `middleware.md`)
>
> as **engineer** → *"**Yes.** Retry middleware is required on every model
> call. Providers return 429s under normal operation, so calls without retries
> treat routine back-pressure as an outage. Calling a model in a tight loop
> without retries is explicitly forbidden."* (cites
> `resilience-standards.md`)
>
> Same deployment, same thread API, same instructions, same model. **Opposite
> answers**, both correct for their reader — because the run carried a
> different role.

Verified live on the deployment, one side at a time, before phase 03 existed.

Both answers are correct. The employee **cannot** produce the engineer's
answer: the internal runbooks are not in its tool surface, and their content
exists nowhere public. The engineer could answer from the product docs but is
told to prefer the runbooks, so it answers from them.

A flat contradiction is the best possible shape for this demo — "No, optional"
against "Yes, required" needs no explanation from the stage, and it resolves
the moment the audience is told who was asking.

The difference is structural in one direction and preferential in the other —
and the demo says which is which (C2).

## What this build proves

| Claim | Proven by | Phase |
|---|---|---|
| Instructions and skills are managed centrally and injected at runtime | `instructions.md` + `skills/` live in Context Hub; editing the Hub copy changes agent behaviour | 01 |
| Tools stay in code; credentials are managed centrally and resolved at runtime | one `mda connection`, resolved by slug per run — no key in the repo, and rotation needs no redeploy | 02, 05 |
| One deployed agent exposes different tool surfaces per caller context | `wrap_model_call` filters `request.tools` from `runtime.context.role` | 03 |
| Traces show which tools and connections were available and invoked per role | run metadata carries role + granted prefixes; denials appear as tool messages | 03, 05 |
| A DE clones only the UI | UI reads `MDA_API_URL` + their own `LANGSMITH_API_KEY`; no agent code | 06 |

## Phase graph

```text
01 context-hub ──┬─→ 02 tools-and-corpora ──┐
                 │        (needs bootstrap  │
                 │         deploy, §7)      │
                 └─→ 03 identity-middleware ─┴─→ 04 agent-wiring ─→ 05 deploy ─→ 06 ui
```

01 and 03 are independent of each other and can be built in parallel. 02 has a
hard ordering dependency on a deploy existing (§7). 04 is pure assembly: if 01,
02 and 03 met their acceptance criteria, 04 is wiring plus one end-to-end test.

**Before any of it**, run the five gates in
[01-context-hub.md](./01-context-hub.md) — MDA beta access, shared-workspace
access, LLM Gateway with an OpenAI provider secret, the `mda init` model
string, and a hosting account for phase 02. All five are admin- or
account-side, so none can be fixed by changing code, and G3 in particular fails
*late* if skipped: the deploy succeeds and the first model call 402s.

| Phase | File | Delivers |
|---|---|---|
| 01 | [01-context-hub.md](./01-context-hub.md) | project scaffold, `contracts/`, `instructions.md`, `skills/`, Context Hub repo, bootstrap deploy |
| 02 | [02-tools-and-corpora.md](./02-tools-and-corpora.md) | two Context Hub corpora, one connection, four authored tools |
| 03 | [03-identity-and-middleware.md](./03-identity-and-middleware.md) | role context, grant table, three-layer gating middleware |
| 04 | [04-agent-wiring.md](./04-agent-wiring.md) | the assembled MDA project, end-to-end local run |
| 05 | [05-deploy.md](./05-deploy.md) | canonical deployment, trace contract, DE onboarding |
| 06 | [06-ui.md](./06-ui.md) | cloneable Next.js UI with the identity selector |

---

## 1 · Primer — the five facts that shape this design

**1 · An MDA project is a directory.** File *location* determines role:
`instructions.md` is the system prompt, `tools/mcp.py` declares MCP servers,
`middleware/` holds application code, `identity.py` turns on caller
authentication. There is no central config file listing capabilities.

**2 · `instructions.md` and `skills/` are the only things that sync to Context
Hub.** Tools, middleware, MCP declarations, channels and the agent definition
ship with the compiled build. Consequence for this demo: **there is no
per-role instruction set.** Role differentiation has to come from tools.

**3 · `define_deep_agent()` accepts `context_schema`.** The published docs
parameter table omits it; the wheel has it
(`managed_deepagents 0.7.1.dev5`, `define_deep_agent.py:65`). This is the hinge
of the whole design — see C3.

**4 · Authored tools are a static list, identical on every run.** MDA does not
discover tools — they are imported and passed as `tools=`. So all four docs
tools are in the agent's list for every caller, and the *only* thing that
varies per caller is what middleware leaves in `request.tools`. Gating is a
middleware responsibility, full stop.

**5 · An authored tool resolves its connection per run.**
`connections.get(...)` returns a lazy reference that must be awaited inside a
run, and the credential is read on each call. So rotating or revoking the key
in the workspace changes behaviour on the next run, with no redeploy. (MCP
connectors behave oppositely — the wheel caches an agent-owned connection as a
static bearer header for the process lifetime,
`_connectors/mcp/load.py:51-62` — but this build uses no MCP connectors.)

### Where this design is honest and where it is costume

The **mechanism** is real: real MCP servers, real credentials in the LangSmith
workspace, real deterministic middleware gating, real traces.

The **identity** is simulated. The role is a string chosen from a dropdown. It
is not authenticated, and the demo must say so on screen (C5).

The **content sensitivity is now real**, which earlier drafts could not claim.
The engineering corpus is a private Context Hub repo behind a service key: the
employee's tools cannot read it, and nobody without the key can. It is
*invented* content — a fictional internal environment, so nothing genuine
leaks — but its inaccessibility is not staged.

So: mechanism real, content boundary real, **identity simulated**. That is the
one thing to keep saying, and never present this as an access-control product.

---

## 2 · Glossary

| Term | Means here |
|---|---|
| **MDA** | Managed Deep Agents — the LangSmith-hosted Deep Agents runtime |
| **canonical deployment** | The single MDA deployment in the shared Demo workspace that every DE points at |
| **role** | One of the two strings in C1. Not a LangSmith concept; ours |
| **corpus** | One of three path-scoped slices of `docs.langchain.com` |
| **corpus repo** | The private Context Hub repo holding one corpus: `product-docs` or `engineering-runbooks` |
| **snapshot** | One `pull_agent` result — a `commit_hash` plus `{path: content}` for every file in a corpus repo |
| **grant** | The role → corpus mapping in C2 |
| **primary order** | The role → preferred-corpus ordering in C2. Shapes answers; gates nothing |
| **prefix** | The `{serverName}__` string MDA prepends to each MCP tool name |
| **DE** | Design Engineer / Demo Engineer — the person who clones the UI and presents |

---

## 3 · Contracts

Contracts are numbered and referenced by number from every phase. A phase that
violates a contract is not done, however well it demos.

### C1 · The role vocabulary is closed, and absence is a hard failure

```python
# contracts/roles.py
from typing import Literal, get_args

Role = Literal["engineer", "employee"]
ROLES: tuple[str, ...] = get_args(Role)
```

Exactly two values. No `admin`, no `public`, no `guest`.

**A run whose `context.role` is missing or not in `ROLES` is rejected before
the first model call**, with a message naming the allowed values. It does not
silently downgrade to a least-privilege surface.

The reasoning: a silent downgrade is the wrong lesson to teach from a stage. If
a caller does not declare a role, the honest behaviour is to refuse, and the
refusal is visible in the trace. The UI always sets a role (C5), so this path
only fires for a raw `curl` — which is exactly when you want it to fire.

#### Acceptance criteria

- [x] `contracts/roles.py` is the only place the two role strings are written
      as literals — `contracts/check-contracts.sh`, *"role literals only in
      contracts/ and tests/"*.
- [x] A run with no `context` fails with *"this deployment requires
      context.role; expected engineer or employee"* and makes no model call —
      verified against the deployment, and confirmed in the trace (no LLM
      span at all).
- [x] A run with `context.role = "admin"` fails the same way: *"unknown role
      'admin'; expected one of employee, engineer"*.
- [x] The failure is a run error in the trace, not a normal answer. **One
      wrinkle worth knowing:** MDA mirrors the context it was given *before*
      C1 rejects, so a run sent with `role: "admin"` still shows
      `metadata.role = "admin"`. It looks like a leak and is not — the run
      died with no model call. Recorded in `docs/DE-onboarding.md` §6.

### C2 · One grant table, imported everywhere, written nowhere else

```python
# contracts/grants.py
from contracts.roles import Role

#: corpus prefix → (Context Hub repo, connection slug). The single table of
#: what exists. Both corpora are read with one workspace service key, because
#: Context Hub access is workspace-level, not per-repo (ph. 02 §1.3).
CORPORA: dict[str, tuple[str, str]] = {
    "productDocs":     ("product-docs",         "context-hub-corpus"),
    "engineeringDocs": ("engineering-runbooks", "context-hub-corpus"),
}

#: role → the tool-name prefixes that role may call.
#: NESTED: employee's grant is a strict subset of engineer's.
GRANTS: dict[Role, frozenset[str]] = {
    "engineer": frozenset({"productDocs", "engineeringDocs"}),
    "employee": frozenset({"productDocs"}),
}

#: role → corpora it should treat as authoritative, most specific first.
#: This shapes the ANSWER; it does not gate anything. See "Preference is not
#: enforcement" below.
PRIMARY_ORDER: dict[Role, tuple[str, ...]] = {
    "engineer": ("engineeringDocs", "productDocs"),
    "employee": ("productDocs",),
}
```

**The grants are nested: `employee` ⊂ `engineer`.** An engineer can reach
everything an employee can, plus the internal runbooks. This models a real
organization, where seniority accretes access rather than swapping it.

Nesting has one consequence that shapes the whole demo, and it must be designed
around rather than discovered on stage:

> **The asymmetry is one-directional.** There is no question the employee can
> answer that the engineer cannot. So "same question, different answers" cannot
> come from the employee reaching a corpus the engineer lacks — it has to come
> from the engineer reaching one the employee lacks, and from each role
> *preferring* the most specific corpus it has.

That gives the demo two beats rather than one symmetric pair:

| Beat | Question | employee | engineer |
|---|---|---|---|
| **1 · same question, different answers** | *"Do we require retry middleware on model calls?"* — covered by both corpora | **"No"** — the public docs list retries as one use of middleware, not a requirement | **"Yes, on every model call"** — the team standard, with the reason |
| **2 · refusal** | *"What is our on-call escalation path?"* — only the internal runbooks cover it | refuses, names what it has | answers |

Beat 2 is now the load-bearing one: it is the only place the difference is
*enforced*. Beat 1 is real but softer — see below.

### Preference is not enforcement

`PRIMARY_ORDER` is injected into the prompt (C8) so each role answers from the
most specific corpus it holds. That is **instruction, not enforcement.** With
nested grants the engineer *can* read Fleet docs, and on some questions it will
legitimately cite both.

Say so plainly when demoing beat 1: *"both identities can read the public and
employee docs; the engineer also has the runbooks and is told to prefer them."*
Do not claim beat 1 is enforced — beat 2 is what enforcement looks like, and
conflating them is the one way this demo can be fairly called misleading.

`productDocs` is shared, which is what makes the *same question* land for
both.

`contracts/` also holds `version.py` (`DEMO_VERSION`, C9) and
`emit_grants_json.py`, which writes a committed `contracts/grants.json` for the
UI to read (ph. 06 §4). Python stays the source of truth; the JSON is a
generated projection, checked in CI to be in sync. Nothing reads the mapping
from a second hand-written copy.

#### Acceptance criteria

- [x] Everything that needs the mapping imports `contracts.grants` —
      `check-contracts.sh`, *"corpus prefixes only in contracts/, tools/,
      middleware/, tests/"*. The UI reads the generated `grants.json` and
      nothing else.
- [x] `set(GRANTS) == set(ROLES)` is asserted at import time.
- [x] Asserted at import time — though **`CONNECTION_SLUGS` no longer
      exists**. Both corpora share one connection (Context Hub access is
      workspace-level, not per-repo), so the table became `CORPORA`, mapping
      prefix → (repo, slug). The check is `_prefixes <= set(CORPORA)`, which
      is the same guarantee under the name the code actually uses.
- [x] `GRANTS["employee"] < GRANTS["engineer"]` — strict subset, asserted at
      import. If the two were ever equal every other assertion here would
      still pass while the demo had silently stopped demonstrating anything,
      which is why the strictness is the assertion rather than a comment.
- [x] `"engineeringDocs" not in GRANTS["employee"]` — asserted at import and
      again in `tests/test_role_gate.py`, and again as a row of the
      deployment matrix.
- [x] `set(PRIMARY_ORDER[r]) == GRANTS[r]` for every role, asserted at
      import.
- [x] Every value in `GRANTS` is a subset of `set(CORPORA)`, asserted at
      import.
- [x] `CORPORA` is the only place a repo name or connection slug is written
      — `check-contracts.sh`, *"repo handles only in contracts/grants.py"*.
- [x] No role→tool mapping in `instructions.md`, in any skill, or in the UI
      — three separate contract checks, plus `lib/grants.ts` being the UI's
      only reader of the generated projection.

### C3 · The role arrives as run context, typed, and nowhere else

```python
# context_schema.py
from dataclasses import dataclass
from contracts.roles import Role

@dataclass
class RequestContext:
    """Per-run context set by the UI's server route. Carries no content."""
    role: Role
    display_name: str          # "Lang (Engineer)" — for the trace, not for auth
    demo_version: str          # C9
```

Passed as the top-level `context` field on run create:

```json
{
  "assistant_id": "role-aware-docs-assistant",
  "input": {"messages": [{"role": "user", "content": "..."}]},
  "context": {"role": "engineer", "display_name": "Lang (Engineer)",
              "demo_version": "v1"},
  "stream_mode": ["messages-tuple", "updates"]
}
```

**This path is proven, not assumed.** `RunCreate` carries `context` in both
SDKs (`langgraph_sdk/schema.py:535`; `@langchain/langgraph-sdk` `types.ts:68`,
"added in LangGraph.js 0.4"), the React `useStream().submit(input, {context})`
forwards it (`react/stream.lgp.tsx:580`), LangGraph passes context through
unchanged when no schema is declared (`pregel/main.py:4355`), and a sibling
project already runs this shape against a deployed MDA over HTTP.

The role must **not** reach the agent any other way:

- not appended to the user message,
- not in `metadata` as the authority (metadata carries a *copy* for trace
  filtering — see C9 — but middleware reads `runtime.context`),
- not inferred from the LangSmith API key,
- not stored on the thread.

The reason is that every alternative is a path a model can influence. Context
is the only channel the model cannot write to.

#### Acceptance criteria

- [x] `runtime.context.role` is readable inside middleware in a deployed run,
      not only under `mda dev`.
- [x] `grep -rn 'role' instructions.md skills/` returns nothing that *sets* a
      role; only text about roles in general.
- [x] No tool takes a `role` parameter — `check-contracts.sh`, *"no tool
      parameter named role/identity/corpus"*. The corpus is closed over by
      the tool factory, so it is not addressable by the model at all.
- [x] Changing the role in the run body, with the message byte-identical,
      changes the tool surface. This is the phase 04 end-to-end test.

### C4 · Every corpus is a closed scope, structurally

Two corpora, each a private Context Hub repo. Each tool **closes over exactly
one repo name**, which is never a parameter.

| Prefix | Context Hub repo | Content | Provenance |
|---|---|---|---|
| `productDocs` | `product-docs` | Public LangChain product documentation | curated copy of `docs.langchain.com` |
| `engineeringDocs` | `engineering-runbooks` | Internal runbooks — deploy, on-call, break-glass, environments | **invented** (ph. 02 §3) |

Phase 02 owns the page lists and the corpus contents.

Enforcement is structural rather than a check that could be got wrong:

- **The repo is not in the tool's input surface.** A tool cannot be asked for
  another corpus — not by the model, not by a crafted path, not by prompt
  injection.
- **Path traversal is meaningless.** Paths are keys in a pulled dict, not
  filesystem or URL paths.
- **For the engineering corpus the credential is a second boundary**: without
  the service key the content is unreadable at all.

> The engineering corpus is **invented, not mirrored** — a fictional internal
> environment. That is both a leak constraint and the thing that makes the
> refusal real: content that exists nowhere public cannot be reached from the
> shared corpus, however broad it is.

#### Acceptance criteria

- [x] The repo appears in `agent/tools/corpus.py` only as a factory argument,
      never as a tool parameter or a value read from tool input.
- [x] `engineeringDocs__fetch_doc("../product-docs/index.md")` returns
      "not found in this corpus" — a missing key, not a traversal.
- [x] For every engineering page, the same question against `productDocs`
      returns nothing above `MIN_SCORE`. This is the mechanical check that beat
      2 exists.
- [ ] **No page of the engineering corpus names a real system, procedure, or
      person.** *Needs a human read.* The 12 pages were written to be
      fictional — team **Platform Agents**, `PLAT-` tickets, `agent-checks`
      CI, a `deploy-agents` pipeline, `dev`/`staging`/`prod-us`/`prod-eu`, a
      secret store called **Keyring**, the `platform-agents-oncall` rotation
      and `#platform-agents-releases` — but the author of an invention is the
      worst person to audit it for accidental resemblance, and this is the
      criterion protecting the one constraint that cannot be walked back once
      the demo is recorded. Original: no page of the engineering corpus names
      a real system, procedure, or
      person (ph. 02 §3).
- [x] Each tool's description names its own corpus and does not reveal the
      other's existence.

### C5 · The simulation is labelled, and the role is set server-side

Two separate obligations.

**Labelled.** The identity selector is visibly a demo control: the words
"Simulated identity — not authenticated" (or equivalent) are on screen next to
it, and the README says the same. Someone screenshotting the UI must not be
able to present it as an access-control feature.

**Server-side.** The browser never talks to the deployment and never sets
`context` itself. The Next.js route handler injects `RequestContext` from the
selected identity held in a server-side session. The architecture therefore
mirrors a real deployment — swap the dropdown for Supabase and the trust
boundary does not move.

```text
browser  ──POST /api/chat {question, identity}──→  Next.js route (server)
                                                    ├─ holds LANGSMITH_API_KEY
                                                    ├─ builds RequestContext
                                                    └─→ POST {MDA}/threads/{t}/runs/stream
```

#### Acceptance criteria

- [x] `LANGSMITH_API_KEY` is read only by the proxy route, asserted by
      `ui/scripts/check-no-secrets.mjs` against the **built output** as well
      as the source. Original: `grep -rn 'LANGSMITH_API_KEY' ui/` shows it
      read only in server code
      (route handlers / server actions), never in a client component and never
      prefixed `NEXT_PUBLIC_`.
- [x] Every script the page loads is same-origin, and no served chunk
      contains the key or the deployment URL — asserted by fetching each
      `<script src>` and scanning it, rather than by reading a network tab.
- [x] The simulated-identity label is in the UI (sticky, unconditional,
      asserted in a test) and in `ui/README.md` in its own section.
- [x] A curl against the deployment with a wrong role is rejected (C1) — so the
      server route is the only thing that constructs a valid role, by
      construction rather than by trust.

### C6 · Gating is two layers, and the denial is visible

Both layers read `contracts.grants`.

1. **`wrap_model_call`** replaces `request.tools` with only the granted tools
   (`ModelRequest.override(tools=...)`,
   `langchain/agents/middleware/types.py:203`). The model never sees an
   ungranted tool, so it never tries to call one, so the happy path is clean.
2. **`wrap_tool_call`** refuses a call to an ungranted tool by name and returns
   a `ToolMessage` saying so. Nothing should ever reach it in the demo. It
   exists so that a leak is a visible denial in the trace instead of a silent
   success.

The second layer is what you point at when someone asks "but what enforces it?"

#### Acceptance criteria

- [x] With `role="employee"`, the model's tool list in the trace contains no
      `engineeringDocs__*` tool.
- [x] A synthetic test that injects an `engineeringDocs__*` tool call into an
      employee run gets a refusal `ToolMessage` and no upstream HTTP request.
- [x] Layer 2 does not fire in a normal demo run — a row of the deployment
      matrix counts `Access denied` tool messages across all nine runs and
      asserts zero. Original: assert its counter is zero
      across the scripted flow.
- [x] Both layers derive the allowed set from `contracts.grants`, not from a
      literal list.

### C7 · The agent tells the truth about what it can reach

Asked "what can you access?", the agent answers from its **actual tool list**,
not from `instructions.md`. Asked something only the other role can answer, it
says it does not have access to that documentation and names what it does have
— without describing the other role's corpus in detail.

This is the sentence that makes the demo land, so it is a contract and not a
nicety.

#### Acceptance criteria

- [x] Verified live. As `employee` it answers *"I can search public LangChain
      product documentation only"* and never mentions the runbooks; as
      `engineer` it lists both, in priority order. Original: as `employee`,
      "what documentation can you search?" names the public and
      employee corpora and does not name the engineering one as available.
- [x] As `employee`, an engineering-only question produces a refusal plus a
      pointer to what it *can* do, and no fabricated answer from parametric
      knowledge.
- [x] The two answers differ in corpus, not only in wording — verified by
      comparing the tool calls in the two traces, not by reading the prose.
- [x] Neither role's answer leaks the other's contents, and neither does the
      **prompt**: the employee's injected "Granted access" section names only
      the public corpus, so the model is never told the runbooks exist. Read
      out of the trace, both roles.

### C8 · Instructions and skills are global; role text is injected

One `instructions.md` for both roles. No `skills/engineer/`, no
`skills/employee/`. Middleware appends a short, generated system-message
section naming the granted corpora and the refusal rule.

The reason is mechanical: Context Hub holds one instruction set per deployment
(§1 fact 2), and two deployments would defeat the "same deployed agent" claim.

#### Acceptance criteria

- [x] `skills/` contains no role name in any directory name —
      `check-contracts.sh`.
- [x] `instructions.md` contains no per-role branching and no tool-name list
      — `check-contracts.sh`.
- [x] Verified by reading both system messages out of the traces: the
      employee's lists one corpus, the engineer's lists two in order, and the
      messages differ. Original: the injected section is visible in the
      trace's system message and differs
      between the two roles.
- [x] Proven in ph. 01 §8 — a Hub-only edit changed deployed behaviour on a
      fresh thread with no redeploy and no restart. Original: editing
      `instructions.md` in the Context Hub UI changes deployed
      behaviour with no redeploy — the phase 01 acceptance test.

### C9 · Trace contract — a trace answers the demo's questions without code

Every root run carries, in `metadata`:

```python
{"demo": "role-aware-docs", "demo_version": "v4",        # static, from the build
 "role": "engineer", "display_name": "Lang · Engineer"}  # mirrored from context
```

**Both halves arrive without middleware**, which took two corrections to learn:

| Keys | Mechanism |
|---|---|
| `demo`, `demo_version` | `define_deep_agent(metadata=...)`, applied to the **root** run. Says which *build* answered |
| `role`, `display_name` | **MDA mirrors every run-context field into root-run metadata.** Nothing of ours writes them |

#### Two claims measurement disproved

**1 · A metadata middleware is unnecessary, and could not have worked.** An
earlier draft had a `trace_meta` hook stamp `role` and `granted` onto the run
tree. Measured on the deployment: `role` and `display_name` were present
(mirrored from context) and **`granted` never appeared** — a hook runs inside a
node, and its run-tree write does not reach the root run a trace filter reads.
The middleware was written, deployed, measured, and deleted.

**2 · `granted` is not obtainable, and not needed.** It is derivable from
`role` through `contracts/grants.py`, and the authoritative per-run record is
the **"Granted access" section in the system message** — visible on every model
call, and unable to disagree with the tool list because C6 computes both from
one set. Point at that, not at a metadata key.

#### The collision that broke the static half

Because MDA mirrors context into metadata, **a context field named like a build
metadata key overwrites it.** `RequestContext` had a `demo_version` field, and a
probe sending `demo_version="e2e"` replaced the build's `v3` on the root run —
defeating the entire "no caller can override it" property that made the static
half worth having.

The field was removed, and a test asserts `RequestContext` has exactly
`{role, display_name}`. **Any key passed in `metadata=` must not also be a
context field name.**

`demo_version` is a hand-maintained counter in `contracts/version.py`, bumped
whenever agent behaviour changes — instructions, grants, tool set, middleware,
model. Not derived from git, because what matters is whether the agent behaves
differently and only a person knows that. It is compiled in, so a bump takes
effect on the next deploy. The UI *displays* it from `contracts/grants.json`
(C2) and must **not** send it.

The UI's proxy may add its own keys, such as `ui`, to distinguish browser runs
from script runs — provided none collides with the above.

#### Acceptance criteria

- [x] The role is on the root run as `metadata.role`, mirrored from the
      context by MDA with no middleware — present on every run in the
      matrix. (How *fast* a stranger finds it is the cold-read check in
      ph. 05 §3, which is still open and needs a person.) Original: opening
      any run in LangSmith, the role is readable in under five seconds
      without opening the repo.
- [x] ~~`metadata.granted` matches the tool list~~ — **not obtainable**; the
      system message's "Granted access" section is the per-run record instead.
- [x] Filtering the project by `metadata.role` splits the scripted demo runs
      cleanly in two.
- [x] Changing grants without bumping `DEMO_VERSION` fails a pre-deploy
      check — `contracts/check_version_bump.py`, with a seeded-violation test
      for each watched path. It caught the real v4 → v5 bump in ph. 05.
      **Not built** — currently manual discipline, followed so far (v1 → v4).

### C10 · One deployment, many keys, shared threads — documented and accepted

The canonical deployment lives in the shared Demo workspace. Each DE uses their
**own** LangSmith API key from that workspace. This works:

- agent-owned connections belong to the *deployment*, so every caller resolves
  the same credentials regardless of key;
- the default `auth.langsmith_api_key()` identity verifies any valid workspace
  key.

The consequence, from the identity docs: with API-key identity, callers "may see
the same threads". **DEs will see each other's threads.** For a shared demo
that is acceptable and arguably useful. It is written down here so nobody
discovers it on stage.

#### Acceptance criteria

- [ ] **Two different workspace API keys both reach the deployment.**
      *Blocked:* the build account cannot mint a second key —
      `POST /api/v1/api-key` returns 403 `workspaces:manage-keys`. What C10
      actually asserts **is** verified: one key, two roles, two disjoint tool
      surfaces, so the role travels with the request and not with the
      credential. A second key would exercise LangSmith's auth rather than
      this build. Original: two different workspace API keys both reach the
      deployment and both get a
      role-correct answer.
- [x] Substituted and verified: a syntactically valid key belonging to
      nobody is rejected **403**, and no key at all **401**. A key from
      another organisation was not available, but both substitutes reject
      before the agent runs, which is the property.
- [x] `docs/DE-onboarding.md` §7 states the shared-thread behaviour
      explicitly, as the first item under "what will surprise you".
- [x] Nothing in the repo contains a LangSmith API key. The check is now
      **repo-wide** (it was scoped to `agent/` before `ui/` existed) and asks
      **git** what would actually be committed, so a real `.env.local` is
      correctly ignored while an accidental `git add -f` is caught. It
      seed-and-fails in both directories — and it caught a real one during
      ph. 05: an all-zeros placeholder key in a test, now assembled from
      parts so no key-shaped literal is committed anywhere.

### C11 · No user-owned connections in this build

There is **one** connection, `context-hub-corpus`, holding a workspace-scoped
read-only service key, and it is agent-owned. One and not three: Context Hub
access is workspace-level, not per-repo, so both corpora are read with the same
key, and three named connections holding one credential would be theater.

Consequences, stated so they are not rediscovered:

- caller identity does not affect credential resolution — **all** role
  behaviour is middleware;
- no `credential_authorization_required` interrupt can occur, so the UI needs no
  authorization round-trip (which the docs note is not yet first-class for
  custom frontends);
- **rotation takes effect without a redeploy.** An authored tool resolves the
  connection per run, so revoking or rotating the key changes behaviour on the
  next run. The MCP-connector path is the opposite — it caches the credential
  for the deployment's process lifetime — so delete that caveat wherever it
  survives in narration.

#### Acceptance criteria

- [x] `check-contracts.sh` asserts `connections.get` is always agent-owned.
      site, and no `"user"`.
- [x] `mda connections list` shows `context-hub-corpus` for this project.
      (The workspace also lists `mda/slack-bot-token`, which belongs to a
      different project and is not read by this agent.)
- [ ] **The stored credential is a service key (`lsv2_sk_`), not a PAT.**
      *Blocked:* creating one needs `workspaces:manage-keys`, denied to this
      account (403). It currently holds a dedicated PAT, whose **expiry date
      is unknown and needs recording**. Swapping it needs no redeploy, so
      this is a one-command fix for someone with the right rights. Original:
      the stored credential is a service key (`lsv2_sk_`), not a PAT, and is
      read-only.
- [ ] **Revoking and restoring the key, with no redeploy.** *Blocked, and
      attempted:* `mda connections delete` returns **403 "not authorized to
      access Agent Auth connections"**, and the CLI has no `update`, so
      rotation means delete-then-create. The attempt failed safely — the
      connection was never modified and the deployment kept answering. The
      claim is argued from the code (per-run resolution, 60s cache) but
      **not demonstrated**; do not promise the rotation beat on stage.
      Original: revoking the key breaks the tools and restoring it fixes them
      **with no
      redeploy** — demonstrated once, with the trace recorded.
- [x] The UI has no authorization-interrupt code path. It chooses an
      identity and renders; every access decision is in the agent.

---

## 4 · Repository layout

```text
interrupt-26-ny-mda-chat-langchain/
  docs/
    specs/                      these files
    DE-onboarding.md            ph. 05
  agent/                        the MDA project (ph. 01–05)
    agent.py
    instructions.md
    context_schema.py
    identity.py
    contracts/
      roles.py                  C1
      grants.py                 C2
      version.py                DEMO_VERSION (C9)
      grants.json               generated for the UI (C2, ph. 06 §4)
      emit_grants_json.py       writes grants.json
      check-contracts.sh        the grep-level assertions in this file
    middleware/
      role_gate.py              C6
      trace_meta.py             C9
    skills/
      docs-answering/SKILL.md   ph. 01
    tools/
      corpus.py                 the four tools + snapshot reader (C4, ph. 02)
    tests/
  corpus/                       corpus sources and seeding (ph. 02)
    engineering/                the ~15 INVENTED runbook pages — source of truth
    product_allowlist.py        which docs.langchain.com pages to curate
    seed_product.py             fetch the allowlist, push to product-docs
    seed_engineering.py         push corpus/engineering/ to engineering-runbooks
  ui/                           the directory a DE runs (ph. 06)
    app/api/identity/           sets the identity cookie
    app/api/lg/[.._path]/       proxy: attaches the key, overwrites context
    lib/grants.ts               reads agent/contracts/grants.json
```

Single repo. DEs clone it and run `ui/` only; `ui/README.md` says so in its
first paragraph. The alternative — a separate UI repo — was rejected because
the demo's credibility depends on being able to open the agent code next to the
UI when someone asks how the gating works.

---

## 5 · Model and spend

**Decided: GPT-5.6 Luna through LLM Gateway.**

```python
model="langsmith:openai/gpt-5.6-luna"
```

Both identities must use the *same* model, or the demo's "only the tools
differ" claim is false. Asserted from run metadata, not from the source.

Two facts about the id, because the two forms are easy to mix up:

- **Gateway ids use a slash** after the provider: `langsmith:openai/gpt-5.6-luna`.
  A model called directly uses a colon: `openai:gpt-5.6-luna`. The `langsmith:`
  prefix is what routes through the gateway.
- `gpt-5.6-luna` is a **bring-your-own-key** model, not a Gateway Credits
  hosted one (credits currently cover the `moonshotai/*` slugs). So the
  workspace needs an **OpenAI provider secret** configured, and the deploying
  key needs `gateway:invoke` and `workspaces:read`.

Verify the exact id against the workspace before writing it into `agent.py` —
the gateway's own model list is the authority, not these specs:

```bash
curl -s https://gateway.smith.langchain.com/v1/models \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" | jq -r '.data[].id' | grep -i gpt-5.6
```

Gateway earns its place in this build beyond convenience: it extends the
demo's own argument — credentials live in the workspace, not the repo — from
tools to the model. Spend is not a factor; development plus a live demo is a
few hundred runs.

---

## 6 · What each phase may assume

| Phase | May assume | Must not assume |
|---|---|---|
| 01 | nothing | that tools exist, that a role exists |
| 02 | a deployment exists (§7); `contracts/` exists (ph. 01 §2) | that middleware gates anything |
| 03 | `contracts/` exists; tool *names* from C2 | that the corpora are populated — test with fakes |
| 04 | 01, 02, 03 all met acceptance | that the canonical deployment is shared yet |
| 05 | a working local `mda dev` run for both roles | that the UI exists |
| 06 | a canonical deployment URL and C1/C3/C5 hold | that it may hold agent code or secrets |

Phase 03 explicitly builds against **fake** tools carrying the real names, so
middleware work is not blocked on the corpora being written. This is the one
place the phase order in the original plan needed help.

---

## 7 · The ordering trap: connections need a deployment

From the connections docs: *"Agent-owned credentials belong to the project's
deployment, so create them after at least one successful `mda deploy`."*

So the naive order — build tools, then deploy — deadlocks: `tools/mcp.py`
declares connections that cannot be created until something is deployed.

The resolution, and every phase that touches it:

```text
ph. 01  build instructions + skills + contracts/
ph. 01  mda deploy          ← BOOTSTRAP: no tools, no middleware, no connection
ph. 02  write corpus/engineering/, seed both Context Hub repos
ph. 02  mda connections create context-hub-corpus --secret-from-env LS_CORPUS_SERVICE_KEY
ph. 02                       ← now legal, because a deployment exists
ph. 02  add tools/corpus.py, redeploy
ph. 03  middleware against fakes, then against the real tools
ph. 04  assemble, mda dev, end-to-end both roles
ph. 05  mda deploy           ← CANONICAL: the deployment DEs point at
```

The bootstrap deploy is throwaway in spirit but **not** in identity: it creates
the deployment that owns the connection, so do it in the shared Demo workspace
from the start, under the final name. Deploying the bootstrap to a personal
workspace and the canonical build to the shared one means creating the
connection twice.

Seeding the corpus repos does **not** depend on the deploy — it uses your own
credentials from a script — so it can happen in parallel with phase 01.

### Acceptance criteria

- [x] The bootstrap deploy reaches `DEPLOYED` before any
      `mda connections create` runs.
- [x] The bootstrap and canonical deploys share one deployment name and one
      workspace.
- [x] `mda connections list` shows one agent-owned slug before
      `tools/corpus.py` is added.
- [x] A redeploy after adding `tools/corpus.py` does not require recreating the
      connection.

---

## 8 · How to test the whole thing

The end-to-end check that every phase ultimately serves. Run from `agent/`.

```bash
# 1 · contracts hold
contracts/check-contracts.sh

# 2 · same question, two roles, against the deployment
for ROLE in engineer employee; do
  curl -sS "$MDA_API_URL/threads" -H "x-api-key: $LANGSMITH_API_KEY" \
    -H 'content-type: application/json' -d '{}' \
  | jq -r .thread_id > /tmp/tid.$ROLE
  curl -sS "$MDA_API_URL/threads/$(cat /tmp/tid.$ROLE)/runs/wait" \
    -H "x-api-key: $LANGSMITH_API_KEY" -H 'content-type: application/json' \
    -d "{\"assistant_id\":\"role-aware-docs-assistant\",
         \"input\":{\"messages\":[{\"role\":\"user\",
           \"content\":\"Do we require retry middleware on model calls?\"}]},
         \"context\":{\"role\":\"$ROLE\",\"display_name\":\"probe\",
                      \"demo_version\":\"v1\"}}" > /tmp/out.$ROLE.json
done

# 3 · the answers differ, and differ in the right way
diff <(jq -r '.messages[-1].content' /tmp/out.engineer.json) \
     <(jq -r '.messages[-1].content' /tmp/out.employee.json)   # must differ

# 4 · no role declared → rejected, not answered
curl -sS -o /dev/null -w '%{http_code}\n' \
  "$MDA_API_URL/threads/$(cat /tmp/tid.engineer)/runs/wait" \
  -H "x-api-key: $LANGSMITH_API_KEY" -H 'content-type: application/json' \
  -d '{"assistant_id":"role-aware-docs-assistant",
       "input":{"messages":[{"role":"user","content":"hi"}]}}'
```

**Assert computed values, never literals.** Do not write an expected answer
string into a test: the docs change, the model changes, and a spec that pins
prose goes stale on its own.

Assert instead, for the pair, remembering that grants are **nested** (C2):

| Assertion | Kind |
|---|---|
| the employee run called **no** `engineeringDocs__*` tool | enforced — a failure here is a bug |
| every tool each run called was in that role's grant | enforced |
| every path each run cited is inside a corpus that role holds | enforced |
| the engineer run called at least one `engineeringDocs__*` tool | preference — a failure is a question-choice problem (ph. 05 §4) |
| the two answers differ | observed |

---

## 9 · Open items leaving this phase

| # | Item | Owner |
|---|---|---|
| O1 | ~~Can a custom frontend pass `context` to a deployed MDA?~~ **Closed: yes.** `RunCreate.context` exists in both SDKs, `useStream` forwards it, LangGraph passes it through unschema'd, `define_deep_agent(context_schema=)` accepts a type, and a sibling project runs this exact shape over HTTP against a deployed MDA | closed |
| O2 | ~~Does `chat-langchain-lite` use the docs MCP server?~~ **Closed: no.** Its three tools are hardcoded Python dicts. Nothing there to proxy; phase 02 builds the corpora from `docs.langchain.com` directly | closed |
| O3 | ~~Different DE API keys, one workspace?~~ **Closed: fine**, with shared threads (C10) | closed |
| O4 | Where the three MCP servers are hosted (ph. 02 §7). **Not** three LangSmith deployments — that endpoint exposes the agent as one tool and authenticates with an interchangeable workspace key (ph. 02 §1) | ph. 02 · **needs a decision** |
| O5 | ~~Disjoint or nested grants?~~ **Closed: nested**, `employee` ⊂ `engineer`. Consequence — the asymmetry is one-directional, so beat 2 (refusal) carries the demo and beat 1 relies on `PRIMARY_ORDER` preference (C2) | closed |
| O6 | ~~Gateway or direct provider key?~~ **Closed: Gateway**, `langsmith:openai/gpt-5.6-luna` (§5). Needs an OpenAI provider secret in the workspace | closed |
| O7 | The canonical demo question and its script | ph. 05 |
| O8 | Whether MDA's `mda dev` forwards `context` identically to the deployment | ph. 04 — test both, do not assume |
