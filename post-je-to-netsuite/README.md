# post-je-to-netsuite

A Claude Code skill for safely posting journal entries to NetSuite via the
NetSuite MCP connector. Designed as the **universal terminal step** for any
accounting workflow that produces a JE: render a chat preview, take explicit
user confirmation, then create the record in NetSuite as **Pending Approval**.

## Quick install — paste this into Claude

Not sure where to start? Copy the block below and paste it into Claude Code.
Claude will clone the skill, ask you for your NetSuite details, and configure
everything interactively.

```
Install the post-je-to-netsuite skill from GitHub and set it up for my NetSuite account.

Repo: https://github.com/tmarsteller/netsuite-accounting-toolkit

Steps:
1. Clone the repo into my Claude skills directory (~/.claude/skills/post-je-to-netsuite/).
2. Look up my NetSuite subsidiary IDs using ns_getSubsidiaries (or ask me to paste them).
3. Update KNOWN_SUBSIDIARIES in scripts/validate_je.py with my real IDs and names.
4. Fill in references/your-org-coa.md.template with my subsidiary list, custom form IDs,
   and any key accounts. Save it as references/your-org-coa.md.
5. Confirm the skill is ready and show me the trigger phrases I can say to use it.
```

## Why

Most JE-producing automations either reinvent the NetSuite payload assembly
or stop at "draft in Excel" and rely on a human to retype the JE into NS. This
skill closes that gap with a single, audited posting path that:

- Validates balance, account/subsidiary IDs, and required fields before posting
- Renders a markdown preview in the chat so the human reviews exactly what
  will hit NetSuite
- Hard-codes Pending Approval (`approved: false`, `approvalStatus.id: "1"`) so
  approval workflows can't be accidentally bypassed
- Supports both `journalentry` and `advintercompanyjournalentry` (AICJE)

## Install

1. Copy this folder into your Claude Code skills directory:
   - Project-level: `<your-repo>/.claude/skills/post-je-to-netsuite/`
   - User-level: `~/.claude/skills/post-je-to-netsuite/`
2. Make sure the NetSuite MCP connector is installed and authenticated
   (`mcp__...__ns_createRecord` available).
3. Fill in `references/your-org-coa.md.template` with your subsidiary IDs,
   custom form IDs, and key accounts. Rename it to `your-org-coa.md`.
4. Read `SKILL.md` end-to-end before first use.

## Customize for your org

Edit these files to match your NetSuite tenant:
- `references/your-org-coa.md.template` — your subsidiary list, custom forms, account refs
- `scripts/validate_je.py` — replace `KNOWN_SUBSIDIARIES` with your real IDs
- The `SKILL.md` description — adjust trigger phrases for your team's vocabulary

## Layout

```
post-je-to-netsuite/
├── SKILL.md
├── references/
│   ├── payload-shapes.md
│   ├── handoff-format.md
│   ├── your-org-coa.md.template
│   ├── aicje-overview.md
│   └── skill-creator-integration.md
├── scripts/
│   ├── validate_je.py
│   ├── render_preview.py
│   └── post_je.py
└── templates/
    └── je-preview.md.tpl
```

## License

MIT — see `LICENSE`.
