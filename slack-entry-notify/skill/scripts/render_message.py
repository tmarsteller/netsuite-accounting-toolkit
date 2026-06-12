"""
Render a Slack notification message from a structured payload.

Pure formatting — no Slack API calls, no external dependencies. The skill
calls this script to produce the message text, then invokes whatever Slack
MCP tool / webhook is available in the environment to post it.

Designed for "review-queue" style notifications: an entry (record,
transaction, journal entry, approval request, etc.) that has a set of
labeled line items with optional left/right numeric columns (e.g.
debit/credit, in/out, before/after) plus a total.

Usage:
    python render_message.py payload.json
    python render_message.py < payload.json

See ../references/payload-shape.md for the full schema.
"""
from __future__ import annotations

import io
import json
import sys
from decimal import Decimal
from typing import Any

# Force UTF-8 stdout so emoji + unicode render correctly on every platform
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ---- Configurable column labels (override via payload["columns"]) -----------
DEFAULT_LEFT = "Left"
DEFAULT_RIGHT = "Right"


def fmt_amount(value: Any, currency: str = "$") -> str:
    """Format a numeric cell. Empty string for None/0 so the table stays clean.
    Negative values render in parentheses (accounting convention)."""
    if value is None or value == 0:
        return ""
    d = Decimal(str(value))
    if d == d.to_integral_value():
        s = f"{currency}{abs(d):,.0f}"
    else:
        s = f"{currency}{abs(d):,.2f}"
    return f"({s})" if d < 0 else s


def fmt_total(value: Any, currency: str = "$") -> str:
    """Total cell — never blank."""
    if value is None:
        value = 0
    d = Decimal(str(value))
    if d == d.to_integral_value():
        s = f"{currency}{abs(d):,.0f}"
    else:
        s = f"{currency}{abs(d):,.2f}"
    return f"({s})" if d < 0 else s


def line_label(line: dict) -> str:
    """Build the label for a line. Supports a 'code'+'name' pair or a plain
    'label'. e.g. {'code': '4000', 'name': 'Revenue'} -> '4000 Revenue'."""
    if line.get("label"):
        return str(line["label"])
    code = str(line.get("code", "")).strip()
    name = str(line.get("name", "")).strip()
    if code and name and not name.startswith(code):
        return f"{code} {name}".strip()
    return name or code


def render_review(payload: dict, status: str) -> str:
    cfg_icon = {
        "pending": ":receipt:",
        "posted": ":white_check_mark:",
    }
    cfg_status_text = {
        "pending": payload.get("status_text", "ready for review"),
        "posted": payload.get("status_text", "complete"),
    }
    icon = payload.get("icon", cfg_icon.get(status, ":receipt:"))
    status_text = cfg_status_text.get(status, "ready for review")
    currency = payload.get("currency_symbol", "$")

    cols = payload.get("columns", {})
    left_label = cols.get("left", DEFAULT_LEFT)
    right_label = cols.get("right", DEFAULT_RIGHT)

    out = []
    out.append(f"{icon} **{payload['title']}** — {status_text}")
    if payload.get("subtitle"):
        out.append(f"_{payload['subtitle']}_")
    out.append("")

    notes = payload.get("notes") or []
    if notes:
        for n in notes:
            out.append(f"> {n}")
        out.append("")

    lines = payload.get("lines", [])
    if lines:
        out.append(f"| Item | {left_label} | {right_label} |")
        out.append("|---|---:|---:|")
        if len(lines) > 20:
            for ln in lines[:18]:
                out.append(f"| {line_label(ln)} | {fmt_amount(ln.get('left'), currency)} "
                           f"| {fmt_amount(ln.get('right'), currency)} |")
            out.append(f"| _+ {len(lines) - 18} more — see attachment_ |  |  |")
        else:
            for ln in lines:
                out.append(f"| {line_label(ln)} | {fmt_amount(ln.get('left'), currency)} "
                           f"| {fmt_amount(ln.get('right'), currency)} |")
        if "total" in payload:
            t = fmt_total(payload["total"], currency)
            out.append(f"| **Total** | **{t}** | **{t}** |")
        out.append("")

    # Footer links
    if payload.get("link"):
        link_text = payload.get("link_text", "View record")
        out.append(f"🔗 [{link_text}]({payload['link']})")
    if payload.get("attachment_path"):
        out.append(f"📎 {payload['attachment_path']}")

    return "\n".join(out).rstrip() + "\n"


def render_info(payload: dict) -> str:
    """A short informational message — no line table. Use for 'nothing to do
    this period' style heartbeats."""
    icon = payload.get("icon", ":information_source:")
    out = []
    title = payload.get("title", payload.get("workflow_name", "Notification"))
    period = payload.get("period", "")
    header = f"{icon} **{title}**"
    if period:
        header += f" — {period}"
    out.append(header)
    out.append("")
    if payload.get("reason"):
        out.append(payload["reason"])
        out.append("")
    notes = payload.get("notes") or []
    for n in notes:
        out.append(f"> {n}")
    if notes:
        out.append("")
    if payload.get("attachment_path"):
        out.append(f"📎 {payload['attachment_path']}")
    return "\n".join(out).rstrip() + "\n"


def render(payload: dict) -> str:
    status = payload.get("status", "pending")
    if status == "info":
        return render_info(payload)
    if status in ("pending", "posted"):
        return render_review(payload, status)
    raise ValueError(f"Unknown status: {status!r} (expected pending|posted|info)")


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = json.load(sys.stdin)
    sys.stdout.write(render(payload))


if __name__ == "__main__":
    main()
