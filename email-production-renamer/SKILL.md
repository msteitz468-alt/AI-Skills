---
name: email-production-renamer
description: rename email production files into a standardized insurance-production naming convention and folder structure. use when the user provides or references a folder of outlook .msg files, or related .eml/.txt email exports, and wants codex/chatgpt to extract email metadata, apply ai judgment to identify client, sender, subject summary, policy number, and move/rename the emails into a completed folder organized by client and policy/account.
---

# Email Production Renamer

## Purpose

Rename a folder of email production files, primarily Outlook `.msg` files, into a consistent filesystem-safe naming convention while preserving the original email content. Move the renamed files into a `completed` folder organized by client and policy number.

Use scripts for efficient extraction and file operations, but use AI judgment to decide the final client, description, and policy number when the evidence is ambiguous.

## Required Deliverable

Create a folder named `completed` containing only the moved/renamed email files in this structure:

```text
completed/
  <CLIENT NAME or none>/
    <POLICY NUMBER or Account>/
      YYYYMMDD HHMM - CLIENT NAME - f. SenderInitial. SenderLastName - BriefDescription[, Iteration#][ - POL# PolicyNumber].msg
```

Do not create a rename log unless the user specifically asks for one.

## Standard Filename Format

```text
YYYYMMDD HHMM - CLIENT NAME - f. SenderFirstInitial. SenderLastName - BriefDescription, POL# PolicyNumber
```

Rules:
- Include `- POL# <PolicyNumber>` only when a policy number is actually identified.
- If no policy number is identified, omit the policy segment entirely and place the file under the `Account` subfolder.
- Keep filenames safe for Windows and macOS. Remove or replace `<>:"/\\|?*`, control characters, trailing periods, and trailing spaces.
- Preserve the original extension, usually `.msg`.
- Move/rename the original files into `completed`; do not copy unless the user requests copy-only behavior.

## Metadata Rules

### Timestamp

Use the email's internal timestamp and always convert the output timestamp to Pacific Time.

Preference order:
1. `.msg` delivery time / received time.
2. `.msg` sent time.
3. `.eml` `Date` header.
4. Extracted date-like metadata from `.txt` exports.
5. `00000000 0000` if no reliable timestamp is available.

Format as `YYYYMMDD HHMM` using a 24-hour clock. Do not include a colon between hour and minute.

### Client Name

Read the email subject and body to identify the client. Use AI judgment; do not rely only on regex. Insurance account names are often apparent from signatures, subject lines, forwarded headers, attached-file names, or repeated account references.

If no client is observable, use exactly:

```text
none
```

Use the same client string in both the filename and folder path. Sanitize it for folders and filenames.

### Sender

Use the sender's first initial and last name only.

Format:

```text
f. J. Smith
```

Preference order:
1. Sender display name.
2. Sender email local part.
3. `Unknown` if still not inferable.

If a sender is an organization or mailbox and no person is clear, use the most human-readable mailbox identity available, or `Unknown`.

### BriefDescription

Create a brief human-readable description from the cleaned subject and, when useful, body context.

Clean subject prefixes before forming the description:
- Remove repeated prefixes such as `RE:`, `FW:`, `FWD:`, `WG:`, `TR:`, and equivalents regardless of case.
- Remove external/system tags such as `_EXTERNAL_`, `[EXTERNAL]`, `[EXT]`, and similar bracketed security markers.
- Remove leading separators left behind by prefix cleanup.

Keep the description concise, normally under about 80 characters. If trimming is necessary, end with `...` before sanitizing. Do not include slashes, colons, or other invalid filename characters.

### Policy Number

Use AI judgment to identify policy numbers from subject and body. Often the correct number is obvious from nearby words such as `policy`, `pol`, `policy #`, `policy no.`, `quote`, or line-of-business context.

Helpful patterns:
- 2-6 letters followed by 5-12 digits, for example `PAC1100385`.
- Long numeric-only strings of 7-12 digits when they clearly function as a policy number.

Prefer a policy number from the subject over the body if both are plausible. Do not force a weak match. If no policy number is available, omit the `POL#` segment and route to the `Account` subfolder.

