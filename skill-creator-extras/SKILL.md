---
name: skill-creator-extras
description: Encoding-safe companion for the built-in skill-creator. Use alongside skill-creator when creating, updating, normalizing, or validating SKILL.md files that may contain a UTF-8 BOM, non-ASCII punctuation, or invalid text encoding.
---

# Skill Creator Extras

**Internal skill:** This companion is maintained in the user's global Codex skill library.

Extend the built-in `skill-creator` with deterministic encoding checks. Continue to use `skill-creator` for design, structure, metadata, and general validation rules.

## Encoding workflow

1. Generate and edit `SKILL.md` as UTF-8 without a byte-order mark.
2. Before delivery, run:

   ```bash
   python scripts/validate_skill_encoding.py <skill-directory>
   ```

3. If the validator reports a UTF-8 BOM, normalize the file and validate again:

   ```bash
   python scripts/validate_skill_encoding.py <skill-directory> --normalize
   ```

4. Run the built-in `skill-creator` validator after the encoding check passes:

   ```bash
   python <skill-creator>/scripts/quick_validate.py <skill-directory>
   ```

## Required behavior

- Read `SKILL.md` with UTF-8 BOM awareness.
- Treat non-ASCII punctuation as valid UTF-8.
- Report invalid UTF-8 as a concise validation error; do not expose a decoding traceback.
- Normalize only when `--normalize` is explicitly supplied.
- Write normalized content as UTF-8 without a BOM and preserve the decoded text exactly.
- Re-run validation after normalization.
