# Phase 02 — Corpora and tools: two Context Hub repos

> **Status:** COMPLETE (2026-09-23), 47/52 criteria · **Depends on:** [00-overview.md](./00-overview.md) C2, C4, C11, §7 · [01-context-hub.md](./01-context-hub.md) §2 (`contracts/`) and §7 (bootstrap deploy must exist)
>
> Two private Context Hub repos hold the corpora. Four authored tools read them
> through one workspace service key. **No MCP servers, no hosting, no
> third-party dependency.** No gating in this phase — after it, every role can
> reach both corpora, and that is correct.

## What this phase delivers

- `product-docs` — a curated copy of public LangChain product documentation.
- `engineering-runbooks` — **invented** internal runbooks for a fictional team.
- One connection holding a read-only workspace service key.
- Four authored tools: a `search_docs` / `fetch_doc` pair per corpus.

And a deployed agent that can answer:

> *"What documentation can you search?"*
> → names both corpora, with page counts read from its own snapshots.

## What this phase does not deliver

| Not here | Where |
|---|---|
| Role gating of any kind | ph. 03 |
| `context_schema.py` | ph. 03 |
| The canonical deployment | ph. 05 |

---

## 1 · Why Context Hub, and the three paths not taken

The corpora live in **private Context Hub repos**, read by authored tools using
a service key resolved from a connection at runtime. Recording the alternatives
because each was live at some point and the reasons are not obvious in
hindsight.

| Option | Hosting | Real credential | Content genuinely private | Verdict |
|---|---|---|---|---|
| Three MCP servers we build and deploy | **3 services** | yes ×3, but all guarding public docs | no | **No** — hosting, and the credentials guard nothing |
| The real `docs.langchain.com/mcp` server | none | none needed | no | **No** — see §1.2 |
| Private GitHub repo + fine-grained PAT | none | yes | yes | **No** — ties the demo to a personal or bot GitHub account, with an expiry to babysit |
| **Private Context Hub repos + service key** | **none** | **yes** | **yes** | **Chosen** |

### 1.1 · What the chosen option buys

- **Nothing to host.** Both corpora live in LangSmith. No containers, no URLs,
  no uptime to own. This is what killed the three-MCP-server design.
- **The credential is institutional, not personal.** A workspace-scoped service
  key (`lsv2_sk_`), read-only, admin-created, no expiry unless you set one. Not
  anyone's PAT, so it survives people leaving.
- **The content is genuinely private.** The engineering corpus is unreadable
  without the key. "Only engineers can see the runbooks" stops being costume —
  it is simply true, which is the honesty problem earlier drafts could not fix.
- **Rotation works without a redeploy.** An authored tool calls
  `connections.get(...)` per run, so rotating the key in the workspace takes
  effect on the next run. The MCP-connector path cached the credential for the
  deployment's process lifetime and needed a redeploy — a caveat that no longer
  applies and should be deleted from the narration wherever it survives.
- **Versioning and pinning come free.** `pull_agent` returns a `commit_hash`
  and accepts `name:tag` or a commit, so a run is reproducible against an exact
  corpus version.
- **One code path.** Both corpora are Context Hub repos, so there is one reader
  and one search implementation, not two.

### 1.2 · Why not the real public docs MCP server

Tempting: zero maintenance, a genuine third-party MCP connector demonstrated
for free. Rejected for one reason that matters more than all of that.

**We would not control the public corpus.** That server serves every page on
`docs.langchain.com` — the SDK reference, the Agent Server API, the REST
endpoints, the self-hosting guides. There is no way to scope it. So the
employee identity could reach the entire public documentation set, and any
"engineering" corpus assembled from public material would be reachable by the
role that is supposed to be excluded from it.

Two consequences, both fatal to the demo:

- **Beat 2 dies.** An engineering-shaped question gets answered from public docs
  instead of refused.
- **Beat 1 converges.** Both identities read the same underlying pages, so the
  answers stop differing in substance.

A curated corpus we own removes both, because we decide what is in it.

> The overlap risk is also why the engineering corpus is **invented** (§3)
> rather than mirrored. Invented content has no public counterpart by
> construction, so no amount of public-corpus breadth can reach it.

### 1.3 · What is given up

Say these plainly rather than discovering them in a Q&A:

- **No MCP server is demonstrated.** `tools/mcp.py` and `define_mcp` are unused.
  Note that this is *closer* to the original pitch — *"define the tools in the
  agent repository and configure multiple named, agent-owned Connections"* — and
  it was the MCP elaboration that dragged hosting in.
- **One connection, not three.** Context Hub access is workspace-level, not
  per-repo, so both corpora are read with the same key. Three named connections
  holding one credential would be theater. Claim one real connection and mean
  it. The build's second central-credential story is LLM Gateway resolving the
  OpenAI provider secret from the workspace (ph. 04 §6) — no model key in the
  repo either.
