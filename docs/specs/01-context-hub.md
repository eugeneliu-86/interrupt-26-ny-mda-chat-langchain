# Phase 01 — Context Hub: instructions and skills

> **Status:** COMPLETE (2026-09-23) · **Depends on:** [00-overview.md](./00-overview.md) C7, C8, C9, §7
>
> Scaffold the MDA project, declare `contracts/`, write the one global
> instruction set and the one skill, get them into Context Hub, and prove that
> editing the Hub copy changes deployed behaviour. Ends with the **bootstrap
> deploy** that phase 02's connections depend on.

## What this phase delivers

A deployed agent with **no tools** that can answer one question honestly:

> *"What documentation can you search?"*
> → "Nothing yet. I have no documentation tools."

And a second, harder proof:

> Edit `instructions.md` in the LangSmith Context Hub UI to change the refusal
> wording. Ask again, **without redeploying**. The wording changes.

That second proof is the entire "instructions are managed centrally and
injected at runtime" claim. If it works here, phase 05 does not need to
re-prove it.

## What this phase does not deliver

| Not here | Where |
|---|---|
| Any tool, any corpus, the connection | ph. 02 |
| `context_schema.py`, role gating, middleware, `check-contracts.sh` | ph. 03 |
| The assembled agent with tools + middleware | ph. 04 |
| The canonical deployment DEs point at | ph. 05 |
| Anything a browser touches | ph. 06 |

---

## Gates — verify before writing any code

Five checks, about ten minutes, all of them capable of blocking day one. Every
one is admin-side or account-side, which means none of them can be fixed by
changing the code you are about to write. Run them first.

### G1 · MDA beta access and toolchain

```bash
uvx --from managed-deepagents mda --version
```

**Result: pass on `mda 0.7.4` (d53cce5, 2026-09-22).** MDA is public beta, **US
LangSmith Cloud only**. A 401/403 on the first deploy means the key's workspace
lacks beta access.

Re-confirmed against 0.7.4 that `define_deep_agent` accepts the three
parameters this build depends on:

```bash
uvx --from managed-deepagents python -c "
import inspect, managed_deepagents as m
p = inspect.signature(m.define_deep_agent).parameters
print({k: k in p for k in ('context_schema', 'metadata', 'tools')})"
# → {'context_schema': True, 'metadata': True, 'tools': True}
```

> **The docs and the installed wheel disagree, and the wheel wins.** Already
> confirmed for this build: the documented `define_deep_agent` parameter table
> omits `context_schema`, which the wheel accepts
> ([00-overview.md](./00-overview.md) §1 fact 3). Check `mda --help` and the
> installed package before treating any doc statement as binding.

### G2 · Shared Demo workspace write access

The bootstrap deploy (§7) must land in the shared Demo workspace, because it
becomes the owner of the connection from phase 02. Landing it in a
personal workspace costs a full redo later.

```bash
# What the deploy key can actually reach — the authoritative answer.
curl -sS https://api.smith.langchain.com/api/v1/workspaces \
  -H "X-API-Key: $LANGSMITH_API_KEY" | jq -r '.[] | "\(.id)  \(.display_name)"'
```

**Result: `LANGSMITH_WORKSPACE_ID=a3866f07-2cf5-4e9c-a287-59ed817c2ecd`
("Demo Workspace" in the **LangChain Inc.** org).**

### The trap this gate exists for: a 403 can mean the wrong org

**Two organizations each contain a workspace displayed as "Demo Workspace".**

| Org | Workspace id | |
|---|---|---|
| LangChain Inc. (`f5c798a2…`) | `a3866f07-2cf5-4e9c-a287-59ed817c2ecd` | **ours** |
| Deployed Engineering (`fcb2f57b…`) | `fd6b1198-8e6a-4f06-80f5-20e1b40ded12` | not ours |

A key from the wrong org returns **403** on the right workspace id. That reads
exactly like a bad id, and during this build it caused the correct id to be
discarded and replaced with the same-named workspace in the other org — which
passed every subsequent check, because it is a real workspace with the gateway
configured. The build would have deployed to the wrong org's workspace and
nobody would have noticed until a DE could not see it.

**So list the org, not just the workspaces**, and confirm the workspace id
appears under the org the key belongs to:

