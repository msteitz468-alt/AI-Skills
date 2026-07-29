# JSON Document Record Specification

Create one JSON object per source file. Use valid UTF-8 JSON. Use the exact string `Not specified` for unavailable scalar values and an empty list when a repeated field is unavailable or not applicable.

Do not include full source text in JSON. Preserve source identity, source pages for material values, and extracted coverage data.

## Required Top-Level Shape

```json
{
  "document_id": "doc_000001",
  "source": {
    "exact_filename": "Example Policy.pdf",
    "relative_path": "Example Policy.pdf",
    "sha256": "Not specified",
    "page_count": 10
  },
  "document_type": "policy",
  "document_name": "Example Policy.pdf",
  "client": "Example Client",
  "named_insureds": [],
  "locations": [],
  "policy_number": "ABC123",
  "policy_type": "Commercial Package",
  "policy_effective_date": "2026-07-01",
  "policy_expiration_date": "2027-07-01",
  "endorsement_effective_date": "Not specified",
  "transaction_effective_date": "Not specified",
  "effective_year": 2026,
  "base_policy_reference": {
    "policy_number": "Not specified",
    "policy_term": "Not specified",
    "matched_document_id": "Not specified",
    "base_policy_effective_date": "Not specified",
    "match_confidence": "unmatched",
    "match_basis": [],
    "conflicts": []
  },
  "broker_agency": "Not specified",
  "coverage_lines": [],
  "coverages": [],
  "premiums": [],
  "limits": [],
  "sublimits": [],
  "deductibles": [],
  "valuation_methods": [],
  "endorsements_exclusions": [],
  "exposures": [],
  "schedules": {
    "locations": [],
    "vehicles": [],
    "equipment": [],
    "properties": [],
    "forms": [],
    "other": []
  },
  "review_flags": [],
  "source_notes": [],
  "extraction": {
    "status": "complete",
    "completed_at": "2026-07-22T00:00:00Z",
    "method": "document review",
    "confidence": "high"
  }
}
```

## Document Types

Use one of:

- `policy`
- `endorsement`
- `declaration`
- `quote`
- `binder`
- `proposal`
- `cancellation`
- `reinstatement`
- `audit`
- `notice`
- `other`

## Repeated Field Objects

### Location

```json
{
  "location_number": "0001",
  "building_number": "0001",
  "address": "123 Main St, Fresno, CA",
  "source_pages": [3]
}
```

### Coverage

```json
{
  "coverage": "Commercial General Liability",
  "insurer": "Example Insurance Company",
  "naic": "12345",
  "am_best_rating": "A++ (Superior)",
  "financial_size_category": "XV",
  "rating_source": "https://ratings.ambest.com/...",
  "rating_as_of_date": "2026-07-22",
  "policy_effective_date": "2026-07-01",
  "policy_expiration_date": "2027-07-01",
  "premium": "$10,000",
  "limits": [],
  "sublimits": [],
  "deductibles": [],
  "endorsements": [],
  "source_pages": [1]
}
```

### Premium

```json
{
  "coverage": "Commercial Auto",
  "component": "Liability",
  "amount": "$10,000",
  "source_pages": [3]
}
```

### Limit

```json
{
  "coverage": "Commercial General Liability",
  "name": "Each Occurrence",
  "amount": "$1,000,000",
  "description": "Not specified",
  "source_pages": [2]
}
```

### Sublimit

```json
{
  "coverage": "Commercial Property",
  "sublimit": "Debris Removal",
  "description": "Additional coverage",
  "amount": "$25,000",
  "source_pages": [4]
}
```

### Deductible

```json
{
  "coverage": "Commercial Property",
  "deductible_type": "AOP",
  "amount": "$5,000",
  "percentage": "Not specified",
  "applies_to": "Building + BPP",
  "basis": "Per occurrence",
  "source_pages": [4]
}
```

### Valuation Method

```json
{
  "coverage": "Commercial Property",
  "property_or_item": "Building",
  "valuation": "Replacement Cost",
  "source_pages": [5]
}
```

### Endorsement or Exclusion

