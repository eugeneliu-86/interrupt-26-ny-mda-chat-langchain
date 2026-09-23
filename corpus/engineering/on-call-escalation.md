# On-call and escalation

The rotation is `platform-agents-oncall`. One primary, one secondary, weekly
handover on Monday.

## Tiers

| Tier | Means | Response target | Who |
|---|---|---|---|
| T1 | Degraded: elevated latency or error rate, agent still answering | 30 minutes, business hours | primary |
| T2 | Down: an agent is not answering, or answering wrongly in production | 15 minutes, any hour | primary, then secondary at 15 min |
| T3 | Data or credential exposure | immediate | primary pages the team lead directly |

## Escalation path

1. **Primary** acknowledges and starts a thread in
   `#platform-agents-releases`. Post what you see before you start fixing —
   an unrecorded early symptom is the thing you will wish you had later.
2. **Secondary** is paged automatically if a T2 is unacknowledged for 15
   minutes.
3. **Team lead** is paged for any T3, and for a T2 lasting more than an hour.
4. A T3 is never handled by one person alone. Wake someone.

## What the on-call engineer may do without a ticket

- Roll back a revision (`break-glass.md`).
- Disable a schedule or a channel.
- Rotate a credential they believe is exposed (`rotate-a-credential.md`).

Everything else waits for a `PLAT-` ticket. File the ticket retroactively
within one business day, naming the tier and what was done.
