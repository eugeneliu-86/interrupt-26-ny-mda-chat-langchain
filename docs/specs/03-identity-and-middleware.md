# Phase 03 — Simulated identity and the gating middleware

> **Status:** COMPLETE (2026-09-23), 36/41 criteria · **Depends on:** [00-overview.md](./00-overview.md) C1, C2, C3, C6, C8, C9 · tool *names* from [02-tools-and-corpora.md](./02-tools-and-corpora.md) §9
>
> The phase that makes the demo true. Build `contracts/`, `context_schema.py`,
> and the middleware that turns `runtime.context.role` into a tool surface —
> deterministically, in code, with the denial visible.

## What this phase delivers

Two runs, same question, same deployment, same instructions, different answers:

```text
context.role = "engineer"   → tools: productDocs__*, engineeringDocs__*
                              prefers: engineeringDocs
context.role = "employee"   → tools: productDocs__*
                              prefers: productDocs
context.role = "admin"      → run rejected, no model call
context absent              → run rejected, no model call
```

Grants are **nested** (C2): the employee surface is a strict subset. So the
enforced difference runs one way — the employee cannot reach the runbooks — and
the ordered preference is what makes the engineer answer from them.

Built and tested **against fakes** with the real tool names, so middleware work
is not blocked on the corpora being written (overview §6).

## What this phase does not deliver

| Not here | Where |
|---|---|
| Real MCP tools wired in | ph. 04 |
| The end-to-end deployed proof | ph. 04, 05 |
| Anything that chooses a role | ph. 06 |
| Real authentication | nowhere — it is simulated by design (C5) |

---

## 1 · What "identity" means here, precisely

There is no authentication in this phase and none in this build. Say it plainly
so nobody later mistakes the demo for a product:

| Layer | What it actually is | Real? |
|---|---|---|
| Who may call the deployment | A valid LangSmith workspace API key | **Real** — MDA verifies it |
| Which role the run carries | A string the caller puts in `context` | **Simulated** |
| What that role can reach | Middleware filtering `request.tools` from a code-level grant table | **Real and deterministic** |

The middle row is the costume. The bottom row is the mechanism, and it is the
thing worth showing: **once a role is established, enforcement is code, not
persuasion.** Swapping the dropdown for Supabase-verified JWT claims changes
only the middle row — no middleware change, no agent change. That substitution
story is the most valuable sentence in the demo, and it is only available
because the role enters through `context` (C3) rather than through the message.

### Why not use MDA's real identity mechanisms?

| Option | Why not, here |
|---|---|
| Supabase identity, real sign-in | Real, and the right answer for production. Costs a Supabase project, a sign-in flow, and a user-seeding step — for a demo where the audience needs to see *both* identities in 90 seconds. Switching identities would mean signing out and in |
| User-owned connections per role | Would make credentials the enforcement point, which sounds better but is worse here: three DEs would each have to authorize three docs accounts, and a `credential_authorization_required` interrupt has no first-class path in a custom frontend yet |
| A separate API key per role | Keys authenticate the *client*, not a person, and the mapping key→role would live in the UI anyway — same simulation, more moving parts |

**Decision: simulate the role, label it (C5), and make everything downstream
real.** The 90-second identity switch is the demo; a real login is a different
demo.

### Acceptance criteria

- [x] `docs/DE-onboarding.md` (§1) and the UI both state the role is
      simulated (C5). In the UI it is a sticky, unconditional banner, and
      `ui/README.md` repeats it in its own section. A test asserts it is in
      the rendered HTML.
- [x] No middleware or tool reads a LangSmith user id, key, or thread owner to
      determine a role.
- [x] The middleware's grant computation is a pure function of
      `runtime.context.role` and `contracts.grants` — no I/O, no model call.
      Testable without a network and without an LLM.

---

## 2 · `contracts/`

The package was created in [01-context-hub.md](./01-context-hub.md) §2, so that
phases 02 and 03 could both start without waiting on the other. This is where
it becomes load-bearing, and where the two pieces that need code to point at
get written: the import-time assertions, `granted_prefixes()`, and
`check-contracts.sh`.

