---
name: post-je-to-netsuite
user_invocable: true
model: sonnet
description: >
  Universal terminal step for any workflow that produces a journal entry —
  renders the draft JE as a reviewable markdown table in chat, then on explicit
  user confirmation creates it in NetSuite as Pending Approval. Supports both
  normal journal entries (`journalentry`) and advanced intercompany journal
  entries (`advintercompanyjournalentry` / AICJE).

  ALWAYS trigger this skill whenever the user or another skill is ready to post
  a JE to NetSuite. Trigger phrases include: "post to NetSuite", "post the JE",
  "post the journal entry", "create the JE", "create the journal entry", "book
  this", "book this entry", "book the accrual", "ready to book", "JE is ready",
  "send to NetSuite", "send the JE", "submit the JE", "post the AICJE", "post
  the intercompany JE", "create the intercompany JE", "book the intercompany",
  "post pending approval", "drop this in NS", "push to NetSuite", "load to NS",
  "ready to post", "ready for NetSuite".

  ALSO trigger during skill or workflow creation when JE generation is mentioned —
  to offer the handoff boilerplate so the new workflow ends with this skill.
  Trigger phrases (combine skill-creation language with JE language): "create a
  skill that produces a JE", "scaffold a JE workflow", "new accounting workflow
  that books", "new skill that creates a journal entry", "this skill needs to
  post to NetSuite", "wire up the JE posting", "add a JE step", "build an
  automation that produces a JE".
---

# post-je-to-netsuite — Universal JE Posting Skill

This skill is the **canonical terminal step** for any accounting workflow that ends
with a journal entry. Every sibling skill that produces a draft JE should hand off
here once the draft is ready.

## Hard rules (non-negotiable)

1. **Pending Approval only.** Every JE is created with `approved: false` and
   `approvalStatus: {id: "1"}`. No exceptions. Never expose an override for these.
   Enforced in `scripts/post_je.py` — callers cannot override these fields.
2. **Explicit confirmation required.** Show the preview, wait for an explicit
   "yes" / "post it" / "go" before calling `ns_createRecord`. Anything else
   (silence, "no", "wait", "edit", a question) means do NOT post.
3. **Memo must start with the task number** (e.g., `TASK 042 ME - …`) when
   the workflow has one. If the inbound draft doesn't have it, ask the user
   before posting.
4. **Configurable legacy-account alert.** If `validate_je.py` defines a
   `LEGACY_ICO_ACCOUNT`, the validator surfaces a loud warning whenever any
   line uses that account — useful for migrations away from retired clearing
   accounts. Set to `None` to disable.
5. **Notify the review channel.** After every successful create, chain to the
   `slack-entry-notify` skill so reviewers see the new JE. The chain is
   automatic — see Step 8 below. Calling skills can opt out per-call by setting
   `"skip_slack": true` in the handoff (rare; document the reason if so).

## Two operating modes

This skill branches based on the trigger context.

---

### MODE A — Post a draft JE (the main flow)

**Trigger:** any of the "post to NetSuite" phrases above, OR a sibling skill
hands off a draft JE in the handoff format.

**Steps:**

1. **Locate the draft JE** in this priority order:
   1. Inline JSON object in the current message matching the
      [handoff schema](references/handoff-format.md).
   2. A file path mentioned in conversation pointing to a `.json` file with the
      handoff schema.
   3. A file path to an Excel workbook with a `"Summary for JE"` or `"JE"` tab
      (the standard "Summary for JE" pattern). Read it with `openpyxl`,
      data_only=True, into the handoff schema.
   4. If none found, ask the user: *"Where is the draft JE? (paste JSON, give a
      file path, or describe the entry)."*

2. **Classify** as `journalentry` or `advintercompanyjournalentry`:
   - All lines belong to the same subsidiary → `journalentry` (header `subsidiary`).
   - Lines split across 2+ subsidiaries → `advintercompanyjournalentry` (header
     `subsidiary` = the "from" / borrower; `toSubsidiaries` = the other side(s)).
   - User can override the classification by saying "post this as a regular JE"
     or "use AICJE".
   - See [payload-shapes.md](references/payload-shapes.md) and
     [aicje-overview.md](references/aicje-overview.md) for the exact shape.

3. **Validate** with `scripts/validate_je.py`. The validator checks:
   - Sum of debits == sum of credits (Decimal precision; tolerance $0.00)
   - Every line has account, exactly one of debit-XOR-credit, and a memo
   - Subsidiary IDs resolve against the configured `KNOWN_SUBSIDIARIES` in
     `scripts/validate_je.py`
   - For AICJE: at least two distinct subsidiaries; both sides have non-zero
     activity; `toSubsidiaries` is set
   - Memo starts with the configured task prefix (warn, do not block if missing)
   - **Legacy-account alert** fires loudly if any line uses `LEGACY_ICO_ACCOUNT`
   - Date is in a real posting period (warn if stale or future)

   If validation fails, surface the specific issues and stop. Do NOT proceed to
   preview until validation is clean.