### Iteration / Duplicate Handling

The timestamp usually resolves duplicates. Only add iteration markers when two or more emails would otherwise produce the same filename or when they have the exact same date/time stamp and otherwise indistinguishable naming components.

Append iteration in the BriefDescription segment:

```text
BriefDescription, 1
BriefDescription, 2
```

Use stable ordering, such as source filename sort order, so repeated runs produce consistent results.

## Workflow

1. Inspect the input folder and identify email files. Prioritize `.msg`; also handle `.eml` and `.txt` exports when present.
2. Run `scripts/extract_email_metadata.py` to produce structured metadata and body snippets for AI review. For `.msg`, use Aspose.Email FOSS as the primary decoder; the helper may use `extract_msg` only as a compatibility fallback. The helper is intentionally extraction-focused, not the final naming authority.
3. Review the extracted subject, body preview, sender, recipients, and timestamps with AI judgment.
4. Decide final `client`, `sender`, `brief_description`, `policy_number`, and Pacific timestamp for each file.
5. Compute destination path:
   - `completed/<client>/<policy_number>/` when policy number exists.
   - `completed/<client>/Account/` when no policy number exists.
6. Move/rename each source file into its destination folder.
7. After moving, verify that every source email file is present under `completed` exactly once and that no filename contains invalid filesystem characters.

## Recommended Codex Implementation Pattern

When implementing the operation in Codex:

- Use the bundled extraction helper to parse `.msg` efficiently and emit JSON for model review.
- Decode `.msg` with `aspose-email-foss` first. This path must not start Outlook or use COM. If Aspose cannot open a specific message, allow the bundled helper to try `extract_msg` and record the decoder plus the Aspose failure in `warnings`.
- Do not use Outlook COM for ordinary `.msg` processing. Treat COM as an explicitly requested last-resort diagnostic only after both standalone decoders fail.
- Isolate subject, sender, recipient, timestamp, body, validation, and attachment reads. A failure reading one property must produce a property-specific warning and preserve every successfully extracted field.
- Read all needed properties and attachments before closing the decoder object.
- Use Python's `email` package for `.eml` files.
- Use plain text parsing for `.txt` exports.
- Keep extraction separate from final naming decisions. The extraction helper should expose enough evidence for AI to decide, not hide everything behind rigid regexes.
- Use a second small move/rename routine after AI decisions are finalized.
- Do not edit email contents.

## Bundled Script

Use `scripts/extract_email_metadata.py` as a starter extraction helper. It scans an input folder and writes JSON to stdout containing:

- source path and extension
- source SHA-256 and the `.msg` decoder used
- subject
- sender display/email
- sent/received timestamp candidates
- Pacific-normalized timestamp when available
- body preview
- possible policy-number candidates
- attachment names, hashes, sizes, MIME types, and optional staged paths
- extraction warnings

Example:

```bash
python scripts/extract_email_metadata.py /path/to/email-folder > extracted_emails.json
```

To extract `.msg` attachments losslessly into a staging directory while collecting metadata:

```bash
python scripts/extract_email_metadata.py /path/to/email-folder --attachments-dir /path/to/staging/attachments > extracted_emails.json
```

The script may require:

```bash
python -m pip install --user aspose-email-foss
```

`extract-msg` is optional and used only as a fallback for an individual `.msg` that Aspose cannot decode.

After reading `extracted_emails.json`, make final AI-reviewed rename decisions and perform the move into `completed`.

## Quality Checks

Before final delivery:

- Confirm `completed` exists.
- Confirm every input `.msg`, `.eml`, and `.txt` email file has been moved into `completed` or explicitly flagged as unreadable.
- Confirm the folder structure uses client folders and policy/account subfolders.
- Confirm timestamps are Pacific Time.
- Confirm partially readable messages retain their successful metadata fields and carry property-specific warnings.
- Confirm each `.msg` record identifies `aspose-email-foss` as the decoder, or clearly records why the `extract-msg` fallback was used.
- When attachments were requested, confirm each staged attachment hash matches the bytes reported in the extraction JSON.
- Confirm filenames contain no forbidden Windows/macOS filename characters.
- Confirm no log file was created unless requested.