```bash
curl -sS https://api.smith.langchain.com/api/v1/orgs/current \
  -H "X-API-Key: $LANGSMITH_API_KEY" | jq -r '.display_name'
curl -sS https://api.smith.langchain.com/api/v1/workspaces \
  -H "X-API-Key: $LANGSMITH_API_KEY" | jq -r '.[] | "\(.id)  \(.display_name)"'
```

A PAT is scoped to one org: the two PATs involved here reached 6 and 34
workspaces respectively, with **no overlap**. Matching key to workspace is
therefore the same question as matching key to org.

### G3 · LLM Gateway is enabled, with an OpenAI provider secret

The model is `langsmith:openai/gpt-5.6-luna` (§5 of the overview), which is a
**bring-your-own-key** model — it needs a workspace OpenAI provider secret, not
Gateway Credits.

```bash
curl -s https://gateway.smith.langchain.com/v1/models \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" | jq -r '.data[].id' | grep -i gpt-5.6
```

| Result | Meaning |
|---|---|
| the id prints | gateway enabled, provider secret present, key permitted — proceed |
| empty list | the OpenAI provider secret is missing; a BYOK provider with no secret is omitted from the list |
| `403` | the key lacks `gateway:invoke` / `workspaces:read`, or cannot reach that workspace at all |
| the id is absent but others print | the model name has changed — **use what the endpoint returns**, not what this spec says |

**Result: PASS for "Demo Workspace" — and this is workspace-by-workspace, not
account-wide.** Gateway provider secrets are workspace-scoped, so "the gateway
is configured" is never a global fact. Measured with the same key and only the
`X-Tenant-Id` header varying:

| Workspace | Gateway models | `gpt-5.6-luna` |
|---|---|---|
| `fd6b1198` **Demo Workspace** | 230 | **yes** |
| `5bf28bce` Dev Demo | 60 | yes |
| `d7378353` Prod Demo | 2 | no |
| `ee1cc96c` personal | 2 | no |

Two of the four plausible targets cannot run this build's model. Probe the
workspace you are actually deploying to, with the key you are actually
deploying with:

```bash
curl -sS https://gateway.smith.langchain.com/v1/models \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" \
  -H "X-Tenant-Id: $LANGSMITH_WORKSPACE_ID" | jq -r '.data[].id' | grep gpt-5.6

This is the gate most likely to fail, and it fails *late* if skipped: the deploy
succeeds and the first model call 402s or 403s.

### G4 · `mda init` accepts the gateway model string

```bash
uvx --from managed-deepagents mda init /tmp/gate-probe \
  --model langsmith:openai/gpt-5.6-luna --no-sandbox && rm -rf /tmp/gate-probe
```

**Result: pass, with a docs divergence. There is no `--gateway` flag in mda
0.7.4.** The documented `mda init --gateway` does not exist in this release;
`--model langsmith:openai/gpt-5.6-luna` is accepted on its own and written
straight into `agent.py`, so the `langsmith:` prefix is all that routes through
the gateway. Do not pass `--gateway`.

Two more things the probe established, both of which simplify §2:

- **`identity.py` is scaffolded by default**, already using
  `auth.langsmith_api_key()`. It does not need writing — only its docstring
  enriching (§2).
- **No `skills/` directory is scaffolded**, so there is no default skill to
  delete before adding ours (§4).
- The scaffold pins `managed-deepagents==0.7.4` and nothing else. This build
  also needs `langsmith>=0.7.35` (Context Hub SDK methods) and `httpx`.

### G5 · A credential exists that can read Context Hub in that workspace

Phase 02 stores one credential in the connection. Verify the candidate can
actually read and write Context Hub **in the target workspace** before relying
on it:

```python
from langsmith import Client
from langsmith.schemas import FileEntry
# with LANGSMITH_WORKSPACE_ID set to the target
c = Client(api_key=CANDIDATE)
c.push_agent("zz-probe-delete-me", files={"AGENTS.md": FileEntry(content="probe\n")},
             is_public=False)
