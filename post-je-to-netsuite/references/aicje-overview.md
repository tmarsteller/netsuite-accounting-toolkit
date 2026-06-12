# Advanced Intercompany Journal Entry (AICJE) — Overview

NetSuite offers two ways to book intercompany activity:

1. **Normal `journalentry` with per-line intercompany fields** — set
   `lineSubsidiary` and `dueToFromSubsidiary` on each line. Works for simple
   two-subsidiary IC entries.
2. **`advintercompanyjournalentry`** (AICJE) — a separate record type designed
   for multi-subsidiary IC. Header has `subsidiary` (from) and
   `toSubsidiaries` (to side(s)). Better audit trail and easier reporting.

The classifier in `SKILL.md` Mode A picks the type automatically:
- 1 subsidiary → `journalentry`
- 2+ subsidiaries → `advintercompanyjournalentry`

The user can override the classification ("post this as a regular JE").

## Header shape

| Field | `journalentry` | `advintercompanyjournalentry` |
|---|---|---|
| `subsidiary` | Booking subsidiary | The "from" subsidiary |
| `toSubsidiary` (singular) | Optional (single-counterparty IC) | Not used |
| `toSubsidiaries` (plural) | Not used | **Required** |
| `exchangeRate` | Not used | Used for cross-currency AICJE |

## Per-subsidiary balance (critical)

NetSuite requires each subsidiary touched by an AICJE to **internally balance**
(its lines sum to $0). A draft that nets to zero overall but unbalances
individual subs will be rejected by NetSuite. The validator enforces this
before posting.

## Multi-subsidiary AICJE (3+ subs)

NetSuite's REST API accepts `toSubsidiaries` as a comma-separated id string:
- 1 counterparty: `"toSubsidiaries": {"id": "28"}`
- 2+ counterparties: `"toSubsidiaries": {"id": "28,30"}`

The skill warns when 3+ subs are detected so you can confirm the formatting
empirically the first time.

## Configure for your org

Pin your AICJE custom form ID in `references/your-org-coa.md` after running:
```sql
SELECT id, name FROM customform WHERE recordtype = 'advintercompanyjournalentry' AND isinactive = 'F'
```
