"""
orchestrator.py — Shared helpers for NetSuite accounting automations.

Provides:
  - send_slack()         : post a notification to a Slack webhook
  - post_je()            : create a NetSuite journal entry via REST (OAuth 1.0 TBA)
  - get_posting_period() : look up a NetSuite posting period ID by name
  - verify_balance()     : assert that JE lines balance before posting

Config is read from environment variables first, then from an
orchestrator_config.json next to this file if present (see
orchestrator_config.example.json — never commit the real one).

Usage:
    from orchestrator import send_slack, post_je, get_posting_period

All JEs are created in Pending Approval status — this is non-negotiable.
"""

import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

import requests
from requests_oauthlib import OAuth1

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parent / "orchestrator_config.json"

_config_cache: Optional[dict] = None


def _config() -> dict:
    """Load config from file once; env vars always take precedence over file values."""
    global _config_cache
    if _config_cache is None:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                _config_cache = json.load(f)
        else:
            _config_cache = {}
    return _config_cache


def _get(env_key: str, config_key: str, required: bool = True) -> Optional[str]:
    """Return env var if set, else config file value, else None (or raise if required)."""
    value = os.environ.get(env_key) or _config().get(config_key)
    if not value and required:
        raise EnvironmentError(
            f"Missing required config: set env var '{env_key}' "
            f"or add '{config_key}' to orchestrator_config.json"
        )
    return value


# ---------------------------------------------------------------------------
# Slack notification helper
# ---------------------------------------------------------------------------
def send_slack(
    automation: str,
    month: str,
    status: str,
    details: str = "",
    je_link: str = "",
    webhook_url: str = "",
) -> bool:
    """
    Post a Slack notification to the configured webhook.

    Args:
        automation: Name of the automation, e.g. "CBW Classification"
        month:      Month string, e.g. "Mar 2026"
        status:     "success" | "error" | any short label
        details:    Free-form detail text shown in the message body
        je_link:    Optional URL to the NetSuite JE
        webhook_url: Override webhook URL (defaults to env/config)

    Returns:
        True on HTTP 200, False otherwise.
    """
    url = webhook_url or _get("SLACK_WEBHOOK_URL", "slack_webhook_url")

    icon = ":white_check_mark:" if status.lower() == "success" else ":x:"
    header = f"{icon} *{automation}* — {month} — `{status.upper()}`"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
    ]

    if details:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": details}}
        )

    if je_link:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{je_link}|View JE in NetSuite>",
                },
            }
        )

    payload = {"blocks": blocks}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[Slack] Notification sent: {automation} / {month} / {status}")
            return True
        else:
            print(f"[Slack] ERROR {resp.status_code}: {resp.text}")
            return False
    except Exception as exc:
        print(f"[Slack] Exception while sending notification: {exc}")
        return False


# ---------------------------------------------------------------------------
# NetSuite OAuth 1.0 TBA helpers
# ---------------------------------------------------------------------------
def _ns_auth() -> OAuth1:
    """Build an OAuth1 object from env vars / config."""
    account_id      = _get("NETSUITE_ACCOUNT_ID",       "netsuite_account_id")
    consumer_key    = _get("NETSUITE_CONSUMER_KEY",      "netsuite_consumer_key")
    consumer_secret = _get("NETSUITE_CONSUMER_SECRET",   "netsuite_consumer_secret")
    token_id        = _get("NETSUITE_TOKEN_ID",          "netsuite_token_id")
    token_secret    = _get("NETSUITE_TOKEN_SECRET",      "netsuite_token_secret")

    return OAuth1(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=token_id,
        resource_owner_secret=token_secret,
        realm=account_id.upper().replace("-", "_"),
        signature_method="HMAC-SHA256",
    )


def _ns_base_url() -> str:
    account_id = _get("NETSUITE_ACCOUNT_ID", "netsuite_account_id")
    # NetSuite REST URL uses dashes for the account subdomain
    subdomain = account_id.lower().replace("_", "-")
    return f"https://{subdomain}.suitetalk.api.netsuite.com/services/rest"