- **Using Context Hub as a document store is slightly off-label.** It is
  designed for agent and skill context. Everything used here is documented
  public API — arbitrary files, `is_public=False`, SDK read — but it is not the
  purpose it was pitched for. If someone asks, say so.

### Acceptance criteria

- [x] `mcp-server/` does not exist, and nothing in the repo provisions a
      container, a URL, or a hosted service.
- [x] `agent/tools/mcp.py` does not exist. Its absence is deliberate: the
      filename is a reserved MDA managed declaration, so an empty or stray file
      there would enable an MCP connector.
- [x] `grep -rn "docs.langchain.com/mcp" agent/` returns nothing.
- [x] One connection exists, not three (§5).

---

## 2 · The two corpora

| Prefix (= tool-name prefix) | Context Hub repo | Content | Provenance | Pages |
|---|---|---|---|---|
| `productDocs` | `product-docs` | Public LangChain product documentation — concepts, agents, quickstarts, Fleet | curated copy of `docs.langchain.com` (§4) | ~40 |
| `engineeringDocs` | `engineering-runbooks` | Internal runbooks — deploy procedure, on-call, break-glass, environments, change process | **invented** (§3) | ~15 |

Both repos are **private** (`is_public=False`), in the shared Demo workspace.

### On naming: `productDocs`, not `publicDocs`

Earlier drafts called the shared corpus `publicDocs`. That name describes a
*permission*, and under nested grants (C2) both roles read it — so the name
would imply a distinction that does not exist and invite the reader to think
the other corpus is gated by *publicness* rather than by tool surface. It also
became wrong in fact: the corpus is a curated copy in a private repo.

`productDocs` describes the content. Rename everywhere: `contracts/grants.py`,
the middleware blurbs, `grants.json`, the UI.

### The employee corpus, deliberately absent

The original use case had three corpora, including "general employee
documentation". This build has two, and the employee identity holds only
`productDocs`. The demo's core is unaffected: both identities share a corpus,
one identity has an additional one.

If that leg is wanted back it is a **third Context Hub repo read through the
same connection** — one repo to write, no new credential, and §7's tool factory
takes it as one more entry. Deliberately deferred rather than designed out.

### Acceptance criteria

- [x] Both repos exist in the shared Demo workspace with `is_public=False`.
- [x] Neither repo name collides with the agent's own deploy-owned Context Hub
      repo (`role-aware-docs-assistant`), which `mda deploy` syncs. A collision
      would let a deploy overwrite a corpus.
- [x] `mda deploy` leaves both corpus repos untouched — verified by checking
      their `commit_hash` across a deploy.
- [x] Page counts are **computed** from the pulled snapshot and logged, never
      asserted as literals; the table above is a sanity range.
- [x] No corpus name, repo name, or prefix is written anywhere but
      `contracts/grants.py` (C2).

---

## 3 · The engineering corpus is invented

**Nothing in this corpus describes a real system, a real procedure, or a real
person.** It is a fictional internal environment for a team that does not
exist — the same approach as the fictional carrier in the openwiki insurance
POC.

Two reasons, and the first is not about the demo:

1. **A demo leaks.** It gets screenshotted, recorded, shown to customers, and
   cloned by other engineers. Real internal procedure placed in one travels
   further than the session that created it, and cannot be recalled.
2. **Invented content makes the demo work.** Because it exists nowhere public,
   no breadth of public documentation can reach it — so the employee's refusal
   is structural rather than a partition artifact (§1.2). And because we write
   it, the contrast can be made sharp on purpose.

### What it contains

About fifteen short pages. Each one answers a question public documentation
cannot, and names invented specifics so the answer is unmistakably internal.

Twelve pages, as built. The fictional environment is kept consistent across
them and is documented in `corpus/README.md`: team **Platform Agents**, change
tickets `PLAT-<n>`, CI workflow `agent-checks`, pipeline `deploy-agents`,
environments `dev`/`staging`/`prod-us`/`prod-eu`, secret store **Keyring**,
rotation `platform-agents-oncall`, channel `#platform-agents-releases`.

| Page | Answers |
|---|---|
| `deploy-to-production.md` | the ticket, the approval, the region order, the freeze window |
| `environments.md` | the four environments and the rules that are not negotiable |
| `on-call-escalation.md` | tiers, response targets, who is woken when |
| `break-glass.md` | recovering a stuck deployment — roll back before diagnosing |
| `rotate-a-credential.md` | routine rotation, and the different order under suspected exposure |
| `eval-gate.md` | what must pass before a prompt change merges |
| `dependency-standards.md` | pinning rules and why upgrades are their own ticket |
| `resilience-standards.md` | retries, checkpointing, timeouts; what is forbidden |
| `observability-standards.md` | tracing required in production; how to read a trace in an incident |
| `agent-code-standards.md` | framework constructs, context rules, review requirements |
| `documentation-standards.md` | the canonical docs domain; how to write a runbook |
| `incident-review.md` | when one is written, what it contains, required actions |

