# Phase 05 — Deploy the canonical agent

> **Status:** COMPLETE · **Depends on:** [04](./04-agent-wiring.md) all · [00-overview.md](./00-overview.md) C9, C10
>
> Promote the working local build to the one deployment every DE points at,
> prove the trace contract against it, write the onboarding doc, and pick the
> demo question from real runs.

## What this phase delivers

- One canonical deployment in the shared Demo workspace, with a stable URL.
- A LangSmith project where **a trace answers the demo's questions without
  opening the repo** (C9).
- `docs/DE-onboarding.md`: what a DE needs, what they must not do, and what
  will surprise them.
- A demo script built from observed runs, not from hope.

## What this phase does not deliver

| Not here | Where |
|---|---|
| The UI | ph. 06 |
| Any change to gating behaviour | ph. 03 — if this phase wants one, it goes there and comes back through 04 |

---

## 1 · One deployment, and why it is already the right one

The deployment to promote is the one phase 01 §7 bootstrapped: same workspace,
same name, and the owner of the connection from phase 02.

There is no "promotion" step to perform, which is the point of having done the
bootstrap correctly. If the bootstrap landed in a personal workspace, this is
where that costs a full redo: a new deployment means a new connection and a new
URL for every DE.

```bash
cd agent
uv run mda deploy
uv run mda logs            # tail while the revision comes up
```

`--deployment-type prod` exists and is tempting. It is **not** used here: this
is a demo that will be redeployed repeatedly during rehearsal, and a dev
deployment redeploys faster with fewer guardrails. Record the choice so nobody
"upgrades" it the morning of.

Use `--no-wait` only in CI. It skips schedule reconciliation and exits before
`DEPLOYED`, so a local operator loses the one signal that says the thing works.

### The context-strategy decision, made once

Phase 01 §7 established it: **project files are the source of truth.** Anyone
who edited `instructions.md` in the Hub during rehearsal copies the wording
back into the repo first, then deploys with `--context-strategy overwrite`.

The failure mode this prevents: a deploy the night before silently keeping a
Hub-edited prompt that nobody has read, in a demo whose entire premise is that
the Hub and the repo are in sync.

### Acceptance criteria

- [x] The deployment is in the shared Demo workspace under
      `role-aware-docs-assistant`, and `mda connections list` from `agent/`
      shows the same slug it did in phase 02 (`context-hub-corpus`).
- [x] The dashboard URL and the Agent Server API URL are recorded in
      `docs/DE-onboarding.md` §4.
- [x] A redeploy does not require recreating the connection or re-seeding a
      corpus — verified across the v5 deploy.
- [x] `agent/README.md` records the `--deployment-type` and
      `--context-strategy` decisions with their reasons.
- [x] `mda logs` is reachable and shows the live revision.

---

## 2 · Post-deploy verification

Run the overview §8 script against the deployment, then these:

| Check | Pass |
|---|---|
| Both roles answer the canonical question | Answers differ; each cites only granted paths |
| No role declared | Run rejected; no model call |
| Unknown role | Same |
| Employee asks an engineering question | Refusal naming its own corpora |
| Engineer asks a product-docs question | **Answers** — grants are nested (C2) |
| `fetch_doc` for a page in the other corpus | "Not found in this corpus" — a missing key, not a traversal (C4) |
| Two different DE API keys | Both work (C10) |
| A key from another workspace | 401/403 |

**The employee refusal row is the one that carries the demo.** With nested
grants (C2) it is the only place the difference is *enforced*: the engineer can
reach everything the employee can, so nothing the employee does is unavailable
to the engineer.

That makes this a permission *level* demo rather than a permission *surface*
one, which is the honest reading of nested grants and is how a real org
usually works. Narrate it that way: *"the employee's tools are a subset — and
here is the question that proves it."* The engineer-prefers-the-runbooks beat
is real and worth showing, but it rests on the ordered prompt section
([03](./03-identity-and-middleware.md) §5), not on enforcement, and saying
otherwise is the one claim that would not survive scrutiny.

