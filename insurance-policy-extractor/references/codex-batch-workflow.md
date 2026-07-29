# Codex Batch Workflow

## Goal

Process insurance documents into concise annual JSON without accumulating document bodies in model context. The durable state is extracted coverage data, not complete source text. Annual client JSON must remain handbook-compatible by preserving a top-level `documents[]` array with the full staged record and legacy field aliases.

## Workspace Layout

```text
SOURCE_FOLDER/
  source documents...

WORK_DIR/
  extraction_manifest.json
  documents/
    doc_000001.json

OUTPUT_DIR/
  2026_Policies.json
```

## Phase 1: Inventory Without Model Ingestion

Run:

```bash
python scripts/inventory_policy_files.py SOURCE_FOLDER --work-dir WORK_DIR
```

Do not open source documents during inventory.

### Root `Legacy Files` Exclusion

When `SOURCE_FOLDER` is a client root, exclude `SOURCE_FOLDER/Legacy Files/` from inventory, hashing, assignment, OCR, extraction, duplicate detection, staging, and validation unless the user specifically asks to process that folder by name. This exclusion applies only to the root-level preserved archive; ordinary legacy source folders elsewhere may still be processed according to the assignment.


## Phase 2: Coordinator-Controlled Fan-Out

The main agent owns the authoritative manifest. Subagents never update it directly.

1. Partition pending, nonduplicate document IDs into immutable assignments:

```bash
python scripts/create_agent_batches.py --manifest WORK_DIR/extraction_manifest.json --output-dir WORK_DIR/agent-shards --batch-size 5
```

2. Give exceptionally long documents their own batch when practical.
3. Each assignment lists document ID, exact filename, relative path, source path, SHA-256, and expected output path.
4. Resolve each assignment source before reading it. If the literal path is missing, run `draft_pdf_record.py` with the assignment SHA-256; accept a repaired or sibling path only when the bytes match that hash, and preserve the resolved actual filename in the record.
5. Spawn one subagent per available batch when delegation is required. A subagent may own several sources but must process them sequentially with only one source body active at a time.
6. For each source, extract only the field set in `extraction-fields.md`; do not preserve complete source text in JSON.
   - Forms and endorsements are mandatory evidence. Search for schedule labels and variants including `Schedule of Forms`, `Forms and Endorsements`, `Endorsements Effective at Inception`, `Forms Attached at Issuance`, `Endorsement Schedule`, `Endt. No.`, `Form No.`, and `Form Number`.
   - If a schedule exists but contains only form numbers or abbreviated rows, extract every visible form number as its own row in `endorsements_exclusions` and `schedules.forms`, using `Not specified` for missing descriptions, edition dates, coverage, or form type.
   - Reserve `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` for the narrow case where no schedule/equivalent listing is visible after the searched pages/sections are documented in `source_notes`.
   - Add `SPARSE_FORMS_SCHEDULE` or `FORM_TITLES_NOT_SPECIFIED` when row extraction is complete but source descriptions are absent.
7. Write one JSON record per source to `WORK_DIR/agent-shards/<batch-id>/records/<document-id>.json`.
8. Write a shard completion report when useful. Do not write to another shard.

Do not call `next_policy_file.py --claim` or `stage_document.py` concurrently. The shared manifest is not a concurrent job queue.

## PDF Parser and OCR Recovery

Create transient page-level evidence for one PDF at a time:

```bash
python scripts/draft_pdf_record.py SOURCE_PDF --expected-sha256 SHA256 --output DRAFT_JSON
```

The helper tries pypdf first and uses a local-copy PyMuPDF fallback when the first parser fails or yields no reliable text. If `pdfinfo` or `pdftotext` hangs, crashes, fails silently, fails on a network path, or returns no output, stop that command and run the helper with `--parser pymupdf` or its local-copy fallback before declaring the PDF unreadable.

For image-heavy files, OCR unresolved pages in bounded chunks. After each chunk, update the review flags and report progress. Pages that remain parser- or OCR-unresolved must produce a `needs_review` record with page-level error evidence; they must not be marked complete.

Do not create a metadata-only, generated/partial-artifact, unsupported, or low-confidence hold for a PDF that appears policy-related until direct parser evidence has been attempted and inspected. Narrowing extraction scope may defer detailed schedules, but the worker still must inspect text evidence for policy number, endorsement number, LOB, carrier, named insured, and policy term.

## Progress Visibility

While subagents, parsers, or OCR jobs are active, publish a concise status matrix and update the user at least every 60 seconds. Report completed batches and genuine blockers as they occur. Preliminary evidence is not final completion.

## Phase 3: Main-Agent Fan-In

After subagents finish, the main agent:

1. Confirms each assigned document ID appears exactly once and no unassigned record exists.
2. Recomputes every source SHA-256 and rejects stale or changed records.
3. Validates assignment ownership, current hashes, and record schema:

```bash
python scripts/validate_agent_shards.py --manifest WORK_DIR/extraction_manifest.json --shards-dir WORK_DIR/agent-shards
```

4. Stages accepted base policies and declarations first, then endorsements serially with `stage_document.py`.
5. Performs endorsement reconciliation from staged JSON only.
6. Builds only calendar-year annual files in the handbook-compatible top-level `documents[]` shape.

## Endorsement Matching Without Reopening the Archive

Use staged JSON records first. Reopen a base-policy source only when its staged JSON is insufficient for a defensible decision.

Never force a relationship merely because documents share a folder.

## Consolidation

```bash
python scripts/build_year_outputs.py --manifest WORK_DIR/extraction_manifest.json --output-dir OUTPUT_DIR
```

Policies remain in their inception calendar year. Endorsements are grouped into the matched base policy's inception calendar year while retaining their own endorsement effective date and base-policy reference. The generated `YYYY_Policies.json` file must use top-level `documents[]` plus `metadata`, not a thinner nested `policies`/`endorsements` shape.

## Validation

```bash
python scripts/validate_outputs.py --manifest WORK_DIR/extraction_manifest.json --output-dir OUTPUT_DIR
```

Resolve every review-only or unassigned item before final calendar-year output delivery.

## Cleanup

After validation and delivery, remove transient work artifacts only when they are no longer needed and the user has not asked to preserve them. Removable transient artifacts include shard `drafts/` folders, page image folders such as `*_pages/`, local-copy parser scratch files, and empty staging folders. Preserve `extraction_manifest.json`, shard `assignment.json` files, final shard `records/`, staged `documents/`, validated `outputs/`, final annual JSON files, source documents, plans, logs, ledgers, exceptions, and other audit artifacts unless the user explicitly authorizes removal.

When building from a year-scoped source manifest, remove cross-year generated files before delivery. The final output shape may contain only the intended `YYYY_Policies.json` files for that run. Report cleanup bytes removed and categories removed in the run summary.

## Failure Handling

- Missing effective date: stage as `needs_review`; do not guess a year.
- Unmatched endorsement: preserve its own dates, set `effective_year` to `Not specified`, and do not finalize calendar-year outputs until the relationship is resolved or the item is excluded by explicit exception.
- Unreadable document or page: record an `UNREADABLE_PAGE` or document-level review flag.
- Unsupported file: leave it in the manifest with an explanatory status or exclusion note.
- Exact duplicate: mark `duplicate` and reference the canonical document ID.
- Conflicting values: preserve all sourced values and flag the conflict.