**Substance from Chat LangChain Lite, specifics invented.** The eight
`SAFE_PATTERNS`, six `ANTIPATTERNS`, and the deployment and evaluation guides
supplied the engineering opinions; the pages add the team-specific skin — the
CI job, the ticket prefix, the environments — that makes them non-public. So
this is assembled rather than invented from nothing, which is why it took an
hour and not a day.

### Beat 1 and beat 2 are different pages, and the test knows which

Not every page can carry the refusal. `resilience-standards.md` asks about
retry middleware, and the product corpus's `middleware.md` genuinely discusses
retry middleware — so that question hits **both** corpora.

That is not a flaw; it is beat 1. The classification is explicit in
`tests/test_corpus_separation.py`:

| Class | Requirement | Pages |
|---|---|---|
| **beat 2** (clean) | the product corpus returns **nothing** above `MIN_SCORE` — the employee provably cannot answer | 11 of 12 |
| **beat 1** (overlap) | both corpora answer, with **different** top pages: generic versus ours | `resilience-standards.md` |

`PRODUCT_OVERLAP` is asserted in both directions, so a page that drifts between
classes fails the test rather than quietly weakening the demo.

Style constraints, so it reads as real internal writing and not as marketing:

- Procedural and terse. Steps, commands, names. No preamble.
- Every page names at least one invented internal identifier, so an answer
  drawn from it is visibly internal.
- No page restates something public documentation already covers. If a page
  could have been written from `docs.langchain.com`, it belongs in
  `productDocs` instead, and having it in both is how beat 1 gets muddy.
- Length bands are guidance, not gates: a page that is short because the
  procedure is short is correct.

### Acceptance criteria

- [x] No page contains a real service name, hostname, credential, person, team,
      or procedure. **Still needs a human read** before the demo is shown —
      written to be fictional, not yet reviewed by anyone but its author.
- [x] Every page names at least one invented internal identifier.
- [x] Every page has a question in `ENGINEERING_QUESTIONS`, and a page added
      without one fails the test.
- [x] Every beat-2 question returns nothing above `MIN_SCORE` in `productDocs`;
      every overlap page is asserted to still overlap. Mechanical, 27 assertions,
      offline.
- [x] The corpus is committed under `corpus/engineering/` as the source of
      truth and pushed by `corpus/seed.py`, so it is reviewable in a PR rather
      than only in the Hub UI.
- [x] `corpus/README.md` records that the corpus is fictional and lists the
      invented names, and is **excluded from the push** so the agent cannot
      retrieve and quote it.

---

## 4 · The product corpus comes from Chat LangChain Lite

`chat-langchain-lite` already holds its documentation content as Python dicts
in `agent/tools.py`: six concept entries and four setup guides. That content is
written, self-contained and public, so it **is** the product corpus.

```bash
python corpus/extract_product.py      # -> corpus/product/*.md  (10 pages)
```

The extractor parses the source module with `ast` and reads the dict literals
directly — nothing from it is executed, so `langchain_core` need not be
installed to run it.

### What choosing this source removed

An earlier draft curated pages from `docs.langchain.com` over an allowlist of
path prefixes, walking `llms.txt` to build an index. All of that is gone:

| Gone | Why it no longer exists |
|---|---|
| the `llms.txt` walk and its non-recursive-index quirks | the content is local |
| the page allowlist and its exclusions | the corpus is exactly CLL's ten topics |
| upstream fetch failures, partial corpora, refresh TTLs | no network at seed time |
| "is the public corpus too broad to leave beat 2 intact?" | it is ten pages, and they are known |

It also makes the demo literally *"replicate Chat LangChain Lite, but
role-aware"*, which was the original framing.

### The consequence to accept

**The shared corpus is small — ten topics.** A question outside them is refused
by *both* identities. For a scripted demo that is fine and honest, but the
demo's questions have to live inside those ten topics. Phase 05's question
selection gets easier, not harder: the surface is small and knowable.

```text
langchain · langgraph · langsmith · deep-agents · middleware · tracing
installation · environment · deployment · evaluation
```

### One thing deliberately not carried over

CLL's `SAFE_PATTERNS` contains an intentional bug for its own demo: it
recommends `python.langchain.com` and `js.langchain.com` as canonical
documentation, which are stale domains. `engineering/documentation-standards.md`
states `docs.langchain.com` instead. Do not "restore" the original wording.

### Acceptance criteria

- [x] `python corpus/extract_product.py` writes 10 pages and prints their sizes.
- [x] It executes nothing from the source module — `ast.literal_eval` only.
- [x] Titles are properly cased: a `DISPLAY` map, because `str.title()` renders
      "langgraph" as "Langgraph" and that then appears in the agent's answers.
