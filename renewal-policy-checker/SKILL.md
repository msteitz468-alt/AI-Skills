---
name: renewal-policy-checker
description: Review commercial insurance renewals by comparing the client submission, the selected final renewal quote and binding documents, the issued renewal policy, and the expiring policy. Use for policy checking, quote-to-policy audits, renewal discrepancy reviews, silent coverage-change detection, endorsement/form comparisons, exposure schedule validation, or insurer-ready Excel comparison reports. Accept original PDFs, scans, emails, spreadsheets, Word files, and policy-extraction JSON, alone or in combination. Infer document roles from filenames and content, confirm ambiguous classifications or selected quotes, and focus on the placement actually bound rather than competing options.
---

# Renewal Policy Checker

Perform a defensible renewal-policy audit and deliver a professionally formatted Excel workbook. Treat document content as authoritative; do not fill unsupported gaps with general insurance knowledge.

## Workflow

1. Inventory and classify every supplied file.
2. Resolve the selected bound placement and the final intended bind terms.
3. Extract and normalize comparable facts.
4. Compare the documents in the required order.
5. Classify each discrete finding and determine urgency.
6. Build and quality-check the Excel workbook.
7. Summarize the most important results in chat and link the workbook.

Read these references as needed:
- `references/input-normalization.md` for file classification, mixed hard-copy/JSON handling, and ambiguity rules.
- `references/review-protocol.md` for comparison logic, categories, authority rules, and severity.
- `references/workbook-schema.md` before assembling the workbook payload or changing the output layout.

## 1. Inventory and classify files

Infer roles first from filenames and then verify from content. Recognize roles such as submission, quote, bind order, binder, carrier bind confirmation, renewal policy, expiring policy, endorsement, schedule, and supplemental evidence.

Ask the user to confirm only when any of these conditions apply:
- A file cannot be classified confidently.
- More than one quote could be the selected bound quote.
- Binding documents conflict or do not identify the selected carrier/option.
- Multiple policy terms or insureds are mixed together.
- A JSON structure or field meaning is materially ambiguous.

Do not ask for confirmation when filename and content clearly establish the role.

## 2. Resolve the intended bound terms

Focus on the placement actually bound. Do not compare every competing quote or optional alternative unless it is needed to identify the selected placement.

Construct the intended bound terms from:
1. The selected final quote.
2. Explicit negotiated revisions or carrier emails accepted before binding.
3. The bind order.
4. The binder or carrier bind confirmation.

Treat a later explicit binding instruction or carrier confirmation as an override to an earlier quote term. Record the override so the issued policy is compared against the final intended bind terms, not an obsolete option.

Use these concepts consistently:
- **Submission:** client intent and exposure information.
- **Final quote/bind terms:** coverage the parties intended to bind.
- **Issued renewal policy:** legal contract actually issued.
- **Expiring policy:** baseline for renewal changes.

## 3. Extract and normalize

Build a normalized fact set for each relevant line of business. Preserve exact values, qualifiers, form numbers, editions, endorsement titles, and schedule entries.

For original documents:
- Read parsed text and visually inspect rendered pages containing declarations, schedules, tables, forms lists, handwritten selections, or scanned material.
- Verify that referenced forms and endorsements are actually included when possible.
- Distinguish a forms schedule from the actual wording. A listed-but-unavailable form is not fully verified.

For JSON:
- Use the existing schema directly when clear.
- Preserve JSON values and paths during analysis even though source paths are omitted from the default workbook.
- Ask for clarification only when a field is ambiguous or essential information appears structurally missing.

For mixed inputs:
- Use JSON for efficient structured comparison.
- Use original documents to resolve conflicts, validate wording, inspect tables, and confirm forms or endorsements.
- Treat the original issued policy as controlling when it conflicts with an extraction JSON.

## 4. Perform the comparisons

Always perform these comparisons when the corresponding sources are available:

1. **Submission vs Final Quote/Bind Terms**
   - Determine whether requested coverage and submitted exposures were quoted accurately.

2. **Final Quote/Bind Terms vs Issued Renewal Policy** — highest priority
   - Determine whether the legal policy matches what was bound.

3. **Issued Renewal Policy vs Expiring Policy**
   - Identify renewal changes, reductions, new restrictions, retention changes, and lost enhancements.

Compare every applicable category in `references/review-protocol.md`. Split combined issues into separate rows whenever different corrective actions or severities apply.

Never assume a missing item is unchanged. Mark it Missing Info or Unverifiable.

## 5. Classify findings

Apply the severity rules in `references/review-protocol.md` consistently.

Keep severity separate from resolution status:
- A material difference may remain Critical even if it was knowingly accepted.
- Use status values such as `Open`, `Explained`, `Accepted`, `Expected`, or `Verified` to show context.

Use this exact wording when the effect of wording cannot be determined:

> Potential wording discrepancy – requires policy form review

## 6. Build the workbook

Create a normalized JSON payload matching `references/workbook-schema.md`, then run:

```bash
python scripts/build_workbook.py --input review_payload.json --output renewal_policy_check.xlsx
```

Add `--include-sources` only when the user asks for detailed source references.

Use these worksheets:
1. Executive Summary
2. Quote vs Policy
3. Submission vs Quote
4. Renewal vs Expiring
5. Detailed Findings
6. Missing-Unverifiable
7. Source Index

Do not add detailed page/form/JSON-path citations by default. The Source Index should still identify each file, its inferred role, whether it was selected for the bound review, and classification confidence.

## 7. Quality control

Before delivery:
- Reconcile every specific comparison tab to the master Detailed Findings tab.
- Confirm the quote-to-policy tab exists whenever both sources are available.
- Check that all Critical items appear in Immediate Attention on the Executive Summary.
- Check formulas, filters, wrapped text, column widths, freeze panes, and severity formatting.
- Open or render every worksheet and visually inspect for clipping, unreadable rows, broken formulas, or empty required sections.
- Confirm the output contains no unsupported assumptions.

## Required behavior for incomplete reviews

Do not abandon the review because a source is missing. Complete all supported comparisons, list each gap in Missing-Unverifiable, explain why it matters, and identify what document or clarification is needed.

If the selected final quote or renewal policy cannot be identified, pause before making the workbook and ask the user to confirm the correct file.
