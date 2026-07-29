---
name: insurance-policy-extractor
description: >
  Extract concise, source-grounded insurance policy, quote, binder, declaration,
  proposal, and endorsement data into auditable JSON. Use when ChatGPT or Codex
  must analyze insurance documents, capture document information, coverage lines,
  insurers, AM Best ratings, premiums, limits, sublimits, deductibles, valuation
  methods, endorsements/exclusions, exposures, and key schedules, or build annual
  policy JSON files for client-folder workflows. Enforce one-source-file-at-a-time
  ingestion without preserving full document text in JSON.
---

# Insurance Policy Extractor

## Purpose

Extract practical insurance coverage data without invention. The JSON output captures the fields in `references/extraction-fields.md`, based on `H:\AI Workflow\Policy_Extraction_Workflow.md`.

This skill does not require storing complete page text in JSON. Read enough of each source to extract the required fields, preserve exact filenames/paths, and cite source pages where the document exposes pages.

## Root `Legacy Files` Protection

When working inside a client root, treat a root-level folder named exactly `Legacy Files` as a preserved archive. Do not inventory, read, extract, OCR, hash, copy, move, rename, delete, or classify anything inside `<client-root>/Legacy Files/` unless the user specifically asks to process that folder by name. This is distinct from ordinary legacy source folders elsewhere in the client root.


## References

Read these when applicable:

- `references/extraction-fields.md` for the required field set.
- `references/json-record-spec.md` before creating or reviewing a JSON record.
- `references/codex-batch-workflow.md` for folder ingestion, subagent assignment, staging, and annual JSON consolidation.

Use bundled scripts for inventory, batching, staging, consolidation, and validation. Their output is audit support; do not replace document analysis with filename-only extraction.

## Non-Negotiable Rules

1. Never invent, estimate, or silently infer policy data.
2. Use the exact string `Not specified` when information is missing or unreadable.
3. Preserve the exact source filename, relative path, SHA-256, and page count when available.
4. Record source page numbers for material values when the format exposes pages.
5. Identify each coverage line separately.
6. Extract all available premiums, limits, sublimits, deductibles/SIRs, valuation methods, endorsements/exclusions, exposures, and listed schedules that fit the required field set.
7. Treat deductibles, SIRs, and percentage deductibles as critical fields.
8. Extract every listed form from the schedule of forms and endorsements, including advisory notices, notices to policyholders, exclusions, amendatory endorsements, coverage forms, common policy forms, and policy jacket forms. Preserve row-level form number, title, edition date, coverage/policy part, form type, and source pages in both `endorsements_exclusions` and `schedules.forms` when available. If the source schedule gives only form numbers, or form numbers with no descriptions, each form number is still a required row: set `title`, `edition_date`, `coverage`, or other missing fields to `Not specified` rather than omitting the row or treating the schedule as missing.
9. For schedules, extract the rows needed by the required schedule schemas: locations, vehicles, equipment, property, forms, and other material schedules.
10. A policy, endorsement, declaration, quote, binder, proposal, or other coverage-terms record must not be marked `complete` with an empty `endorsements_exclusions` and empty `schedules.forms` list unless `review_flags` includes `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` and `source_notes` states the pages/sections checked. Do not use `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` when a sparse or form-number-only schedule exists; extract the visible rows and add `SPARSE_FORMS_SCHEDULE` or `FORM_TITLES_NOT_SPECIFIED` if titles/descriptions are absent.
11. For management-liability records, do not treat filename shorthand such as `PL` as the coverage line when the document distinguishes D&O, EPL, Fiduciary, Side A, DIC, or Side A DIC. Extract `policy_type`, `coverage_lines`, primary/excess layer position, Side A/DIC wording, limit of liability, underlying insurance, attachment/SIR, and followed-policy references when available so folder workflows can name files with ranges such as `$10M xs $20M`.
12. Output JSON only for durable extraction artifacts. Do not put full source text in JSON.
13. In folder mode, each worker must process one source document at a time and write one JSON record before opening the next.
14. AM Best rating is required when web access or reliable current source context is available. If it cannot be verified, use `Not specified` and add a review flag.
15. Represent parser, OCR, or visual-review failures honestly. A record may finish as `needs_review` with page-level flags; never mark unresolved pages complete or invent their contents.
16. Never downgrade a PDF that appears policy-related to a metadata-only, generated/partial-artifact, unsupported, or low-confidence record until at least one direct text extraction path has been attempted and documented. Try `pdftotext` when available; if it crashes, hangs, fails silently, fails on a network path, or produces no usable text, run `draft_pdf_record.py` with its local-copy/PyMuPDF fallback and inspect the extracted text for filing-critical fields before holding the document.