### Acceptance criteria

- [x] Every row passes **against the deployment**, not locally.
      `agent/tests/verify_deployment.py` runs the matrix and writes
      `tests/verification.json`. **11/11 against v5.**
- [x] Each check's trace URL is recorded — in `tests/verification.json` for
      every row, and the demo-script runs are linked from
      `docs/DE-onboarding.md` §5 as reference runs.
- [x] Layer 2 fires zero times across the whole set (C6) — asserted as a row
      of the matrix, not checked by eye.

Two rows could not be tested as written, both for the same reason:

| Row | Why not |
|---|---|
| Two different DE API keys | The build account cannot mint a second key: `POST /api/v1/api-key` returns 403 `workspaces:manage-keys`. **What C10 actually claims is tested**: one key, two roles, two disjoint tool surfaces — the role travels with the request, not with the key. A second key would exercise LangSmith's auth, not this build's. |
| A key from another workspace | No key from another org was available. Substituted: a syntactically valid key belonging to nobody (**403**) and no key at all (**401**). Both reject before the agent runs. |

---

## 3 · The trace contract, verified (C9)

The claim: *"LangSmith traces show which tools and connections were available
and invoked for each role."* Verify it the way the audience will — by opening a
trace cold.

Hand someone who has not seen the repo a single trace URL and ask:

1. Which identity made this run?
2. Which documentation corpora could it reach?
3. Which did it actually call?
4. Was anything denied?

All four must be answerable from the LangSmith UI in about a minute.

| Question | Where it is answered | Provided by |
|---|---|---|
| 1 | Run metadata `role`, `display_name` — mirrored from context by MDA, not written by us | C9 |
| 2 | The model call's tool list, and the "Granted access" system section. **Not** a `granted` metadata key — it is not obtainable (C9) | ph. 03 §5 |
| 3 | Tool call spans, prefixed by server name | ph. 02 §9 |
| 4 | A `ToolMessage` with `status="error"` — absent in a clean run | ph. 03 §6 |

**Connections are the weak spot.** A trace shows tool calls to
`engineeringDocs__fetch_doc`; it does not show that the call carried the
`engineering-docs` credential. The honest way to close that on stage is to
show `mda connections list` next to the trace, and to point out that the server
name in the tool prefix maps one-to-one to a connection slug in
`contracts/grants.py`. Do not claim the trace displays credential resolution.

### What LangSmith does and does not show

**Everything in this build is visible in LangSmith**, which was not true of
earlier designs — the corpora used to be containers on third-party hosting with
no LangSmith presence at all. Now:

| Surface | Shows |
|---|---|
| Deployments | one deployment, `role-aware-docs-assistant` |
| **Context Hub** | four repos: the agent's own (`instructions.md`, `skills/`) plus `product-docs` and `engineering-runbooks` — **with commit history, browsable, and diffable** |
| Connections | one slug, `context-hub-corpus`, and its credential metadata |
| Traces | tool calls carrying the `{corpus}__` prefixes, and each corpus's `commit_hash` |
| `gateway` project | model calls routed through LLM Gateway (ph. 04 §6) |

The Context Hub row is the strongest screen in the demo and worth building a
beat around: **the instructions, the skills, and both corpora are all in one
place, versioned, editable, with history.** That is the "context is managed
centrally" claim made literal rather than asserted — and you can open
`engineering-runbooks` next to the trace that cited it.

Two things to show together, because neither is complete alone:

- **`mda connections list`** — the credential exists and is named.
- **A trace** — the tool was called and which corpus commit answered.

A trace does not display credential resolution, so do not claim it does. What
you *can* demonstrate live is rotation: revoke the key, run again, watch both
tools fail with no redeploy, restore it, run again (ph. 02 §5).

### Acceptance criteria

