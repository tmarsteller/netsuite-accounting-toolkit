# NetSuite `ns_createRecord` payload shapes

Sourced from the live NetSuite REST metadata catalog
(`/services/rest/record/v1/metadata-catalog/<recordType>`) on 2026-05-22 via
`ns_getRecordTypeMetadata`, and cross-checked against a known-working
JE payload in the parent repository.

The MCP tool is:

```
mcp__<your-netsuite-connector-id>__ns_createRecord
```

It takes two top-level arguments:

```json
{
  "recordType": "journalentry" | "advintercompanyjournalentry",
  "data": { ... see below ... }
}
```

---

## 1. `journalentry` — normal JE (single subsidiary, or single-counterparty IC)

```jsonc
{
  "recordType": "journalentry",
  "data": {
    "customForm":    { "id": "200" },            // optional; e.g. Standard JE form
    "subsidiary":    { "id": "10" },             // REQUIRED — the booking subsidiary
    "tranDate":      "2026-05-31",               // ISO date
    "memo":          "TASK 042 ME - Monthly Accrual 2026-05",
    "currency":      { "id": "1" },              // optional; defaults to subsidiary base ccy
    "approved":      false,                      // HARD-CODED FALSE
    "approvalStatus": { "id": "1" },             // HARD-CODED Pending Approval
    "line": {
      "items": [
        {
          "account": { "id": "60100" },          // GL account internal ID
          "debit":   1234.56,                    // number, 2dp; exactly one of debit XOR credit
          "credit":  null,
          "memo":    "Monthly consulting accrual",
          "department": { "id": "3" },           // optional
          "class":      { "id": "5" },           // optional
          "location":   { "id": "1" },           // optional
          "entity":     { "id": "12345" },       // optional — vendor/customer/employee
          "lineSubsidiary":      { "id": "20" }, // optional — for per-line intercompany on a NORMAL JE
          "dueToFromSubsidiary": { "id": "20" }  // optional — pairs with lineSubsidiary
        },
        {
          "account": { "id": "21500" },
          "credit":  1234.56,
          "memo":    "Monthly consulting accrual"
        }
      ]
    }
  }
}
```

**Notes:**
- `subsidiary.id` MUST be the string form of the subsidiary internal ID.
- `tranDate` must fall in an open posting period.
- `line.items` is the sublist; the wrapping shape is exactly `{ "line": { "items": [...] } }`.
- `debit` and `credit` are mutually exclusive per line — set the one that applies, leave the other unset or null.
- `approvalStatus.id` enum is `["11", "1", "2", "3"]`; we always send `"1"` (Pending Approval).

---

## 2. `advintercompanyjournalentry` (AICJE) — multi-subsidiary

Same shape as `journalentry` **plus** two header changes:

```jsonc
{
  "recordType": "advintercompanyjournalentry",
  "data": {
    "customForm":     { "id": "<aicje-form-id>" },
    "subsidiary":     { "id": "10" },              // the "from" subsidiary
    "toSubsidiaries": { "id": "20" },              // the "to" subsidiary (or list — see below)
    "tranDate":       "2026-05-31",
    "memo":           "TASK 099 ME - ICO Clearing Reclass 2026-05",
    "currency":       { "id": "1" },
    "exchangeRate":   1.0,                         // FX between subsidiary and toSubsidiaries
    "approved":       false,
    "approvalStatus": { "id": "1" },
    "line": {
      "items": [
        {
          "account": { "id": "13000" },            // ICO clearing account on the FROM side
          "debit":   10000.00,
          "memo":    "Reclass May ICO",
          "department": { "id": "3" }
        },
        {
          "account": { "id": "23000" },            // ICO payable on the TO side
          "credit":  10000.00,
          "memo":    "Reclass May ICO"
        }
      ]
    }
  }
}
```

**Key differences from a normal JE:**
| Field | `journalentry` | `advintercompanyjournalentry` |
|---|---|---|
| Header `subsidiary` | Booking subsidiary | The "from" / posting subsidiary |
| Header `toSubsidiary` (singular) | Present — used for single-counterparty IC | NOT present |
| Header `toSubsidiaries` (plural) | NOT present | **Required** — the other side(s) of the IC |
| Header `exchangeRate` | Not present | Present — FX between the two subs |
| Line `lineSubsidiary` | Present (optional) | NOT present on AICJE lines |
| Line `dueToFromSubsidiary` | Present (optional) | NOT present on AICJE lines |
| Per-line IC indicator | `dueToFromSubsidiary` | `custcol_ic_act_type` (custom col) |

**Multi-subsidiary AICJE (3+ subs):**
The metadata schema shows `toSubsidiaries` as a single reference object (`{id, refName, externalId}`), but the field name is plural. In practice, NetSuite's REST API accepts this as a comma-separated list of IDs for multi-target AICJEs. For 3+ subsidiaries, format as:

```json
"toSubsidiaries": { "id": "28,30" }
```

**Open item:** validate the multi-target format against a real 3-subsidiary AICJE the first time we encounter one. For now, `validate_je.py` warns when >2 distinct subsidiaries appear and asks the user to confirm.

---

## 3. The hard-coded Pending Approval guard

Every payload — both record types — has these two fields hard-coded by
[`scripts/post_je.py`](../scripts/post_je.py). They are **not** parameters
the caller can override:

```python
data["approved"] = False
data["approvalStatus"] = {"id": "1"}
```

If the inbound handoff payload has `approved: true` or any other
`approvalStatus.id`, the post script overwrites them silently and logs a
warning. Per `~/.claude/CLAUDE.md`:
> *"NEVER create JEs in approved/posted status. All journal entries must be
> created in Pending Approval state. No exceptions."*

---

## 4. Custom body fields commonly set

These show up in NetSuite metadata for both record types and may matter for
specific workflows:

- `custbody_ic_aje` (boolean) — "Intercompany AJE" — set TRUE for adjusting IC entries
- `custbody_ico_je_created` (boolean) — automation flag; leave default
- `custbody_st_invoice_number` (string) — useful for AR-related JEs
- `custbody1` (string) — "Loan ID" — used by lending workflows

Skip these unless the inbound handoff explicitly requests them.

---

## 5. Reading existing JEs (sanity check before reposting a duplicate)

Before posting, you can check for an existing JE with the same memo via
SuiteQL:

```sql
SELECT id, tranid, trandate, memo, approvalstatus
FROM transaction
WHERE recordtype IN ('journalentry', 'advintercompanyjournalentry')
  AND TO_CHAR(trandate, 'YYYY-MM') = '2026-05'
  AND memo LIKE '%TASK 042%'
```

The skill should warn (not block) if a matching pending JE already exists for
the same month + task number.
