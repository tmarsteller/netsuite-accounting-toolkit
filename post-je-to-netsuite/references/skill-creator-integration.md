# Skill-creator integration — boilerplate for Mode B

When the user is scaffolding a new skill or automation that will produce a
journal entry, append these three artifacts to the new skill so it hands off
cleanly to `post-je-to-netsuite`.

---

## 1. Append to the new skill's `SKILL.md`

```markdown
## Handoff: posting to NetSuite

This skill does **not** post journal entries directly. When the draft JE is
ready, it must be handed off to the [`post-je-to-netsuite`](../post-je-to-netsuite/)
skill, which renders a chat preview, takes explicit user confirmation, and
creates the record in NetSuite as Pending Approval.

**Contract:** produce a JSON object matching the schema in
[`post-je-to-netsuite/references/handoff-format.md`](../post-je-to-netsuite/references/handoff-format.md),
then surface a message like:

> "Draft JE is ready. Handing off to `post-je-to-netsuite` for review and posting."

That phrasing is one of the `post-je-to-netsuite` trigger phrases, so it will
fire automatically.

### Required handoff fields

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | e.g. `"<TASK-PREFIX> 020"` |
| `memo` | string | Must start with the `task_id` value |
| `tran_date` | string (ISO `YYYY-MM-DD`) | Falls in an open posting period |
| `subsidiary` | string | NetSuite subsidiary internal ID (from-side for IC) |
| `to_subsidiaries` | string[] (optional) | If set, this is an AICJE |
| `lines` | object[] | Each line: `account`, `subsidiary`, `debit` xor `credit`, `memo` |
| `workpaper` | string (optional) | Absolute path to the supporting Excel workbook |

### Example handoff
\`\`\`json
{
  "task_id": "TASK 042",
  "memo": "TASK 042 ME - Monthly Accrual 2026-05",
  "tran_date": "2026-05-31",
  "subsidiary": "10",
  "custom_form": "200",
  "lines": [
    {
      "account": "60100",
      "account_name": "Professional Services",
      "subsidiary": "10",
      "debit": 1000.00,
      "memo": "May consulting accrual"
    },
    {
      "account": "21500",
      "account_name": "Accrued Liabilities",
      "subsidiary": "10",
      "credit": 1000.00,
      "memo": "May consulting accrual"
    }
  ],
  "workpaper": "/path/to/Monthly_Accrual_2026-05.xlsx"
}
\`\`\`
```

---

## 2. Update the new skill's frontmatter `description:`

Add this sentence to the new skill's description (so the dispatcher knows the
chain):

> "…produces a draft JE in the standard handoff format and then hands off to
> `post-je-to-netsuite` for review and posting."

Concretely: edit the new skill's `description:` to end with that phrase.

---

## 3. Remove any "posts to NetSuite" wording

Audit the new skill's description and body for any phrasing that says it
directly posts to NetSuite. The new responsibility split is:
- New skill: **builds** the draft JE
- `post-je-to-netsuite`: **previews + posts** the draft JE

Phrases to replace:
| Before | After |
|---|---|
| "creates the JE in NetSuite" | "produces a draft JE handed off to `post-je-to-netsuite`" |
| "posts to NetSuite" | "hands off to `post-je-to-netsuite`" |
| "books the entry" | "drafts the entry for posting" |

---

## Verification after wiring

After the boilerplate is appended:

1. Re-read the new skill's `SKILL.md` end-to-end — confirm no double-posting
   language.
2. Confirm the description ends with the handoff phrase.
3. Do a dry-run: ask the user to invoke the new skill on a real example;
   verify it produces a handoff JSON, and that `post-je-to-netsuite` then
   auto-triggers and shows the preview.
