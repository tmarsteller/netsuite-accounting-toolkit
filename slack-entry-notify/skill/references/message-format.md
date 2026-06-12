# Message format

Three layouts, chosen by payload `status`. All use Slack-flavored markdown.

---

## Layout 1: `status = "pending"` (default)

```
:receipt: **<TITLE>** — <status_text or "ready for review">
_<SUBTITLE>_

> <note 1>
> <note 2>

| Item | <left label> | <right label> |
|---|---:|---:|
| <line label> | <left> | <right> |
| ... |  |  |
| **Total** | **<total>** | **<total>** |

🔗 [<link_text>](<link>)
📎 <attachment_path>
```

**Example:**

```
:receipt: **Entry #1234** — ready for review
_Acme LLC • 2026-01-31_

> Rate assumption is an estimate — confirm before approving.

| Item | Debit | Credit |
|---|---:|---:|
| 4000 Revenue |  | $10,000 |
| 1000 Cash | $10,000 |  |
| **Total** | **$10,000** | **$10,000** |

🔗 [View record](https://example.com/record/1234)
📎 Workpaper: /path/to/file.xlsx
```

---

## Layout 2: `status = "posted"`

Identical to Layout 1 except the icon defaults to `:white_check_mark:` and the
trailing text defaults to "complete".

---

## Layout 3: `status = "info"` (header-only heartbeat)

```
:information_source: **<workflow_name or title>** — <period>

<reason>

> <note>
📎 <attachment_path>
```

**Example:**

```
:information_source: **Monthly Recon** — January 2026

No exceptions this period — nothing to review.
```

---

## Formatting rules

- **Numeric cells**: blank when null/0; parentheses for negatives; whole
  numbers show no decimals, otherwise 2 decimals.
- **Empty cells** stay blank (no `$0`, no dash).
- **Notes** become blockquote lines, emoji prefixes preserved.
- **Attachment path** rendered verbatim (not a hyperlink — local/UNC paths
  don't resolve as Slack links).
- **Long tables** (>20 rows) truncate to 18 + a "+ N more" row.