- [ ] **A cold reader answers all four questions from one trace.** *Needs a
      person who has not seen this repo.* The DATA is verified present —
      `agent/tests/verify_trace_contract.py` answers all four from the API for
      every run in the matrix (7/7 clean) — but "findable in about a minute by
      a stranger" is not something a script can assert, and claiming it from a
      passing API check would be exactly the kind of overreach §3 exists to
      prevent.
- [x] ~~`metadata.granted`~~ — not obtainable; read the model call's tool list.
- [x] Filtering the project by `metadata.role` splits the scripted runs
      cleanly — verified: `{engineer, employee}` across the matrix.
- [x] `demo_version` is present and correct on every run — uniform `v5`.
- [x] The connections caveat is written into `docs/DE-onboarding.md` §7 and
      repeated in §8 "what not to say".
- [x] Rewritten, because the premise changed: there are no docs *servers*
      any more. Both corpora are Context Hub repos and **are** visible in
      LangSmith. `docs/DE-onboarding.md` §4 names all four repos and §7 gives
      the one thing that genuinely is not visible — credential resolution —
      with the two screens that evidence it instead.

### One surprise, found while verifying this

A run rejected for an **invalid** role still carries that role in its root
metadata: a run sent with `role: "admin"` shows `metadata.role = "admin"`.
MDA mirrors the context it was given, and C1 rejects after that mirroring.

It reads like a leak and is not — the run died at the first middleware hook
with no model call and no tools. But a DE filtering the project on
`metadata.role` sees a third value, so it is written into
`docs/DE-onboarding.md` §6 rather than left to be rediscovered under
pressure.

---

## 4 · Choosing the demo question (O7)

Deferred to here on purpose: the right question is discovered from runs, not
designed in advance.

Nested grants raise the bar here, because the question now has to earn its
difference from *preference* rather than from availability. A question
qualifies when all five hold:

1. **Both roles answer it** — beat 1 is a difference demo, not a refusal demo.
2. **Both answers are correct**, and a knowledgeable audience member would
   accept each as the right answer *for that person*.
3. **The answers differ in substance**, not tone: different steps, different
   artifacts, different paths cited.
4. **The engineer reliably prefers the runbooks** — three runs out of three,
   verified from the traces. This is the criterion nesting makes hard, and a
   question that satisfies it does so because the runbook answer is *clearly
   more specific* for an engineer, not because the prompt shouted louder.
   Invented content helps here: a runbook page written to answer the question
   directly will out-score a general product page on the same terms.
5. **The difference is legible in fifteen seconds**, side by side, to someone
   who does not know the product.

Criterion 4 replaces the "neither role can produce the other's answer" test,
which nesting makes unsatisfiable: the engineer can always produce the
employee's answer. If no candidate passes it three-for-three, the honest move
is to lead with beat 2 (the refusal) and present beat 1 as "and it also
prefers the right source for you" — rather than to keep hunting for a question
that flatters the mechanism.

**Chosen, and verified live:**

> **"Do we require retry middleware on model calls?"**
> employee → **"No"** — the public docs describe middleware and list retries as
> one possible use, not a requirement; optional unless your app needs it
> (`middleware.md`)
> engineer → **"Yes, on every model call"**, with the reason (providers 429
> under normal operation) and the explicit prohibition on retry-less loops
> (`resilience-standards.md`)

A flat contradiction is the ideal shape: it needs no explanation from the
stage, and it resolves the instant the audience learns who was asking.

### Retrieval score is not answerability — screen offline, confirm live

The candidate this spec previously named, *"How do I deploy a managed deep
agent?"*, scored as a valid beat 1 offline: both corpora returned a page above
`MIN_SCORE`, with different top pages. **Live, it produced a double refusal.**

The model was right and the metric was wrong. Neither corpus actually covers
*managed* deep agent deployment: the product corpus comes from Chat LangChain
Lite and predates it, and `deploy-to-production.md` is about deploying this
team's agents generally. Both pages *scored*; neither *answered*.

So the offline scorer is a **screen**, not a verdict:

