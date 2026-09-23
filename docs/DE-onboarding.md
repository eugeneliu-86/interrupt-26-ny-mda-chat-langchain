# Running the role-aware docs demo

You have fifteen minutes and you have not read the specs. This is everything
you need. You do **not** deploy anything — the agent is already running and
shared; you run the UI locally against it.

---

## 1 · What this is

One deployed agent answers documentation questions. You pick who is asking
from a menu — **Lang, an engineer** or **Polly, a non-technical employee** — and
the same question comes back with a different answer, because middleware
hands the model a different set of tools depending on the role.

**The identity is simulated.** Nobody logs in. There is no authentication and
no authorization anywhere in this demo. A person chooses a name from a
dropdown, the server writes it into a cookie, and the server injects it into
the run. Say this out loud early; the screen says it too, permanently.

What *is* real is the mechanism: the role is established server-side, the
browser cannot set it, and the tool filtering is deterministic code rather
than a prompt asking the model to behave. Swapping the dropdown for a
verified JWT claim would change nothing downstream.

---

## 2 · What you need

A **LangSmith API key issued in the shared Demo workspace**:

```
LangChain Inc. → Demo Workspace → a3866f07-2cf5-4e9c-a287-59ed817c2ecd
```

Your personal key from another workspace **will not work** — it returns 403,
which reads like a broken URL rather than a wrong key. Two organisations each
have a workspace named "Demo Workspace"; `fd6b1198-…` is the other one and is
not ours.

Everyone uses their own key. The role does not come from the key — it comes
from the request — so any valid key in this workspace gets the full demo.

---

## 3 · Run it

```bash
git clone <this repo> && cd interrupt-26-ny-mda-chat-langchain/ui
cp .env.example .env.local     # then paste YOUR key into LANGSMITH_API_KEY
pnpm install
pnpm dev                       # → http://localhost:3000
```

That is the whole setup. You need Node 20+ and pnpm. You do not need Python,
`uv`, or the `mda` CLI unless you intend to change the agent.

---

## 4 · The URLs

| | |
|---|---|
| Agent Server API | https://role-aware-docs-assistant-679d6573475f558188a07a13bc2b152c.us.langgraph.app |
| Deployment dashboard | https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/host/deployments/f28f4f92-95fb-49c9-81f2-2b8458deae4a |
| LangSmith project (traces) | https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686 |
| Context Hub | `chat-lc-lite/product-docs`, `chat-lc-lite/engineering-runbooks`, `chat-lc-lite/role-aware-docs-assistant` |

Current build: **v4**. It is shown in the UI's left rail and on every trace as
`metadata.demo_version`.

---

## 5 · The demo script

Three questions, in this order. All three are in the UI as one-click chips.

### Beat 1 — same question, two answers

> **"Do we require retry middleware on model calls?"**

| | |
|---|---|
| **Lang (engineer)** | **"Yes — required on every model call"**, because providers return 429s during normal operation. Cites `resilience-standards.md` from the internal runbooks. |
| **Polly (employee)** | **"No requirement is stated."** The public docs describe retry middleware as one available capability, not a rule. Cites `middleware.md`. |

A flat contradiction, and it resolves the moment the audience learns who was
asking. Point at the tool-call chips: different corpus, different page.

Reference runs — [Lang](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd5-e2bd-7750-82f4-2dd4504b0332) ·
[Polly](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd5-e291-7f23-b381-180e9666ad7a)

### Beat 2 — the refusal. **This is the one that proves the mechanism.**

> **"What is our on-call escalation path?"**

| | |
|---|---|
| **Lang** | Answers in detail: the `platform-agents-oncall` rotation, T1/T2/T3 tiers, 15- and 30-minute response times. |
| **Polly** | Refuses, and names what it *does* have: "the only corpus available to me is the public LangChain product documentation." |

Say plainly: *Polly's model was never offered a tool that can reach those
runbooks.* It is not declining; it cannot. Then show the ✗ row in the left
rail — that row was on screen before the question was asked.

Reference runs — [Lang](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd6-50e9-7323-ac77-fb5dd52dfd8f) ·
[Polly](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd6-51a5-7bb3-89ca-5f154d4de79d)

### Spare — if the room wants something else

> **"What environments do we have?"**

Lang gets a four-row table (`dev`, `staging`, `prod-us`, `prod-eu`) from
`environments.md`. Polly gets a list of *environment variables* from
`environment.md` and says the docs describe no deployment environments.
Verified stable across three runs per role.

Reference runs — [Lang](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd6-0946-7310-8153-3e3209e62009) ·
[Polly](https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686/r/01a0ccd6-0f6a-7380-b17d-6df3da91ae3b)

### What to point at, in order

1. **The left rail, before asking.** Lang's list is numbered 1–2. Polly's has a
   crossed-out row. The difference is visible before anything runs.
2. **The chips, during the run.** `engineeringDocs__fetch_doc
   resilience-standards.md` — the corpus *and* the page.
3. **"view trace ↗", after.** Open it and show `metadata.role`, then the
   model call's tool list.
4. **Context Hub.** The instructions, the skills, and both corpora, versioned
   and diffable in one place. This is the strongest screen in the demo.

