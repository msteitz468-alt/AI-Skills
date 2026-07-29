# Commercial Lines File Naming and Folder Structure Standard

## Purpose

Use this standard to keep client files consistent, searchable, and easy to audit. File names should clearly identify the policy term, insured/client name, line of business, policy number, effective date, and document type or description.

The permanent folder schema in this document matches `client-folder-workflow` so cleanup and raw-ingestion produce the same client-root structure.

## General File Naming Rules

Use this clean general standard whenever possible:

```text
YY-YY [Client Name] - [LOB] Pol# [Policy#] - Eff MM.DD.YY - [Document Type / Description]
```

Example:

```text
25-26 ABC Company - GL Pol# ABC123 - Eff 07.01.25 - Policy
```

Field guidance:

- `YY-YY` = policy term year, such as `25-26`.
- `[Client Name]` = insured/client name as it should appear in the file name.
- `[LOB]` = line of business abbreviation, such as `GL`, `PROP`, `PKG`, `WC`, `UMB`, `AUTO`, `D&O`, `EPL`, `Fiduciary`, or `GL/UMB`.
- `Pol# [Policy#]` = policy number. Omit this segment only when no policy number applies.
- `Eff MM.DD.YY` = effective date of the policy, endorsement, agreement, or document. Use dots for Windows filenames.
- `[Document Type / Description]` = short, specific description of the document.

### Management Liability Naming

For management-liability programs, do not use `PL` as a catch-all LOB when the document can be identified as D&O, EPL, Fiduciary, Side A, DIC, or Side A DIC. File actual policies under the specific line: `D&O`, `EPL`, or `Fiduciary`. Use `Management Liability` only for combined program summaries, schematics, loss runs, correspondence, or account-level materials that cover several management-liability lines. Keep `PL` only for true professional-liability/E&O placements supported by the source.

Policy filenames for D&O, EPL, and Fiduciary towers should include layer position and attachment/limit wording when available:

```text
YY-YY [Client Name] - D&O - Primary - $10M Agg Pol# [Policy#] - Eff MM.DD.YY - Policy
YY-YY [Client Name] - D&O - 2nd Excess - $10M xs $20M Pol# [Policy#] - Eff MM.DD.YY - Policy
YY-YY [Client Name] - EPL - Primary - $5M EPL - $6M Agg Pol# [Policy#] - Eff MM.DD.YY - Policy
YY-YY [Client Name] - Fiduciary - 1st Excess - $5M xs $5M Pol# [Policy#] - Eff MM.DD.YY - Policy
```

If the document identifies Side A, DIC, or Side A DIC, include that wording in the layer segment, for example `D&O - Side A DIC - $10M xs $40M`.

## Folder Structure

Use the same legacy-style client-root filing model as `client-folder-workflow`. Create only the folders needed for the current files. Permanent filing families live directly under the client root by document family, year, and LOB/category—not under a per-LOB root with category subfolders.

```text
<Client Root>\
|-- Account\
|   `-- <YYYY>\
|       `-- <account category, when supported>\
|-- Applications\
|   `-- <YYYY>\
|       `-- <LOB>\
|-- Broker of Record Info\
|-- Loss Runs\
|   `-- <YYYY>\
|-- Stewardship\
|   `-- <YYYY>\
|-- Policies\
|   `-- <YYYY>\
|       `-- <LOB>\
|-- Quotes\
|   `-- <YYYY>\
|       |-- Quote Proposal\
|       `-- <LOB>\
|           `-- <Carrier>\
`-- Schedules\
    `-- <YYYY>\
