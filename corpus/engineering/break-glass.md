# Break-glass: recovering a stuck or bad deployment

Use this when an agent is failing in production and the normal deploy path is
too slow or is itself broken. Authorized by the on-call engineer; a Tier-2
engineer's agreement is required before step 3.

## Order of operations

**Roll back before you diagnose.** A running bad revision costs more than the
information you would gain from leaving it up.

1. **Identify the last known-good revision** from `#platform-agents-releases`.
   Every deploy is posted there, which is why the posting rule exists.
2. **Roll back to it** through the `deploy-agents` pipeline using the
   `--rollback` path. This skips approval by design; it is logged.
3. **If the pipeline itself is broken**, get a Tier-2 engineer's agreement, then
   redeploy the known-good commit directly. Record in the incident thread who
   agreed and when.
4. **Confirm recovery by reading a trace**, not by the absence of alerts. An
   agent can answer with a 200 and still be wrong.
5. **Only then diagnose.** Attach the failing traces to the incident thread.

## If a credential is the suspected cause

Do not roll back first. Go to `rotate-a-credential.md` — rolling back a
revision does not revoke a leaked credential, and the rollback will appear to
fix the symptom while the exposure continues.

## Afterwards

- File a `PLAT-` ticket within one business day.
- Write the incident review (`incident-review.md`) within three business days.
- If the rollback required step 3, the pipeline break is its own `PLAT-`
  ticket, and it is a T1 until fixed. A broken rollback path is the failure
  that makes every other failure worse.