- [x] Re-running rewrites the directory from scratch, so a removed source entry
      cannot leave a stale page behind.
- [x] The stale-domain bug is not propagated.

---

## 5 · The connection

One connection, holding a **workspace-scoped, read-only service key**.

```bash
cd agent
LS_CORPUS_SERVICE_KEY=lsv2_sk_... \
  uv run mda connections create context-hub-corpus \
    --secret-from-env LS_CORPUS_SERVICE_KEY
uv run mda connections list
```

### Which credential, and the gap we are shipping with

A service key is the right answer and a dedicated PAT is the one available.

| | Dedicated PAT *(current)* | Service key (`lsv2_sk_`) *(target)* |
|---|---|---|
| Permissions | inherits its creator's, across their whole org | scoped to chosen workspaces |
| Owner | a person — dies on rotation or departure | the workspace |
| Read-only | **no** | yes |
| Expiry | set at creation | configurable, including never |
| Blast radius if leaked | that person's org access, **read and write** | read access to one workspace |

Creating a service key needs `organization:pats:create` +
`workspaces:manage-keys`, which was not available during this build. So the
connection currently holds a **PAT created specifically for this demo, with an
expiry set**, and that is a recorded gap rather than a silent one.

**Why shipping the PAT is acceptable for now, and what makes it safe to fix
later:** the connection's value rotates *without a redeploy*, because authored
tools resolve it per run (§1.1). So swapping the PAT for a read-only service
key is a one-command change with no code edit and no deploy — which is exactly
the property this design was chosen for, now doing real work.

**Two obligations that follow, not optional:**

- **Swap before the demo runs in front of anyone.** Ask a Workspace Admin on
  the target workspace for a workspace-scoped, read-only service key.
- **Record the PAT's expiry date** in `docs/DE-onboarding.md` next to the
  freeze date. An expiring credential kills the demo silently, months later,
  and the symptom looks like "the agent got worse".

**Honest over-privilege note, true of either credential:** Context Hub
permissions are workspace-level, so no key can be scoped to just these two
repos. A key that can read the corpora can read everything in the
workspace — traces, datasets, other repos, deployments. On Enterprise, attach a
custom role limited to context reads. Otherwise accept it and write it down.

### Three keys, three jobs

Worth stating because conflating them causes confusing failures:

| Key | Authenticates | Ever in the deployment? |
|---|---|---|
| Your PAT | `mda deploy` | **No** — reserved, not uploaded |
| The corpus service key | the tools, to read Context Hub | Yes, via the connection |
| Each DE's own key | that DE, to the deployment | No — it never leaves their UI's server |

DEs never handle the corpus credential and need no Context Hub access of their
own.

### The ordering trap still applies

Agent-owned credentials belong to the deployment, so this runs **after** the
phase 01 bootstrap deploy ([00-overview.md](./00-overview.md) §7).

### Local development

`connections.get` resolves from `MDA_DEV_<SLUG_UPPER>` when running locally
(`_connections.py:116,352`):

```text
# agent/.env  (local only)
MDA_DEV_CONTEXT_HUB_CORPUS=lsv2_sk_...
```

### Acceptance criteria

- [x] `mda connections list` shows `context-hub-corpus` (kind `secret`), created after the bootstrap deploy as the ordering trap requires.
- [x] The stored credential can read both corpus repos in the target
      workspace, verified by a live pull rather than by inspecting the key.
- [ ] **Before the event:** *(blocked — `workspaces:manage-keys` denied for
      this account, confirmed by a 403 from `POST /api/v1/api-key`)* the
      stored credential is a service key
      (`lsv2_sk_`), workspace-scoped and read-only, and a write attempt with it
      fails. Until then the PAT gap is recorded in `docs/DE-onboarding.md` with
      its expiry date.
- [ ] Swapping the credential changes behaviour with **no redeploy**. *Blocked by the same 403 as above.* The claim is **argued but not demonstrated**: the tools resolve the connection per run and cache for 60 seconds, so a changed value takes effect on the next pull — but until someone rehearses it, do not promise the rotation beat on stage.
- [x] `grep -rn 'connections.get' agent/` shows `{"type": "agent"}` at every
      call site and no `"user"` (C11).
- [x] `mda dev` reads both corpora using only `MDA_DEV_CONTEXT_HUB_CORPUS` — verified with a single question that cited a page from each.
- [x] An invalid credential makes the tools report the corpus unreachable — verified locally, and it exposed the silent-death bug above. **The no-redeploy rotation itself is still unproven** and is a ph. 05 rehearsal beat: change the connection value, run again, watch it take effect.
- [x] No key appears in the repo, in `.env.example`, or in any trace.

---

## 6 · Reading a corpus

