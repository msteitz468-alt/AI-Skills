#!/usr/bin/env python3
"""Build a professionally formatted renewal policy discrepancy workbook.

Input is a normalized JSON payload documented in references/workbook-schema.md.
The script intentionally uses only openpyxl so it can run in ChatGPT or Codex
without proprietary dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.dimensions import ColumnDimension


SHEET_EXECUTIVE = "Executive Summary"
SHEET_QP = "Quote vs Policy"
SHEET_SQ = "Submission vs Quote"
SHEET_RE = "Renewal vs Expiring"
SHEET_DETAIL = "Detailed Findings"
SHEET_MISSING = "Missing-Unverifiable"
SHEET_SOURCE = "Source Index"

NAVY = "1F4E78"
DARK_NAVY = "17365D"
WHITE = "FFFFFF"
LIGHT_BLUE = "D9EAF7"
PALE_BLUE = "EAF3F8"
CRITICAL_FILL = "F4CCCC"
CRITICAL_FONT = "9C0006"
MODERATE_FILL = "FCE5CD"
MODERATE_FONT = "9C5700"
MINOR_FILL = "FFF2CC"
MINOR_FONT = "7F6000"
MISSING_FILL = "E7E6E6"
MISSING_FONT = "595959"
SUCCESS_FILL = "D9EAD3"
SUCCESS_FONT = "274E13"
CAUTION_FILL = "FCE4D6"
STATIC_GRAY = "F2F2F2"
GRID = "D9E1F2"
TEXT = "1F1F1F"
GREEN_TEXT = "008000"
GRAY_TEXT = "666666"

THIN_GRAY = Side(style="thin", color=GRID)
MEDIUM_NAVY = Side(style="medium", color=NAVY)

SEVERITY_CANONICAL = {
    "critical": "Critical",
    "red": "Critical",
    "moderate": "Moderate",
    "orange": "Moderate",
    "minor": "Minor",
    "yellow": "Minor",
    "missing info": "Missing Info",
    "missing": "Missing Info",
    "unverifiable": "Missing Info",
}

COMPARISON_CANONICAL = {
    "quote_vs_policy": "quote_vs_policy",
    "quote vs policy": "quote_vs_policy",
    "quote-policy": "quote_vs_policy",
    "submission_vs_quote": "submission_vs_quote",
    "submission vs quote": "submission_vs_quote",
    "submission-quote": "submission_vs_quote",
    "renewal_vs_expiring": "renewal_vs_expiring",
    "renewal vs expiring": "renewal_vs_expiring",
    "policy_vs_expiring": "renewal_vs_expiring",
    "policy vs expiring": "renewal_vs_expiring",
    "detailed": "detailed",
    "missing": "missing",
}

COMPARISON_LABEL = {
    "quote_vs_policy": "Quote vs Policy",
    "submission_vs_quote": "Submission vs Quote",
    "renewal_vs_expiring": "Renewal vs Expiring",
    "detailed": "Detailed Review",
    "missing": "Missing / Unverifiable",
}


class PayloadError(ValueError):
    """Raised for a malformed workbook payload."""


def safe_text(value: Any) -> str:
    """Convert arbitrary JSON values to readable cell text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def normalize_severity(value: Any) -> str:
    text = safe_text(value)
    stripped = (
        text.replace("🔴", "")
        .replace("🟠", "")
        .replace("🟡", "")
        .replace("⚪", "")
        .strip()
    )
    key = stripped.casefold()
    if key in SEVERITY_CANONICAL:
        return SEVERITY_CANONICAL[key]
    if stripped in {"Critical", "Moderate", "Minor", "Missing Info"}:
        return stripped
    raise PayloadError(
        f"Unsupported severity {text!r}. Use Critical, Moderate, Minor, or Missing Info."
    )