print(c.pull_agent("zz-probe-delete-me").commit_hash)
c.delete_agent("zz-probe-delete-me")
```

**Result: pass with a dedicated PAT.** Creating a *service key* needs
`organization:pats:create` + `workspaces:manage-keys` and was not available, so
the build uses a PAT created specifically for this purpose, with an expiry set
(ph. 02 §5 records the tradeoff and the swap path).

Nothing is hosted in this build, so there is no infrastructure account to
arrange.

### Acceptance criteria

- [x] G1–G4 all pass before `mda init` runs for real. **G1 and G4: passed**
      against mda 0.7.4, with the `--gateway` divergence recorded above.
- [x] G3's model id is recorded, and it is the id that goes into `agent.py`.
- [x] Any gate that failed is written into this section as a closed item with
      what fixed it. Two are recorded: **G2** (the workspace-id 403 that was
      an org mismatch, with the worked example) and the **`--gateway`**
      divergence between the docs and mda 0.7.4.
- [x] G5 has an owner and an account, even if the provider is undecided.

---

## 1 · Why instructions cannot carry the role

Context Hub holds **one** `instructions.md` and **one** `skills/` tree per
deployment (C8). There is no per-caller instruction set, no conditional
include, and the agent cannot modify either at runtime.

Three designs were considered and rejected:

| Design | Why not |
|---|---|
| Two deployments, one per role | Destroys the "same deployed agent" claim, which is the demo's headline |
| `skills/engineer/` and `skills/employee/`, agent picks | The *model* would be choosing its own permissions. Nondeterministic, and exactly the anti-pattern the demo argues against |
| Branching text in `instructions.md` ("if the user is an engineer…") | Same problem one level down: enforcement by persuasion |

**The decision: instructions describe the *rule*, middleware supplies the
*facts*.** `instructions.md` says "you can only search the corpora listed in
your granted-access section, and you must refuse anything else." Middleware
injects that section per run (C8), generated from `contracts.grants`.

The instruction file therefore never names a role and never names a tool. It is
role-agnostic by construction, which is what lets one file serve both
identities.

---

## 2 · Project scaffold

```bash
cd interrupt-26-ny-mda-chat-langchain
uvx --from managed-deepagents mda init agent \
  --gateway \
  --model langsmith:openai/gpt-5.6-luna \
  --no-sandbox
cd agent
uv sync
uv run mda --version
```

`--gateway` scaffolds the project to route model calls through LLM Gateway
([00-overview.md](./00-overview.md) §5). Verify the exact model id against the
workspace before trusting it — the gateway's model list is the authority:

```bash
curl -s https://gateway.smith.langchain.com/v1/models \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" | jq -r '.data[].id' | grep -i gpt-5.6
```

If `mda init` rejects the combination of `--gateway` and a `langsmith:` model
string, scaffold without `--model` and set it in `agent.py` (§5). The model id
lives in exactly one place either way.

`--no-sandbox` is deliberate: this agent reads Context Hub over HTTPS and runs
no code. A sandbox declaration would add cold-start latency and a bake step for
nothing. `mda init` writes one by default, so it has to be opted out.

`--identity` is **not** passed. The default identity (`auth.langsmith_api_key()`)
is what C10 depends on — every DE's own workspace key works, and threads are
shared. Passing `--identity` scaffolds user-owned threads and would put us on
the Supabase path, which this build does not want.

Post-scaffold, delete what the demo does not use, so that a reader of the repo
sees only load-bearing files:

- no `memory.py` — the agent has no durable memory and should not appear to
- no `sandbox/`
- no `channels/`, `schedules/`

### `identity.py`

**The scaffold already writes this file**, using `auth.langsmith_api_key()` —
confirmed against mda 0.7.4 (G4). Do not recreate it; replace its docstring
with the one below, which is where the C10 consequence gets recorded next to
the code that causes it:

```python
# agent/identity.py
"""Who may call this deployment (C10).

Callers present a LangSmith workspace API key as `x-api-key`. This answers
whether a caller is allowed; it does NOT give each person private threads —
every DE holding a key for this workspace resolves to one identity, and they
will see each other's threads.

A workspace API key is workspace-scoped, not request-scoped, so it must never
reach a browser: phase 06 keeps it in the UI's server runtime (C5).

Upgrade path, out of scope here: auth.supabase(project_ref=...) gives each
signed-in person private threads and lets a browser call the deployment
directly with a Bearer token. Adding it later does not backfill owner metadata
onto existing threads, so it is a migration, not a config change.
"""

from managed_deepagents import auth, define_identity

