"""
Render a draft JE (handoff format) as a markdown preview for the chat.

Public API:
    render(handoff: dict, validation: ValidationResult) -> str
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from validate_je import KNOWN_SUBSIDIARIES, ValidationResult


def _fmt_money(v: Any) -> str:
    if v is None or v == "":
        return ""
    try:
        d = Decimal(str(v)).quantize(Decimal("0.01"))
        return f"{d:,.2f}"
    except Exception:
        return str(v)


def _sub_label(sub_id: str | None) -> str:
    if not sub_id:
        return ""
    name = KNOWN_SUBSIDIARIES.get(str(sub_id), "")
    short = name.split(",")[0].split("(")[0].strip() if name else f"sub {sub_id}"
    return f"{short} ({sub_id})"


def _acct_label(line: dict) -> str:
    acct = str(line.get("account", "")).strip()
    name = line.get("account_name")
    return f"{acct} - {name}" if name else acct


def render(handoff: dict, validation: ValidationResult) -> str:
    """Build the chat preview block."""
    kind = "AICJE" if validation.is_aicje else "JE"

    header_sub = str(handoff.get("subsidiary", "")).strip()
    to_subs = handoff.get("to_subsidiaries") or []
    if isinstance(to_subs, (str, int)):
        to_subs = [to_subs]
    to_subs = [str(s).strip() for s in to_subs]

    lines = handoff.get("lines", [])

    # --- Header block ---
    out: list[str] = []
    out.append(f"## Journal Entry Preview — {kind}")
    out.append("")
    out.append(f"**Memo:**         `{handoff.get('memo', '<missing>')}`")
    out.append(f"**Date:**         {handoff.get('tran_date', '<missing>')}")
    out.append(f"**From sub:**     {_sub_label(header_sub)}")
    if validation.is_aicje and to_subs:
        out.append(f"**To sub(s):**    {', '.join(_sub_label(s) for s in to_subs)}")
    if handoff.get("custom_form"):
        out.append(f"**Custom Form:**  {handoff['custom_form']}")
    if handoff.get("currency"):
        out.append(f"**Currency:**     id={handoff['currency']}")
    if handoff.get("workpaper"):
        out.append(f"**Workpaper:**    `{handoff['workpaper']}`")
    out.append("")

    # --- Lines table ---
    out.append("| #  | Account                          | Sub                | Debit          | Credit         | Memo                              |")
    out.append("|----|----------------------------------|--------------------|----------------|----------------|-----------------------------------|")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for idx, ln in enumerate(lines, start=1):
        acct = _acct_label(ln)[:32]
        sub = _sub_label(str(ln.get("subsidiary") or header_sub or "").strip())[:18]
        debit = _fmt_money(ln.get("debit"))
        credit = _fmt_money(ln.get("credit"))
        memo = (ln.get("memo") or "")[:33]

        if ln.get("debit") is not None:
            total_debit += Decimal(str(ln["debit"])).quantize(Decimal("0.01"))
        if ln.get("credit") is not None:
            total_credit += Decimal(str(ln["credit"])).quantize(Decimal("0.01"))

        out.append(f"| {idx:<2} | {acct:<32} | {sub:<18} | {debit:>14} | {credit:>14} | {memo:<33} |")

    balance_ok = "✓" if total_debit == total_credit else "✗"
    out.append(
        f"|    | **Totals**                       |                    | "
        f"**{_fmt_money(total_debit):>10}** | **{_fmt_money(total_credit):>10}** | "
        f"Balanced {balance_ok}                       |"
    )
    out.append("")

    # --- Per-subsidiary balance (AICJE only) ---
    if validation.is_aicje:
        per_sub: dict[str, Decimal] = {}
        for ln in lines:
            s = str(ln.get("subsidiary") or header_sub or "").strip()
            d = Decimal(str(ln.get("debit") or 0)).quantize(Decimal("0.01"))
            c = Decimal(str(ln.get("credit") or 0)).quantize(Decimal("0.01"))
            per_sub[s] = per_sub.get(s, Decimal("0.00")) + d - c
        out.append("**Per-subsidiary balance** (must net to 0 per sub):")
        for s, v in sorted(per_sub.items()):
            mark = "✓" if v == Decimal("0.00") else "✗"
            out.append(f"  - {_sub_label(s):<28} net {v:>+12,.2f}  {mark}")
        out.append("")

    # --- Status footer ---
    out.append("Status to be created: **Pending Approval** (`approved=false`, `approvalStatus.id=\"1\"`)")
    out.append("")

    # --- Validation messages ---
    if validation.errors:
        out.append("**Errors (must fix before posting):**")
        for e in validation.errors:
            out.append(f"  - ❌ {e}")
        out.append("")

    if validation.warnings:
        out.append("**Warnings:**")
        for w in validation.warnings:
            out.append(f"  - ⚠️  {w}")
        out.append("")

    if validation.ok:
        out.append("Post this to NetSuite? (`yes` / `no` / `edit`)")
    else:
        out.append("**Cannot post** — fix the errors above, then re-run.")

    return "\n".join(out)


# --- CLI ---
if __name__ == "__main__":
    import json
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    from validate_je import validate

    if len(sys.argv) != 2:
        print("usage: render_preview.py <handoff.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8-sig") as f:
        h = json.load(f)

    res = validate(h)
    print(render(h, res))
    sys.exit(0 if res.ok else 1)