```text
agent/contracts/
  roles.py            C1 — from ph. 01 §2
  grants.py           C2 — from ph. 01 §2, + the additions below
  version.py          C9 — from ph. 01 §2
  check-contracts.sh  NEW here: the grep-level assertions from the overview
```

`roles.py` and `grants.py` are as written in
[00-overview.md](./00-overview.md) C1 and C2. Two additions:

```python
# contracts/grants.py  (tail)
from contracts.roles import ROLES

assert set(GRANTS) == set(ROLES), "every role needs a grant"
for _role, _prefixes in GRANTS.items():
    assert _prefixes <= set(CONNECTION_SLUGS), f"{_role} grants an unknown prefix"

# Nesting is the design (C2): employee is a STRICT subset of engineer.
assert GRANTS["employee"] < GRANTS["engineer"], "employee must be nested in engineer"
# The one exclusion the demo depends on — beat 2 exists only because of it.
assert "engineeringDocs" not in GRANTS["employee"]
# A role must be told to prefer exactly what it holds, or prompt and tools disagree.
for _role in ROLES:
    assert set(PRIMARY_ORDER[_role]) == GRANTS[_role], f"{_role}: order != grant"


def granted_prefixes(role: str) -> frozenset[str]:
    """The tool-name prefixes this role may call. Raises on an unknown role."""
    try:
        return GRANTS[role]  # type: ignore[index]
    except KeyError:
        raise ValueError(
            f"unknown role {role!r}; expected one of {', '.join(sorted(ROLES))}"
        ) from None


def primary_order(role: str) -> tuple[str, ...]:
    """Corpora for this role, most authoritative first. Shapes answers only."""
    granted_prefixes(role)          # one failure mode for an unknown role
    return PRIMARY_ORDER[role]      # type: ignore[index]
```

The import-time asserts exist so a change to the access model is a deliberate
act rather than a diff nobody notices. With nested grants the *strictness*
assert is the important one: if `employee` ever equalled `engineer`, every
acceptance criterion below would still pass while the demo had silently
stopped demonstrating anything.

`granted_prefixes` raising on an unknown role is how C1's rejection is
implemented — one function, one failure mode, used by both middleware layers.
`primary_order` routes through it so an unknown role fails identically
wherever it is first touched.

### Writing `check-contracts.sh`: three ways it lied before it worked

The script asserts what a unit test cannot — that a fact is written in exactly
one place. Its first version reported **4 of 11 failing**, and every one was a
defect in the script rather than the project:

**1 · `eval` ate the quoting.** The user-owned-connection check was
`grep -q "\"user\""` inside an `eval`'d string. After two rounds of shell
parsing that became `grep -q ""user""` — an **empty pattern, matching every
line**. A check whose failure is indistinguishable from its success is worse
than no check. The rewrite has no `eval`: explicit `if` blocks, quoted patterns.

**2 · An unquoted glob.** `--include=*.py` is expanded by some shells before
grep sees it. Quote it: `--include='*.py'`.

**3 · The scan included build output.** `.mda/build/` holds a copy of every
project file *plus* the vendored runtime, so the project's own sources were
reported as violating single-source rules and the runtime's own connection code
matched `"user"`. All scans now exclude `.mda`, `.venv`, `__pycache__`,
`.pytest_cache`, `node_modules`.

**Then each rule was seeded with a violation and observed to fail** — a
contract check that has never failed is not known to work:

| Seeded violation | Result |
|---|---|
| `instructions.md` mentions a role | fails as expected |
| a tool asks for a user-owned credential | fails as expected |
| a role literal leaks into `middleware/` | fails as expected |
| `grants.json` goes stale | fails as expected |

### Acceptance criteria

- [x] `python -c "import contracts.grants"` passes; flipping one grant to a
      superset makes it fail.
- [x] `granted_prefixes("admin")` and `primary_order("admin")` both raise
      `ValueError` naming both valid roles.