## Interactive Mode

Use when the user identifies one document at a time.

1. Analyze only the current document.
2. Write a concise structured extraction summary in chat before finalizing when the user needs review.
3. Identify missing, conflicting, or uncertain fields.
4. When requested or accepted, create one JSON record using `references/json-record-spec.md`.

## Codex Folder Mode

Use when processing policies and endorsements inside a client folder.

1. Read `references/codex-batch-workflow.md`.
2. Inventory files without loading document bodies into model context:

```bash
python scripts/inventory_policy_files.py SOURCE_FOLDER --work-dir WORK_DIR
```

3. Create immutable assignments:

```bash
python scripts/create_agent_batches.py --manifest WORK_DIR/extraction_manifest.json --output-dir WORK_DIR/agent-shards --batch-size 5
```

4. For each assigned PDF, create page-level evidence with the assignment hash:

```bash
python scripts/draft_pdf_record.py SOURCE_PDF --expected-sha256 SHA256 --output DRAFT_JSON
```

   The helper repairs common mojibake path damage, verifies hash-based sibling recovery, and falls back from pypdf to a local-copy PyMuPDF parse. If an external Poppler command hangs, crashes, returns no output, or fails on a network path, stop it and rerun the helper with `--parser pymupdf` or a local-copy fallback before treating the document as unreadable. A routing-grade narrowed extraction may defer detailed schedules, but it must still inspect parser text for policy number, endorsement number, LOB, carrier, named insured, and term before a policy-looking PDF is held.
5. Spawn one subagent per available batch when the calling workflow requires delegation. Each subagent may own a bounded batch but must process sources sequentially.
6. Each subagent writes one JSON record per source to WORK_DIR/agent-shards/<batch-id>/records/<document-id>.json.
   - Subagents must include a short forms-schedule evidence note for each source: pages/sections checked, whether a schedule was found, whether rows were extracted, and whether the schedule was sparse/form-number-only.
   - Subagents must not report "no visible schedule found" until they have searched for common schedule labels and nearby variants such as `Schedule of Forms`, `Forms and Endorsements`, `Endorsements Effective at Inception`, `Forms Attached at Issuance`, `Endorsement Schedule`, `Endt. No.`, `Form No.`, `Form Number`, and carrier-specific declarations pages.
   - When the schedule is sparse, subagents must still return one row per visible form number in `endorsements_exclusions` and `schedules.forms`, using `Not specified` for missing titles/descriptions or edition dates.
7. During delegated or OCR-heavy work, report the active batches and send a concise progress update at least every 60 seconds. Report each completed batch or genuine blocker immediately; do not report final completion while workers remain active.
8. The main agent validates shard records:

```bash
python scripts/validate_agent_shards.py --manifest WORK_DIR/extraction_manifest.json --shards-dir WORK_DIR/agent-shards
```

9. Stage accepted base policies and declarations first, then endorsements serially with `stage_document.py` so endorsement year assignment can use staged base-policy JSON.
10. Build calendar-year JSON outputs only, using the handbook-compatible `documents[]` annual output shape:

```bash
python scripts/build_year_outputs.py --manifest WORK_DIR/extraction_manifest.json --output-dir OUTPUT_DIR
```

11. Validate outputs:

```bash
python scripts/validate_outputs.py --manifest WORK_DIR/extraction_manifest.json --output-dir OUTPUT_DIR
```

## Large Folder Delegation Protocol

Use this protocol when a `raw/` folder or source folder contains more files than can be reliably processed in a single pass.