# ---------------------------------------------------------------------------
# Balance verification
# ---------------------------------------------------------------------------
def verify_balance(lines: list) -> None:
    """
    Raise ValueError if total debits != total credits.

    Each line must be a dict with either 'debit' or 'credit' (float/int, dollars).
    """
    total_debit  = sum(Decimal(str(l.get("debit",  0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)

    total_debit  = total_debit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_credit = total_credit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if total_debit != total_credit:
        raise ValueError(
            f"JE does not balance: debits={total_debit} credits={total_credit} "
            f"(difference={abs(total_debit - total_credit)})"
        )
    print(f"[JE] Balance check passed: debits = credits = {total_debit}")


# ---------------------------------------------------------------------------
# Posting period lookup
# ---------------------------------------------------------------------------
def get_posting_period(month_name: str) -> str:
    """
    Return the NetSuite internal ID for a posting period by name.

    Args:
        month_name: e.g. "Mar 2026"

    Returns:
        The internal ID string, e.g. "123"

    Raises:
        ValueError if the period is not found or multiple matches returned.
    """
    url = f"{_ns_base_url()}/query/v1/suiteql"
    query = (
        "SELECT id, periodname "
        "FROM accountingperiod "
        f"WHERE periodname = '{month_name}' "
        "AND isquarter = 'F' AND isyear = 'F'"
    )
    payload = {"q": query}

    print(f"[NS] Looking up posting period: {month_name}")
    resp = requests.post(
        url,
        json=payload,
        auth=_ns_auth(),
        headers={"Content-Type": "application/json", "Prefer": "transient"},
        timeout=30,
    )
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise ValueError(f"No posting period found for '{month_name}'")
    if len(items) > 1:
        raise ValueError(
            f"Multiple posting periods found for '{month_name}': {items}"
        )

    period_id = str(items[0]["id"])
    print(f"[NS] Posting period '{month_name}' -> id={period_id}")
    return period_id


# ---------------------------------------------------------------------------
# Journal entry posting
# ---------------------------------------------------------------------------
def post_je(
    subsidiary_id: int,
    memo: str,
    tran_date: str,
    posting_period_id: str,
    custom_form_id: int,
    lines: list,
) -> dict:
    """
    Create a NetSuite journal entry via REST API (OAuth 1.0 TBA).

    ALWAYS creates in Pending Approval status (approved=false). Non-negotiable.

    Args:
        subsidiary_id:     NetSuite subsidiary internal ID
        memo:              JE-level memo / description
        tran_date:         Transaction date string, e.g. "2026-03-31"
        posting_period_id: NetSuite posting period internal ID (use get_posting_period())
        custom_form_id:    Custom form internal ID (your account's standard JE form)
        lines:             List of line dicts, each containing:
                             - account_id (int): NetSuite account internal ID
                             - debit (float, optional): debit amount in dollars
                             - credit (float, optional): credit amount in dollars
                             - memo (str, optional): line-level memo

    Returns:
        dict with keys: internal_id, je_number, url

    Raises:
        ValueError  if lines do not balance
        requests.HTTPError on API failure
    """
    # Safety check: lines must balance before we touch the API
    verify_balance(lines)

    # Build line items for the NetSuite payload
    je_lines = []
    for i, line in enumerate(lines, start=1):
        ns_line: dict = {
            "account": {"id": str(line["account_id"])},
            "memo": line.get("memo", ""),
        }
        if line.get("debit", 0):
            ns_line["debit"] = float(line["debit"])
        if line.get("credit", 0):
            ns_line["credit"] = float(line["credit"])
        je_lines.append(ns_line)

    payload = {
        "approved": False,
        "approvalStatus": {"id": "1"},          # Pending Approval — never change this
        "customForm": {"id": str(custom_form_id)},
        "subsidiary": {"id": str(subsidiary_id)},
        "memo": memo,
        "tranDate": tran_date,
        "postingPeriod": {"id": str(posting_period_id)},
        "lineList": {"line": je_lines},
    }

    url = f"{_ns_base_url()}/record/v1/journalentry"
    print(f"[NS] Creating JE: {memo} | {tran_date} | {len(lines)} lines")

    resp = requests.post(
        url,
        json=payload,
        auth=_ns_auth(),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()

    # NetSuite returns 204 with a Location header on success
    location = resp.headers.get("Location", "")
    internal_id = location.rstrip("/").split("/")[-1] if location else ""

    # Fetch the created record to get the JE number (tranId)
    je_number = ""
    if internal_id:
        get_resp = requests.get(
            f"{url}/{internal_id}?fields=tranId",
            auth=_ns_auth(),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if get_resp.status_code == 200:
            je_number = get_resp.json().get("tranId", "")

    account_id = _get("NETSUITE_ACCOUNT_ID", "netsuite_account_id")
    subdomain  = account_id.lower().replace("_", "-")
    ns_ui_url  = (
        f"https://{subdomain}.app.netsuite.com/app/accounting/transactions/"
        f"journal.nl?id={internal_id}"
    )

    result = {
        "internal_id": internal_id,
        "je_number":   je_number,
        "url":         ns_ui_url,
    }
    print(f"[NS] JE created: id={internal_id} | tranId={je_number}")
    return result
