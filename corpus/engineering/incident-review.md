# Incident review

Written within three business days of any T2 or T3, by the engineer who was
on-call. Blameless: the subject is the system, not the person.

## Contents

1. **Timeline** — what happened, in order, with timestamps from traces rather
   than memory.
2. **What the user experienced.** Not the alert — the answer they got.
3. **Detection** — how we found out, and how long that took. If a user told us
   first, that is the most important finding on the page.
4. **Cause** — the change, condition or assumption. "Human error" is not a
   cause; the system let the error reach production.
5. **What made it worse** — every step that extended the incident, including
   missing or wrong runbooks.
6. **Actions** — each one a `PLAT-` ticket with an owner. No action without a
   ticket, and no ticket without an owner.

## Required actions

Two are not negotiable:

- **An eval case** covering the wrong behaviour, added to
  `plat-<agent>-regression` (`eval-gate.md`).
- **A runbook fix** for anything that was wrong or missing when it was needed.

## What not to do

- Do not close the review on "we will be more careful".
- Do not skip the review because the fix was obvious. The fix is not the point;
  what let it ship is.