```python
# agent/tools/corpus.py  (shape)
from langsmith import AsyncClient
from managed_deepagents import connections

from contracts.grants import CORPORA


async def _snapshot(prefix: str) -> tuple[str, dict[str, str]]:
    """Pull one corpus. Returns (commit_hash, {path: content}).

    The key is resolved per run from the connection — nothing ambient, nothing
    personal. `pull_agent` returns every file's content, so one call gives both
    the index and the bodies.
    """
    repo, slug = CORPORA[prefix]          # the only source of both (C2)
    key = await connections.get(slug, {"type": "agent"})
    snap = await AsyncClient(api_key=key).pull_agent(repo)
    return snap.commit_hash, {p: f.content for p, f in snap.files.items()}
```

Four things this depends on, all now verified against the live workspace:

0. **The identifier must be owner-qualified.** `pull_agent("product-docs")`
   returns `400 invalid repository reference`; `pull_agent("chat-lc-lite/product-docs")`
   works. The docs say a bare name resolves against the current workspace
   owner; it does not here. `contracts.grants.repo_and_slug()` returns the
   qualified form, so no call site has to remember.

1. **`pull_agent` returns file contents, not just a listing** — confirmed by
   the SDK docs (`agent.commit_hash`, `list(agent.files)`), by
   `chat-langchain-lite` in production, and by a live round-trip in this
   workspace: pushed two files privately, pulled them back with contents and a
   commit hash intact, deleted the probe.
2. **`connections.get(...)` returns a lazy reference** resolved inside a run. It
   cannot be awaited at import.
3. **Context Hub methods need `langsmith>=0.7.35`** (Python). Pin it; the
   build resolved `langsmith 0.14.0`.

4. **The client must be given credentials explicitly.** A bare `Client()`
   silently fell back to ambient credentials during phase 01 and targeted a
   *different* workspace, returning one unrelated repo — which reads as "the
   corpus did not sync" rather than "wrong account". Pass `api_key=` from the
   connection and set `LANGSMITH_WORKSPACE_ID`.

Minor: `list_agents(limit=…)` caps at **100**; a larger limit returns `422`.

### Caching, and what rotation actually costs

The snapshot is cached in memory per corpus with a **60-second** TTL
(`CORPUS_CACHE_TTL`). A failed refresh keeps the previous snapshot; a failed
*first* pull raises from `snapshot()`, so the cause stays visible in the trace
and the logs — but the **tools catch it** (see below).

### An unreachable corpus must not kill the run

Found by pointing the corpus credential at a deliberately invalid key.

A raising tool did **not** become a `ToolMessage`. LangGraph's tool-error
handling re-raised the `LangSmithError` from the pull, the run died, and
`/threads/{id}/runs/wait` answered:

```text
HTTP 200
{"__error__": {"error": "LangSmithError", "message": "An internal error occurred"}}
```

No messages, no tool result, HTTP 200. On stage that is a **silent agent** —
indistinguishable from the model having nothing to say, and the worst possible
failure shape.

So each tool converts an unreachable corpus into a readable result:

```text
This corpus is temporarily unreachable (LangSmithError). Tell the user the
documentation cannot be reached right now, and do not answer from memory.
```

With the fix, the same bad credential produces: *"I can't answer this from
documentation right now because the engineering runbook corpus is temporarily
unreachable… I shouldn't infer our on-call escalation path from memory."*
Degraded, honest, and visibly not a crash.

Two consequences worth carrying forward:

- **Any transient Context Hub blip would otherwise kill a run mid-demo**, not
  just a bad credential. This is a resilience fix, not a credential fix.
- **Phase 06's UI must check for `__error__`** on an otherwise-200 response
  (ph. 06 §5), or a dead run renders as an empty bubble.

**Correcting an earlier overclaim in this spec:** rotation does *not* take
effect "immediately". A cached snapshot keeps serving until it expires, and
resolving the credential is not the same as exercising it — `connections.get`
returns the stored value whether or not the provider still honours it. So the
honest claim is:

> Rotating or revoking the credential takes effect **on the next pull** —
> within the cache TTL, or immediately on a cold process. No redeploy.

That is still the thing worth demonstrating, and the TTL is 60 seconds
precisely so the demo does not require a wait.

### `commit_hash` is not a content hash

Measured, because the earlier draft assumed otherwise: **two repos with
completely different content report the same `commit_hash`**
(`product-docs` at 10 pages / 4,439 chars and `engineering-runbooks` at 12
pages / 15,653 chars both returned `13ac11f11da3`). The value appears to be
positional — every repo's first commit shares a hash, every second commit
shares another.

Consequences:

- **Usable** to pin or identify a version *within one repo*, which is what
  `pull_agent("owner/repo", version=…)` needs.
- **Not usable** as a content fingerprint, and not as a cache key across
  corpora — keying a shared cache by hash alone would collide. The cache is
  keyed by corpus prefix, and the hash is carried for display and pinning only.

### Every push creates a commit

