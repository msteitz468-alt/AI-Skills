# Insurance Extraction Fields

This field set is based on `H:\AI Workflow\Policy_Extraction_Workflow.md`. Use `Not specified` for missing information. Do not store full document text in JSON.

## Annual Handbook-Compatible Fields

When building annual client policy JSON, preserve enough information to reproduce the older handbook extraction files. The annual file must include top-level `documents[]`, and every document record must carry the extracted document information, coverage data, locations, forms/endorsements/exclusions, schedules, source page/page-count evidence, review flags, extraction notes, and policy-term folder alias when available.

## Document Information

For each document extract:

- Document name, exact filename
- Source relative path
- Source SHA-256
- Page count, when available
- Client
- Named insureds
- Locations
- Policy number
- Policy type
- Policy effective date
- Policy expiration date
- Broker/agency, if listed
- Endorsements and exclusions
- Source page references for material values

## Coverage Detection

Identify each coverage section separately. Common coverage lines include:

- Commercial General Liability
- Commercial Property
- Farm Property
- Farm Liability
- Business Personal Property (BPP)
- Commercial Auto
- Umbrella / Excess
- Workers Compensation
- Cyber
- Pollution Liability
- Inland Marine
- Crime
- Employee Benefits
- Other stated coverages

## For Each Coverage Line

### Insurer Information

- Insurer
- NAIC, if available
- AM Best rating, required when current web/source context is available
- AM Best financial size category, when available
- Rating source and verification date

### Policy Information

- Policy effective date
- Policy expiration date
- Endorsements

## Premiums

Extract all available premium information. Use `Not specified` when missing.

Examples:

- Coverage premium
- Commercial auto premium
- Commercial property premium
- Total policy premium
- Taxes, fees, and surcharges when shown

Component premiums when listed:

- Auto: liability, UM/UIM, medical payments, comprehensive, collision
- Property: building, BPP, equipment, inland marine, mobile equipment

## Limits

Extract all limits individually.

Examples:

- General Liability: each occurrence, general aggregate, products/completed operations, personal and advertising injury, damage to rented premises, medical payments
- Property: building, BPP, equipment, mobile equipment, inland marine, scheduled property
- Auto: liability, UM/UIM, medical payments, physical damage

## Sublimits

Extract all sublimits individually with:

- Coverage
- Sublimit
- Description or applies-to detail
- Amount, if stated
- Source pages

Common examples:

- Property: debris removal, pollutant cleanup, fungi/bacteria, outdoor property, electronic data, accounts receivable, valuable papers, property off premises, property in transit
- Liability: fire legal liability, medical payments, fungi/bacteria
- Auto: medical payments, rental reimbursement, towing/labor

## Deductibles and SIRs

Extract every deductible or SIR structure with:

- Coverage
- Deductible type
- Amount
- Percentage, if any
- Applies to
- Basis, if stated
- Source pages

Common examples:

- Property: AOP/main, wind/hail, named storm, mobile equipment, business income and extra expense, earthquake
- Property category deductibles: building, BPP, mobile equipment, scheduled equipment, transit
- Auto: collision, comprehensive, vehicle-specific

## Valuation Method

Extract valuation type where stated:

- Replacement Cost
- Actual Cash Value
- Agreed Value
- Stated Amount

## Endorsements, Exclusions, and Forms

This section is mandatory for every issued policy, endorsement, declaration, quote, binder, proposal, or other document with coverage terms. Do not treat forms and endorsements as optional summary text.

Extract every row from any Schedule of Forms, Schedule of Endorsements, Policy Forms and Endorsements, Applicable Forms, Notices, Exclusions, Amendatory Endorsements, or similar form listing. Include all forms, exclusions, state amendatory endorsements, mandatory endorsements, advisory notices, notices to policyholders, coverage forms, and policy jacket/common policy forms.

For each listed row, capture:

- Coverage or policy part, when stated
- Form number exactly as shown
- Endorsement, exclusion, notice, or form title
- Edition date, when listed
- Effective date, when different and listed
- Form type: `endorsement`, `exclusion`, `coverage_form`, `notice`, `advisory_notice`, or `other`
- Source pages

Write the same row-level listing in both `endorsements_exclusions` and `schedules.forms` unless a legacy output shape requires one location; in that case preserve all row details in the available field and add a `source_notes` entry explaining the mapping.

If the document has no visible form/endorsement schedule, do not leave this silently blank. Add review flag `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` with the pages or sections checked, and add a `source_notes` entry stating that no schedule of forms, endorsements, exclusions, or notices was found.

## Exposures

Extract exposures when listed:

- Gross sales
- Payroll / payroll by class code/state
- Vehicle count
- Property values
- Equipment values
- Acreage
- Employee count
- Other stated rating bases

## Schedule Extraction

Extract rows for these schedules when present.

### Endorsement/Form Schedule

- Form number
- Title or description
- Edition date
- Coverage
- Form type
- Source pages

### Vehicle Schedule

- Vehicle/unit number
- VIN
- Year
- Make
- Model
- Value
- Deductible
- Coverage

### Equipment Schedule

- Equipment/item number
- Serial/VIN
- Description
- Value
- Deductible
- Coverage

### Property Schedule

- Location
- Property type
- Description
- Limit
- Deductible
- Valuation

### Location Schedule

- Location number
- Building number, when listed
- Address

## Review and Conflicts

- Never invent data.
- Record conflicting values instead of silently choosing one.
- Add review flags for unreadable pages/regions, missing effective dates, unmatched endorsements, unverified AM Best ratings, incomplete schedules, and conflicts.
