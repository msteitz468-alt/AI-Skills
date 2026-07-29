# Input Classification and Normalization

## Contents
1. Classification order
2. Filename signals
3. Content verification
4. Selected-placement resolution
5. JSON handling
6. Mixed-source conflict rules
7. Clarification triggers

## 1. Classification order

Classify each file using this sequence:

1. Filename signals.
2. Document title and first-page labels.
3. Carrier, insured, policy term, and policy number.
4. Internal evidence such as quote conditions, binding language, declarations, or form schedules.
5. Cross-document consistency.

Assign a confidence level:
- **High:** filename and content agree.
- **Medium:** content establishes the role but filename is generic.
- **Low:** role is inferred from context or conflicting indicators.

## 2. Filename signals

Treat these terms as strong but not conclusive signals.

### Submission / client intent
`submission`, `application`, `renewal app`, `supplemental`, `risk assessment`, `renewal summary`, `SOV`, `TIV`, `exposure`, `schedule`, `loss data`

### Quote
`quote`, `proposal`, `indication`, `renewal terms`, `carrier response`, `option`, `pricing`

### Binding evidence
`bind order`, `binder`, `bind confirmation`, `coverage confirmation`, `bound`, `subjectivities`, `final terms`

### Renewal policy
`policy`, `issued policy`, `renewal policy`, `POL`, policy number plus current renewal term

### Expiring policy
`expiring`, `prior term`, `current policy`, `last year`, prior policy term, earlier effective dates

### Endorsement or supplemental policy document
`endorsement`, `endt`, `form`, `schedule`, `declarations`, `dec`, `jacket`

## 3. Content verification

Verify role by content:
- A quote generally proposes terms, premium, conditions, subjectivities, options, and a validity period.
- A bind order directs placement and identifies selected terms or options.
- A binder or bind confirmation evidences temporary/final placement before full policy issuance.
- An issued policy contains declarations, policy number, effective dates, forms/endorsements, and contract wording.
- An expiring policy has the prior term and is used only as the baseline unless renewed unchanged by explicit evidence.
- A submission contains client-provided exposures, applications, schedules, requested limits, and coverage intent.

Do not classify a proposal as the selected quote merely because it is the most recent file. Establish that it matches the bound carrier, term, policy, premium, option, or binding evidence.

## 4. Selected-placement resolution

When multiple quotes or options are present:

1. Match the issued policy carrier and policy term.
2. Match premium, limits, deductible, and selected option.
3. Review bind order, binder, and final carrier confirmation.
4. Use explicit accepted revisions as overrides.
5. Mark all non-selected quotes/options as `Not selected` in Source Index.

If two plausible selected quotes remain, ask the user to confirm before comparing.

## 5. JSON handling

Accept one combined JSON or separate JSON files by document role.

Normalize equivalent concepts without changing meaning, including:
- insured / named_insured / entities
- effective_date / inception / policy_period
- limit / sublimit / aggregate / occurrence
- deductible / retention / SIR
- forms / endorsements / exclusions
- locations / vehicles / drivers / equipment / payroll / sales / receipts
- premium / taxes / fees / total_cost

Retain the original JSON path internally for traceability. Do not place paths in the workbook unless detailed sourcing is requested.

Ask for clarification when:
- The same field name appears to have different meanings.
- The JSON does not identify its document role or policy term.
- A summarized value conflicts with its detailed schedule.
- A field essential to a Critical comparison is truncated or null without explanation.

## 6. Mixed-source conflict rules

Use this precedence for factual conflicts:

1. Original issued document over extraction JSON.
2. Explicit final binding instruction/confirmation over an earlier quote.
3. Actual form wording over a forms list or summary.
4. Detailed schedule over a high-level total, while flagging the internal inconsistency.
5. Client-approved final submission over an earlier draft.

Do not silently overwrite conflicts. Record the conflict as a finding when it affects the review.

## 7. Clarification triggers

Ask a concise question only when the answer changes the comparison basis, such as:
- Which quote/option was bound?
- Is this policy current renewal or expiring?
- Does this bind-order email amend the quote?
- Is this JSON a complete extraction or a partial summary?
- Are two named insured spellings different entities or a clerical variation?

Otherwise proceed and place uncertainty in Missing-Unverifiable.