Also measured: pushing byte-identical content advances the commit hash. So
`corpus/seed.py` pulls first and **skips an unchanged push**; without that, a
re-run adds a commit that says nothing and the history stops being readable.

### Bodies change what search can do

Because the snapshot includes content, search covers **titles, paths and
bodies** — not just an index. That is better retrieval than the earlier
`llms.txt` design could offer, and it removes the synonym fragility that made
`MIN_SCORE` delicate (§7).

### Acceptance criteria

- [x] A tool reads both repos through the connection, with no ambient
      `LANGSMITH_API_KEY` dependency. Verified by unsetting it locally.
- [x] `commit_hash` appears in the trace, so a run is attributable to an
      exact corpus version. Wired in **v5**: `tools/corpus.py:stamp_provenance`
      writes `{prefix}_commit` onto the **tool's own span** via
      `get_current_run_tree()`. Verified live — `productDocs_commit` and
      `engineeringDocs_commit` are both present and distinct.
- [x] A simulated failure during *refresh* keeps serving the previous snapshot;
      a failure on *first* pull surfaces as a tool error naming the corpus.
- [ ] **Revoking the key mid-session causes the next pull to fail.**
      *Blocked, not skipped.* The rehearsal was attempted in ph. 05 and the
      credential could not be changed: `mda connections delete` returns
      **403 "not authorized to access Agent Auth connections"**, and the CLI
      has no `update`, so rotation means delete-then-create. The attempt
      failed safely — the connection was never modified and the deployment
      kept answering. Needs an account with connection-delete rights.
- [x] Snapshot size and pull latency are measured and recorded. If a pull is
      slow enough to be felt, the corpus is too big and §4's allowlist narrows.

---

## 7 · The four tools

Two per corpus. Two, not three, and not one: `search_docs` alone forces answers
from titles, `fetch_doc` alone forces path guessing.

```python
# agent/tools/corpus.py  (shape)
from langchain.tools import tool


def corpus_tools(prefix: str, blurb: str) -> list:
    """Build the (search, fetch) pair for one corpus.

    The prefix is closed over and resolves to a repo through CORPORA; neither
    is ever a tool parameter — see §8.
    """

    @tool(f"{prefix}__search_docs")
    async def search(query: str, limit: int = 8) -> str:
        """Search {blurb} by keyword. Returns matching page titles and paths.

        Fetch a page with the matching fetch tool before making a claim from it.
        """

    @tool(f"{prefix}__fetch_doc")
    async def fetch(path: str) -> str:
        """Fetch one page from {blurb} as Markdown."""

    return [search, fetch]


TOOLS = [
    *corpus_tools("productDocs", PRODUCT_BLURB),
    *corpus_tools("engineeringDocs", ENGINEERING_BLURB),
]
```

`tool()` takes an explicit name as its first argument, so the
`{prefix}__{name}` convention that MDA's MCP prefixing gave for free is kept
deliberately — **and phases 03–06 need no changes**, because they match on the
same strings.

### Docstrings are part of the demo

They are what the model reads to choose a tool, and what appears in the trace.
Two constraints:

1. **Each tool describes its own corpus, never the other.** A docstring
   mentioning internal runbooks would tell an employee-role model that they
   exist — inviting exactly the speculation `instructions.md` forbids (C7).
2. **The blurb is generated from config**, so the two pairs are
   distinguishable. Identical descriptions make the model pick by coin flip.

### Search

`tools/search.py`. Tokenize, stem, score each query term once at its strongest
field, then scale by coverage:

```python
W_TITLE, W_PATH, W_BODY = 3.0, 2.0, 1.0
MIN_SCORE = 1.6              # calibrated by the separation test, not chosen

score = sum(best_field_weight(term) for term in matched) * (matched / total)
```

Synonyms apply at half weight, so a synonym can surface a page but never
outrank a literal match.

### Three bugs the separation test caught, which reading the code did not

The first scorer passed casual inspection and failed 7 of 26 assertions. Each
failure was a real defect, and each is worth knowing because they are the
obvious way to write this:

**1 · Substring matching is directional.** `"evals" in "the eval gate"` is
False, so `eval-gate.md` was invisible to the question it exists to answer.
Fixed by tokenizing both sides and comparing light stems — enough to make
`evals`/`eval` and `approvals`/`approval` one term, without a linguistics
dependency.

**2 · One title hit beat three body hits.** With per-field weights alone, a
page whose *filename* contained one query word outranked the page whose text
answered the whole question: *"Is tracing required in production here?"*
returned `deploy-to-production` over `observability-standards`, purely because
"production" is in the former's name. Fixed by the coverage factor — how much
of the question a page accounts for.

**3 · Repetition inflated scores.** Counting every occurrence let one
frequently-mentioned word outweigh breadth. Each query term now contributes
once.

`MIN_SCORE` was then set from data rather than taste: the lowest value at which
every beat-2 question stays unanswered in the product corpus while every
engineering question clears the bar in its own.

