# Deploying an agent to production

Applies to every agent owned by Platform Agents. Product documentation covers
how the platform's deploy mechanism works; this page is what we additionally
require.

## Before you deploy

1. Open a `PLAT-` change ticket. One ticket per deploy, even for a prompt-only
   change.
2. `agent-checks` must be green on the commit you intend to ship. A red or
   skipped run is not a deploy candidate.
3. The eval gate must pass — see `eval-gate.md`.
4. If the change alters agent behaviour, bump the agent's version counter in
   the same commit. Traces are compared by that counter, so a behaviour change
   that reuses a version makes the comparison meaningless.

## Deploying

1. Deploy to `staging` first. Always, including for prompt-only changes.
2. Run the agent's smoke questions against `staging` and read the traces. Do
   not rely on the run succeeding — read what the agent actually did.
3. Promote through the `deploy-agents` pipeline. The pipeline requires a second
   engineer's approval on the `PLAT-` ticket; self-approval is blocked.
4. Deploy `prod-us`, wait for one clean run, then `prod-eu`. Never both at once
   — a bad revision in both regions leaves nowhere to fail over to.
5. Post the ticket and the revision in `#platform-agents-releases`.

## Freeze window

No production deploys after 14:00 UTC on Fridays, or during an active Tier-2
incident. Break-glass deploys are the exception and follow `break-glass.md`.

## If it goes wrong

Roll back first, diagnose second. The rollback procedure is in
`break-glass.md`. Do not attempt a forward fix in production without the
on-call engineer's agreement.