identity = define_identity(auth=auth.langsmith_api_key())
```

The docstring is doing real work: it is where the C10 consequence — shared
threads — is written down next to the code that causes it.

#### Acceptance criteria

- [x] `identity.py` exists and uses `auth.langsmith_api_key()`.
- [x] A valid workspace API key reaches the deployment; a key from another
      workspace gets 401/403.
- [x] The file records the shared-thread consequence and the Supabase upgrade
      path.

### The contracts package

`contracts/` is written **here**, in the scaffold, even though nothing consumes
it until phase 02. It is pure declaration — two mappings, a version string, and
a lookup — with no dependency on tools, middleware, or a deployment. Writing it
now removes an ordering conflict that is otherwise easy to create: phase 02's
`tools/corpus.py` needs `CORPORA`, and phase 03's middleware needs
`granted_prefixes`, so if it belonged to either of them the other would be
blocked.

```text
agent/contracts/
  __init__.py
  roles.py                C1 — the closed role vocabulary
  grants.py               C2 — CORPORA, GRANTS, PRIMARY_ORDER, granted_prefixes()
  version.py              C9 — DEMO_VERSION
  emit_grants_json.py     writes grants.json for the UI (ph. 06 §4)
  grants.json             generated, committed
```

The contents are specified in [00-overview.md](./00-overview.md) C1, C2 and C9,
and the import-time assertions and `granted_prefixes()` in
[03-identity-and-middleware.md](./03-identity-and-middleware.md) §2. Phase 03
adds `check-contracts.sh` — the enforcement script needs code to point at, and
in this phase there is none.

Nothing in this phase imports `contracts/`. That is expected: it exists so that
phases 02 and 03 can both start without waiting on the other.

#### Acceptance criteria

- [x] `python -c "import contracts.grants, contracts.roles, contracts.version"`
      passes from `agent/`.
- [x] `python contracts/emit_grants_json.py` is idempotent — running it twice
      produces no diff.
- [x] `DEMO_VERSION` is defined once, in `contracts/version.py`, and
      `grants.json` carries the same value.
- [x] `agent.py`, `instructions.md`, and `skills/` do not import or mention
      `contracts/` — it is not load-bearing yet, and pretending otherwise would
      hide the phase-02 dependency this section exists to remove.

### The `.env` split

```text
# agent/.env  — never committed
LANGSMITH_API_KEY=lsv2_...          # reserved: deploy auth + gateway auth
LANGSMITH_WORKSPACE_ID=...          # reserved: the shared Demo workspace
```

**No provider key.** Routing through the gateway means the OpenAI credential is
a workspace **provider secret**, resolved by the gateway — it never enters
`.env`, the build archive, or the deployment. That is the same argument the
connections make (C11), applied to the model, and it is worth pointing at
during the demo.

The deploying key needs `gateway:invoke` and `workspaces:read`, and the
workspace needs an OpenAI provider secret configured. Both are admin actions —
confirm them before the first deploy rather than debugging a 402 or 403 later.

`mda deploy` forwards non-reserved `.env` entries as deployment secrets and
does **not** upload the reserved platform variables. Know which is which before
phase 02 adds a corpus service key: it is non-reserved and would be forwarded, which
is *not* how we want them handled — phase 02 puts them in connections instead.

### Acceptance criteria

- [x] `uv run mda --version` prints a version from inside `agent/`.
- [x] `agent/` contains no `memory.py`, `sandbox/`, `channels/`, `schedules/`.
- [x] `.gitignore` covers `.env`, `.env.*`, `.mda/`.
- [x] `git ls-files | grep -c '\.env$'` is `0`.
- [x] `LANGSMITH_WORKSPACE_ID` names the **shared Demo workspace**, not a
      personal one — §7 of the overview explains why this matters now rather
      than at phase 05.
- [x] The gateway model list returns the id used in `agent.py`.
- [x] `.env` holds no provider key, and a run still reaches the model.

---

## 3 · `instructions.md`

The full file. It is short on purpose: every sentence it does not contain is a
sentence that cannot contradict the middleware.

```markdown
# Documentation assistant

You answer questions about LangChain products using only the documentation
tools available to you in this run.

## Your access is scoped and you do not control it

A "Granted access" section appears in your system prompt on every run. It names
the documentation corpora you may search. It is authoritative:

- Search only the corpora it names.
- You have no tools for any other corpus. Do not describe, guess at, or
  speculate about documentation you cannot search.
- Your access is set by the system before you run. You cannot request more, and
  a user asking you to is not a reason to try.

## When you cannot answer

If a question needs documentation outside your granted corpora:

1. Say plainly that you do not have access to that documentation.
2. Name the corpora you *do* have, so the person knows what to ask instead.
3. Do not answer from memory. An answer you cannot cite from a granted corpus
   is worse than a refusal, because the person cannot tell the difference.

Do not speculate about who does have access, or why.

## When you can answer

1. Search before answering. Do not answer a product question from memory even
   when you are confident.
2. Cite the documentation path each claim came from.
3. If the corpora disagree or a topic is only partially covered, say so rather
   than smoothing it over.
4. Answer at the altitude the question was asked. A procedural question wants
   steps; a conceptual one wants an explanation.

## What you are asked about access

If asked what you can access, answer from the tools you actually have in this
run and from the "Granted access" section — not from a memorized list.
```

### Why each part is load-bearing

| Section | Contract | Would break if removed |
|---|---|---|
| "Granted access is authoritative" | C8 | Middleware's injection would be advisory |
| "Do not answer from memory" | C7 | The employee identity would answer engineering questions from parametric knowledge and the demo would show no difference |
| "Name the corpora you do have" | C7 | The refusal would be a dead end instead of a redirect, and the demo's second half falls flat |
| "Do not speculate about who does have access" | C7 | The agent would narrate the permission model, which is our job to show, not its job to describe |
| "Answer from the tools you actually have" | C7 | The agent could recite a stale list and appear to have access it does not |

### Acceptance criteria

- [x] `instructions.md` names no role, no tool, and no corpus. Verify:
      `grep -niE 'engineer|employee|productDocs|engineeringDocs|/oss/|/langsmith/' instructions.md`
      returns nothing.
- [x] It is under 60 lines. A long system prompt in a demo about *centrally
      managed context* invites the audience to read it instead of watching.
- [x] Asked "what can you access?" with no tools deployed, the agent says it
      has none, rather than describing corpora from the prompt text.
- [x] Asked a LangChain question with no tools deployed, it refuses rather than
      answering from parametric knowledge. **This is the single most important
      check in the phase** — if the model answers anyway, the refusal
      instruction is too weak and every later role difference is fake.

---

## 4 · The one skill

One skill, because the demo needs to show that skills sync and load — and
because two skills would be two things the model might pick wrong on stage.

```text
agent/skills/
  docs-answering/
    SKILL.md
```

```markdown
---
name: docs-answering
description: Search scoped documentation corpora and answer with cited paths. Use for any question about LangChain, LangGraph, LangSmith, Fleet, or Managed Deep Agents behaviour, configuration, or APIs.
---

# Answering from scoped documentation

## 1 · Find the shape of the question

Decide what kind of answer would satisfy it before searching:

- **procedural** — "how do I…" wants ordered steps and the file or endpoint
  they act on
- **conceptual** — "what is…", "why…" wants the model of how it works
- **reference** — "what does X accept" wants exact parameters or fields

The shape decides which corpus is likely to hold it, and how much you need to
read.

## 2 · Search, then read

Search each granted corpus for the question's terms. Search results are titles
and paths; they are not the answer. Fetch the page before making a claim from
it.

If a search returns nothing in a granted corpus, do not substitute a different
corpus's answer and do not fill the gap from memory. Say the corpus does not
cover it.

## 3 · Answer

- Lead with the answer, then support it.
- Cite the path for each claim: `/langsmith/fleet/schedules`.
- Quote exact names — a flag, a field, a file path — verbatim from the page.
  Paraphrasing an identifier makes an answer unusable.
- If the granted corpora cover only part of the question, answer the covered
  part and name the gap.

## 4 · When the corpora do not cover it

