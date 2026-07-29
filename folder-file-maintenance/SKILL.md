---
name: folder-file-maintenance
description: >
  Organize and clean up client file folders using commercial insurance naming
  standards and the same legacy-style permanent folder schema as
  client-folder-workflow (Account, Applications, Policies, Quotes, Schedules,
  Loss Runs, Stewardship, Broker of Record Info). Use when Codex needs to
  inventory, rename, move, or audit policy, binder, endorsement, certificate,
  application, submission, quote, invoice, audit, loss run, carrier
  correspondence, client email, BOR, surety, schedule, specs, or account
  transition files into a consistent folder structure.
---

# Folder File Maintenance

Use this skill to clean up commercial insurance account folders without losing auditability.

## Root `Legacy Files` Protection

When the selected account or client root contains a folder named exactly `Legacy Files` at its top level, treat that folder as a preserved archive. Do not inventory, read, hash, copy, move, rename, delete, classify, route, or audit-log individual files inside `<client-root>/Legacy Files/` unless the user specifically asks to process that folder by name. This is distinct from ordinary legacy year, LOB, category, or holding folders elsewhere in the cleanup scope, which may still provide routing context.


## Workflow

1. Read any local project instructions first, especially `codex.md`, `README`, or cleanup notes.
2. Inventory files before moving anything. Use path-safe enumeration when Windows path lengths are long.
3. Classify files by line of business, policy year, root document family, and document category using filenames, current folders, spreadsheets, summaries, and readable document metadata. Treat the current folder path as a strong routing clue when it reflects a legacy year, LOB, root document-family, or document-category filing system.
4. Create the target folder structure only as needed.
5. Dry-run the proposed destinations and sample every policy-term pattern before applying moves. Reject term matches embedded inside document dates and require plausible consecutive renewal years.
6. Rename and move high-confidence files first. When the user asks to make sure everything is filed correctly or otherwise authorizes cleanup, use the file's current destination/legacy folder context to route otherwise ambiguous files instead of leaving them behind solely because the filename is generic.
7. Keep an audit log such as `cleanup-move-log.csv` with source and destination paths.
8. After moving, run a final inventory for files outside the target structure and report remaining temp, system, duplicate, or uncertain files. If year-named or legacy folders should be retired, verify they are recursively file-free before removing empty folders.

## Commercial Lines Standard

Read `references/commercial-lines-standard.md` when organizing commercial insurance files or when the user asks to apply the file naming and folder structure standard.

Use Windows-safe filenames. Replace `/` in effective dates with dots, for example `Eff 04.15.26`, because `/` is not valid inside Windows filenames.

Avoid deleting files during cleanup unless the user explicitly asks. Leave `Thumbs.db`, Office lock files beginning with `~$`, and other system/temp artifacts alone unless deletion is specifically requested.

## Classification Guidance

Use the existing folder path as strong evidence, not a weak hint, when the path appears to represent an intentional legacy filing scheme such as year folders, LOB folders, policy folders, quote folders, application folders, loss run folders, surplus-lines folders, or named account subfolders. If a file lives in a legacy folder whose year, LOB, or document category is clear, use that current destination to route the file into the corresponding standard folder unless stronger evidence in the filename, document text, policy register, or existing target structure contradicts it. Do not leave files behind solely because their filenames are generic when their current folder gives reliable classification context.

Determine policy term separately from document date. Prefer explicit `YY-YY` tokens, four-digit renewal ranges, or supported policy effective/expiration dates. Reject any `YY-YY` match embedded inside an `MM-DD-YY` or `MM.DD.YY` date, such as the `10-15` fragment in `3-10-15`. Require plausible consecutive years, and do not interpret `6-25-26` as a `25-26` policy term.

Use the same permanent folder schema as `client-folder-workflow` (see `references/commercial-lines-standard.md`). Root filing families take precedence over LOB placement: filenames containing `schedule` or `specs` route to `Schedules/<YYYY>` based on supported policy term, effective year, or represented year; loss runs route to `Loss Runs/<YYYY>` based on pulled/valued/generated year; quotes, indications, terms, proposals, comparisons, and quote summaries route to `Quotes/<YYYY>/<LOB>/<Carrier>`; multi-line client-facing quote proposals route to `Quotes/<YYYY>/Quote Proposal/`. Do not guess missing year, LOB, or carrier evidence. Do not create the former per-LOB policy-root category tree (`GL/2026/Policy - End - Summary`, etc.) for new work.

Common LOB destination folders include `Auto`, `Cyber`, `Crime`, `D&O`, `EPL`, `Fiduciary`, `GL`, `International`, `KRE`, `Package`, `Pollution`, `Prof. Liab`, `Property`, `Management Liability`, `Umbrella-Excess`, `Surety`, and `WC`. Use `D&O`, `EPL`, and `Fiduciary` as separate LOBs when management-liability records can be separated by coverage part. Use `Management Liability` only for combined program summaries, schematics, correspondence, loss runs, or other account-level items that materially cover several management-liability lines. Use `Prof. Liab` / `PL` only for a true professional-liability/E&O placement when the source evidence supports that line; do not use `PL` as a generic bucket for D&O, EPL, or Fiduciary policies.