1. The main agent inventories the folder first, before spawning workers. Identify emails, extracted attachments, policies, endorsements, quotes, binders, schedules, decorative attachments, duplicates, and unsupported files.
2. The main agent groups work into bounded batches by client/account, line of business, policy term, source email thread, carrier, or policy number when those relationships are visible. Prefer smaller batches over large mixed batches; the default batch size is 5 source documents unless the file set is unusually simple.
3. Spawn multiple subagents only after the manifest and batch assignments are created. Each subagent receives one bounded batch and must process only the files assigned to that batch.
4. A subagent may own a batch, but it must still process one source document at a time, write one JSON record or explicit failure for that source, then move to the next source. Do not let a subagent merge several policies, endorsements, or email attachments into a single summary record.
5. Subagents extract and classify; the main agent remains responsible for final decisions. The main agent validates every subagent JSON record, resolves duplicates and conflicts, confirms policy-number and term matching, stages base policies before endorsements, updates annual JSON outputs, and decides final filing/routing.
6. Subagents must not update the annual `YYYY_Policies.json`, policy register, Markdown archive, processing ledger, or final client folder locations unless the calling workflow explicitly assigns that authority. Their normal output is shard JSON plus concise batch notes.
7. The main agent tracks every inventory item to a terminal state: extracted, duplicate, decorative/excluded, unsupported, failed with reason, or held for user review. Do not finish a large-folder run while any worker is still active or any assigned item lacks a terminal status.
8. If the folder contains a large number of `.msg` emails, preserve the relationship between each email and its attachments. Assign email threads and their extracted attachments together when possible so request context, BOR transmittals, policy documents, endorsements, invoices, and follow-up emails are not separated.
## Effective-Year Assignment

- Policy, declaration, quote, binder, or proposal: use the policy or proposed term effective date.
- Endorsement: use the matched base policy's policy effective date for calendar-year assignment; preserve the endorsement effective date separately.
- Cancellation, reinstatement, audit, or similar transaction: use the transaction effective date when stated.
- If the grouping date is missing or the endorsement relationship is not defensible, set `effective_year` to `Not specified`, add a review flag, and do not finalize calendar-year outputs until the item is resolved or assigned to a supportable calendar year.

## Endorsement Matching

Match endorsements using, in order:

1. Exact normalized policy number.
2. Explicit referenced policy term.
3. Named insured.
4. Carrier.
5. Coverage line or policy type.
6. Endorsement number and form references.

Never force a match. Record match confidence, match basis, and conflicts.

## Output Files

Folder mode produces JSON outputs only:

```text
WORK_DIR/
  extraction_manifest.json
  documents/
    doc_000001.json

OUTPUT_DIR/
  2026_Policies.json
```

Calendar-year JSON files are derived directly from staged records and can be rebuilt. The annual output must use a top-level `documents[]` array with `metadata`, preserving every staged record plus legacy-compatible aliases such as `source_path`, `source_page_count`, `searchable_pages_reviewed`, `extraction_notes`, and `term_folder`. Do not collapse records into a thinner nested `policies`/`endorsements` structure unless the user explicitly asks for that alternate shape. Do not create or deliver master or sidecar output files.

## Completion Check

Before delivery, verify:

- every nonduplicate inventory item has a terminal status;
- every assigned item produced exactly one JSON record or an explicit failure;
- every policy-looking PDF with an explicit failure or metadata-only record has documented `pdftotext` or `draft_pdf_record.py` fallback evidence;
- every issued policy, endorsement, declaration, quote, binder, proposal, or other coverage-terms record either contains row-level forms/endorsements/exclusions in `endorsements_exclusions` and `schedules.forms`, or is marked `needs_review` with `MISSING_FORMS_ENDORSEMENTS_SCHEDULE`;
- every complete staged record with an integer `effective_year` appears in the matching annual JSON file under top-level `documents[]` with the full extraction fields and legacy-compatible aliases;
- endorsement years use the matched base policy's effective year while retaining endorsement effective dates;
- OCR repairs were processed in bounded chunks with progress visible between chunks;
- the output directory contains only the intended annual `YYYY_Policies.json` files;
- `validate_outputs.py` exits successfully.





## Legacy Annual-JSON Consolidation

When rebuilding an annual JSON from legacy term-year records, preserve historical assertions without treating uncertain relationships as validated modern data.

1. Retain the prior label in a `legacy_document_type` field or equivalent provenance field.
2. Keep an item classified as an endorsement only when a base-policy relationship is defensible under the endorsement-matching rules.
3. When that relationship cannot be defended, classify the rebuilt item as `other`, preserve its legacy classification, and add a source note explaining the decision.
4. Never force a base-policy match to satisfy validation.
5. Validate the rebuilt annual file before replacing the live annual output.

## Operational-File Exclusion

Before creating extraction assignments or a source manifest, exclude `_Workflow`, `Policy_Register.csv`, `AGENTS.md`, lock files, manifests, and other operational control artifacts. Treat them as workflow metadata, never as policy, quote, or endorsement sources.