Refuse per your instructions: say you lack access to that documentation, name
what you do have, and stop. Do not approximate.
```

### Why the skill and the instructions are not the same file

`instructions.md` is loaded on **every** run and costs tokens on every run;
`SKILL.md` is loaded only when the agent judges the task matches its
description. The split is: *rules about access* are always-on (they must
survive a question that does not trigger the skill), *procedure for answering
well* is on-demand.

There is also a demo reason. Skills are visible in the LangSmith UI as their
own artifacts with their own history, so having one real skill makes "skills
are managed centrally" a thing you can click on rather than assert.

### Acceptance criteria

- [x] `skills/docs-answering/SKILL.md` has `name` and `description`
      frontmatter, and `name` matches the directory.
- [x] No directory under `skills/` contains a role name (C8).
- [x] The description is written to *trigger*: it names the question kinds, not
      just "answer documentation questions".
- [x] **The description names no corpus, and does not imply one exists.** Every
      role sees every skill's description at startup, so a description
      mentioning internal runbooks tells an employee-role run that such
      documentation exists — the same C7 leak the instructions must avoid. This
      one bit during the build: a first draft read *"how this team deploys,
      operates, or runs on-call"* and had to be neutralized.
- [x] After deploy, the skill appears in Context Hub and in the LangSmith UI.
- [x] In a trace, the skill's contents appear only on runs that needed it — not
      on a "hello" run. If it loads on every run, the description is too broad.

---

## 5 · `agent.py` for the bootstrap

Deliberately minimal. Phase 04 owns the final version.

```python
# agent.py
from managed_deepagents import define_deep_agent

agent = define_deep_agent(
    name="role-aware-docs-assistant",
    model="langsmith:openai/gpt-5.6-luna",
)
```

Note the punctuation: a gateway id is `langsmith:<provider>/<model>` — colon
after `langsmith`, **slash** before the model. A model called directly is
`openai:gpt-5.6-luna`, with a colon. Mixing them produces a provider-resolution
error that reads like a missing key.

**The name is final from this moment.** MDA uses it as the LangGraph assistant
id and the default deployment name, and the connections created in phase 02
belong to *this* deployment. Renaming later means recreating all three
connections.

Do not set `backend`, `store`, `checkpointer`, `memory`, `skills`, or the system
prompt — the managed runtime owns those, and `skills/` + `instructions.md` are
discovered from the filesystem, not passed here.

### Acceptance criteria

- [x] `uv run mda build` compiles with no tools and no middleware.
- [x] `agent.py` sets none of the managed fields listed above.
- [x] The `name` matches the value phase 02's connections and phase 06's
      `assistant_id` will use. Written once, referenced everywhere.

---

## 6 · Local run before deploy

```bash
uv run mda dev
# → local LangGraph dev server; open LangSmith Studio against it
```

Three questions, in this order:

| Ask | Expect |
|---|---|
| "What documentation can you search?" | "None — I have no documentation tools." |
| "How do I deploy a managed deep agent?" | A refusal. **Not** an answer. |
| "Who has access to the engineering runbooks?" | Declines to speculate |

The second is the one that fails. Models want to answer LangChain questions
from parametric knowledge, and a single weak sentence in `instructions.md` will
not stop it. If it answers, strengthen §3 and re-run before deploying —
do not proceed hoping tools will mask it, because they will, and the
employee-refusal half of the demo will be built on sand.

**Result: all three pass on `gpt-5.6-luna`.** Q2 returned *"I can't answer this
from the available documentation… no product documentation corpus covering
managed deep-agent deployment"* — a refusal, with no attempt to answer from
training data. The refusal instruction in §3 is strong enough as written.

A fourth check, for §4's progressive-disclosure criterion: asking `"hi"`
called **no tools and loaded no skill**, so the skill description is scoped
tightly enough not to fire on everything.

### Two things about `mda dev` that cost time

**1 · The port is random, and port 2024 may be someone else's server.** The CLI
prints its URL; read it rather than assuming. During this build, `2024` was
already serving an unrelated project, and querying it returned that project's
assistants — which looks like the agent misbehaving rather than the wrong
server answering.

```bash
uv run mda dev > /tmp/mdadev.log 2>&1 &
PORT=$(grep -oE 'http://127\.0\.0\.1:[0-9]+' /tmp/mdadev.log | head -1 | grep -oE '[0-9]+$')
curl -sS -X POST "http://127.0.0.1:$PORT/assistants/search" \
  -H 'content-type: application/json' -d '{"limit":5}'   # must show OUR assistant