- [x] Setting `GRANTS["employee"] = GRANTS["engineer"]` fails at import — the
      check that the demo still demonstrates something.
- [x] `contracts/check-contracts.sh` passes from `agent/` and asserts:
      role literals appear only under `contracts/` and tests; no tool takes a
      `role` parameter; `connections.get` is always `{"type": "agent"}`;
      `instructions.md` and `skills/` name no role, tool, or corpus.
- [x] `check-contracts.sh` exits non-zero on a seeded violation of each rule.
      A contract check that has never failed is not known to work.

---

## 3 · `context_schema.py`

```python
# agent/context_schema.py
from dataclasses import dataclass

from contracts.roles import Role


@dataclass
class RequestContext:
    """Per-run context, set by the UI's server route (C3, C5).

    Carries identity metadata only. No document content, no credentials, and
    nothing the model can write to.
    """

    role: Role
    display_name: str
    demo_version: str
```

Passed to the agent definition (phase 04):

```python
agent = define_deep_agent(
    name="role-aware-docs-assistant",
    model="langsmith:openai/gpt-5.6-luna",
    context_schema=RequestContext,
    middleware=[reject_unknown_role, role_gate, deny_ungranted_tool, trace_meta],
)
```

**`context_schema` is accepted by the wheel even though the published parameter
table omits it** — `managed_deepagents 0.7.1.dev5`,
`define_deep_agent.py:65`. Treat the wheel as the authority; the docs table
lists eight fields and the function takes more.

### Why a dataclass and not a dict

LangGraph coerces a dict into a dataclass or Pydantic model when a
`context_schema` is declared, and passes it through untouched when none is
(`langgraph/pregel/main.py:4337-4364`). Declaring the dataclass buys two
things: `runtime.context.role` instead of `runtime.context["role"]`, and a
`TypeError` at coercion time if the UI sends a malformed context — which is a
better failure than a `KeyError` three hooks later.

It does **not** buy validation of the role's *value*: `Role` is a `Literal`
and dataclasses do not enforce those at runtime. §4 does that.

### Every field is optional, and that is deliberate

LangGraph coerces the caller's dict into the dataclass **before any middleware
runs**. With required fields, a run sent with no context failed at coercion:

```text
TypeError: RequestContext.__init__() missing 3 required positional arguments:
'role', 'display_name', and 'demo_version'
```

The right outcome — the run is rejected — with the wrong message: a Python
internals leak instead of *"expected engineer or employee"*, and `before_agent`
cannot intercept it because coercion runs first. With defaults, coercion always
succeeds and `reject_unknown_role` produces the useful message. The run still
fails closed; only the wording improves.

### Acceptance criteria

- [x] `runtime.context.role` is readable as an attribute inside middleware.
- [x] A run whose `context` omits `role` fails at coercion or in §4 — never
      reaches the model.
- [x] ~~A run with an extra unknown key in `context` fails loudly~~ —
      **measured: unknown keys are silently ignored.** Benign, and the case that
      matters still fails safely: a *typo'd* role field (`roles`) leaves `role`
      unset, which layer 0 rejects. Note that MDA mirrors context into run
      metadata, so a stray key also appears there.
- [x] `RequestContext` has no field carrying document content or a credential.
- [x] The same context shape works under `mda dev` **and** against the
      deployment (overview O8 — verify both, do not assume).

---

## 4 · Layer 0 — reject an undeclared or unknown role

```python
# agent/middleware/role_gate.py
from langchain.agents.middleware import before_agent

from context_schema import RequestContext
from contracts.grants import granted_prefixes


@before_agent
async def reject_unknown_role(state, runtime) -> None:
    """Fail the run before any model call if the role is missing or unknown (C1).

    Deliberately does not downgrade to a least-privilege surface: a silent
    downgrade is the wrong lesson to teach from a stage, and the UI always sets
    a role, so this only fires for a raw client.
    """
    ctx: RequestContext | None = runtime.context
    if ctx is None or getattr(ctx, "role", None) is None:
        raise ValueError(
            "this deployment requires context.role; expected engineer or employee"
        )
    granted_prefixes(ctx.role)  # raises ValueError on an unknown role
```

