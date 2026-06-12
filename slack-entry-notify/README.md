# slack-entry-notify

A small, dependency-free skill/utility that turns a structured JSON payload
into a clean Slack message for **review-queue style notifications** — an entry
with labeled line items, an optional two-column numeric layout (debit/credit,
in/out, before/after), a total, contextual notes, and footer links.

Built for the pattern: *"a workflow just produced something a team should see
and possibly review."* Approvals, postings, reconciliation results, batch
completions, scheduled-job heartbeats.

## Why

Most teams hand-roll Slack notification formatting inside every automation.
This pulls the formatting into one tested, domain-agnostic renderer so each
workflow only has to build a payload.

## What's in the box

```
skill/
  SKILL.md                      # how an agent uses this (Claude Code / Agent SDK skill)
  references/
    payload-shape.md            # the input JSON contract
    message-format.md           # exact output layouts
  scripts/
    render_message.py           # the formatter — pure Python, zero dependencies
  templates/
    notification.md.tpl         # message template reference
examples/
  pending_journal_entry.json    # accounting-style entry, ready for review
  posted_with_benefit.json      # negative amounts (parentheses)
  info_heartbeat.json           # header-only "nothing to do" message
```

## Quick start

The renderer is the whole engine and has no dependencies:

```bash
python skill/scripts/render_message.py examples/pending_journal_entry.json
```

That prints Slack-ready markdown. Post it however you like:

- **Slack MCP server** (Claude Code / Agent SDK): pass the output to a
  `slack_send_message`-style tool with your `channel_id`.
- **Incoming webhook**: `curl -X POST -H 'Content-type: application/json'
  --data "{\"text\": \"$(...)\"}" "$SLACK_WEBHOOK_URL"`.
- **Slack Web API**: `chat.postMessage` with `text=<rendered>`.

## Payload at a glance

```json
{
  "status": "pending",
  "title": "JE #1234 — Monthly Accrual",
  "subtitle": "Acme Holdings, Inc. • 2026-01-31",
  "columns": { "left": "Debit", "right": "Credit" },
  "notes": ["Estimate — confirm before approving."],
  "lines": [
    { "code": "60100", "name": "Consulting Expense", "left": 10000, "right": null },
    { "code": "21500", "name": "Accrued Liabilities", "left": null, "right": 10000 }
  ],
  "total": 10000,
  "link": "https://example.com/erp/journal/1234",
  "link_text": "Open JE #1234"
}
```

Full schema: [`skill/references/payload-shape.md`](skill/references/payload-shape.md).

## Three layouts

| `status`  | Use for |
|-----------|---------|
| `pending` | An entry ready for someone to review/approve (full table). |
| `posted`  | An entry already complete (same table, "complete" framing). |
| `info`    | A short heartbeat with no table ("nothing to do this period"). |

## Customizing

- **Column labels**: `columns: {left, right}` — Debit/Credit, In/Out, Before/After…
- **Currency**: `currency_symbol` (default `$`).
- **Icon / status text**: `icon`, `status_text`.

## Using it as a Claude Code / Agent SDK skill

Drop the `skill/` directory into your skills folder (rename to taste). The
`SKILL.md` frontmatter makes it invocable; the agent renders with the script
and posts via whatever Slack tool your environment exposes.

## Development

```bash
python -m pip install -e ".[test]"
pytest -q
```

The suite (31 tests) covers the renderer end to end and runs on Python 3.9+.

## License

MIT — see [LICENSE](LICENSE).

## Notes

- The renderer makes no network calls and imports only the Python standard
  library. It's safe to vendor `render_message.py` on its own.
- No channel, workspace, company, or domain values are baked in. You supply
  the channel and the posting mechanism.
