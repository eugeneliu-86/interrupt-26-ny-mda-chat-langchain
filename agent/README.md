# role-aware-docs-assistant

The canonical Managed Deep Agent for the role-aware documentation demo. One
deployment answers documentation questions; middleware exposes a different tool
surface depending on the role the run carries.

**The specs are the source of truth**, not this file:
[../docs/specs/](../docs/specs/). Start with `00-overview.md`, which holds the
contracts (C1–C11) every phase is measured against.

## Layout

```text
agent/
  agent.py                  define_deep_agent(...) — `name` is the deploy id and is FINAL
  identity.py               who may call the deployment (C10)
  instructions.md           always-on system prompt, synced to Context Hub
  skills/docs-answering/    procedure for answering, loaded on demand
  contracts/                roles, grants, version — the single source (C1, C2, C9)
  tools/corpus.py           the corpus tools, one search/fetch pair per corpus
  tools/search.py           keyword scoring; MIN_SCORE is load-bearing for the refusal
  middleware/role_gate.py   the three-layer gate: reject, filter, deny
  tests/                    106 offline, 11 e2e, plus the phase 05 harnesses
```

## Verification harnesses

These need the deployment and are run deliberately, not by `pytest`:

```bash
uv run python -m tests.verify_deployment        # the 11-row matrix -> verification.json
uv run python -m tests.verify_trace_contract    # the four trace questions, per run
uv run python -m tests.score_candidates         # screen demo questions offline
uv run python -m tests.pick_question            # run candidates live, 3x per role
```

## Decisions recorded here so nobody re-litigates them under time pressure

### Deploy target

| | |
|---|---|
| Org | LangChain Inc. (`f5c798a2…`) |
| Workspace | **Demo Workspace** `a3866f07-2cf5-4e9c-a287-59ed817c2ecd` |

**Two orgs each have a workspace displayed as "Demo Workspace".** A key from
the wrong org returns 403 on the right id, which reads like a bad id. Ours is
the one above; `fd6b1198…` is the other org's and is *not* ours. See
`docs/specs/01-context-hub.md` gate G2.

### `--context-strategy`: the project files win

`mda deploy` syncs `instructions.md` and `skills/` to Context Hub. Once the Hub
copy has been edited, the next deploy stops and asks whether to overwrite it;
non-interactively it errors and demands `--context-strategy`.

**Standing decision: the repo is the source of truth.** Hub edits are for
demonstrating live injection, not for authoring. So:

1. copy any wording you liked from the Hub back into `instructions.md`, then
2. `uv run mda deploy --context-strategy overwrite`

The failure this prevents: a deploy the night before silently keeping a
Hub-edited prompt nobody has read, in a demo whose premise is that the Hub and
the repo are in sync.

### `--deployment-type`: dev, not prod

Not `prod`. This gets redeployed repeatedly during rehearsal, and a dev
deployment redeploys faster with fewer guardrails. Do not "upgrade" it on the
morning of the demo.

### Model: GPT-5.6 Luna through LLM Gateway

`model="langsmith:openai/gpt-5.6-luna"` — colon after `langsmith`, **slash**
before the model. A direct provider call would be `openai:gpt-5.6-luna`, with a
colon; mixing the two gives a provider-resolution error that reads like a
missing key.

No provider key lives in `.env`: the gateway resolves the OpenAI credential
from a workspace provider secret. Verified present in this workspace (315
models). There is no `--gateway` flag in `mda` 0.7.4 despite the docs.

### Corpus credential: a PAT, with a gap recorded

The `context-hub-corpus` connection should hold a workspace-scoped **read-only
service key**. Creating one needs admin rights that were not available, so it
currently holds a **dedicated PAT with an expiry**.

Swapping it needs **no redeploy** — authored tools resolve the connection per
run — so this is a one-command fix, not a rebuild. Do it before the demo runs
in front of anyone, and record the PAT's expiry date in
`docs/DE-onboarding.md`.

## Commands

```bash
uv sync                                   # install
uv run mda build                          # compile locally, creates nothing remote
uv run mda dev                            # local server (note: picks a random port)
uv run mda deploy                         # deploy to the workspace in .env
uv run mda deploy --context-strategy overwrite   # after a Hub edit
uv run mda logs                           # tail the deployed revision
uv run python -m contracts.emit_grants_json      # regenerate contracts/grants.json
uv run python -m contracts.check_version_bump    # BEFORE every deploy
uv run python -m contracts.check_version_bump --record   # AFTER a successful deploy
bash contracts/check-contracts.sh                # 11 grep-level contract checks
```

### The deploy sequence, in order

```bash
uv run python -m contracts.check_version_bump    # refuses if behaviour changed without a bump
uv run python -m contracts.emit_grants_json      # a version bump makes grants.json stale
uv run mda deploy --context-strategy overwrite   # ~3m30s
uv run python -m contracts.check_version_bump --record
uv run python -m tests.verify_deployment         # expects 11/11
```

`.env` is gitignored and must stay that way. `.env.example` names every
variable and holds no values.