### Measured behaviour

| Query | `productDocs` | `engineeringDocs` | |
|---|---|---|---|
| "How do I deploy a managed deep agent?" | `deep-agents` | `deploy-to-production` | ← both score, **neither answers** (ph. 05 §4) |
| "What is our on-call escalation path?" | **nothing** | `on-call-escalation` (7.0) | beat 2 |
| "What is LangGraph?" | `langgraph` | **nothing** | product only |

The second and third rows are the demo: each corpus is silent on the other's
territory.

### The threshold is load-bearing for the refusal

### The threshold is load-bearing for the refusal

Without `MIN_SCORE`, a query the corpus does not cover still returns its
best-scoring page — a real page, entirely irrelevant.

Hand that to the model and beat 2 dies: instead of refusing, the agent fetches
an unrelated page, finds nothing, and produces a confused half-answer. So below
`MIN_SCORE`, `search_docs` returns **no results and says so**:

```text
No pages in this corpus match that query. This corpus covers public LangChain
product documentation.
```

An explicit "this corpus does not cover it" is a fact the model can act on. A
weak hit is a trap.

### Acceptance criteria

- [x] Exactly four tools, named
      `{productDocs,engineeringDocs}__{search_docs,fetch_doc}`.
- [x] Each rendered description names its own corpus and no other.
- [x] No tool takes a role, a repo, a scope, or an identity parameter (§8).
- [x] For every engineering page (§3), its question scores above `MIN_SCORE` in
      `engineeringDocs` and below it in `productDocs`.
- [x] `MIN_SCORE` is calibrated by a table test over those pairs; changing a
      corpus re-runs it.
- [x] `fetch_doc` accepts a path with or without a leading slash and with or
      without `.md`.
- [x] A path not in the corpus returns "not found in this corpus",
      distinguishable from an empty search — the right next action differs.

---

## 8 · Scope enforcement is structural

Earlier designs enforced corpus boundaries with path-prefix checks. That is
gone, and what replaces it is stronger.

**Each tool closes over exactly one repo name. There is no code path that takes
a repo as an argument.** So:

- A tool cannot be asked for another corpus — not by the model, not by a
  crafted path, not by prompt injection. The repo is not in the tool's input
  surface at all.
- Path traversal is meaningless: paths are **keys in a pulled dict**, not
  filesystem or URL paths. `../` is either a key or it is not.
- For the engineering corpus the credential is a second, independent boundary:
  without the service key the content is unreadable, full stop.

Contrast with the three-server design, where a corpus boundary was a prefix
comparison that a bug could get wrong.

### Acceptance criteria

- [x] `grep -n "repo" agent/tools/corpus.py` shows the repo only as a factory
      argument, never as a tool parameter or a value read from tool input.
- [x] `engineeringDocs__fetch_doc("../product-docs/index.md")` returns
      "not found in this corpus" — it is a missing key, not a traversal.
- [x] A crafted `path` cannot cause a pull of a different repo. Unit-tested.
- [x] Tool unit tests run with no network and no credential, against a fake
      snapshot.

---

## 9 · Registering the tools

The one real difference from MCP connectors: **authored tools are not
discovered.** Import them and pass them in.

```python
# agent/agent.py  (ph. 04 owns the final version)
from tools.corpus import TOOLS

agent = define_deep_agent(
    name="role-aware-docs-assistant",
    model="langsmith:openai/gpt-5.6-luna",
    tools=TOOLS,
    ...
)
```

Three notes:

- **`tools/mcp.py` is a reserved filename** — an MDA managed declaration. Our
  module is `tools/corpus.py`. A stray `tools/mcp.py`, even empty, would enable
  an MCP connector.
- **All four tools are in the agent's list on every run**, whoever calls. The
  only thing that varies per caller is what middleware leaves in
  `request.tools` (ph. 03). Gating is a middleware responsibility, full stop.
- **`langchain` must be a direct dependency.** `mda init` pins only
  `managed-deepagents`, and the runtime bundles LangChain for the *deployment* —
  but `from langchain.tools import tool` then fails locally with
  `ModuleNotFoundError`, which reads as a broken tools module rather than a
  missing dependency. The project declares `langchain>=1.0` (resolved 1.4.2),
  `langsmith>=0.7.35` and `httpx`, plus `pytest` in a dev group that is not
  shipped.

### Acceptance criteria

- [x] `uv run mda build` compiles with `tools=TOOLS`.
- [x] Exactly four tools load, named `{productDocs,engineeringDocs}__{search_docs,fetch_doc}`, each with its own corpus in its description.
- [x] A test asserts every prefix in `GRANTS` has at least one loaded tool, and
      every loaded docs tool's prefix is in `GRANTS`'s union. This is what
      catches a renamed prefix before it silently ungates a corpus in phase 03.
- [x] `agent/tools/mcp.py` does not exist.

---