`before_agent` runs once per run, before the model. Raising there fails the run
with no model call and no tool call, and the error is visible in the trace.

**Middleware must use async hooks.** MDA always invokes the agent with
`ainvoke`/`astream`, so a sync-only hook never runs. The decorators install the
async variant when given an `async def`; sync hooks remain valid only for
non-MDA Deep Agents usage.

### Acceptance criteria

- [x] A run with no `context` fails, with an error naming both valid roles, and
      records **zero** model calls in the trace.
- [x] Same for `role="admin"` and `role=""`.
- [x] The failure is a run error, not a normal assistant message — a refusal
      the model composed would prove nothing about enforcement.
- [x] Every hook in `middleware/` is `async def`. A test asserts it, because
      a sync hook fails silently by never running, which is the worst possible
      failure mode.

---

## 5 · Layer 1 — the tool surface and the prompt section, together

One hook does both, on purpose.

```python
# agent/middleware/role_gate.py  (continued)
from langchain.agents.middleware import wrap_model_call
from langchain.messages import SystemMessage

from contracts.grants import granted_prefixes, primary_order

_CORPUS_BLURB = {
    "productDocs": "public LangChain product documentation",
    "engineeringDocs": "internal engineering runbooks for this team",
}


def _granted_access_section(order: tuple[str, ...]) -> str:
    """The per-run prompt section. Ordered most authoritative first (C2)."""
    lines = "\n".join(
        f"{i}. {_CORPUS_BLURB[p]}" for i, p in enumerate(order, start=1)
    )
    return (
        "## Granted access\n\n"
        "You may search only these documentation corpora in this run, listed "
        "most authoritative for your caller first:\n\n"
        f"{lines}\n\n"
        "Prefer the highest-listed corpus that covers the question, and say "
        "which one you used. Fall back to a lower one only when the higher "
        "corpus does not cover it.\n\n"
        "You have no tools for anything else. Refuse questions that need other "
        "documentation, and name what you do have."
    )


@wrap_model_call
async def role_gate(request, handler):
    """Expose only the granted tools, and describe exactly those (C6, C8).

    Tool list and prompt text come from ONE computed set, so the prompt can
    never claim access the tool list does not have.
    """
    role = request.runtime.context.role
    prefixes = granted_prefixes(role)
    order = primary_order(role)          # same set, ordered (asserted in contracts)
    tools = [t for t in request.tools if _prefix_of(t) in prefixes or _is_builtin(t)]
    section = _granted_access_section(order)
    base = request.system_message.content if request.system_message else ""
    return await handler(
        request.override(
            tools=tools,
            system_message=SystemMessage(content=f"{base}\n\n{section}"),
        )
    )
```

### Ordering is why the prompt does more work here than it looks

With nested grants (C2), the tool filter alone no longer differentiates the two
roles on a question both corpora cover: the engineer holds Fleet docs too. The
ordered list is what makes the engineer answer from the runbooks.

That is **preference, not enforcement**, and the distinction is load-bearing:

| Mechanism | Guarantees |
|---|---|
| tool filter (below) | the employee **cannot** reach the runbooks — deterministic |
| ordered prompt section | the engineer **prefers** the runbooks — probabilistic |

Phase 05 §4 picks a demo question knowing this, and the narration says which
is which. An ordered list that happens to work on the rehearsed question is not
an access-control claim, and presenting it as one is the single most damaging
thing this demo could do.

### Why one hook instead of two

Splitting the tool filter and the prompt injection into separate middleware
creates a state where they disagree — the prompt says a corpus is available
while the tool is gone, or worse the reverse. The agent then either refuses
something it can do or promises something it cannot, and the demo looks broken
in a way that is hard to diagnose live. Computing `prefixes` once and using it
for both makes that class of bug unrepresentable.

`_prefix_of(tool_or_name)` returns the text before `__` or `None`;
`_is_builtin(tool)` is `"__" not in name`. Both live in `role_gate.py` beside
the hooks, and both are covered by §9's table tests.

