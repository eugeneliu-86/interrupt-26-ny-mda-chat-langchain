# Rotating a credential

Credentials live in Keyring under `platform/agents/*`. Agents resolve them at
runtime, so rotation does not require a redeploy — which is the point, and why
this procedure is short enough to run under pressure.

## Routine rotation

1. Create the new credential at the provider. Do not revoke the old one yet.
2. Write the new value to the same Keyring path. Overwrite; do not create a
   `-v2` path. A second path is how an agent ends up reading the old value for
   months.
3. Trigger one run per environment and confirm from the trace that the call
   succeeded.
4. Revoke the old credential at the provider.
5. Note the rotation on the `PLAT-` ticket, with the new expiry date.

## Suspected exposure

Order changes: **revoke first.**

1. Revoke at the provider immediately. Accept that agents will fail.
2. Page the on-call engineer and declare a T3.
3. Create the replacement and write it to Keyring.
4. Confirm recovery from a trace.
5. Search for where it leaked — logs, transcripts, tickets, screenshots. A
   credential pasted into a chat or a screenshot is exposed even if the message
   was deleted.

## Standing rules

- **Every credential has an expiry.** A credential with no expiry is an
  unreviewed credential.
- **Record expiry dates on the owning agent's ticket.** An expiring credential
  fails silently months later, and the symptom looks like the agent getting
  worse rather than a credential problem.
- **Never store a credential in a repository**, including in a file you intend
  to delete before committing.