1. Score candidates offline — seconds, and it eliminates most of them.
2. **Run the survivors live, one identity at a time**, and read the answers.
3. Only then write one into the script.

A corollary worth stating: **this demo cannot answer questions about Managed
Deep Agents itself.** The product corpus has ten topics and MDA is not among
them. Do not take an MDA question from the audience on the assumption that the
public corpus covers it.

Test at least four candidates and keep two: a primary and a spare for when the
room asks for something else.

The second beat, same session — **and this is the one carrying the demo under
nested grants**:

> **"What is our on-call escalation path?"**
> engineer → answers from `engineering-runbooks/on-call-escalation.md`
> employee → refuses and names what it does have

This beat is now *structurally* safe in a way it was not in earlier drafts. The
engineering corpus is **invented** (ph. 02 §3), so its content exists nowhere
public — there is no page in `product-docs`, and no page on the internet, that
could answer it. The employee's refusal is not a partition artifact.

Earlier drafts drew both corpora from public documentation, and two candidates
died for reasons worth remembering:

| Candidate | Outcome |
|---|---|
| "How do I deploy a managed deep agent?" | **Rejected twice, for different reasons.** First run: a double refusal despite scoring as beat 1. Re-tested at v5: it now *answers* for both roles, and that is worse — see below. |
| "Should I turn on tracing in production?" | beat 2, not beat 1 — the product corpus returns nothing |
| "How should I pin my dependency versions?" | beat 2 |
| "What do I need to do before deploying to production?" | beat 2 |
| "Do we require retry middleware on model calls?" | **chosen — primary.** Opposite answers, both cited, stable 3/3 |
| "How should agent code be structured and reviewed?" | rejected — **unstable**: the engineer reached one corpus on two runs and two on the third, and the employee fetched nothing twice and seven pages once |
| "What environments do we have?" | **chosen — spare.** Stable 3/3, exactly one page per side |
| "What timeout should I use for a model call?" | rejected — passes every mechanical test and **fails criterion 2**: the engineer's answer opens "the available documentation does not specify a numeric timeout". Correct, and useless on stage |

#### The MDA question got *more* dangerous, not less

This spec previously recorded "How do I deploy a managed deep agent?" as a
double refusal. Re-tested against v5, three runs per role, it is now a clean
mechanical beat 1: both roles answer, the engineer prefers the runbooks 3/3,
and the answers differ.

**It is still rejected, and the reason is worth keeping.** The employee's
answer is a confident, well-formatted, entirely generic LangGraph deployment
procedure — `uv add deepagents`, write a `langgraph.json` — assembled from
`installation.md` and `deployment.md`. None of it is about Managed Deep
Agents. A refusal is a safe failure; a fluent wrong answer is not, because
nothing on screen marks it as wrong.

So the corollary hardens rather than relaxes: **do not take an MDA question
from the audience.** The product corpus has ten topics, MDA is not among
them, and the agent will not tell you that.

Both failure modes are now impossible for a question the engineering corpus was
written to answer — which is the point of authoring it. The remaining work is
choosing *which* runbook page makes the best beat, and verifying the pairing
mechanically:

- the question scores above `MIN_SCORE` in `engineeringDocs`, and
- below it in `productDocs`.

Phase 02 §3 requires that check for **every** page, so any runbook page is a
valid beat-2 candidate. Choose on stagecraft: pick the one whose answer is
shortest to read aloud and most obviously internal.

### Acceptance criteria

- [x] **Five** candidates tested against the deployment, three runs per role
      (30 runs), every trace URL recorded in `agent/tests/question_selection.json`.
- [x] Every candidate is **scored offline first** — fifteen of them, by
      `agent/tests/score_candidates.py`, which classifies each as beat 1,
      beat 2, inverted or dead in seconds.
- [x] The beat-2 question is verified in **both** directions: `7.00` in
      `engineeringDocs` and `0.00` in `productDocs` against `MIN_SCORE = 1.6`.
      Phase 02 §3 asserts this for every runbook page, so the refusal is
      structural rather than lucky.
