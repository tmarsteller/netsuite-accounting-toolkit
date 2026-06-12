"""
Validation for the post-je-to-netsuite handoff format.

Public API:
    validate(handoff: dict) -> ValidationResult

The validator never modifies the input. It returns a structured result that
the skill renders in chat. Hard-fail errors block posting; warnings are
surfaced but do not block (the user can override).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


# Fill in your org's subsidiaries (run `ns_getSubsidiaries` to get the IDs).
KNOWN_SUBSIDIARIES: dict[str, str] = {
    # "1": "Your Subsidiary, Inc.",
    # "2": "Another Subsidiary LLC",
}

# Your org's intercompany clearing accounts (if any). Used to warn when an
# AICJE doesn't touch any ICO account (often an indicator of a misclassified entry).
ICO_CLEARING_ACCOUNTS: set[str] = set()

# A retired account that, if used, should trigger a loud warning.
# Set to None to disable.
LEGACY_ICO_ACCOUNT: str | None = None

# Required memo prefix (warn if missing). Set to None to disable.
# e.g. "TASK " to require memos like "TASK 042 ME - Monthly Accrual 2026-05"
MEMO_PREFIX: str | None = None


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_aicje: bool = False
    subsidiaries_touched: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _as_decimal(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _normalize_sub(v: Any) -> str | None:
    if v is None:
        return None
    return str(v).strip()


def validate(handoff: dict) -> ValidationResult:
    r = ValidationResult()

    # --- top-level required fields ---
    for key in ("memo", "tran_date", "subsidiary", "lines"):
        if not handoff.get(key):
            r.fail(f"Missing required field: `{key}`")

    if not r.ok:
        return r

    # --- tran_date ---
    try:
        _dt.date.fromisoformat(handoff["tran_date"])
    except (TypeError, ValueError):
        r.fail(f"`tran_date` is not a valid ISO date: {handoff.get('tran_date')!r}")

    # --- memo ---
    memo = str(handoff.get("memo", ""))
    if MEMO_PREFIX and not memo.startswith(MEMO_PREFIX):
        r.warn(f"Memo does not start with {MEMO_PREFIX!r}: {memo!r}. Confirm the memo prefix.")

    # --- header subsidiary ---
    # When KNOWN_SUBSIDIARIES is unconfigured (empty), skip ID validation and
    # warn once — out of the box, entries should not hard-fail on this.
    if not KNOWN_SUBSIDIARIES:
        r.warn(
            "KNOWN_SUBSIDIARIES is not configured in validate_je.py — skipping "
            "subsidiary ID validation. Populate it (via `ns_getSubsidiaries`) to "
            "catch typo'd subsidiary IDs before they hit NetSuite."
        )
    header_sub = _normalize_sub(handoff.get("subsidiary"))
    if KNOWN_SUBSIDIARIES and header_sub not in KNOWN_SUBSIDIARIES:
        r.fail(f"Header `subsidiary` {header_sub!r} is not a known subsidiary ID.")

    # --- AICJE classification ---
    to_subs_raw = handoff.get("to_subsidiaries") or []
    if isinstance(to_subs_raw, (str, int)):
        to_subs_raw = [to_subs_raw]
    to_subs = [_normalize_sub(s) for s in to_subs_raw if _normalize_sub(s)]

    line_subs = set()
    for ln in handoff.get("lines", []):
        ls = _normalize_sub(ln.get("subsidiary"))
        if ls:
            line_subs.add(ls)

    distinct_subs = ({header_sub} if header_sub else set()) | set(to_subs) | line_subs
    distinct_subs.discard(None)

    r.is_aicje = len(distinct_subs) >= 2 or bool(to_subs)
    r.subsidiaries_touched = sorted(distinct_subs)

    if r.is_aicje:
        if not to_subs:
            # Lines reference multiple subs but header `to_subsidiaries` is empty
            inferred = sorted(s for s in line_subs if s != header_sub)
            r.fail(
                f"Lines touch multiple subsidiaries {sorted(distinct_subs)} but "
                f"`to_subsidiaries` is empty. Set `to_subsidiaries` to {inferred} "
                f"(this is an AICJE)."
            )
        for s in to_subs:
            if KNOWN_SUBSIDIARIES and s not in KNOWN_SUBSIDIARIES:
                r.fail(f"`to_subsidiaries` contains unknown subsidiary ID: {s!r}")
            if s == header_sub:
                r.fail(f"`to_subsidiaries` includes the header subsidiary {s!r} (self-IC not allowed).")
        if len(distinct_subs) >= 3:
            r.warn(
                f"AICJE touches {len(distinct_subs)} subsidiaries "
                f"({sorted(distinct_subs)}). Multi-target `toSubsidiaries` payloads "
                f"are less common — confirm the first one posts correctly."
            )

    # --- lines ---
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    per_sub_balance: dict[str, Decimal] = {}

    for idx, ln in enumerate(handoff.get("lines", []), start=1):
        prefix = f"Line {idx}"

        if not ln.get("account"):
            r.fail(f"{prefix}: missing `account`.")
        if not ln.get("memo"):
            r.fail(f"{prefix}: missing `memo`.")

        debit = _as_decimal(ln.get("debit"))
        credit = _as_decimal(ln.get("credit"))

        if debit is not None and credit is not None:
            r.fail(f"{prefix}: both `debit` and `credit` set — only one allowed.")
        if debit is None and credit is None:
            r.fail(f"{prefix}: neither `debit` nor `credit` set.")
        if debit is not None and debit <= 0:
            r.fail(f"{prefix}: `debit` must be positive, got {debit}.")
        if credit is not None and credit <= 0:
            r.fail(f"{prefix}: `credit` must be positive, got {credit}.")

        line_sub = _normalize_sub(ln.get("subsidiary")) or header_sub
        if KNOWN_SUBSIDIARIES and line_sub and line_sub not in KNOWN_SUBSIDIARIES:
            r.fail(f"{prefix}: subsidiary {line_sub!r} is not a known subsidiary ID.")

        if debit is not None:
            total_debit += debit
            if line_sub:
                per_sub_balance[line_sub] = per_sub_balance.get(line_sub, Decimal("0.00")) + debit
        if credit is not None:
            total_credit += credit
            if line_sub:
                per_sub_balance[line_sub] = per_sub_balance.get(line_sub, Decimal("0.00")) - credit

        # legacy-account alert (no-op when LEGACY_ICO_ACCOUNT is None)
        acct = str(ln.get("account", "")).strip()
        if LEGACY_ICO_ACCOUNT and acct == LEGACY_ICO_ACCOUNT:
            new_accts_hint = (
                " / ".join(sorted(ICO_CLEARING_ACCOUNTS))
                if ICO_CLEARING_ACCOUNTS
                else "your current ICO clearing account(s)"
            )
            r.warn(
                f"{prefix}: uses **legacy account {LEGACY_ICO_ACCOUNT}**. This account "
                f"is retired for new ICO entries — use {new_accts_hint} instead. "
                f"If this is intentional (clean-up reversal), say "
                f'"{LEGACY_ICO_ACCOUNT} is intentional" to override.'
            )

    # --- overall balance ---
    diff = total_debit - total_credit
    if diff != Decimal("0.00"):
        r.fail(f"Debits ({total_debit}) ≠ Credits ({total_credit}). Out by {diff}.")

    # --- AICJE per-subsidiary balance ---
    if r.is_aicje:
        unbalanced = {s: v for s, v in per_sub_balance.items() if v != Decimal("0.00")}
        if unbalanced:
            details = ", ".join(f"sub {s}: {v:+}" for s, v in sorted(unbalanced.items()))
            r.fail(
                f"AICJE per-subsidiary balance broken: {details}. "
                f"NetSuite requires each subsidiary to internally balance."
            )

        # Warn if no ICO clearing account is touched (skipped when not configured)
        accts = {str(ln.get("account", "")).strip() for ln in handoff.get("lines", [])}
        if ICO_CLEARING_ACCOUNTS and not (accts & ICO_CLEARING_ACCOUNTS):
            r.warn(
                f"AICJE does not touch any ICO clearing account "
                f"({' / '.join(sorted(ICO_CLEARING_ACCOUNTS))}). "
                f"Confirm this is intentional."
            )

    # --- tran_date sanity ---
    try:
        td = _dt.date.fromisoformat(handoff["tran_date"])
        today = _dt.date.today()
        if td > today + _dt.timedelta(days=14):
            r.warn(f"`tran_date` is in the future: {td}. Confirm intent.")
        if (today - td).days > 60:
            r.warn(f"`tran_date` is {(today - td).days} days old. Posting period may be closed.")
    except (KeyError, ValueError):
        pass  # already flagged above

    return r


# --- CLI for quick local checks ---
if __name__ == "__main__":
    import json
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if len(sys.argv) != 2:
        print("usage: validate_je.py <handoff.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8-sig") as f:
        h = json.load(f)
    res = validate(h)
    print(f"OK: {res.ok}")
    print(f"Type: {'AICJE' if res.is_aicje else 'JE'}")
    print(f"Subsidiaries touched: {res.subsidiaries_touched}")
    for e in res.errors:
        print(f"  ERROR: {e}")
    for w in res.warnings:
        print(f"  WARN:  {w}")
    sys.exit(0 if res.ok else 1)
