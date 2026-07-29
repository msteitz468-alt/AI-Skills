---
name: spreadsheets-extras
description: 'Protect established Excel workbooks during structured edits and appended rows. Use alongside the spreadsheet skill when updating an existing workbook, table, tracker, or formatted template with formulas, validation, conditional formatting, or existing date storage.'
---

# Spreadsheet Editing Extras

Use this guidance with the spreadsheet skill when changing an established workbook. Preserve its working behavior, not just its visible layout.

## Map Before Writing

1. Inspect the target sheet's headers and create an explicit header-to-column map before writing values.
2. Compare a populated peer or representative row to identify formula columns, styles, number formats, validation, conditional formatting, row height, and wrap conventions.
3. Write only to mapped input fields. Preserve formulas, non-target columns, sheet dimensions, and existing rules.

## Preserve Stored Values

1. Inspect a representative existing value and number format before editing dates, numbers, or formulas.
2. When a workbook uses Excel serial dates, preserve serial-date storage for new or changed dates; do not assume runtime date objects are compatible.
3. Reopen the saved workbook and scan representative values and formulas for errors such as `#VALUE!`.

## Append Rows Completely

After adding table rows, verify separately that the table range, cell formatting, wrap, fonts, row heights, date formats, conditional-format ranges, and data-validation ranges include the new rows. Apply missing cell-level formats or explicitly extend the relevant rules; do not assume a table append inherited them.

## Verify Before Delivery

Reopen and render the workbook. Check representative edited and appended rows, dropdown controls, formula columns, and unchanged non-target sheets.
