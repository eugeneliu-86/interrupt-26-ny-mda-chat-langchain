# Environments

Four environments. Each has a different purpose and a different rule about who
may change it.

| Environment | Purpose | Who deploys | Data |
|---|---|---|---|
| `dev` | Individual development. Recreated freely. | anyone on the team | synthetic only |
| `staging` | Pre-production verification. Mirrors `prod-us` configuration. | anyone on the team | synthetic only |
| `prod-us` | Production, US region. | `deploy-agents` pipeline only | real |
| `prod-eu` | Production, EU region. Deployed after `prod-us`. | `deploy-agents` pipeline only | real, must not leave the region |

## Rules that are not negotiable

- **No real data in `dev` or `staging`.** If you need realistic inputs, use the
  synthetic fixtures in the agent's own eval dataset.
- **`prod-eu` data stays in `prod-eu`.** Do not copy threads, traces or
  datasets from `prod-eu` into any other environment, including for debugging.
- **Nothing is deployed to production by hand.** If the pipeline is broken, fix
  the pipeline or follow `break-glass.md`; do not work around it.
- **`staging` configuration drift is a bug.** If `staging` and `prod-us` differ
  in anything but scale, open a `PLAT-` ticket. A verification environment that
  does not match production verifies nothing.
