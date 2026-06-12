---
name: slack-entry-notify
user_invocable: true
description: >
  Post a standardized, review-queue-style notification to a Slack channel from
  a structured payload — an entry with labeled line items (optional two-column
  numeric layout like debit/credit or in/out), a total, contextual notes, and
  footer links. Designed as a reusable terminal step that any workflow can
  call after it produces a record worth notifying a team about.

  Trigger phrases: "notify Slack", "post to the review channel", "send the
  notification", "announce this entry", "Slack the record", "post to Slack
  for review".

  Three layouts: pending (ready for review), posted (already complete), and
  info (a short heartbeat with no line table).
---

# slack-entry-notify — Universal Slack Notification Step

A small, dependency-light skill that turns a structured payload into a clean
Slack message and posts it to a channel. Built for "something happened that a
team should see and possibly review" — approvals, postings, recon results,
batch completions, etc.

## Setup (do this once per environment)

1. **Connect a Slack integration.** This skill posts via whatever Slack tool
   your environment exposes — an MCP server (`slack_send_message`-style tool),
   an incoming webhook, or the Slack Web API. The skill is tool-agnostic: it
   renders the message text, you post it with whatever you have.
2. **Pick a default channel** and put its ID in your environment / config.
   The skill never hardcodes a channel — it must be supplied per call or via
   your own config.

## How it works

1. Receive a payload (see [references/payload-shape.md](references/payload-shape.md)).
2. Render the message with `scripts/render_message.py` — pure formatting, no
   network calls.
3. Post the rendered text to the target channel using your Slack tool.
4. Echo the message permalink back to the caller.

```
python scripts/render_message.py payload.json   # prints Slack-ready markdown
```

## Operating modes

### Mode A — Chained from another workflow (the main use)
A producing workflow finishes (creates a record, completes a recon, etc.),
builds a payload, and invokes this skill as its terminal step. If the payload
sets `"skip": true`, exit cleanly without posting.

### Mode B — Manual / standalone
A user asks to notify a channel about something. Collect the details, render,
show the message in chat, get explicit confirmation, then post.

## Message layouts

See [references/message-format.md](references/message-format.md) for exact
output. Selected by payload `status`:

- `pending` — full entry with line table + total + links ("ready for review")
- `posted`  — same layout, "complete" framing
- `info`    — short message, no table (e.g. "nothing to do this period")

All layouts support:
- Title + optional subtitle
- Contextual notes (rendered as blockquotes)
- Footer link + attachment reference

## Customization

- **Column labels** — set `payload["columns"] = {"left": "Debit", "right": "Credit"}`
  (or "In"/"Out", "Before"/"After", etc.). Defaults to "Left"/"Right".
- **Currency symbol** — `payload["currency_symbol"]` (default `$`).
- **Icons / status text** — override `payload["icon"]` and `payload["status_text"]`.

## Files

- `SKILL.md` — this file
- `references/payload-shape.md` — input JSON contract
- `references/message-format.md` — exact output layouts with examples
- `scripts/render_message.py` — the formatter (pure Python, no deps)
- `templates/notification.md.tpl` — message template reference
- `../examples/` — runnable sample payloads

## Design notes

The formatter (`render_message.py`) has **no external dependencies** and no
knowledge of any specific domain, company, or channel. It's safe to lift into
any project on its own. The line table is a generic two-numeric-column layout;
name the columns whatever fits your use case.