## 10 · Redeploy and verify

```bash
cd agent && uv run mda deploy
```

Against the deployment. All five measured on the live revision:

| Ask | Measured |
|---|---|
| "What documentation can you search?" | Names **both** corpora from its tool descriptions, with no search call — the descriptions are doing their job |
| "Do we require retry middleware on model calls?" | Answers **"Yes, required on every model call"** from `resilience-standards.md`, with the reason and the prohibition |
| "What is our on-call escalation path?" | Answers from `on-call-escalation.md`, quoting the rotation name, all three tiers, response targets and the ticket rule |
| "How do I deploy a managed deep agent?" | Searches **both** corpora, then refuses — neither covers MDA. This is the row that proves both corpora are reachable in one run |
| "Fetch the page 'nonexistent-thing'" | *"does not exist in the public LangChain product documentation corpus"* — a clean miss, not a crash |

### The finding: it already prefers the specific corpus

Earlier drafts of this section expected a **blended** answer — the agent
reaching across both corpora and merging them, which phase 03 would then split.

That is not what happens. With **no gating and no injected ordering**, asked
about the retry requirement, the agent searched `engineeringDocs` three times,
fetched three pages from it, and never touched `productDocs`. It preferred the
more specific corpus on its own.

Two consequences, both good:

- **Beat 1 is more robust than the design assumed.** `PRIMARY_ORDER`
  (ph. 03 §5) reinforces a preference the model already has rather than
  creating one, so the beat does not rest entirely on prompt wording.
- **The "before" picture is a preference, not a blend.** When narrating phase
  03, the honest framing is *"it already chose the internal answer; now watch
  the employee be unable to"* — the change is in what is **reachable**, which
  is the enforced half anyway.

Do not read this as making the ordering unnecessary. It was measured on one
question with one model; the ordering is what makes the behaviour specified
rather than lucky.

### Acceptance criteria

- [x] All five rows behave as described against the **deployment**.
- [x] One trace shows tool calls to both corpora in a single run (the MDA-deploy row).
- [x] Both corpora are reachable: at least one successful `fetch_doc` each.
- [x] `commit_hash` for both corpora appears in the trace. **Wired in v5**, and not where this line expected: not as run metadata from middleware (that route was tried in v3 and never reached the root run) but on each **tool span**, written from inside the tool. Better placement — a tool is its own run, and it is where a reader asking "which document answered this?" is already looking. The model never sees the hash, which is deliberate: a commit hash in tool output is something it might quote at the user.

---

## 11 · What phase 03 inherits

| Guarantee | From |
|---|---|
| Four tools named `{productDocs,engineeringDocs}__{search_docs,fetch_doc}` | §7, §9 |
| One agent-owned connection holding a read-only service key | §5 |
| Both corpora private, in the shared Demo workspace | §2 |
| The engineering corpus is invented and has no public counterpart | §3 |
| Corpus boundaries are structural — the repo is closed over, not a parameter | §8 |
| `contracts/grants.py` prefixes match the deployed tool names | §7 |
| A blended, un-gated answer exists as the "before" picture | §10 |
| The tool list is identical on every run, whoever calls | §9 |
| Credential rotation takes effect without a redeploy | §5, §6 |

Phase 03 must **not** assume: that any role exists, that `context_schema.py`
exists, or that Context Hub is reachable from its test environment — it builds
against fakes with the real names (overview §6).

## Open items leaving this phase

| # | Item | Owner |
|---|---|---|
| O2.1 | ~~Where are the three MCP servers hosted?~~ **Closed: nothing is hosted.** Both corpora are Context Hub repos (§1) | closed |
| O2.2 | ~~Should `publicDocs` include `/oss/*/integrations/`?~~ **Closed: no** (§4), and the corpus is now curated and renamed `productDocs` (§2) | closed |
| O2.3 | ~~Is keyword search good enough?~~ **Closed: yes, with synonym expansion, dedupe and `MIN_SCORE`** (§7). Re-measure against the populated corpora, since the numbers were taken against a different corpus shape | closed, re-measure |
| O2.4 | Snapshot cache TTL, and whether a pull is fast enough to skip caching entirely (§6) | ph. 02 build time |
| O2.5 | ~~A "Tool Server" tab with per-tool toggles in the LangSmith UI?~~ **Closed: no such tab**, and it would not have been usable — a UI toggle is static config, while this demo varies the surface per run by caller | closed |
| O2.6 | **Context Hub size limits are unknown.** ~55 pages across two repos should be unremarkable, but verify before writing the full corpus: push a padded repo and confirm both push and `pull_agent` behave | ph. 02 · **verify first** |
| O2.7 | Whether the third (`employeeDocs`) corpus gets added back (§2). One repo, same connection | ph. 05 |
| O2.8 | Who writes the ~15 invented pages, and who reviews them for accidental realism (§3) | **needs an owner** |
