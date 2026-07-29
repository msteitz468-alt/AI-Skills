# Workbook Payload and Layout

## Contents
1. Command
2. Payload schema
3. Worksheet mapping
4. Output rules
5. Example payload

## 1. Command

```bash
python scripts/build_workbook.py --input review_payload.json --output renewal_policy_check.xlsx
```

Add `--include-sources` only when the user requests detailed source references.

## 2. Payload schema

```json
{
  "review": {
    "insured_name": "Required display name",
    "policy_term": "Optional",
    "line_of_business": "Optional",
    "prepared_date": "Optional ISO date or display date",
    "overall_risk": "Optional narrative",
    "alignment": "Optional override: Aligned, Minor Variances, Material Mismatch, Review Incomplete",
    "scope_notes": "Optional"
  },
  "documents": [
    {
      "filename": "Required",
      "role": "submission|quote|bind_order|binder|bind_confirmation|renewal_policy|expiring_policy|endorsement|schedule|other",
      "selected": true,
      "confidence": "High|Medium|Low",
      "carrier": "Optional",
      "policy_term": "Optional",
      "notes": "Optional"
    }
  ],
  "findings": [
    {
      "id": "Optional; generated if omitted",
      "comparison": "quote_vs_policy|submission_vs_quote|renewal_vs_expiring|detailed|missing",
      "category": "Required",
      "item": "Required",
      "submission": "Optional",
      "quote": "Optional",
      "bind_terms": "Optional; preferred when quote was modified",
      "renewal_policy": "Optional",
      "expiring_policy": "Optional",
      "issue": "Required for discrepancies",
      "severity": "Critical|Moderate|Minor|Missing Info",
      "status": "Open|Explained|Accepted|Expected|Verified",
      "action": "Optional",
      "why_it_matters": "Optional for missing items",
      "needed_from": "Optional for missing items",
      "sources": {
        "submission": "Optional filename/page/path",
        "quote": "Optional filename/page/path",
        "policy": "Optional filename/page/path",
        "expiring": "Optional filename/page/path"
      }
    }
  ],
  "immediate_attention": ["Optional explicit alerts"],
  "red_flags": ["Optional explicit smart flags"],
  "notes": ["Optional methodology or scope notes"]
}
```

Use `bind_terms` as the final quote-side value when a bind order, binder, or carrier confirmation modifies the quote. If `bind_terms` is blank, the script uses `quote`.

## 3. Worksheet mapping

### Executive Summary
Show insured, term, line, prepared date, risk narrative, formula-driven severity counts, alignment, Immediate Attention, Red Flag Alerts, and scope notes.

### Quote vs Policy
Include findings with `comparison = quote_vs_policy`.

### Submission vs Quote
Include findings with `comparison = submission_vs_quote`.

### Renewal vs Expiring
Include findings with `comparison = renewal_vs_expiring`.

### Detailed Findings
Include every finding except purely missing/unverifiable rows. This is the master discrepancy list used for severity counts.

### Missing-Unverifiable
Include findings with `comparison = missing` or `severity = Missing Info`.

### Source Index
Include every document classification. Record competing/non-selected quotes as `selected = false`.

## 4. Output rules

- Keep exact worksheet names.
- Use filters, frozen headers, wrapped text, professional widths, hidden gridlines, and severity-based highlighting.
- Leave specific comparison tabs present even when no findings exist; show a single `No discrepancies identified from supplied information` row.
- Do not add detailed source columns unless `--include-sources` is used.
- Keep Critical items visible in Executive Summary Immediate Attention. If the payload omits the list, derive it from open Critical findings.
- Deduplicate alerts while preserving order.

## 5. Example payload

```json
{
  "review": {
    "insured_name": "ABC Company",
    "policy_term": "07/01/2026–07/01/2027",
    "line_of_business": "Commercial General Liability",
    "overall_risk": "The issued policy contains one material quote-to-policy mismatch."
  },
  "documents": [
    {"filename": "ABC Submission.pdf", "role": "submission", "selected": true, "confidence": "High"},
    {"filename": "ABC Final Quote.pdf", "role": "quote", "selected": true, "confidence": "High"},
    {"filename": "ABC Renewal Policy.pdf", "role": "renewal_policy", "selected": true, "confidence": "High"}
  ],
  "findings": [
    {
      "comparison": "quote_vs_policy",
      "category": "Limits & Sublimits",
      "item": "Damage to Premises Rented to You",
      "quote": "$300,000",
      "renewal_policy": "$100,000",
      "issue": "Issued policy limit is lower than the selected final quote.",
      "severity": "Critical",
      "status": "Open",
      "action": "Request corrected endorsement from carrier."
    }
  ],
  "red_flags": ["Coverage reduced at binding"]
}
```