---

## 6 · Reading a trace (four questions, one minute)

Open any run in the project above.

| Question | Where |
|---|---|
| Who made this run? | Root run → Metadata → `role`, `display_name` |
| What could it reach? | The model call span → its tool list |
| What did it actually call? | The tool spans, named `{corpus}__{tool}` |
| Was anything denied? | A tool span with an error. **Absent in every healthy run** |

Filtering the project by `metadata.role` splits the runs cleanly.

**One surprise:** a run rejected for an invalid role still carries that role
in its metadata — a run sent with `role: "admin"` shows `metadata.role =
"admin"`. It looks like a leak; it is not. The run died at the first
middleware hook with no model call and no tools. Check for the error on the
root run.

---

## 7 · What will surprise you

- **Threads are shared across everyone using the deployment.** Two DEs
  demoing simultaneously are writing into the same deployment. Threads are
  per-browser, so you will not see each other's conversations, but you are
  sharing rate limits and the traces land in one project.
- **Switching identity clears the thread, on purpose.** Continuing a thread
  after a switch would feed the new identity documents the old one fetched,
  and the demo would appear to leak the exact thing it prevents.
- **The first question of the session is slow** — cold start plus a corpus
  pull. Ask a throwaway question before you present.
- **The trace does not show credential resolution.** It shows that
  `engineeringDocs__fetch_doc` was called; it does not show which credential
  carried the call. To evidence that, show `mda connections list` next to the
  trace and point out that the corpus prefix maps to a connection slug in
  `agent/contracts/grants.py`. Two screens, because neither is complete alone.
- **Rotating the corpus credential needs no redeploy.** Authored tools resolve
  the connection per run, and snapshots cache for 60 seconds. Change the
  connection, wait a minute, and the next run uses the new value.
- **Redeploying takes about 3½ minutes** (measured: 209 seconds). That is also
  what a rollback costs, because a rollback is a deploy of an earlier commit.

---

## 8 · What not to say

- **Do not present this as access control.** It is a demonstration of
  deterministic tool scoping driven by request context. There is no
  authentication. Somebody in the room will ask; answer it directly.
- **Do not claim the docs are private company documents.** The engineering
  corpus is **invented** — fictional team, fictional environments, fictional
  ticket prefixes. It is in a private Context Hub repo, so "only the engineer
  role can reach this" is literally true, but the content is written, not
  leaked.
- **Do not claim Lang's *preference* for the runbooks is enforced.** Two
  different things are on screen:
  - Polly's missing tool — **enforced**, in code, unbypassable.
  - Lang's ordering (runbooks first) — **a sentence in the prompt.** Lang can
    reach the product docs too; grants are nested.

  Beat 2 is the enforced one. Lead with the mechanism there.
- **Do not claim the trace shows which credential was used.** See §7.
- **Do not take a question about Managed Deep Agents from the audience.** The
  product corpus comes from Chat LangChain Lite and has ten topics; MDA is not
  one of them. Asked anyway, the agent produces a confident, generic LangGraph
  deployment answer that is not about MDA at all — which is worse than a
  refusal, because it sounds right.

---

## 9 · When it breaks

Work down this list. The first check catches the most common failure.

| Symptom | Check |
|---|---|
| Both identities suddenly answer the same, or answer nothing | `cd agent && uv run mda connections list` — is `context-hub-corpus` still there, and has its key expired? An expired corpus credential presents as "the agent got dumber today". |
| "This corpus is temporarily unreachable" | Same as above, then open both repos in Context Hub. |
| Everything 403s | Your key is from the wrong workspace. See §2. |
| Every run is rejected | The UI is not sending a role. Check the identity cookie exists, then `ui/app/api/lg/[.._path]/route.ts` — a run-create path shape it does not match goes out with no context and fails closed. |
| An empty assistant bubble | A content-block rendering bug, or a dead run returning HTTP 200 with `__error__`. Check the browser console and the trace. |
| Nothing loads at all | `MDA_API_URL` or `LANGSMITH_API_KEY` missing from `.env.local` — the page shows a red banner saying so. |
| The deployment itself | `cd agent && uv run mda logs` |

---

## 10 · Before the event

- [ ] **Freeze date: `________`** — last deploy at least 24 hours before the
      session. Rehearsing on one revision and presenting on another is how a
      demo fails in the only session that counts.
- [ ] Re-run the verification matrix against the frozen revision:
      `cd agent && uv run python -m tests.verify_deployment` (expects 11/11).
- [ ] **Swap the corpus PAT for a read-only service key.** It currently holds
      a dedicated personal token. Needs the `workspaces:manage-keys`
      permission, which the build account does not have.
      **PAT expiry date: `________`** ← fill this in; if it lapses mid-demo,
      every corpus call fails at once.
- [ ] Ask one throwaway question to warm the deployment.

Rollback, in order of preference:

1. **Edit the instructions in Context Hub** — wording only, no redeploy,
   seconds.
2. **Redeploy an earlier commit** — `cd agent && uv run mda deploy
   --context-strategy overwrite`. **Measured at 3 minutes 29 seconds.**
3. **Re-key the connection** — only if a credential leaked. No redeploy
   needed.