### The three details that will bite

1. **`request.override(...)` returns a new request** — it does not mutate
   (`langchain/agents/middleware/types.py:203-227`). Forgetting to pass the
   result to `handler` silently disables the whole gate, and the demo looks
   fine until someone checks the trace.
2. **Built-in tools must survive the filter.** Deep Agents injects harness
   tools whose names carry no `{corpus}__` prefix. A naive prefix filter removes
   them and breaks the agent in a way that looks like a model problem.

   The observed harness tool list, read from the compiled build:
   `cancel_async_task`, `check_async_task`, `compact_conversation`, `delete`,
   `edit_file`, `execute`, `glob`, `grep`, `list_async_tasks`, `ls`,
   `read_file`, `rubric_grader`, `start_async_task`, `task`,
   `update_async_task`, `write_file`. **None contains `__`** (O3.1 closed), and
   a test pins the list because it is the observed environment.

   **One latent hazard, found while checking that and fixed.** The harness ships
   strings like `__deepagents_subagent_response_format`. A name *beginning* with
   the separator splits to an **empty** prefix, which is not `None`, so such a
   tool would have been dropped **for every role** — failing closed, invisibly,
   and looking like the model misbehaving. An empty prefix now counts as no
   prefix.
3. **`system_prompt` is deprecated in favour of `system_message`.** Use
   `SystemMessage`, and append rather than replace: replacing drops
   `instructions.md`, which is the one thing Context Hub is supposed to own
   (C8).

### Acceptance criteria

- [x] With `role="employee"`, the tool list passed to the model contains no
      `engineeringDocs__*` and does contain `productDocs__*` and
      `productDocs__*`.
- [x] With `role="engineer"`, the tool list contains **all six** docs tools
      (C2 is nested).
- [x] The two surfaces are **not equal** — the employee's is a strict subset.
      With nesting this replaces the disjointness check, and it is the assert
      that catches an accidental widening of the employee grant.
- [x] The injected section is **ordered**, and the first corpus differs between
      the two roles: `engineeringDocs` for engineer, `productDocs` for
      employee.
- [x] Built-in harness tools survive for both roles.
- [x] The injected section names exactly the granted corpora, and the two
      roles' sections differ.
- [x] `instructions.md` text is still present in the final system message —
      appended to, not replaced.
- [x] A test asserts the tool prefixes and the corpora named in the prompt are
      **the same set**, and that the prompt's order equals `primary_order(role)`.
      This is the invariant the single-hook design exists to guarantee, so it
      gets its own test.
- [x] Unit-tested with fake tools named exactly as in phase 02 §9 — no network,
      no network, no LLM.

---

## 6 · Layer 2 — deny an ungranted call, visibly

```python
# agent/middleware/role_gate.py  (continued)
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage


@wrap_tool_call
async def deny_ungranted_tool(request, handler):
    """Refuse a call to a tool this role was never granted (C6, defence in depth).

    Nothing should reach this in a normal run: layer 1 removed those tools from
    the model's view. It exists so a leak is a visible denial in the trace
    rather than a silent success.
    """
    name = request.tool_call["name"]
    prefixes = granted_prefixes(request.runtime.context.role)
    prefix = _prefix_of(name)
    if prefix is not None and prefix not in prefixes:
        return ToolMessage(
            content=(
                f"Access denied: {name} is not available to this caller. "
                "Refuse the request and name the documentation you do have."
            ),
            tool_call_id=request.tool_call["id"],
            status="error",
        )
    return await handler(request)
```

### Why keep a layer that should never fire

Three reasons, in order of how often they matter:

1. **It is the answer to "but what actually stops it?"** Layer 1 is a filter on
   what the model *sees*, which a skeptical engineer will correctly identify as
   not being enforcement. Layer 2 is enforcement, and you can demonstrate it by
   injecting a call.
2. **Tool lists are cached per process** (phase 02 §9 fact 5). Anything that
   ever reintroduces a tool into a request — a future middleware, a replayed
   thread, a state-resumed run with an older tool list — hits layer 2.
