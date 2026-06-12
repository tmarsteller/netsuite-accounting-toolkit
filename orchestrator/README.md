# orchestrator — Python helpers for NetSuite accounting automations

A single-file helper library for Python automations that post journal entries
to NetSuite and notify a team in Slack. Used as the shared base layer by the
other tools in this toolkit (e.g. `netsuite-file-attach` reuses its TBA auth
pattern).

## What it provides

| Function | What it does |
|---|---|
| `post_je()` | Create a journal entry via the REST Record API (OAuth 1.0 TBA, HMAC-SHA256). **Always creates in Pending Approval** (`approved: false`, `approvalStatus.id: "1"`) — callers cannot override this. Returns internal ID, JE number (tranId), and a deep link. |
| `get_posting_period()` | Look up a posting period internal ID by name (e.g. `"Mar 2026"`) via SuiteQL. |
| `verify_balance()` | Raise if total debits ≠ total credits (Decimal precision). Called automatically by `post_je()`. |
| `send_slack()` | Post a status notification (success/error + optional JE link) to a Slack incoming webhook. |

## Setup

```bash
pip install -r requirements.txt
```

Credentials are read from **environment variables first**, then from an
`orchestrator_config.json` next to the script:

| Env var | Config key |
|---|---|
| `NETSUITE_ACCOUNT_ID` | `netsuite_account_id` |
| `NETSUITE_CONSUMER_KEY` | `netsuite_consumer_key` |
| `NETSUITE_CONSUMER_SECRET` | `netsuite_consumer_secret` |
| `NETSUITE_TOKEN_ID` | `netsuite_token_id` |
| `NETSUITE_TOKEN_SECRET` | `netsuite_token_secret` |
| `SLACK_WEBHOOK_URL` | `slack_webhook_url` |

Copy `orchestrator_config.example.json` to `orchestrator_config.json` and fill
in real values. **Never commit `orchestrator_config.json`** — it is gitignored
at the repo root.

## Usage

```python
from orchestrator import post_je, get_posting_period

period_id = get_posting_period("Mar 2026")
result = post_je(
    subsidiary_id=1,
    memo="TASK 042 ME - Monthly Accrual",
    tran_date="2026-03-31",
    posting_period_id=period_id,
    custom_form_id=100,          # your account's standard JE form
    lines=[
        {"account_id": 1234, "debit": 10000.00, "memo": "Accrual"},
        {"account_id": 5678, "credit": 10000.00, "memo": "Accrual"},
    ],
)
print(result["url"])  # deep link to the Pending Approval JE
```

## Notes

- If you use Claude Code with the NetSuite MCP connector, prefer the
  `post-je-to-netsuite` skill in this toolkit for interactive work — this
  library is the headless/scripted fallback for scheduled automations.
- The Pending Approval guard is deliberate: an automation should never be both
  preparer and approver. A human reviews and approves in NetSuite.