```

When present for workflow-controlled clients, the following control folders may also sit at the client root and are not permanent filing destinations for ordinary cleanup:

```text
raw\
Epic_Attach\
_Workflow\
Markdown\
```

Do not invent a parallel per-LOB policy-root tree (for example `GL/2026/Policy - End - Summary`) for new work. Preserve an existing client structure when it already follows this standard. Do not create parallel duplicate structures with slightly different names (for example both `Schedules` and `SPECS`).

### Folder rules

- `Policies/<YYYY>/<LOB>`: Issued policies, endorsements, binders, certificates, audits, accounting, and policy-specific correspondence, using the policy effective year. Retain a document-category subfolder only when an existing client structure has one or it is needed to prevent a supported collision; do not recreate a universal category tree under each LOB.
- `Applications/<YYYY>/<LOB>`: Applications, carrier submissions, SOVs, TIVs, underwriting packets, and submission support, using the proposed effective or represented submission year.
- `Schedules/<YYYY>`: Files whose filenames contain `schedule` or `specs` (case-insensitive), using the supported policy term when available, otherwise the effective or represented year. Prefer `Schedules` over a parallel `SPECS` folder for new work.
- `Loss Runs/<YYYY>`: Loss-run packages and claim-history pulls, using the year the loss run was pulled, valued, or generated—not the policy effective year. If the pulled year is not supportable, do not guess.
- `Quotes/<YYYY>/<LOB>/<Carrier>`: Quotes, indications, terms, proposals, comparisons, and quote summaries, using proposed effective year or represented quote year, then LOB, then carrier. If carrier is not supportable, hold for review rather than inventing a carrier folder.
- `Quotes/<YYYY>/Quote Proposal/`: Client-facing quote proposal presentations and companion workbooks that summarize multiple lines or markets. Do not route these by every coverage line or carrier summarized inside them.
- `Account/<YYYY>`: Account-level materials with no reliable single policy owner (multi-line invoices, premium allocations, finance agreements, record-of-insurance materials, surplus-lines records, corporate financials, transition plans).
- `Account/<YYYY>/<category>`: Optional category under Account when supported (for example accounting, surplus-lines, record-of-insurance, multi-line).
- `Broker of Record Info`: Dedicated root family for broker-of-record materials. Do not route BOR items into a policy folder.
- `Stewardship/<YYYY>`: Stewardship reports, renewal strategy, program reviews, and related account-management deliverables.
- `Markdown`, `raw`, `Epic_Attach`, and `_Workflow` are workflow-control or knowledge folders managed by `client-folder-workflow`. During folder-file-maintenance cleanup, do not move permanent documents into them unless the user explicitly asks.

### LOB folder names

Use standardized LOB display names for destination folders, such as `Auto`, `Cyber`, `Crime`, `D&O`, `EPL`, `Fiduciary`, `GL`, `International`, `KRE`, `Package`, `Pollution`, `Prof. Liab`, `Property`, `Management Liability`, `Umbrella-Excess`, or `WC`. For client-facing quote/proposal destinations, render `AUTO` as `Auto` and `PKG` as `Package`.

For management-liability placements, do not use `PL` as a catch-all LOB folder. File Directors & Officers as `D&O`, Employment Practices Liability as `EPL`, and Fiduciary Liability as `Fiduciary`. Reserve `Management Liability` only for combined/multi-line materials that truly span more than one of those coverages. Use `Prof. Liab` (or `Prof. Liab-E&O` when that is the existing client convention) only for true Professional Liability / E&O placements.

## Naming by Document Type

Policies:

```text
YY-YY [Client Name] - LOB Pol# [Policy#] - Eff MM.DD.YY - Policy
```

Endorsements:

```text
YY-YY [Client Name] - LOB Pol# [Policy#] - Eff MM.DD.YY - Endt [#] [Description]
```

Applications and submissions:

```text
YY-YY [Client Name] - LOB Submission - [Carrier or Status]
```

Audits:

```text
YY-YY [Client Name] - LOB Pol# [Policy#] - Eff MM.DD.YY - Audit
```

Brokerage services agreements:

```text
YY-YY [Client Name] - BSA - Eff MM.DD.YY
```

Schedules and specs:

```text
YYYY [Client Name] - [LOB if known] - Schedule [Description]
```

Permanent documents:

```text
[Client Name] - Permanent - [Document Description]
```

Carrier quote (file under `Quotes/<YYYY>/<LOB>/<Carrier>/`):

```text
YY-YY [Client Name] - [LOB] - Quote - [Carrier-Option if applicable] - MM.DD.YY
```

Multi-line client-facing quote proposal (file under `Quotes/<YYYY>/Quote Proposal/`):

```text
YY-YY [Client Name] - Quote Proposal - MM.DD.YY
```

Binder:

```text
YY-YY [Client Name] - GL Pol# ABC123 - Eff MM.DD.YY - Binder
```

Bind order:

```text
YY-YY [Client Name] - GL - Eff MM.DD.YY - Bind Order to Travelers
```

Accounting or invoice:

```text
YY-YY [Client Name] - GL Pol# ABC123 - Eff MM.DD.YY - Invoice
```

Certificate:

```text
YY-YY [Client Name] - GL Pol# ABC123 - Eff MM.DD.YY - Cert - Certificate Holder
```

Carrier correspondence:

```text
YY-YY [Client Name] - GL/UMB - Travelers Correspondence - Quote Subjectivities
```

Client or internal correspondence:

```text
YY-YY [Client Name] - GL/UMB - Client Email - Renewal Updates
```

## Best Practices

- Keep file names concise but specific enough to identify the document without opening it.
- Use consistent separators: `-` between major sections.
- Use standard LOB abbreviations consistently.
- Include the client name in every file name unless the enclosing system already displays it and the team has approved omission.
- Include the policy number when available.
- Include the effective date when tied to a policy term, endorsement, binder, invoice, audit, or agreement.
- For endorsements, include endorsement number and short change description.
- For correspondence, include party and subject, such as `Travelers Correspondence - Quote Subjectivities` or `Client Email - Renewal Updates`.
- Avoid vague descriptions such as `document`, `scan`, `email`, `policy final`, or `attachment`.
- Do not use filesystem-problem characters: `*`, `?`, `:`, `<`, `>`, `|`, quotation marks, or slashes.