Management-liability policy filenames must expose the tower position and liability range when available. Use the specific LOB plus layer and attachment wording, such as `D&O - Primary - $10M Agg`, `D&O - 2nd Excess - $10M xs $20M`, `EPL - Primary - $5M EPL - $6M Agg`, or `Fiduciary - 1st Excess - $5M xs $5M`. If the source identifies Side A, DIC, or Side A DIC coverage, include that label explicitly in the layer text. Do not let an old filename containing `PL` override policy text, register notes, or JSON that distinguishes D&O, EPL, Fiduciary, Side A, DIC, primary, excess, limits, or attachment.

### Current Location Routing

When a client folder already has meaningful filing structure, use current placement as an explicit classification source:

- Legacy year folders such as `2024` usually indicate the renewal term starting in that year unless the filename or policy register shows a different term.
- Legacy category folders such as `Applications`, `Policies`, `Endorsements`, `Surplus Lines`, `Invoices`, and `Certificates` map into the standard root families: policies/endorsements/binders/certificates/audits/accounting into `Policies/<YYYY>/<LOB>`; applications/SOVs/TIVs into `Applications/<YYYY>/<LOB>`; surplus-lines and multi-line accounting into `Account/<YYYY>/<category>` when no single policy owns them.
- Root families already named `Quotes`, `Loss Runs`, `Schedules`, `Account`, `Applications`, `Policies`, `Stewardship`, and `Broker of Record Info` should be preserved and normalized to the standard schema when year/LOB/carrier evidence is supportable. Prefer `Schedules` over a parallel `SPECS` tree.
- Legacy LOB-root trees such as `Auto/2025/Policy - End - Summary` or `GL/2026/Accounting` should be collapsed into `Policies/<YYYY>/<LOB>` (or the appropriate root family) using the year and LOB from the path when filename evidence is sparse.
- Legacy LOB subfolders such as `Auto`, `GL`, `Property`, `Umbrella`, `Pollution`, `Seedman's E&O`, `Management Liability`, `Workers Compensation`, `Travel`, or carrier/policy folders should drive LOB classification when filename evidence is sparse.
- Account-level or multi-line folders such as `Pre-Renewal Discussions`, named DBA/sub-entity folders, financial statements, premium comparisons, and record-of-insurance files should route to `Account/<YYYY>` or `Account/<YYYY>/<category>` when no single LOB owns the document. Route BOR materials to root `Broker of Record Info`. Route stewardship/program-review materials to `Stewardship/<YYYY>`.
- Do not invent destinations under `raw/`, `Epic_Attach/`, `_Workflow/`, or `Markdown/` during ordinary cleanup unless the user explicitly asks.
- If current-folder logic conflicts with a clear policy number, policy register entry, or document text, prefer the stronger source and record the conflict in the audit log.

For folder-context moves, keep an audit log that records the source path, destination path, and the folder-context reason. After filing, verify that legacy year or holding folders are recursively file-free. Only remove empty folders when the user asks for cleanup or has authorized removal.

Common high-confidence mappings:

- Policies, endorsements, binders, summaries, notices, mod worksheets: `Policies/<YYYY>/<LOB>`
- Certificates, COIs, cert holder lists, evidence, ID cards: `Policies/<YYYY>/<LOB>`
- Premium audits, claims reports, IBNR reports, audit worksheets: `Policies/<YYYY>/<LOB>`
- Invoices, fee agreements, payment plans, LOC materials tied to a policy: `Policies/<YYYY>/<LOB>`; multi-line or unowned accounting: `Account/<YYYY>/<category>`
- Applications, SOVs, TIVs, underwriting packets: `Applications/<YYYY>/<LOB>`
- Schedules/specs: `Schedules/<YYYY>`
- Loss runs: `Loss Runs/<YYYY>`
- Quotes, terms, indications, comparisons: `Quotes/<YYYY>/<LOB>/<Carrier>`
- Multi-line client-facing quote proposals and companion workbooks: `Quotes/<YYYY>/Quote Proposal/`
- BOR letters and broker-of-record packages: `Broker of Record Info`
- Stewardship reports, renewal strategy, program reviews: `Stewardship/<YYYY>`
- Carrier/underwriter correspondence tied to a policy: `Policies/<YYYY>/<LOB>`; multi-line or unowned account correspondence: `Account/<YYYY>`
- Client/internal emails, meeting notes, transition plans with no reliable policy owner: `Account/<YYYY>` (or leave in place / hold for review when email retention rules apply)

## Safety Rules

Preserve extensions and do not infer policy numbers when unsupported. If a policy number is unknown, omit the `Pol#` segment rather than inventing one.

Prefer shorter names when Windows path length may be an issue, while keeping term, client, LOB, policy number if known, effective date if known, and document description.

Use deterministic collision handling. If a destination exists and the files are not confirmed duplicates, append ` (2)`, ` (3)`, etc.





