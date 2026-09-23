# Corpora

Two corpora, both pushed to private Context Hub repos by the seed scripts.

| Directory | Context Hub repo | Source |
|---|---|---|
| `product/` | `product-docs` | **Generated** by `extract_product.py` from Chat LangChain Lite's `agent/tools.py`. Do not hand-edit; re-run the script. |
| `engineering/` | `engineering-runbooks` | Hand-written. **Entirely fictional** — see below. |

## `engineering/` is fictional, deliberately

Every service name, environment, ticket prefix, rotation, tool and threshold in
`engineering/` is **invented**. Nothing in it describes a real system, a real
procedure, or a real person at any company.

Two reasons:

1. **A demo leaks.** It gets screenshotted, recorded, shown to customers and
   cloned by other engineers. Real internal procedure placed in one travels
   further than the session that created it and cannot be recalled.
2. **Invented content is what makes the demo work.** Because it exists nowhere
   public, no amount of public-documentation breadth can reach it — so the
   employee identity's refusal is structural rather than an artifact of how the
   corpora were split.

The fictional environment, kept consistent across pages:

| Thing | Invented value |
|---|---|
| Team | Platform Agents |
| Change tickets | `PLAT-<number>` |
| CI workflow | `agent-checks` |
| Deploy pipeline | `deploy-agents` |
| Environments | `dev`, `staging`, `prod-us`, `prod-eu` |
| Secret store | Keyring, namespace `platform/agents/*` |
| On-call rotation | `platform-agents-oncall`, tiers T1–T3 |
| Release channel | `#platform-agents-releases` |

If you add a page, keep those names consistent and keep it procedural — and do
not restate anything `product/` already covers, or the two corpora stop being
distinguishable.

## One thing deliberately NOT carried over

Chat LangChain Lite's `SAFE_PATTERNS` contains an intentional bug for its own
demo: it recommends `python.langchain.com` and `js.langchain.com` as canonical
documentation, which are stale domains. `documentation-standards.md` states the
correct domain (`docs.langchain.com`) instead. Do not "restore" the original
wording.