```

**2 · The final answer is a list of content blocks, not a string.** With
`gpt-5.6-luna`, an AI message's `content` is a list like
`[{"type":"reasoning"}, {"type":"function_call"}, {"type":"text", "text": …}]`.
Reading `content` as a string yields an empty answer and looks exactly like the
agent returning nothing. Assemble the text blocks:

```python
def final_text(msgs):
    for m in reversed(msgs):
        if m.get("type") != "ai":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()
        if isinstance(c, list):
            parts = [b.get("text", "") for b in c
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(p.strip() for p in parts):
                return "\n".join(parts).strip()
    return ""
```

Phase 06's UI must do the same (ph. 06 §5).

### Acceptance criteria

- [x] All three answers match the table. **Passed.**
- [x] The refusal names what the agent *does* have rather than just declining.
      **Passed** — it named the skill instructions as its only resource.
- [x] No *docs* tool calls appear, because there are no docs tools. The harness
      built-ins (`ls`, `read_file`, `grep`) do appear, reading the skill — that
      is progressive disclosure working, not a leak.
- [x] `"hi"` loads no skill and calls no tools. **Passed** (§4 criterion).
- [x] The dev server queried is **ours** — checked via `/assistants/search`,
      not assumed from the port.

---

## 7 · The bootstrap deploy

```bash
uv run mda deploy
```

This is the deploy that makes phase 02's connections legal
([00-overview.md](./00-overview.md) §7). It must land in the **shared Demo
workspace** under the final agent name.

What it does, in order that matters here: compiles the project, **syncs
`instructions.md` and `skills/` to the agent's Context Hub repo**, uploads, and
deploys.

### The conflict prompt, before it surprises you

Once the Hub copy has been edited — which §8 is about to do deliberately — the
next `mda deploy` stops and asks:

```text
▲  Context Hub instructions.md changed since the last MDA sync.
◆  Overwrite Hub-edited instructions.md with the local version?
│  ○ Yes / ● No
```

The default keeps the Hub version and skips syncing that section. Non-interactively
(CI, or output redirected) there is no prompt: the deploy **exits with an
error** and must be re-run with `--context-strategy overwrite` or
`--context-strategy keep-hub`.

**Standing decision for this repo: the project files are the source of truth.**
Hub edits are for demonstrating live injection, not for authoring. So the normal
answer is `overwrite`, and any wording you liked from a Hub edit gets copied
back into `instructions.md` first. Write it down in the agent README so the
person deploying under time pressure does not have to decide.

### Result: deployed

```text
Organization   LangChain Inc.
Workspace      Demo Workspace  (a3866f07-2cf5-4e9c-a287-59ed817c2ecd)
Agent Server   https://role-aware-docs-assistant-679d6573475f558188a07a13bc2b152c.us.langgraph.app
Dashboard      https://smith.langchain.com/o/a3866f07-.../host/deployments/f28f4f92-95fb-49c9-81f2-2b8458deae4a
Statuses       QUEUED → AWAITING_BUILD → BUILDING → AWAITING_DEPLOY → DEPLOYING → DEPLOYED
```

Four things the deploy established, each worth keeping:

**1 · Context Hub sync, and the identifier trap.** The repo is created as
`chat-lc-lite/role-aware-docs-assistant` and holds `instructions.md`,
`skills/docs-answering/SKILL.md`, and MDA's own
`.mda/deploy-manifest.json`. **`pull_agent` requires the owner-qualified
name**: the bare handle returns `400 invalid repository reference`, even though
the docs say a bare name resolves against the current workspace owner. Phase 02
depends on this, so `contracts/grants.py` now carries `HUB_OWNER` and
`repo_and_slug()` returns the qualified form.

**2 · Identity behaves exactly as C10 requires**, verified against the live
deployment:

| Caller | Result |
|---|---|
| correct workspace key | `200` |
| no key | `401` |
| valid key from another **org** | `403` |

**3 · The gateway route is visible in the logs.** `mda logs` shows
`POST https://gateway.smith.langchain.com/v1/responses "HTTP/1.1 200 OK"` per
model call — so "the model routes through LLM Gateway" is checkable rather than
asserted. Useful for ph. 05 §3's trace contract.

**4 · One harmless warning.** `failed to search existing managed crons: …
operation timed out`, with "Any schedules from a previous deploy may still be
running." There is no `schedules/` directory, so there is nothing to reconcile.
Expect it; do not chase it.

### The conflict path, confirmed and cheap

With `instructions.md` edited in the Hub, a plain non-interactive `mda deploy`
**fails before building**:

```text
└  Context Hub instructions.md changed since the last MDA sync.
   Re-run with --context-strategy overwrite or --context-strategy keep-hub.
```

It costs seconds, not a build — so the failure is a prompt to decide, not a
delay. `--context-strategy overwrite` then restores the repo copy, and because
the Hub sync happens *before* the build, the corrected instructions take effect
as soon as the sync step runs rather than when the revision finishes.

### Acceptance criteria

- [x] `mda deploy` reaches `DEPLOYED` and prints a dashboard URL.
- [x] The deployment is in the shared Demo workspace, not a personal one.
- [x] Context Hub shows `instructions.md` and `skills/docs-answering/SKILL.md`.
- [x] The three §6 questions give the same answers against the deployment as
      they did locally — all three refuse, consistently with the local run.
- [x] `agent/README.md` records the `--context-strategy` decision.
- [x] Identity: `200` / `401` / `403` for correct / missing / wrong-org keys.

---

## 8 · The live-injection proof

The reason this phase exists as its own phase.

```bash
# 1 · ask, against the deployment
#     → note the exact refusal wording

# 2 · in LangSmith → Context Hub → the agent's repo → instructions.md
#     change one refusal sentence to something unmistakable, e.g.
#     "I don't have that documentation in my granted corpora (edited live)."
#     commit in the Hub UI

# 3 · ask the same question again. No redeploy. No restart.
#     → the new wording appears
```

**Result: PASS.** The marker used was *"Begin your reply with the exact token
LIVE-INJECTION-OK"*, spliced into the refusal steps of the Hub copy. The same
question on a fresh thread, with **no redeploy and no restart**, returned:

```text
LIVE-INJECTION-OK I don't have access to documentation for deploying a
managed deep agent in this run.
```

Then reconciled with `--context-strategy overwrite`: the marker is gone from
the Hub, `pull_agent(...).files["instructions.md"]` is byte-identical to the
local file, the skill is still synced, and the deployment is back to its
baseline refusal.

If the wording does not change, something is wrong with the claim itself, and
it is better to find out now than in front of people. Check: did the Hub commit
land, is the deployment reading the repo the Hub UI is showing, and is the
answer being served from a cached thread.

Then put it back: copy the winning wording into the local `instructions.md`,
redeploy with `--context-strategy overwrite`, and confirm the Hub and the repo
agree again.

### Acceptance criteria

- [x] A Hub-only edit changes deployed behaviour with **no redeploy**.
- [x] The change is visible in a fresh thread.
- [x] After the reconciling redeploy, Hub and repo contents are identical.
- [x] The sequence is written down as a runnable demo beat — phase 05 will want
      it in the script. Use a *wording* change rather than a token on stage; the
      token was for mechanical proof.

---

## 9 · What phase 02 and 03 inherit

Phase 02 and 03 may assume, without re-proving:

| Guarantee | From |
|---|---|
| `contracts/roles.py`, `grants.py`, `version.py`, `grants.json` exist and import cleanly | §2 |
| A deployment named `role-aware-docs-assistant` exists in the shared Demo workspace | §7 |
| Agent-owned connections can now be created against it | §7, overview §7 |
| `instructions.md` states the access rule without naming roles or tools | §3 |
| `skills/docs-answering/` exists and loads on documentation questions only | §4 |
| The agent refuses rather than answering from parametric knowledge | §6 |
| Hub edits reach the deployment without a redeploy | §8 |
| `agent.py` sets no managed fields, and the name is final | §5 |

They must **not** assume: that any tool exists, that `context_schema.py`
exists, that `runtime.context` carries anything, or that
`contracts/check-contracts.sh` exists — phase 03 writes it.

## Open items leaving this phase

| # | Item | Owner |
|---|---|---|
| O1.1 | Whether the refusal survives a determined "just answer from what you know" follow-up. Test adversarially in ph. 04, not here | ph. 04 |
| O1.2 | Whether `skills/` needs a second skill for the "compare two corpora" case. Defer until the demo question is chosen | ph. 05 |
| O1.3 | Exact Hub-edit beat to use on stage (§8) | ph. 05 |
