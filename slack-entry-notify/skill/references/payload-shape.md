# Payload shape

The skill accepts a single JSON object. All fields below; only `title` (and
`status`) are strictly required.

```jsonc
{
  // === Routing / control ===
  "status":       "pending",          // "pending" | "posted" | "info"  (default: pending)
  "channel_id":   "C0XXXXXXX",        // target channel — supply per call or via your config
  "skip":         false,              // if true, the skill exits without posting

  // === Header ===
  "title":        "Entry #1234",      // REQUIRED — the bold headline
  "subtitle":     "Acme LLC • 2026-01-31",  // optional italic subline
  "icon":         ":receipt:",        // optional emoji override
  "status_text":  "ready for review", // optional override of the trailing header text

  // === Notes (rendered as blockquotes, in order) ===
  "notes": [
    "Heads-up: rate assumption is an estimate.",
    "Source pulled live at run time."
  ],

  // === Line items (optional; omit for a header-only message) ===
  "columns": { "left": "Debit", "right": "Credit" },   // column labels (default Left/Right)
  "currency_symbol": "$",                               // default "$"
  "lines": [
    { "code": "4000", "name": "Revenue",   "left": 10000.00, "right": null },
    { "code": "1000", "name": "Cash",      "left": null,     "right": 10000.00 },
    { "label": "Custom freeform label",    "left": 5,        "right": null }
  ],
  "total": 10000.00,                  // optional; renders a bold Total row (both columns)

  // === Footer ===
  "link":             "https://example.com/record/1234",
  "link_text":        "View record",            // default "View record"
  "attachment_path":  "Workpaper: /path/to/file.xlsx",  // shown verbatim after a 📎

  // === For status: "info" (header-only heartbeat) ===
  "workflow_name": "Monthly Recon",
  "period":        "January 2026",
  "reason":        "No exceptions this period — nothing to review."
}
```

## Field reference

| Field | Used by | Notes |
|---|---|---|
| `title` | all | Required. Bold headline. |
| `status` | all | `pending` / `posted` / `info`. Default `pending`. |
| `channel_id` | all | Not consumed by the renderer; used by the posting step. |
| `skip` | all | If true, skill exits without posting. |
| `subtitle` | pending/posted | Italic subline under the title. |
| `notes` | all | List of strings → blockquote lines. |
| `columns` | pending/posted | `{left, right}` column labels for the table. |
| `currency_symbol` | pending/posted | Prefix for numeric cells. |
| `lines` | pending/posted | List of `{code?, name?, label?, left?, right?}`. |
| `total` | pending/posted | Bold total row. Omit to skip. |
| `link` / `link_text` | pending/posted | Footer hyperlink. |
| `attachment_path` | all | Free text after a 📎 (e.g. a file path). |
| `workflow_name` / `period` / `reason` | info | Header + body for the heartbeat layout. |

## Line item formatting

- Numeric cells: blank when null/0, parentheses for negatives (accounting style),
  no decimals for whole numbers, 2 decimals otherwise.
- Label: `code + name` when both present (e.g. "4000 Revenue"), else `label`,
  else whichever of code/name exists.
- Tables longer than 20 rows are truncated to 18 with a "+ N more" footer row
  (keeps under Slack's message size limit).
