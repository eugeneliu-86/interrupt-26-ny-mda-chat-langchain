"""What exists, who may reach it, and what they should prefer (C2).

THE SINGLE SOURCE. Every corpus name, repo name, connection slug, grant and
preference ordering is written here and nowhere else. Middleware imports it,
tests import it, and `emit_grants_json.py` projects it for the UI. A second
hand-written copy anywhere is a bug waiting to disagree with this one.

NESTED GRANTS. `employee` is a STRICT subset of `engineer`: an engineer can
reach everything an employee can, plus the internal runbooks. This models a
real organization, where seniority accretes access rather than swapping it.

The consequence shapes the whole demo, so it is written down rather than
rediscovered: the asymmetry runs ONE WAY. There is no question the employee can
answer that the engineer cannot. So the demo has two beats:

  1. same question, different answers — rests on PRIMARY_ORDER, which is
     PREFERENCE expressed in the prompt, not enforcement;
  2. refusal — the employee's tools cannot reach `engineeringDocs` at all,
     which IS enforcement, and is the only place the difference is guaranteed.

Never present beat 1 as enforced. Beat 2 is what enforcement looks like.
"""

from __future__ import annotations

from contracts.roles import ROLES, Role

#: The Context Hub owner handle for this workspace.
#:
#: `pull_agent` requires an OWNER-QUALIFIED identifier: the bare handle returns
#: 400 "invalid repository reference" in this workspace, even though the docs
#: say a bare name resolves against the current workspace owner. Measured
#: against the real deployment, so treat the qualified form as required.
HUB_OWNER = "chat-lc-lite"

#: corpus prefix -> (Context Hub repo, connection slug).
#:
#: Both corpora share one connection because Context Hub access is
#: workspace-level, not per-repo. Three named connections holding one
#: credential would be theater; one real connection is the honest claim.
CORPORA: dict[str, tuple[str, str]] = {
    "productDocs": ("product-docs", "context-hub-corpus"),
    "engineeringDocs": ("engineering-runbooks", "context-hub-corpus"),
}

#: corpus prefix -> how the agent and the UI describe it to a person.
#:
#: Each blurb describes its own corpus and never mentions another. A blurb that
#: named the internal runbooks would tell an employee-role model that they
#: exist, inviting exactly the speculation `instructions.md` forbids (C7).
CORPUS_BLURB: dict[str, str] = {
    "productDocs": "public LangChain product documentation",
    "engineeringDocs": "internal engineering runbooks for this team",
}

#: role -> the tool-name prefixes that role may call.
GRANTS: dict[Role, frozenset[str]] = {
    "engineer": frozenset({"productDocs", "engineeringDocs"}),
    "employee": frozenset({"productDocs"}),
}

#: role -> its corpora, most authoritative first.
#:
#: Injected into the system prompt per run so each role answers from the most
#: specific corpus it holds. This SHAPES ANSWERS; it gates nothing.
PRIMARY_ORDER: dict[Role, tuple[str, ...]] = {
    "engineer": ("engineeringDocs", "productDocs"),
    "employee": ("productDocs",),
}

#: role -> the label the UI shows. Display only; never an authorization input.
ROLE_LABELS: dict[Role, str] = {
    "engineer": "Lang · Engineer",
    "employee": "Polly · Employee",
}

# --- invariants -------------------------------------------------------------
# These run at import so a change to the access model is a deliberate act with
# a failing assert to delete, rather than a diff nobody notices.

assert set(GRANTS) == set(ROLES), "every role needs a grant"
assert set(PRIMARY_ORDER) == set(ROLES), "every role needs a preference ordering"
assert set(ROLE_LABELS) == set(ROLES), "every role needs a label"
assert set(CORPUS_BLURB) == set(CORPORA), "every corpus needs a blurb"

for _role, _prefixes in GRANTS.items():
    assert _prefixes <= set(CORPORA), f"{_role} grants an unknown corpus"
    # A role must be told to prefer exactly what it holds, or the prompt and
    # the tool surface disagree — the one bug the single-hook gate exists to
    # make unrepresentable.
    assert set(PRIMARY_ORDER[_role]) == _prefixes, f"{_role}: order != grant"

# Nesting is the design. STRICT subset: if these were ever equal, every other
# assertion here would still pass while the demo had silently stopped
# demonstrating anything.
assert GRANTS["employee"] < GRANTS["engineer"], "employee must be nested in engineer"

# The one exclusion the demo depends on. Beat 2 exists only because of it.
assert "engineeringDocs" not in GRANTS["employee"]


def granted_prefixes(role: str) -> frozenset[str]:
    """The tool-name prefixes this role may call. Raises on an unknown role.

    This raise is how C1's rejection is implemented: one function, one failure
    mode, used by every middleware layer.
    """
    try:
        return GRANTS[role]  # type: ignore[index]
    except KeyError:
        raise ValueError(
            f"unknown role {role!r}; expected one of {', '.join(sorted(ROLES))}"
        ) from None


def primary_order(role: str) -> tuple[str, ...]:
    """This role's corpora, most authoritative first. Shapes answers only."""
    granted_prefixes(role)  # one failure mode for an unknown role
    return PRIMARY_ORDER[role]  # type: ignore[index]


def withheld_prefixes(role: str) -> frozenset[str]:
    """Corpora this role cannot reach. Emitted for the UI's `✗` row.

    Derived here rather than in TypeScript so "what this role cannot reach"
    has exactly one implementation.
    """
    return frozenset(CORPORA) - granted_prefixes(role)


def repo_and_slug(prefix: str) -> tuple[str, str]:
    """The owner-qualified Context Hub repo and connection slug for one corpus.

    The repo is returned already qualified, so no caller has to remember that
    `pull_agent` rejects a bare handle.
    """
    try:
        repo, slug = CORPORA[prefix]
    except KeyError:
        raise ValueError(f"unknown corpus {prefix!r}") from None
    return f"{HUB_OWNER}/{repo}", slug
