# NetSuite Accounting Toolkit

Production-tested tools for accounting teams running their close on NetSuite —
Claude Code skills, SuiteScripts, and Python helpers, built and battle-tested
in a real multi-subsidiary fintech close process and sanitized for general use.

Everything here follows the same operating principles:

1. **Journal entries are always created in Pending Approval** — the automation
   is the preparer, never the approver. A human reviews and approves in NetSuite.
2. **Preview before post.** Drafts are rendered for explicit confirmation
   before anything touches the ERP.
3. **No secrets in the repo.** Credentials come from environment variables or
   gitignored config files; example templates are provided.
4. **Auditability first.** Workpapers use formulas (never hardcoded totals),
   memos carry task numbers, and every tool surfaces what it did.

## What's in here

| Folder | Type | What it does |
|---|---|---|
| [post-je-to-netsuite](post-je-to-netsuite/) | Claude Code skill | Universal terminal step for any workflow that produces a JE: validates (balance, accounts, subsidiaries), renders a preview table in chat, and on explicit confirmation creates the entry as **Pending Approval** via the NetSuite MCP connector. Supports normal JEs and Advanced Intercompany JEs. |
| [slack-entry-notify](slack-entry-notify/) | Claude Code skill | Renders a structured payload (entry, line items, totals, notes, links) into a clean review-queue-style Slack message. Chained automatically by `post-je-to-netsuite` after each create. |
| [netsuite-file-attach](netsuite-file-attach/) | RESTlet + Python + skill | NetSuite's REST API can't create files. This SuiteScript 2.1 RESTlet (with SDF deploy project and an OAuth 1.0 TBA Python caller) uploads a file to the File Cabinet and attaches it to any record — JE workpapers, invoice support, etc. |
| [rippling-aicje-name](rippling-aicje-name/) | SuiteScript (UE + Map/Reduce) | Auto-fills the line-level Name (entity) field on Advanced Intercompany JEs created by the Rippling payroll integration — Rippling leaves it blank, which breaks intercompany elimination. Fail-open User Event + daily sweep backstop. |
| [netsuite-developer](netsuite-developer/) | Claude Code skill | Disciplined, schema-aware NetSuite development: SuiteQL/SuiteScript guardrails (no DB calls in loops, no unbounded searches, injection-safe queries), MCP connector best practices, and optional feature modules (Multi-Book, ARM, SuiteBilling, SuiteTax). |
| [orchestrator](orchestrator/) | Python library | Headless helpers for scripted automations: post a Pending Approval JE via REST (OAuth 1.0 TBA), look up posting periods, verify balance, notify Slack. |
| [docs/claude-netsuite-admin-setup-guide.pdf](docs/claude-netsuite-admin-setup-guide.pdf) | Setup guide (PDF) | **Start here.** Step-by-step admin guide to connect Claude to NetSuite via the MCP connector — integration record, token-based auth, roles/permissions, and the Claude-side configuration. Prerequisite for the skills below. |
| [docs/HOW_WE_BUILT_IT_TEMPLATE.md](docs/HOW_WE_BUILT_IT_TEMPLATE.md) | Template | Fill-in-the-blanks doc for writing up an accounting automation after you ship it — problem, design decisions, toolchain, gotchas, cost, ownership. Written for controllers and auditors, not engineers. |

## How the pieces chain together

```
your close workflow (recon / accrual / adjustment)
        │  produces a draft JE in the standard handoff format
        ▼
post-je-to-netsuite ── validate → preview → confirm → create (Pending Approval)
        │                                        │
        ▼                                        ▼
netsuite-file-attach                    slack-entry-notify
(attach the workpaper to the JE)        (notify the review channel)
```

Each tool also works standalone — the chaining is convention, not coupling.

## Related

- [structured-vibe-accounting](https://github.com/tmarsteller/structured-vibe-accounting) —
  the six-phase guided process used to design and document these automations.
  ERP-agnostic, so it lives in its own repo.

## Setup

Each folder is self-contained with its own README, requirements, and (where
applicable) example config. Broadly:

- **Claude Code skills**: copy the folder into `~/.claude/skills/` (or your
  project's `.claude/skills/`). The JE-posting skills assume the NetSuite MCP
  connector is configured — see
  [docs/claude-netsuite-admin-setup-guide.pdf](docs/claude-netsuite-admin-setup-guide.pdf)
  to set that up first.
- **SuiteScripts**: deploy via the included SDF projects
  (`suitecloud account:setup`, validate, deploy) under your own account; script
  IDs are parameterized.
- **Python tools**: `pip install -r requirements.txt` per folder; credentials
  via env vars or gitignored config (templates included).

## License

Each component carries its own LICENSE file (MIT unless noted;
`netsuite-developer` is adapted from
[joshOrigami/netsuite-developer](https://github.com/joshOrigami/netsuite-developer)
under CC-BY-4.0 — attribution preserved in its SKILL.md).