- [x] The chosen primary satisfies all five criteria, checked one at a time —
      see the table below.
- [x] A spare is chosen ("What environments do we have?") and meets them too.
- [x] Both run three times per role. Primary: identical corpus sets on all six
      runs. Spare: exactly one page per side on all six.
- [x] Criterion 4 verified from the runs, **3/3** for both.
- [x] Not needed — criterion 4 is met. The order is still **beat 1 then beat
      2**, and §2 already says why beat 2 is the one that carries the
      mechanism.

#### The primary, criterion by criterion

| # | Criterion | Verdict |
|---|---|---|
| 1 | Both roles answer | Yes — neither refuses; each cites a page |
| 2 | Both answers correct *for that person* | Yes. The employee's "no requirement is stated" is true of the public docs; the engineer's "required on every model call" is true of `resilience-standards.md`. **Human judgement, not measured** |
| 3 | Differ in substance | Yes — opposite verdicts, disjoint corpora, different pages |
| 4 | Engineer prefers the runbooks | **3/3** |
| 5 | Legible in fifteen seconds | Yes — "Yes, required" against "No requirement is stated". **Human judgement** |

Criteria 2 and 5 are deliberately not automated. They are judgements about
what an audience will accept, and a script that scored them would launder
taste as measurement. `agent/tests/pick_question.py` prints both answers in
full so a person can make the call; the verdicts above are the author's and
should be confirmed by someone else before the event.

---

## 5 · `docs/DE-onboarding.md`

Written for a DE who has not read these specs and has fifteen minutes.

Must contain:

| Section | Content |
|---|---|
| What this is | One paragraph, and the explicit statement that identity is **simulated** (C5) |
| What you need | A LangSmith API key **in the shared Demo workspace** — not a personal one |
| What to clone | The repo; run `ui/` only. You do not deploy the agent |
| The URLs | Deployment API URL, dashboard URL, LangSmith project |
| Run it | Four commands, copy-pasteable |
| The demo script | The question, both identities, what to point at, in order |
| What will surprise you | Shared threads (C10); connection rotation needs a redeploy; the trace does not show credential resolution (§3) |
| What not to say | Do not present this as access control. Do not claim credentials rotate without a redeploy. Do not claim the docs are private. Do not claim the engineer's *preference* for the runbooks is enforced — the employee's missing tools are enforced; the engineer's ordering is a prompt |
| When it breaks | Check `mda connections list` (is the key still there?); check both corpus repos in Context Hub; check `mda logs`; check that the UI is sending a role |

That last row earns its place: a proxy that has quietly 401'd presents as "the
agent seems dumber today", and a DE without that pointer will debug the prompt.

### Acceptance criteria

- [ ] **A DE who has not read the specs gets a working local UI in under
      fifteen minutes, following only this file.** *Needs a person.* Every
      step is written and each was executed during the build, but "a stranger
      can follow it" is a claim about the reader, not the file.
- [ ] **Tested on someone who has not seen the build.** *Needs a person.*
      This one is stated as `tested, not reviewed` precisely so it cannot be
      closed by the author re-reading their own instructions, and it will not
      be closed that way here.
- [x] Every URL in it resolves — all nine checked.
- [x] The "what not to say" section exists and is specific (§8): five items,
      each naming the exact overclaim rather than advising care.

---

## 6 · Versioning and rollback

`demo_version` (C9) is hand-maintained and bumped whenever agent behaviour
changes: instructions, grants, tool set, middleware, model. Not derived from
git, because what matters is whether the agent behaves differently, and only a
person knows that.

A pre-deploy check fails when `contracts/grants.py`, `instructions.md`,
`skills/`, or `middleware/` changed since the last deploy without
`demo_version` changing.

Rollback, in order of preference:

1. **Hub edit** — wording only, no redeploy, seconds (ph. 01 §8).
2. **Redeploy the previous commit** — anything code-level, minutes.
3. **Re-key a proxy** — only if a key leaked; requires a redeploy because
   MCP-server connections are cached per process (ph. 02 §9 fact 5).

