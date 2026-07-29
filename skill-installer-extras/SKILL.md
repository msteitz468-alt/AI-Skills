---
name: skill-installer-extras
description: 'Validate third-party Codex skill installations after download or repository installation. Use alongside the skill-installer skill when an install times out, a destination may be partial, a SKILL.md has encoding or frontmatter issues, or installation success needs confirmation.'
---

# Skill Installer Extras

Verify the installed artifact, not merely the installer exit status.

## Post-Install Check

1. After a timeout or failure, inspect the destination before retrying. Distinguish a complete installed directory from a partial download.
2. Read `SKILL.md` as UTF-8 and validate its frontmatter against the host schema.
3. When safe and user-authorized, move unsupported provenance metadata into an allowed metadata mapping without changing the skill's instructions.
4. Validate the resulting skill folder before treating the installation as complete.
5. Report whether the destination is complete, partial, invalid, or ready to use.
