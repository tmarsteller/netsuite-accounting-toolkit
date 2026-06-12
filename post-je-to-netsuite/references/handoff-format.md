# Handoff format — JSON schema sibling skills must produce

Any workflow that hands off to `post-je-to-netsuite` must produce a JSON object
in **this canonical shape**. The shape is intentionally minimal and
ERP-agnostic — `post_je.py` translates it into the right NetSuite payload.

## Schema (informal)

```jsonc
{
  // REQUIRED
  "task_id":   "TASK 042",                      // task number (memo prefix; use your org's convention)
  "memo":       "TASK 042 ME - Monthly Accrual 2026-05",
  "tran_date":  "2026-05-31",                    // ISO YYYY-MM-DD

  // ONE OF: a single subsidiary (→ normal JE) or multiple (→ AICJE)
  "subsidiary":     "10",                        // header "from" subsidiary ID
  "to_subsidiaries": ["20"],                     // OPTIONAL — present means AICJE

  // OPTIONAL header fields
  "custom_form":  "200",                         // NS custom form ID
  "currency":     "1",                           // NS currency ID; default = USD (1)
  "exchange_rate": 1.0,                          // FX, only relevant for AICJE
  "department":   "3",
  "class":        "5",
  "location":     "1",

  // REQUIRED — the lines
  "lines": [
    {
      "account":      "60100",                   // GL account internal ID OR account number
      "account_name": "Professional Services",   // OPTIONAL, helpful for the preview
      "subsidiary":   "10",                      // line-level sub; required for AICJE, optional otherwise
      "debit":        10000.00,                  // exactly one of debit XOR credit
      "credit":       null,
      "memo":         "May consulting accrual",
      "department":   "3",                       // optional, overrides header
      "class":        "5",
      "location":     "1",
      "entity":       "12345"                    // vendor/customer/employee, optional
    },
    {
      "account":      "21500",
      "account_name": "Accrued Liabilities",
      "subsidiary":   "10",
      "credit":       10000.00,
      "memo":         "May consulting accrual"
    }
  ],

  // OPTIONAL — supporting workpaper
  "workpaper": "/path/to/Monthly_Accrual_2026-05.xlsx",

  // OPTIONAL — Slack notification controls (passed through to slack-entry-notify)
  "slack_notes": [                                  // bullet list rendered in the Slack message
    "Rate assumption: see workpaper tab 2.",
    "One-line callouts reviewers should see."
  ],
  "skip_slack": false,                              // if true, no review-channel notification (rare)
  "channel_id": "C0XXXXXXXXX"                       // override the default review channel (rare)
}
```

## Validation rules (what `validate_je.py` checks)

| # | Rule | Outcome on fail |
|---|------|-----------------|
| 1 | `sum(debits) == sum(credits)` (Decimal, $0.00 tolerance) | **Hard fail — do not post** |
| 2 | Each line has `account`, exactly one of `debit` XOR `credit`, and a `memo` | **Hard fail** |
| 3 | `subsidiary` (header) resolves against known subsidiary IDs | **Hard fail** |
| 4 | If `to_subsidiaries` is set: all IDs resolve; the set is disjoint from header `subsidiary` | **Hard fail** |
| 5 | If any line has a `subsidiary` different from header `subsidiary` → must be AICJE (`to_subsidiaries` non-empty) | **Hard fail** |
| 6 | `tran_date` is a valid ISO date | **Hard fail** |
| 7 | `memo` starts with `<TASK-PREFIX> ` | Warn |
| 8 | No line uses legacy account `<acct-id>` | **Loud warn**, ask before posting |
| 9 | `tran_date` is in current or recent past posting period (not >60d stale, not future) | Warn |
| 10 | AICJE: at least 2 distinct subsidiary IDs across lines | Hard fail |

## Producing this format from common sources

### From a Python dict (<your-automation> style)
Already produces the shape — see `<your-payload-builder>.py:get_netsuite_je_payload()`.
Wrap with the converter in `scripts/post_je.py:from_legacy_payload()`.

### From an Excel workbook (`Summary for JE` tab)
Expected columns: `Account | Subsidiary | Debit | Credit | Memo`. Header rows:
memo (cell A1 or B1), tran date (A2 or B2). `scripts/post_je.py:from_excel()`
reads this layout.

### From a free-form JE description in chat
Ask the user to convert to the schema, or let Claude assemble it from the
description. Always show the assembled JSON before validating so the user can
catch transcription errors.

## Schema versioning

This is v1 of the handoff format. If we change it, bump a `_schema: "v2"` field
at the root and update both this doc and `scripts/post_je.py:SCHEMA_VERSION`.
