# Policy Register Migration - Phase 1

## Contents

1. Purpose and output boundary
2. Source discovery order
3. Required CSV schema
4. Record granularity and deduplication
5. Field extraction rules
6. Normalization and dates
7. Status rules
8. Conflict handling
9. Verification checklist

## 1. Purpose and output boundary

Build the approved routing register that the later `client-folder-workflow` uses to classify and file emails, policies, endorsements, and other insurance documents.

Create only:

```text
<Client Root>/Policy_Register.csv
```

Do not transition the folder structure in this phase. Do not create operational logs, evidence reports, exception files, proposed-update files, or staging folders.

## 2. Source discovery order

### Primary search

Look for a direct child folder whose name is `Markdown`, case-insensitively. Recursively inspect all `.md` and `.json` files inside it.

If one or more supported files exist in `Markdown/`, use only those files for the first build. Do not supplement them with files from elsewhere merely to increase the record count.

### Fallback search

If `Markdown/` is absent or contains no `.md` or `.json` files, recursively search the entire client root for `.md` and `.json` files.

Exclude:

- every directory named exactly `Legacy Files`, case-insensitively and at any depth; prune it before traversal and never hash its contents during default discovery
- `.git`, `.svn`, `.hg`
- `.codex`, `.agents`
- `_Workflow`, `Epic_Attach`
- `node_modules`, virtual environments, caches, temporary and staging folders
- `AGENTS.md`, `SKILL.md`, `codex.md`, and ordinary README files
- generated manifests and the destination `Policy_Register.csv`

## 3. Required CSV schema

Use this exact column order:

```text
client_name
lob
policy_number
normalized_policy_number
carrier
effective_date
expiration_date
policy_term
status
parent_policy_number
notes
```

Write UTF-8 with BOM so the file opens cleanly in Excel.

Unknown descriptive values may be written as `Not specified`. Leave unknown dates blank rather than inserting an invalid date string.

## 4. Record granularity and deduplication

Create one row per distinct policy term.

Use this identity key when enough information is available:

```text
normalized_policy_number + effective_date + expiration_date
```

Rules:

- Combine the base policy and all endorsements into one parent-policy row.
- Do not create a row for each PDF, Markdown heading, JSON document object, layer schedule line, or endorsement.
- A renewal with the same policy number but new effective dates is a separate row.
- Distinct primary and excess policies are separate rows even when they share the same LOB.
- Preserve separate rows for separate policies that intentionally share carrier and dates.
- Remove exact duplicate records caused by the same policy being repeated in several source files.

## 5. Field extraction rules

### `client_name`

Use the most consistently supported client or first named insured. Do not substitute the broker or carrier.

### `lob`

Use a clear commercial-insurance line of business. Prefer established client terminology. Common values include:

```text
AUTO
Cyber
Crime
D&O
DBA
EPL
Fiduciary
FVWC
GL
International
KRE
Media
PKG
PLL
PL
PROP
SURETY
UMB
WC
Other
```

Do not force a value from a weak abbreviation. Use `Not specified` when the source does not establish the LOB.

### `policy_number`

Preserve the supported display format, including meaningful spaces and hyphens. Do not include labels such as `POL#` in the field.

### `normalized_policy_number`

Convert the display number to uppercase and retain only letters and digits.

Examples:

```text
41-LX-013201492-0 -> 41LX0132014920
100 0004492       -> 1000004492
DOC 3431857-01    -> DOC343185701
```

### `carrier`

Use the legal insurer or issuing carrier when available, not the wholesale broker, retailer, program administrator, or agency.

For subscription placements, use the supported lead/subscribing insurer description without inventing a single carrier.

### `effective_date` and `expiration_date`

Use ISO `YYYY-MM-DD`.

Prefer explicit policy dates. An endorsement effective date does not replace the parent policy effective date.

### `policy_term`

Prefer an explicitly supported term. Otherwise derive it from the policy dates using the final two digits of the effective and expiration years:

```text
2025-05-31 to 2026-05-31 -> 25-26
2025-07-01 to 2028-07-01 -> 25-28
```

### `status`

Use:

- `Active` when the run date falls on or after the effective date and before the expiration date.
- `Future` when the run date is before the effective date.
- `Expired` when the run date is on or after the expiration date.
- `Unknown` when dates are insufficient.
- `Review Required` when the row is identifiable but material sources conflict.

### `parent_policy_number`

Leave blank for normal policy rows. Use only when the source explicitly establishes that the row is subordinate to another policy and the relationship is useful for routing. Do not place endorsement parent numbers here because endorsements are merged into the parent row.

### `notes`

Keep notes concise and semicolon-separated. Include:

- source filename or filenames;
- material missing fields;
- conflicts requiring review;
- unusual multi-year, layered, or parent-policy relationships.

Do not copy large policy summaries into this field.

## 6. Normalization and dates

Normalization is deterministic:

```text
normalized = uppercase(policy_number)
normalized = remove every character that is not A-Z or 0-9
```

Validate dates as real calendar dates. Do not infer day and month ordering from an ambiguous numeric date unless surrounding context resolves it.

## 7. Status rules

Calculate status only after dates are normalized. A policy expiring today is `Expired`; the expiration date is not an active coverage day for register status.

When a source explicitly labels a policy cancelled, rescinded, or nonrenewed, preserve that status in `notes`; use `Review Required` if the date-based status alone would be misleading.

## 8. Conflict handling

Use this source priority:

1. Issued policy information and declarations contained in the source record
2. Issued endorsement identifying the parent policy
3. Structured JSON policy record
4. Detailed Markdown policy extraction
5. Policy schedule or register table in Markdown
6. Filename and folder context only as supporting evidence

If lower-priority evidence conflicts with higher-priority evidence, use the higher-priority value and note the discrepancy only when it could affect routing.

If equally credible sources conflict on policy number, LOB, carrier, or dates:

- do not create multiple speculative rows;
- create one `Review Required` row only when the policy identity is still clear;
- otherwise omit the record and report it as skipped.

## 9. Verification checklist

Before completion, confirm:

- only `Policy_Register.csv` was persistently created or changed;
- every source file remains unchanged;
- the CSV contains the exact required headers once each;
- every nonblank policy number has the correct normalized key;
- supplied dates are valid ISO dates;
- each row represents a policy term, not an endorsement or document;
- exact duplicates were removed;
- renewal terms remain separate;
- review-required conflicts are explained in `notes`;
- rows without supportable policy numbers were not created.