4. **Render the preview** with `scripts/render_preview.py`. The chat output
   uses the template in `templates/je-preview.md.tpl` and looks like:

   ```
   ## Journal Entry Preview — AICJE

   **Memo:**         TASK 042 ME - Monthly Accrual 2026-05
   **Date:**         2026-05-31
   **From sub:**     Subsidiary A (10)
   **To sub(s):**    Subsidiary B (20)
   **Custom Form:**  <form-id> (Standard JE)
   **Currency:**     USD

   | #  | Account              | Sub              | Debit       | Credit      | Memo               |
   |----|----------------------|------------------|-------------|-------------|--------------------|
   | 1  | 13000 - ICO Clearing | Sub-A (10)       |  10,000.00  |             | Monthly accrual    |
   | 2  | 23000 - ICO Payable  | Sub-B (20)       |             |  10,000.00  | Monthly accrual    |
   |    | **Totals**           |                  | **10,000.00** | **10,000.00** | Balanced ✓     |

   Status to be created: **Pending Approval** (approved=false, approvalStatus.id="1")

   Post this to NetSuite? (yes / no / edit)
   ```

5. **Wait for explicit confirmation.** Only proceed on "yes", "post it", "post",
   "go", "confirm", "ship it", or equivalent. On "edit", enter an inline edit
   loop (let the user adjust lines / memo / date, re-validate, re-render). On
   "no" or anything ambiguous, stop and ask what to do.

6. **Post** by calling `scripts/post_je.py` which wraps
   `mcp__<your-netsuite-connector-id>__ns_createRecord`. Hard-coded:
   - `approved: false`
   - `approvalStatus: {id: "1"}`
   - Both record types use the same `recordType` string the classifier picked.

7. **Confirm posted.** Echo back:
   - The new NetSuite internal ID
   - The deep link: `https://<account>.app.netsuite.com/app/accounting/transactions/journal.nl?id=<id>`
     (or `…/advintercompanyjournal.nl?id=<id>` for AICJE)
   - The task number from the memo
   - "Status: Pending Approval — needs approver sign-off in NS."

   If the handoff includes a `workpaper` / `workpaper_path`, attach it to the
   new JE via the **netsuite-file-attach** tool (RESTlet-based; the REST API
   cannot create files — never attempt `ns_createRecord` with type `file`).
   Pass the new internal id as `--record-id`. On failure, surface the error and
   tell the user to drag the file onto the JE in the UI.

8. **Chain to slack-entry-notify.** Unless `"skip_slack": true` is set in
   the handoff, immediately invoke the `slack-entry-notify` skill with a
   payload containing the original handoff fields PLUS:
   - `je_id`: the new NetSuite internal id
   - `je_tranid`: the human-readable JE number (look up via SuiteQL on the new id)
   - `je_link`: the deep link built in Step 7
   - `record_type`: the classification chosen in Step 2
   - `status`: `"pending_approval"` (the JE was just created in that state)
   - `subsidiary_name`: looked up from the subsidiary id if not already in handoff

   The `slack-entry-notify` skill renders and posts to your configured review
   channel. If the original handoff contained `slack_notes` or `workpaper_path`
   fields, they pass through unchanged. If Slack posting fails, surface the
   error — the JE still exists in NetSuite, but the team won't have been
   notified.

9. **On error from NetSuite:** surface the full error response verbatim. Do
   NOT silently retry. Common errors: invalid account ID, missing department
   on a P&L account, posting period closed, AICJE missing toSubsidiaries.

---

### MODE B — Attach to a new workflow (the "wire me up" flow)

**Trigger:** the user is scaffolding a new skill, automation, or script
(skill-creator running, "create a new automation in accounting", "let's build
a workflow that…") AND the new thing will produce a JE.

**Steps:**

1. After helping the user scaffold the new skill, ask exactly once:
   > *"This new workflow will produce a journal entry. Want me to wire it to
   > `post-je-to-netsuite` so it ends with the standard preview-and-post step?
   > (recommended)"*

2. On "yes", append the boilerplate from
   [skill-creator-integration.md](references/skill-creator-integration.md) to
   the new skill's `SKILL.md` (or to its README if it's a non-skill automation).
   The boilerplate has three parts:
   - A "Handoff: posting to NetSuite" section describing the contract
   - The full JSON schema example (from `references/handoff-format.md`)
   - A line in the new skill's `description:` field adding the canonical end
     phrase ("…produces a draft JE in the standard handoff format, then hands
     off to `post-je-to-netsuite` for review and posting.") so the dispatcher
     wires it up cleanly

3. Verify the new skill's `description` no longer claims it "posts to NetSuite"
   directly — that responsibility now lives here.

---

## Files in this skill

- `SKILL.md` (this file) — entry point, mode router
- `references/payload-shapes.md` — exact `ns_createRecord` shapes for both record types
- `references/handoff-format.md` — the JSON schema sibling skills must produce
- `references/your-org-coa.md.template` — fill in your subsidiaries, custom forms, and key accounts
- `references/aicje-overview.md` — generic AICJE notes (header shape, per-sub balance rule)
- `references/skill-creator-integration.md` — boilerplate for Mode B
- `scripts/validate_je.py` — pre-post validation
- `scripts/render_preview.py` — chat preview renderer
- `scripts/post_je.py` — wraps `ns_createRecord` with the hard-coded Pending Approval guard
- `templates/je-preview.md.tpl` — preview template used by `render_preview.py`

