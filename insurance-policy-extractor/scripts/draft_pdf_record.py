#!/usr/bin/env python3
"""Extract page text and OCR-needed signals from one claimed PDF."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from policy_common import resolve_source_path, sha256_file


def quality_for(text: str) -> tuple[str, bool]:
    compact = " ".join(text.split())
    count = len(compact)
    if count == 0:
        return "none", True
    if count < 80:
        return "low", True
    return "readable", False


def page_payload(page_number: int, text: str, warnings: list[str] | None = None) -> dict[str, object]:
    quality, ocr_needed = quality_for(text)
    return {
        "page_number": page_number,
        "character_count": len(text),
        "word_count": len(text.split()),
        "text_quality": quality,
        "ocr_needed": ocr_needed,
        "warnings": warnings or [],
        "text": text,
    }


def extract_with_pypdf(source: Path) -> list[dict[str, object]]:
    from pypdf import PdfReader

    pages: list[dict[str, object]] = []
    reader = PdfReader(str(source))
    for page_number, page in enumerate(reader.pages, start=1):
        page_warnings: list[str] = []
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = ""
            page_warnings.append(f"text extraction failed: {exc}")
        pages.append(page_payload(page_number, text, page_warnings))
    return pages


def extract_with_pymupdf(source: Path) -> list[dict[str, object]]:
    import fitz

    pages: list[dict[str, object]] = []
    with fitz.open(str(source)) as document:
        for page_number, page in enumerate(document, start=1):
            pages.append(page_payload(page_number, page.get_text("text") or ""))
    return pages


def text_total(pages: list[dict[str, object]]) -> int:
    return sum(int(page["character_count"]) for page in pages)


def extract_pages(source: Path, parser_name: str) -> tuple[list[dict[str, object]], str, list[str]]:
    if parser_name == "pypdf":
        return extract_with_pypdf(source), "pypdf", []
    if parser_name == "pymupdf":
        return extract_with_pymupdf(source), "pymupdf", []

    warnings: list[str] = []
    primary_pages: list[dict[str, object]] | None = None
    try:
        primary_pages = extract_with_pypdf(source)
    except Exception as exc:
        warnings.append(f"pypdf failed: {exc}")

    primary_has_errors = bool(primary_pages) and any(page["warnings"] for page in primary_pages)
    if primary_pages and text_total(primary_pages) > 0 and not primary_has_errors:
        return primary_pages, "pypdf", warnings

    try:
        with tempfile.TemporaryDirectory(prefix="policy-pdf-") as temp_dir:
            local_source = Path(temp_dir) / "source.pdf"
            shutil.copy2(source, local_source)
            fallback_pages = extract_with_pymupdf(local_source)
        warnings.append("Used a local-copy PyMuPDF fallback after pypdf failed or returned no reliable text.")
        if primary_pages is None or primary_has_errors or text_total(fallback_pages) >= text_total(primary_pages):
            return fallback_pages, "pymupdf", warnings
    except Exception as exc:
        warnings.append(f"PyMuPDF fallback failed: {exc}")

    if primary_pages is not None:
        return primary_pages, "pypdf", warnings
    raise RuntimeError("; ".join(warnings) or "No PDF parser was available.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract page text and OCR-needed signals for one PDF without creating a final policy record."
    )
    parser.add_argument("source_pdf")
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--parser", choices=("auto", "pypdf", "pymupdf"), default="auto")
    args = parser.parse_args()

    source = resolve_source_path(args.source_pdf, args.expected_sha256)
    output = Path(args.output).expanduser().resolve()
    if source is None or source.suffix.lower() != ".pdf":
        print(f"ERROR: source is not a resolvable PDF file: {args.source_pdf}", file=sys.stderr)
        return 2
    source_digest = sha256_file(source)
    if args.expected_sha256 and source_digest != args.expected_sha256:
        print("ERROR: resolved source SHA-256 does not match --expected-sha256.", file=sys.stderr)
        return 5

    warnings: list[str] = []
    try:
        pages, parser_used, parser_warnings = extract_pages(source, args.parser)
        warnings.extend(parser_warnings)
    except Exception as exc:
        print(f"ERROR: could not read PDF: {exc}", file=sys.stderr)
        return 4

    ocr_pages = [p["page_number"] for p in pages if p["ocr_needed"]]
    if ocr_pages:
        warnings.append(f"OCR or visual review needed for pages: {ocr_pages}")
    payload = {
        "artifact_type": "pdf_text_evidence",
        "assigned_source_path": args.source_pdf,
        "source_path": str(source),
        "source_sha256": source_digest,
        "parser": parser_used,
        "page_count": len(pages),
        "ocr_needed_pages": ocr_pages,
        "warnings": warnings,
        "pages": pages,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Draft text evidence written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