```json
{
  "coverage": "Commercial General Liability",
  "form_number": "CG 00 01",
  "title": "Commercial General Liability Coverage Form",
  "edition_date": "04/13",
  "effective_date": "Not specified",
  "form_type": "coverage_form",
  "source_pages": [6]
}
```

For issued policies, endorsements, declarations, quotes, binders, proposals, and other documents with coverage terms, `endorsements_exclusions` is a mandatory extraction area. It must contain every listed form, endorsement, exclusion, notice, advisory notice, coverage form, policy jacket form, and amendatory endorsement from the source document's form schedule or equivalent listing.

If the source document does not show a form/endorsement schedule, leave `endorsements_exclusions` as an empty list only when `review_flags` includes `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` and `source_notes` identifies the pages or sections checked. A record with coverage terms must not be marked `complete` while this list is empty and the absence is unexplained.

Sparse schedules still count as schedules. If the source lists only form numbers, endorsement numbers, or abbreviated rows with no titles/descriptions, create one row per visible form number and use `Not specified` for missing titles, edition dates, coverage/policy part, or form type. Do not collapse sparse schedules into a summary row. Do not mark the schedule missing merely because descriptions are absent.

### Exposure

```json
{
  "coverage": "Commercial General Liability",
  "basis": "Gross sales",
  "value": "$1,000,000",
  "class_code": "Not specified",
  "state": "CA",
  "source_pages": [7]
}
```

### Schedule Rows

Use these arrays under `schedules`:

- `locations`: location/building/address rows.
- `vehicles`: vehicle, VIN, year, make, model, value, deductible, coverage.
- `equipment`: equipment/item number, serial/VIN, description, value, deductible, coverage.
- `properties`: location, property type, description, limit, deductible, valuation.
- `forms`: form number, title/description, edition date, coverage, form type, and source pages. Mirror the row-level Schedule of Forms and Endorsements listing here when available; keep it synchronized with `endorsements_exclusions`.
- `other`: any other material schedule row.

## Effective Year

- Policy/declaration/quote/binder/proposal: use `policy_effective_date`.
- Endorsement: use matched base policy effective date and preserve `endorsement_effective_date` separately.
- Cancellation/reinstatement/audit/transaction: use `transaction_effective_date`.
- If unresolved, set `effective_year` to `Not specified` and add a review flag.

## Review Flags

Each flag should be actionable:

```json
{
  "code": "UNVERIFIED_AM_BEST",
  "message": "AM Best rating could not be verified from available sources.",
  "source_pages": []
}
```

Common codes:

- `MISSING_EFFECTIVE_DATE`
- `CONFLICTING_EFFECTIVE_DATES`
- `UNMATCHED_ENDORSEMENT`
- `BASE_POLICY_NOT_STAGED`
- `UNVERIFIED_AM_BEST`
- `UNREADABLE_PAGE`
- `INCOMPLETE_SCHEDULE`
- `SPARSE_FORMS_SCHEDULE`
- `FORM_TITLES_NOT_SPECIFIED`
- `CONFLICTING_VALUES`

## Annual Output Shape

Annual client files must be handbook-compatible and preserve the same information as the older term-year files such as `26-27 Allegiant Policies.json`.

Use this shape for rebuilt calendar-year outputs:

```json
{
  "documents": [],
  "metadata": {
    "calendar_year": 2026,
    "generated_at": "2026-07-22T00:00:00Z",
    "source_manifest": "extraction_manifest.json",
    "document_count": 1,
    "output_shape": "legacy_documents_v1"
  }
}
```

Each item in `documents` must preserve the full staged JSON record and must also include these legacy-compatible aliases when available:

- `document_name`
- `source_path`
- `source_sha256`
- `source_page_count`
- `searchable_pages_reviewed`
- `source_text_excerpt` using `Not specified` when no excerpt is intentionally retained
- `extraction_notes`
- `term_folder`
- `client`
- `named_insureds`
- `locations`
- `policy_number`
- `policy_type`
- `document_type`
- `policy_effective_date`
- `policy_expiration_date`
- `broker_agency`
- `coverages`
- `review_flags`

Do not replace this with the thinner nested `policies`, `endorsements`, and `other_documents` structure unless the user explicitly asks for that alternate output. The annual output is allowed to contain additional modern fields from the staged record, but it must not omit the older handbook-consumable fields above.



