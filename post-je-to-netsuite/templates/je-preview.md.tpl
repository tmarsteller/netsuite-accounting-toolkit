{# Template used by scripts/render_preview.py — not directly rendered.        #}
{# The actual rendering happens in render_preview.py; this file is a visual   #}
{# reference for the intended structure of the chat preview block.            #}

## Journal Entry Preview — {KIND}

**Memo:**         `{MEMO}`
**Date:**         {DATE}
**From sub:**     {FROM_SUB}
{IF_AICJE}**To sub(s):**    {TO_SUBS}{ENDIF}
**Custom Form:**  {CUSTOM_FORM}
**Currency:**     id={CURRENCY}
{IF_WORKPAPER}**Workpaper:**    `{WORKPAPER}`{ENDIF}

| #  | Account              | Sub                | Debit       | Credit      | Memo               |
|----|----------------------|--------------------|-------------|-------------|--------------------|
{FOR_EACH_LINE}
| {N} | {ACCT}              | {SUB}              | {DEBIT}     | {CREDIT}    | {LINE_MEMO}        |
{END_FOR}
|    | **Totals**           |                    | **{TD}**    | **{TC}**    | Balanced {BAL}     |

{IF_AICJE}
**Per-subsidiary balance** (must net to 0 per sub):
{FOR_EACH_SUB}
  - {SUB_LABEL}  net {SUB_NET}  {SUB_BAL}
{END_FOR}
{ENDIF}

Status to be created: **Pending Approval** (`approved=false`, `approvalStatus.id="1"`)

{IF_ERRORS}
**Errors (must fix before posting):**
{FOR_EACH_ERROR}
  - ❌ {ERROR}
{END_FOR}
{ENDIF}

{IF_WARNINGS}
**Warnings:**
{FOR_EACH_WARNING}
  - ⚠️  {WARNING}
{END_FOR}
{ENDIF}

{IF_OK}
Post this to NetSuite? (`yes` / `no` / `edit`)
{ELSE}
**Cannot post** — fix the errors above, then re-run.
{ENDIF}