3. **It returns a `ToolMessage`, not an exception**, so the model can read the
   denial and recover into a proper refusal instead of the run dying. That is
   the difference between a graceful demo and a red trace.

### Acceptance criteria

- [x] A synthetic `engineeringDocs__fetch_doc` call injected into an employee
      run returns the denial `ToolMessage` and makes no upstream HTTP request.
- [x] The denial appears in the trace as a tool message with `status="error"`.
- [x] The model, having read the denial, **refuses rather than retrying**.
      Verified against the deployment: zero tool calls after the denial, and
      the answer names the corpus it does have. The "refuse the request and
      name the documentation you do have" instruction is doing its job.

      Layer 2 is unreachable through a normal question — layer 1 removes the
      tool first — so the test seeds a run whose history already contains the
      denial, which is exactly the state layer 2 leaves behind.
      `tests/test_end_to_end.py::test_the_model_refuses_after_a_denial_rather_than_looping`.
- [x] Layer 2 does not fire anywhere in the scripted demo flow — asserted as
      a **row of the deployment matrix** (C6), counting `Access denied` tool
      messages across all nine runs. Zero.

---

## 7 · Trace metadata

```python
# agent/middleware/trace_meta.py
@before_agent
async def trace_meta(state, runtime) -> None:
    """Stamp the run so a trace answers the demo's questions (C9)."""
```

Writes the **per-run** keys — `role` and `granted` (comma-joined, sorted) —
into run metadata.

The **static** keys are not middleware's job. `demo` and `demo_version` go
through `define_deep_agent(metadata=...)`, which MDA applies to the root
LangSmith run (ph. 04 §1). That is strictly better than stamping them here: no
caller can override them, and they describe which *build* answered rather than
what was asked.

Two rules:

- **Metadata is for the eye and for filtering. Middleware reads
  `runtime.context`** (C3). Nothing branches on metadata — it is an output,
  not an input.
- `granted` must be derived from the same `granted_prefixes()` call the gate
  uses, not recomputed from a literal, or a trace can disagree with the run it
  describes.

`demo_version` is hand-maintained and bumped whenever agent behaviour changes —
instructions, grants, tool set, middleware. It is not derived from git, because
what matters is "did the agent behave differently", and only a person knows
that.

### Acceptance criteria

- [x] Every run carries all four metadata keys — the two static ones from the
      agent definition, the two per-run ones from this hook.
- [x] `metadata.granted` equals the prefixes actually left in the model's tool
      list for that run.
- [x] Filtering the LangSmith project by `metadata.role` splits the scripted
      runs cleanly in two.
- [x] A pre-deploy check fails if `contracts/grants.py` changed without
      `demo_version` changing.

---

## 8 · Middleware order

```python
middleware=[reject_unknown_role, role_gate, deny_ungranted_tool, trace_meta]
```

Middleware runs in list order. What the order buys:

| Position | Why there |
|---|---|
| `reject_unknown_role` first | Nothing else should run on a run that has no valid role. Every hook after it may assume `runtime.context.role` is one of the two values |
| `role_gate` before `deny_ungranted_tool` | Not strictly required — they hook different phases — but reading order should match execution order, or the next person will misread it |
| `trace_meta` last | It only observes. Placing it first would stamp runs that are about to be rejected, which pollutes the project with metadata for runs that never ran |

### Acceptance criteria

- [x] The trace shows `reject_unknown_role` before any model call.
- [x] A rejected run produces no `trace_meta` stamp.
- [x] Reordering the list breaks an assertion.
      `tests/test_role_gate.py::test_reordering_the_middleware_list_breaks_this`
      parses `agent.py` and pins the three hooks in order, with the reason
      each position matters written into the docstring.

---

## 9 · How to test this phase, with no network and no LLM

The point: middleware is a pure function of context plus a tool list, so it can
be tested exhaustively and fast.

```bash
cd agent && uv run pytest tests/test_role_gate.py -v
```

