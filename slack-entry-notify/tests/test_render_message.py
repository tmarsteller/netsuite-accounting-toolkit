"""Tests for render_message.py — the formatting engine."""
import json
import sys
from pathlib import Path

import pytest

# Make the script importable
SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import render_message as rm  # noqa: E402


# ---------------------------------------------------------------------------
# fmt_amount
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    (None, ""),
    (0, ""),
    (10000, "$10,000"),
    (10000.00, "$10,000"),
    (1234.5, "$1,234.50"),
    (-2500, "($2,500)"),
    (-2500.75, "($2,500.75)"),
])
def test_fmt_amount(value, expected):
    assert rm.fmt_amount(value) == expected


def test_fmt_amount_custom_currency():
    assert rm.fmt_amount(1000, currency="€") == "€1,000"


# ---------------------------------------------------------------------------
# fmt_total — never blank
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    (None, "$0"),
    (0, "$0"),
    (10000, "$10,000"),
    (-2500, "($2,500)"),
])
def test_fmt_total(value, expected):
    assert rm.fmt_total(value) == expected


# ---------------------------------------------------------------------------
# line_label
# ---------------------------------------------------------------------------
def test_line_label_code_and_name():
    assert rm.line_label({"code": "4000", "name": "Revenue"}) == "4000 Revenue"


def test_line_label_explicit_label_wins():
    assert rm.line_label({"label": "Custom", "code": "4000", "name": "Revenue"}) == "Custom"


def test_line_label_name_only():
    assert rm.line_label({"name": "Cash"}) == "Cash"


def test_line_label_code_only():
    assert rm.line_label({"code": "1000"}) == "1000"


def test_line_label_no_double_code_when_name_starts_with_code():
    assert rm.line_label({"code": "4000", "name": "4000 Revenue"}) == "4000 Revenue"


# ---------------------------------------------------------------------------
# render — pending
# ---------------------------------------------------------------------------
def test_render_pending_basic():
    payload = {
        "status": "pending",
        "title": "Entry #1",
        "subtitle": "Acme • 2026-01-31",
        "columns": {"left": "Debit", "right": "Credit"},
        "lines": [
            {"code": "4000", "name": "Revenue", "left": None, "right": 100},
            {"code": "1000", "name": "Cash", "left": 100, "right": None},
        ],
        "total": 100,
        "link": "https://example.com/1",
        "link_text": "Open",
    }
    out = rm.render(payload)
    assert "**Entry #1** — ready for review" in out
    assert "_Acme • 2026-01-31_" in out
    assert "| Item | Debit | Credit |" in out
    assert "| 4000 Revenue |  | $100 |" in out
    assert "| 1000 Cash | $100 |  |" in out
    assert "| **Total** | **$100** | **$100** |" in out
    assert "🔗 [Open](https://example.com/1)" in out


def test_render_pending_default_columns():
    out = rm.render({"status": "pending", "title": "X", "lines": [{"name": "a", "left": 1}]})
    assert "| Item | Left | Right |" in out


def test_render_notes_as_blockquotes():
    out = rm.render({"status": "pending", "title": "X", "notes": ["note one", "note two"]})
    assert "> note one" in out
    assert "> note two" in out


def test_render_header_only_no_table():
    out = rm.render({"status": "pending", "title": "Header only"})
    assert "**Header only**" in out
    assert "| Item |" not in out


# ---------------------------------------------------------------------------
# render — posted
# ---------------------------------------------------------------------------
def test_render_posted_icon_and_text():
    out = rm.render({"status": "posted", "title": "Done"})
    assert ":white_check_mark:" in out
    assert "complete" in out


def test_render_posted_negative_parentheses():
    payload = {
        "status": "posted",
        "title": "Reversal",
        "lines": [{"name": "Revenue", "right": -2500}],
        "total": -2500,
    }
    out = rm.render(payload)
    assert "($2,500)" in out
    assert "| **Total** | **($2,500)** | **($2,500)** |" in out


# ---------------------------------------------------------------------------
# render — info
# ---------------------------------------------------------------------------
def test_render_info():
    payload = {
        "status": "info",
        "workflow_name": "Recon",
        "period": "Jan 2026",
        "reason": "No exceptions.",
    }
    out = rm.render(payload)
    assert ":information_source:" in out
    assert "**Recon** — Jan 2026" in out
    assert "No exceptions." in out
    assert "| Item |" not in out


# ---------------------------------------------------------------------------
# render — errors & overrides
# ---------------------------------------------------------------------------
def test_render_unknown_status_raises():
    with pytest.raises(ValueError):
        rm.render({"status": "bogus", "title": "X"})


def test_render_icon_override():
    out = rm.render({"status": "pending", "title": "X", "icon": ":fire:"})
    assert out.startswith(":fire:")


def test_render_status_text_override():
    out = rm.render({"status": "pending", "title": "X", "status_text": "needs sign-off"})
    assert "needs sign-off" in out


def test_long_table_truncates():
    lines = [{"name": f"row{i}", "left": i} for i in range(30)]
    out = rm.render({"status": "pending", "title": "Big", "lines": lines})
    assert "more — see attachment" in out
    # 18 shown + truncation row, not all 30
    assert out.count("| row") == 18


# ---------------------------------------------------------------------------
# examples render without error
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("example", [
    "pending_journal_entry.json",
    "posted_with_benefit.json",
    "info_heartbeat.json",
])
def test_examples_render(example):
    path = Path(__file__).resolve().parent.parent / "examples" / example
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = rm.render(payload)
    assert out.strip()  # non-empty