def normalize_comparison(value: Any, severity: str) -> str:
    text = safe_text(value).casefold().strip()
    if severity == "Missing Info" and not text:
        return "missing"
    if text in COMPARISON_CANONICAL:
        return COMPARISON_CANONICAL[text]
    if not text:
        return "detailed"
    raise PayloadError(
        f"Unsupported comparison {value!r}. Use quote_vs_policy, submission_vs_quote, "
        "renewal_vs_expiring, detailed, or missing."
    )


def load_payload(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise PayloadError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PayloadError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise PayloadError("Top-level JSON value must be an object.")

    review = payload.get("review", {})
    if review is None:
        review = {}
    if not isinstance(review, dict):
        raise PayloadError("review must be an object.")
    insured = safe_text(review.get("insured_name"))
    if not insured:
        raise PayloadError("review.insured_name is required.")

    documents = payload.get("documents", []) or []
    findings = payload.get("findings", []) or []
    if not isinstance(documents, list):
        raise PayloadError("documents must be an array.")
    if not isinstance(findings, list):
        raise PayloadError("findings must be an array.")

    normalized_findings: list[dict[str, Any]] = []
    for index, raw in enumerate(findings, start=1):
        if not isinstance(raw, dict):
            raise PayloadError(f"findings[{index - 1}] must be an object.")
        severity = normalize_severity(raw.get("severity", "Missing Info"))
        comparison = normalize_comparison(raw.get("comparison"), severity)
        item = safe_text(raw.get("item"))
        category = safe_text(raw.get("category"))
        if not item:
            raise PayloadError(f"findings[{index - 1}].item is required.")
        if not category:
            raise PayloadError(f"findings[{index - 1}].category is required.")

        finding = dict(raw)
        finding["id"] = safe_text(raw.get("id")) or f"F-{index:03d}"
        finding["severity"] = severity
        finding["comparison"] = "missing" if severity == "Missing Info" else comparison
        finding["status"] = safe_text(raw.get("status")) or "Open"
        normalized_findings.append(finding)

    normalized_documents: list[dict[str, Any]] = []
    for index, raw in enumerate(documents, start=1):
        if not isinstance(raw, dict):
            raise PayloadError(f"documents[{index - 1}] must be an object.")
        filename = safe_text(raw.get("filename"))
        if not filename:
            raise PayloadError(f"documents[{index - 1}].filename is required.")
        document = dict(raw)
        document["filename"] = filename
        normalized_documents.append(document)

    payload["review"] = review
    payload["findings"] = normalized_findings
    payload["documents"] = normalized_documents
    return payload


def final_quote_value(finding: dict[str, Any]) -> str:
    return safe_text(finding.get("bind_terms")) or safe_text(finding.get("quote"))


def source_value(finding: dict[str, Any], key: str) -> str:
    sources = finding.get("sources") or {}
    if isinstance(sources, dict):
        value = safe_text(sources.get(key))
        if value:
            return value
    aliases = {
        "submission": ["source_submission"],
        "quote": ["source_quote", "source_bind_terms"],
        "policy": ["source_policy", "source_renewal_policy"],
        "expiring": ["source_expiring", "source_expiring_policy"],
    }
    for alias in aliases.get(key, []):
        value = safe_text(finding.get(alias))
        if value:
            return value
    return ""


def unique_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = safe_text(item)
        if not text:
            continue
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


def derive_immediate_attention(findings: list[dict[str, Any]]) -> list[str]:
    alerts = []
    for finding in findings:
        if finding["severity"] != "Critical":
            continue
        if safe_text(finding.get("status")).casefold() == "verified":
            continue
        item = safe_text(finding.get("item"))
        issue = safe_text(finding.get("issue"))
        alerts.append(f"{item}: {issue}" if issue else item)
    return unique_preserve(alerts)


def derive_red_flags(findings: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    for finding in findings:
        comparison = finding["comparison"]
        category = safe_text(finding.get("category")).casefold()
        item = safe_text(finding.get("item")).casefold()
        issue = safe_text(finding.get("issue")).casefold()
        quote = final_quote_value(finding)
        policy = safe_text(finding.get("renewal_policy"))
        combined = " ".join([category, item, issue])

        if comparison == "quote_vs_policy":
            if quote and (not policy or any(word in issue for word in ["missing", "omitted", "not included"])):
                flags.append("Quoted but not bound")
            if policy and not quote:
                flags.append("Bound but not quoted")
            if any(word in combined for word in ["reduc", "lower", "narrow", "more restrictive"]):
                flags.append("Coverage reduced at binding")
        if "premium" in combined and any(word in issue for word in ["unexplained", "does not match", "differs", "mismatch"]):
            flags.append("Unexplained premium change")
        if "exclusion" in combined and any(word in combined for word in ["new", "unquoted", "restrict"]):
            flags.append("New exclusion or restrictive endorsement")
        if "form" in combined and any(word in combined for word in ["missing", "unavailable", "not supplied"]):
            flags.append("Missing form or endorsement wording")
        if any(word in combined for word in ["named insured", "scheduled exposure", "location", "vehicle", "equipment"]):
            if any(word in combined for word in ["missing", "omitted", "removed"]):
                flags.append("Named insured or scheduled exposure omitted")
        if any(word in combined for word in ["retroactive", "prior and pending", "continuity", "claims-made"]):
            flags.append("Claims-made continuity issue")
        if any(word in combined for word in ["underlying", "attachment point"]):
            if any(word in combined for word in ["mismatch", "missing", "differs", "wrong"]):
                flags.append("Underlying schedule or attachment-point mismatch")
        if any(word in combined for word in ["policy term", "effective date", "expiration date", "carrier"]):
            if any(word in combined for word in ["mismatch", "wrong", "differs"]):
                flags.append("Policy term or carrier mismatch")
    return unique_preserve(flags)


def set_page_defaults(ws) -> None:
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    ws.oddFooter.center.text = "Page &P of &N"
    ws.oddFooter.right.text = "Renewal Policy Check"


def style_title(ws, title: str, max_col: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    cell = ws.cell(1, 1, title)
    cell.fill = PatternFill("solid", fgColor=NAVY)
    cell.font = Font(name="Aptos Display", size=18, bold=True, color=WHITE)
    cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 30
    for col in range(2, max_col + 1):
        ws.cell(1, col).fill = PatternFill("solid", fgColor=NAVY)


def style_header_row(ws, row: int, max_col: int) -> None:
    for col in range(1, max_col + 1):
        cell = ws.cell(row, col)
        cell.fill = PatternFill("solid", fgColor=DARK_NAVY)
        cell.font = Font(name="Aptos", size=10, bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=MEDIUM_NAVY)
    ws.row_dimensions[row].height = 30


def add_section_label(ws, row: int, label: str, max_col: int, fill: str = NAVY) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
    cell = ws.cell(row, 1, label)
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(name="Aptos", size=11, bold=True, color=WHITE)
    cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 22
    for col in range(2, max_col + 1):
        ws.cell(row, col).fill = PatternFill("solid", fgColor=fill)


def apply_body_style(
    ws, start_row: int, end_row: int, max_col: int, widths: list[float] | None = None
) -> None:
    if end_row < start_row:
        return
    for row in range(start_row, end_row + 1):
        estimated_lines = 1
        for col in range(1, max_col + 1):
            cell = ws.cell(row, col)
            cell.font = Font(name="Aptos", size=10, color=TEXT)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=THIN_GRAY)
            if col == 1:
                cell.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
            text = safe_text(cell.value)
            width = widths[col - 1] if widths and col - 1 < len(widths) else 20
            capacity = max(8, int(width * 0.95))
            lines = sum(max(1, math.ceil(len(part) / capacity)) for part in text.splitlines() or [""])
            estimated_lines = max(estimated_lines, lines)
        ws.row_dimensions[row].height = min(105, max(20, 15 * estimated_lines + 6))


def severity_style(cell, severity: str) -> None:
    styles = {
        "Critical": (CRITICAL_FILL, CRITICAL_FONT),
        "Moderate": (MODERATE_FILL, MODERATE_FONT),
        "Minor": (MINOR_FILL, MINOR_FONT),
        "Missing Info": (MISSING_FILL, MISSING_FONT),
    }
    fill, font = styles[severity]
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(name="Aptos", size=10, bold=True, color=font)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def add_severity_conditional_formatting(ws, severity_col: int, first_data_row: int, last_data_row: int, max_col: int) -> None:
    if last_data_row < first_data_row:
        return
    severity_letter = get_column_letter(severity_col)
    full_range = f"A{first_data_row}:{get_column_letter(max_col)}{last_data_row}"
    for severity, fill_color in [
        ("Critical", CRITICAL_FILL),
        ("Moderate", MODERATE_FILL),
        ("Minor", MINOR_FILL),
        ("Missing Info", MISSING_FILL),
    ]:
        ws.conditional_formatting.add(
            full_range,
            FormulaRule(
                formula=[f'${severity_letter}{first_data_row}="{severity}"'],
                fill=PatternFill("solid", fgColor=fill_color),
                stopIfTrue=False,
            ),
        )


def set_widths(ws, widths: list[float]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def write_table_sheet(
    ws,
    title: str,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    severity_col: int | None,
) -> None:
    max_col = len(headers)
    style_title(ws, title, max_col)
    ws.cell(2, 1, "Review findings based on supplied documents. Empty cells indicate the term was not established in that source.")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
    ws.cell(2, 1).font = Font(name="Aptos", size=9, italic=True, color=GRAY_TEXT)
    ws.cell(2, 1).alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 24

    header_row = 3
    for col, header in enumerate(headers, start=1):
        ws.cell(header_row, col, header)
    style_header_row(ws, header_row, max_col)

    first_data_row = 4
    if rows:
        for row_index, values in enumerate(rows, start=first_data_row):
            for col_index, value in enumerate(values, start=1):
                ws.cell(row_index, col_index, value)
    else:
        ws.cell(first_data_row, 1, "No discrepancies identified from supplied information")
        ws.merge_cells(start_row=first_data_row, start_column=1, end_row=first_data_row, end_column=max_col)
        ws.cell(first_data_row, 1).fill = PatternFill("solid", fgColor=SUCCESS_FILL)
        ws.cell(first_data_row, 1).font = Font(name="Aptos", size=10, italic=True, color=SUCCESS_FONT)
        ws.cell(first_data_row, 1).alignment = Alignment(horizontal="left", vertical="center")

    last_data_row = first_data_row + max(len(rows), 1) - 1
    apply_body_style(ws, first_data_row, last_data_row, max_col, widths)
    if rows and severity_col:
        for row_index in range(first_data_row, last_data_row + 1):
            severity_style(ws.cell(row_index, severity_col), safe_text(ws.cell(row_index, severity_col).value))
        add_severity_conditional_formatting(ws, severity_col, first_data_row, last_data_row, max_col)

    set_widths(ws, widths)
    set_page_defaults(ws)
    ws.auto_filter.ref = f"A3:{get_column_letter(max_col)}{last_data_row}"


def build_specific_rows(
    findings: list[dict[str, Any]], comparison: str, include_sources: bool
) -> tuple[list[str], list[list[str]], list[float], int]:
    selected = [f for f in findings if f["comparison"] == comparison and f["severity"] != "Missing Info"]

    if comparison == "quote_vs_policy":
        headers = [
            "ID", "Category", "Item", "Final Quote / Bind Terms", "Renewal Policy",
            "Issue", "Severity", "Status", "Recommended Action",
        ]
        widths = [11, 22, 28, 30, 30, 40, 14, 14, 34]
        rows = [
            [
                safe_text(f["id"]), safe_text(f.get("category")), safe_text(f.get("item")),
                final_quote_value(f), safe_text(f.get("renewal_policy")), safe_text(f.get("issue")),
                f["severity"], safe_text(f.get("status")), safe_text(f.get("action")),
            ]
            for f in selected
        ]
        if include_sources:
            headers += ["Quote / Bind Source", "Policy Source"]
            widths += [30, 30]
            for row, finding in zip(rows, selected):
                row += [source_value(finding, "quote"), source_value(finding, "policy")]
        return headers, rows, widths, 7

    if comparison == "submission_vs_quote":
        headers = [
            "ID", "Category", "Item", "Submission / Client Intent", "Final Quote / Bind Terms",
            "Issue", "Severity", "Status", "Recommended Action",
        ]
        widths = [11, 22, 28, 30, 30, 40, 14, 14, 34]
        rows = [
            [
                safe_text(f["id"]), safe_text(f.get("category")), safe_text(f.get("item")),
                safe_text(f.get("submission")), final_quote_value(f), safe_text(f.get("issue")),
                f["severity"], safe_text(f.get("status")), safe_text(f.get("action")),
            ]
            for f in selected
        ]
        if include_sources:
            headers += ["Submission Source", "Quote / Bind Source"]
            widths += [30, 30]
            for row, finding in zip(rows, selected):
                row += [source_value(finding, "submission"), source_value(finding, "quote")]
        return headers, rows, widths, 7

    if comparison == "renewal_vs_expiring":
        headers = [
            "ID", "Category", "Item", "Expiring Policy", "Renewal Policy",
            "Change / Issue", "Severity", "Status", "Recommended Action",
        ]
        widths = [11, 22, 28, 30, 30, 40, 14, 14, 34]
        rows = [
            [
                safe_text(f["id"]), safe_text(f.get("category")), safe_text(f.get("item")),
                safe_text(f.get("expiring_policy")), safe_text(f.get("renewal_policy")),
                safe_text(f.get("issue")), f["severity"], safe_text(f.get("status")),
                safe_text(f.get("action")),
            ]
            for f in selected
        ]
        if include_sources:
            headers += ["Expiring Source", "Renewal Policy Source"]
            widths += [30, 30]
            for row, finding in zip(rows, selected):
                row += [source_value(finding, "expiring"), source_value(finding, "policy")]
        return headers, rows, widths, 7

    raise AssertionError(f"Unsupported specific comparison: {comparison}")


def build_detail_rows(findings: list[dict[str, Any]], include_sources: bool):
    selected = [f for f in findings if f["severity"] != "Missing Info" and f["comparison"] != "missing"]
    headers = [
        "ID", "Comparison", "Category", "Item", "Submission / Client Intent",
        "Final Quote / Bind Terms", "Renewal Policy", "Expiring Policy",
        "Issue / Change", "Severity", "Status", "Recommended Action",
    ]
    widths = [11, 20, 22, 28, 28, 28, 28, 28, 40, 14, 14, 34]
    rows = [
        [
            safe_text(f["id"]), COMPARISON_LABEL[f["comparison"]], safe_text(f.get("category")),
            safe_text(f.get("item")), safe_text(f.get("submission")), final_quote_value(f),
            safe_text(f.get("renewal_policy")), safe_text(f.get("expiring_policy")),
            safe_text(f.get("issue")), f["severity"], safe_text(f.get("status")),
            safe_text(f.get("action")),
        ]
        for f in selected
    ]
    if include_sources:
        headers += ["Submission Source", "Quote / Bind Source", "Policy Source", "Expiring Source"]
        widths += [30, 30, 30, 30]
        for row, finding in zip(rows, selected):
            row += [
                source_value(finding, "submission"), source_value(finding, "quote"),
                source_value(finding, "policy"), source_value(finding, "expiring"),
            ]
    return headers, rows, widths, 10


def build_missing_rows(findings: list[dict[str, Any]], include_sources: bool):
    selected = [f for f in findings if f["severity"] == "Missing Info" or f["comparison"] == "missing"]
    headers = [
        "ID", "Category", "Item", "Missing / Ambiguous Information", "Why It Matters",
        "Needed From", "Severity", "Recommended Action",
    ]
    widths = [11, 22, 28, 42, 36, 28, 14, 34]
    rows = [
        [
            safe_text(f["id"]), safe_text(f.get("category")), safe_text(f.get("item")),
            safe_text(f.get("issue")), safe_text(f.get("why_it_matters")),
            safe_text(f.get("needed_from")), "Missing Info", safe_text(f.get("action")),
        ]
        for f in selected
    ]
    if include_sources:
        headers += ["Available Source References"]
        widths += [42]
        for row, finding in zip(rows, selected):
            available = unique_preserve([
                source_value(finding, "submission"), source_value(finding, "quote"),
                source_value(finding, "policy"), source_value(finding, "expiring"),
            ])
            row += [" | ".join(available)]
    return headers, rows, widths, 7


def build_source_rows(documents: list[dict[str, Any]]):
    headers = [
        "Filename", "Inferred Role", "Selected for Bound Review", "Confidence",
        "Carrier", "Policy Term", "Notes",
    ]
    widths = [48, 24, 23, 14, 26, 22, 45]
    rows: list[list[str]] = []
    for document in documents:
        rows.append([
            safe_text(document.get("filename")),
            safe_text(document.get("role")).replace("_", " ").title(),
            safe_text(document.get("selected")),
            safe_text(document.get("confidence")),
            safe_text(document.get("carrier")),
            safe_text(document.get("policy_term")),
            safe_text(document.get("notes")),
        ])
    return headers, rows, widths


def build_executive_summary(ws, payload: dict[str, Any]) -> None:
    review = payload["review"]
    findings = payload["findings"]
    max_col = 9
    style_title(ws, "Renewal Policy Check — Executive Summary", max_col)
    ws.freeze_panes = "A3"
    ws.sheet_view.showGridLines = False

    labels = [
        (3, "Insured", safe_text(review.get("insured_name"))),
        (4, "Policy Term", safe_text(review.get("policy_term"))),
        (5, "Line of Business", safe_text(review.get("line_of_business"))),
        (6, "Prepared Date", safe_text(review.get("prepared_date")) or date.today().isoformat()),
    ]
    for row, label, value in labels:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.cell(row, 1, label)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=max_col)
        ws.cell(row, 3, value)
        for col in range(1, 3):
            ws.cell(row, col).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
        ws.cell(row, 1).font = Font(name="Aptos", size=10, bold=True, color=NAVY)
        ws.cell(row, 1).alignment = Alignment(vertical="center")
        ws.cell(row, 3).font = Font(name="Aptos", size=10, color=GREEN_TEXT)
        ws.cell(row, 3).alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[row].height = 21

    add_section_label(ws, 8, "Overall Assessment", max_col)
    risk = safe_text(review.get("overall_risk")) or "Review the severity summary and detailed findings below."
    ws.merge_cells(start_row=9, start_column=1, end_row=9, end_column=max_col)
    ws.cell(9, 1, risk)
    ws.cell(9, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(9, 1).font = Font(name="Aptos", size=10, color=TEXT)
    ws.row_dimensions[9].height = min(75, max(30, 15 + (len(risk) // 110) * 15))

    ws.merge_cells("A11:D11")
    ws.cell(11, 1, "Severity Summary")
    ws.merge_cells("E11:I11")
    ws.cell(11, 5, "Quote-to-Policy Alignment")
    for start_col, end_col in [(1, 4), (5, 9)]:
        for col in range(start_col, end_col + 1):
            ws.cell(11, col).fill = PatternFill("solid", fgColor=NAVY)
        ws.cell(11, start_col).font = Font(name="Aptos", size=11, bold=True, color=WHITE)
        ws.cell(11, start_col).alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[11].height = 22

    severity_rows = [(12, "Critical", CRITICAL_FILL), (13, "Moderate", MODERATE_FILL), (14, "Minor", MINOR_FILL), (15, "Missing Info", MISSING_FILL)]
    for row, severity, fill in severity_rows:
        ws.cell(row, 1, severity)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.cell(row, 3, "Count")
        ws.cell(row, 4, None)
        ws.cell(row, 1).fill = PatternFill("solid", fgColor=fill)
        ws.cell(row, 1).font = Font(name="Aptos", size=10, bold=True)
        ws.cell(row, 3).fill = PatternFill("solid", fgColor=STATIC_GRAY)
        ws.cell(row, 3).font = Font(name="Aptos", size=10, bold=True, color=GRAY_TEXT)
        if severity == "Missing Info":
            ws.cell(row, 4, f'=COUNTIF(\'{SHEET_MISSING}\'!G:G,"Missing Info")')
        else:
            ws.cell(row, 4, f'=COUNTIF(\'{SHEET_DETAIL}\'!J:J,"{severity}")')
        ws.cell(row, 4).font = Font(name="Aptos", size=11, bold=True, color=TEXT)
        ws.cell(row, 4).alignment = Alignment(horizontal="center")

    alignment_override = safe_text(review.get("alignment"))
    alignment_formula = '=IF(D12>0,"Material Mismatch",IF(D13+D14>0,"Minor Variances",IF(D15>0,"Review Incomplete","Aligned")))'
    ws.merge_cells("E12:I15")
    ws.cell(12, 5, alignment_override or alignment_formula)
    ws.cell(12, 5).font = Font(name="Aptos Display", size=18, bold=True, color=NAVY)
    ws.cell(12, 5).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.cell(12, 5).fill = PatternFill("solid", fgColor=PALE_BLUE)

    immediate = unique_preserve(payload.get("immediate_attention", []) or [])
    if not immediate:
        immediate = derive_immediate_attention(findings)
    red_flags = unique_preserve(payload.get("red_flags", []) or [])
    red_flags = unique_preserve(red_flags + derive_red_flags(findings))
    notes = unique_preserve(payload.get("notes", []) or [])
    scope_notes = safe_text(review.get("scope_notes"))
    if scope_notes:
        notes.insert(0, scope_notes)

    row = 18
    add_section_label(ws, row, "Items Requiring Immediate Attention", max_col, fill="9C0006")
    row += 1
    if immediate:
        for alert in immediate:
            ws.cell(row, 1, "•")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=max_col)
            ws.cell(row, 2, alert)
            for col in range(1, max_col + 1):
                ws.cell(row, col).fill = PatternFill("solid", fgColor=CRITICAL_FILL)
                ws.cell(row, col).font = Font(name="Aptos", size=10, color=CRITICAL_FONT)
                ws.cell(row, col).alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[row].height = min(75, max(20, 15 + (len(alert) // 110) * 15))
            row += 1
    else:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
        ws.cell(row, 1, "No Critical items identified from supplied information.")
        ws.cell(row, 1).fill = PatternFill("solid", fgColor=SUCCESS_FILL)
        ws.cell(row, 1).font = Font(name="Aptos", size=10, color=SUCCESS_FONT)
        row += 1

    row += 1
    add_section_label(ws, row, "Red Flag Alerts", max_col, fill="C55A11")
    row += 1
    if red_flags:
        for flag in red_flags:
            ws.cell(row, 1, "⚑")
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=max_col)
            ws.cell(row, 2, flag)
            for col in range(1, max_col + 1):
                ws.cell(row, col).fill = PatternFill("solid", fgColor=CAUTION_FILL)
                ws.cell(row, col).font = Font(name="Aptos", size=10, color=MODERATE_FONT)
                ws.cell(row, col).alignment = Alignment(wrap_text=True, vertical="top")
            row += 1
    else:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
        ws.cell(row, 1, "No automatic red flags identified.")
        ws.cell(row, 1).fill = PatternFill("solid", fgColor=SUCCESS_FILL)
        ws.cell(row, 1).font = Font(name="Aptos", size=10, color=SUCCESS_FONT)
        row += 1

    row += 1
    add_section_label(ws, row, "Scope and Review Notes", max_col)
    row += 1
    methodology = (
        "Comparison basis: client submission → selected final quote/bind terms → issued renewal policy; "
        "expiring policy used as the change-detection baseline. Detailed source references are omitted unless requested."
    )
    all_notes = [methodology] + notes
    for note in all_notes:
        ws.cell(row, 1, "•")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=max_col)
        ws.cell(row, 2, note)
        ws.cell(row, 2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row, 2).font = Font(name="Aptos", size=10, color=TEXT)
        ws.row_dimensions[row].height = min(75, max(20, 15 + (len(note) // 110) * 15))
        row += 1

    set_widths(ws, [3, 15, 14, 10, 15, 15, 15, 15, 15])
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddFooter.center.text = "Page &P of &N"
    ws.oddFooter.right.text = "Renewal Policy Check"


def build_workbook(payload: dict[str, Any], output_path: Path, include_sources: bool) -> None:
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    wb.properties.title = f"Renewal Policy Check - {safe_text(payload['review'].get('insured_name'))}"
    wb.properties.subject = "Commercial insurance renewal discrepancy review"
    wb.properties.creator = "Renewal Policy Checker"
    wb.properties.description = "Submission, quote/bind terms, renewal policy, and expiring policy comparison."
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"

    ws_exec = wb.create_sheet(SHEET_EXECUTIVE)
    ws_qp = wb.create_sheet(SHEET_QP)
    ws_sq = wb.create_sheet(SHEET_SQ)
    ws_re = wb.create_sheet(SHEET_RE)
    ws_detail = wb.create_sheet(SHEET_DETAIL)
    ws_missing = wb.create_sheet(SHEET_MISSING)
    ws_source = wb.create_sheet(SHEET_SOURCE)

    findings = payload["findings"]

    for ws, comparison, title in [
        (ws_qp, "quote_vs_policy", "Final Quote / Bind Terms vs Issued Renewal Policy"),
        (ws_sq, "submission_vs_quote", "Submission / Client Intent vs Final Quote / Bind Terms"),
        (ws_re, "renewal_vs_expiring", "Issued Renewal Policy vs Expiring Policy"),
    ]:
        headers, rows, widths, severity_col = build_specific_rows(findings, comparison, include_sources)
        write_table_sheet(ws, title, headers, rows, widths, severity_col)

    headers, rows, widths, severity_col = build_detail_rows(findings, include_sources)
    write_table_sheet(ws_detail, "Detailed Findings", headers, rows, widths, severity_col)

    headers, rows, widths, severity_col = build_missing_rows(findings, include_sources)
    write_table_sheet(ws_missing, "Missing / Unverifiable Items", headers, rows, widths, severity_col)

    headers, rows, widths = build_source_rows(payload["documents"])
    write_table_sheet(ws_source, "Source Index", headers, rows, widths, severity_col=None)

    # Color imported/document-index values green and static labels gray.
    for row in ws_source.iter_rows(min_row=4, max_row=ws_source.max_row):
        for cell in row:
            cell.font = Font(name="Aptos", size=10, color=GREEN_TEXT)

    build_executive_summary(ws_exec, payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)

    # Re-open to catch malformed workbook relationships before reporting success.
    check = load_workbook(output_path, data_only=False, read_only=False)
    required = [SHEET_EXECUTIVE, SHEET_QP, SHEET_SQ, SHEET_RE, SHEET_DETAIL, SHEET_MISSING, SHEET_SOURCE]
    missing = [name for name in required if name not in check.sheetnames]
    if missing:
        raise RuntimeError(f"Generated workbook is missing worksheets: {', '.join(missing)}")
    check.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a renewal policy discrepancy workbook from normalized JSON."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to normalized review JSON")
    parser.add_argument("--output", required=True, type=Path, help="Destination .xlsx path")
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Add detailed source-reference columns to finding worksheets",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.output.suffix.lower() != ".xlsx":
        print("ERROR: --output must end in .xlsx", file=sys.stderr)
        return 2
    try:
        payload = load_payload(args.input)
        build_workbook(payload, args.output, args.include_sources)
    except (PayloadError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