```python
# agent/tests/test_role_gate.py  (shape)
FAKE_TOOLS = [
    fake("productDocs__search_docs"),  fake("productDocs__fetch_doc"),
    fake("engineeringDocs__search_docs"), fake("engineeringDocs__fetch_doc"),
    fake("write_todos"), fake("ls"),          # harness built-ins
]

# 1 · surface per role — asserted as sets, derived from GRANTS, not literals
# 1b · employee surface is a STRICT subset of engineer's  (nesting, C2)
# 2 · built-ins survive both roles
# 3 · prompt section names exactly the granted corpora, in primary_order  (§5)
# 4 · unknown / missing role raises before any model call
# 5 · injected ungranted tool call → denial ToolMessage, handler never invoked
# 6 · every hook in middleware/ is async
```

**The tests use the real `ModelRequest`, not a fake.** It is constructible with
a stub model — nothing under test calls the model — and `override()` returns a
new instance leaving the original untouched, so the immutability the gate relies
on is exercised rather than assumed. The decorators install `abefore_agent` /
`awrap_model_call` / `awrap_tool_call`; the tests invoke those directly and also
assert they are the async variants.

Then one integration run per role under `mda dev`, once phase 02's corpora are
populated — but the unit suite is what proves the gate, because it can assert
things a live run cannot: that the handler was never called, that the surfaces
are exactly what `GRANTS` specifies, that nothing hit the network.

**Assert derived values, not literals.** Compute the expected surface from
`GRANTS` inside the test. A test that hardcodes
`{"productDocs__search_docs", ...}` passes after someone widens a grant, which
is precisely the change that must fail.

### Acceptance criteria

- [x] The suite runs offline, with no LLM and no network, in under five seconds.
- [x] Expected surfaces are computed from `contracts.grants`.
- [x] Coverage includes: both roles, unknown role, missing context, injected
      ungranted call, built-in survival, prompt/tool agreement, prompt ordering,
      and strict-subset nesting.
- [x] Seeding a bug in each middleware function breaks at least one test —
      verified by doing it:

      | Seeded bug | Tests broken |
      |---|---|
      | layer 1 stops filtering (passes every tool) | 5 |
      | layer 1 replaces the prompt instead of appending | 1 (`test_base_instructions_are_appended_to_not_replaced`) |
      | layer 2 stops denying | 1 |
      | layer 0 stops rejecting | 2 |

---

## 10 · What phase 04 inherits

| Guarantee | From |
|---|---|
| `contracts/roles.py`, `contracts/grants.py`, `check-contracts.sh` exist and are the only grant authority | §2 |
| `RequestContext` is declared and accepted by `define_deep_agent(context_schema=)` | §3 |
| A run without a valid role is rejected before the first model call | §4 |
| Tool surface and prompt text derive from one computed grant set, ordered by `primary_order` | §5 |
| The employee surface is a strict subset of the engineer's | §2 |
| An ungranted call is denied as a readable `ToolMessage` | §6 |
| Runs carry role and granted prefixes in metadata | §7 |
| Middleware order is specified and protected by a test | §8 |
| The whole gate is provable offline | §9 |

Phase 04 must **not** assume: that the middleware has ever run against real MCP
tools, that the deployment has `context_schema` wired yet, or that `mda dev`
and the deployment forward `context` identically — it tests both (O8).

## Open items leaving this phase

| # | Item | Owner |
|---|---|---|
| O3.1 | Whether Deep Agents' built-in tool names could ever contain `__`, which would break `_is_builtin`. Assert the actual loaded names in ph. 04 rather than trusting the heuristic | ph. 04 |
| O3.2 | ~~Disjoint or nested grants?~~ **Closed: nested** (C2). Consequence: the tool filter no longer differentiates the roles on shared-coverage questions, so §5's ordered prompt section carries beat 1 — as preference, not enforcement | closed |
| O3.3 | Whether a rejected run should surface to the UI as a 4xx or as an error event in the stream | ph. 06 |
| O3.4 | Whether `demo_version` enforcement is a pre-commit hook or a pre-deploy script | ph. 05 |