Before a live demo, freeze: last deploy at least a day ahead, and every check
in §2 re-run against the frozen revision. Rehearsing against one revision and
presenting on another is how a demo fails in the only session that counts.

### Acceptance criteria

- [x] The pre-deploy version check exists and **fails on a seeded violation**.
      `agent/contracts/check_version_bump.py`, with twelve tests in
      `tests/test_version_check.py` covering an edited grant, an edited
      instruction, an added middleware file, a deleted one, and the two
      passing cases. It also caught a real bump in this phase: v4 → v5.
- [x] A rollback is practised and timed: **3 minutes 29 seconds** (209s),
      recorded in `docs/DE-onboarding.md` §10. A rollback is a deploy of a
      different commit, so the deploy time *is* the rollback time.
- [x] The freeze policy is written down with a date field
      (`docs/DE-onboarding.md` §10, first checkbox). **The date is blank and
      needs to be set.**

#### Caveat on the rollback measurement

The repository has **no commits yet**, so "redeploy the previous commit"
could not be executed literally — there is no previous commit to check out.
What was measured is a full `mda deploy --context-strategy overwrite` of the
current tree, which is the same operation and the same cost; only the
`git checkout` in front of it is missing, and that takes a second.

This is worth fixing before the event for a reason beyond the measurement:
phase 06 §7's entire premise is that a DE clones the repo.

#### Rotation could not be rehearsed

§6's third rollback option — re-key the connection — **cannot be exercised
with the current credential.** `mda connections delete` returns:

```
error: This request is not authorized to access Agent Auth connections. (HTTP 403)
```

The PAT can *create* and *list* connections but not *delete* them, and the
CLI has no `update`, so rotation means delete-then-create. The attempt was
made and failed safely: the connection was never modified and the deployment
kept answering throughout.

The "no redeploy" claim is therefore **argued but not demonstrated**: the
tools resolve the connection per run and cache for 60 seconds
(`tools/corpus.py`), so a changed value takes effect on the next pull. Until
somebody with connection-delete rights rehearses it, do not promise the
rotation beat on stage.

---

## 7 · What phase 06 inherits

| Guarantee | From |
|---|---|
| A stable deployment URL and assistant id | §1 |
| A run body shape proven over HTTP for both roles | §2, ph. 04 §5 |
| The rejection response shape for an invalid role | ph. 04 §5 |
| A trace that answers the four questions | §3 |
| A chosen question and a spare | §4 |
| An onboarding doc the UI's README can point at | §5 |

Phase 06 must **not** assume: that it may hold agent code, that it may hold a
LangSmith API key in client code, or that it may decide a grant — the UI
chooses an identity and nothing else.

## Open items leaving this phase

| # | Item | Owner | State |
|---|---|---|---|
| O5.1 | Pre-warmed thread to hide the cold start | ph. 06 | **Closed by documentation, not code.** `docs/DE-onboarding.md` §7 tells the presenter to ask a throwaway question first. Auto-warming on page load was rejected: it spends a model call on every reload and puts an unexplained run at the top of the traces view during the demo |
| O5.2 | Seed the project with reference runs so the traces view is not empty | ph. 05 | **Closed.** ~50 runs now exist from the matrix and the question selection, all at v5, and the seven matrix runs are linked from the onboarding doc as known-good references |
| O5.3 | Event-day freeze date | **needs a date** | Open — the field is in `docs/DE-onboarding.md` §10 |
| O5.4 | Repository has no commits; "redeploy the previous commit" is unavailable and `git clone` does not work | **needs the repo owner** | Open |
| O5.5 | Connection rotation cannot be rehearsed — the PAT lacks connection-delete rights (403) | **needs admin** | Open |
| O5.6 | Corpus credential is a PAT, not a read-only service key — `workspaces:manage-keys` denied | **needs admin** | Open, and it has an unknown expiry |
