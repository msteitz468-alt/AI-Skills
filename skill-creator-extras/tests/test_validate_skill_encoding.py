from __future__ import annotations

import codecs
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_skill_encoding.py"


def run_validator(skill_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_dir), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_skill(skill_dir: Path, payload: bytes) -> None:
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_bytes(payload)


class EncodingValidatorTests(unittest.TestCase):
    def test_accepts_bom_and_non_ascii_punctuation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            skill_dir = Path(folder) / "bom-skill"
            text = "---\nname: bom-skill\ndescription: It\u2019s valid.\n---\n"
            write_skill(skill_dir, codecs.BOM_UTF8 + text.encode("utf-8"))

            result = run_validator(skill_dir)

            self.assertEqual(result.returncode, 0)
            self.assertIn("VALID with UTF-8 BOM", result.stdout)

    def test_normalize_removes_only_the_bom(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            skill_dir = Path(folder) / "normalize-skill"
            text = "---\nname: normalize-skill\ndescription: Caf\u00e9 \u2014 valid.\n---\n"
            write_skill(skill_dir, codecs.BOM_UTF8 + text.encode("utf-8"))

            result = run_validator(skill_dir, "--normalize")

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                (skill_dir / "SKILL.md").read_bytes(),
                text.encode("utf-8"),
            )

    def test_invalid_utf8_is_an_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            skill_dir = Path(folder) / "invalid-skill"
            payload = b"---\nname: invalid-skill\ndescription: bad \x96 byte\n---\n"
            write_skill(skill_dir, payload)

            result = run_validator(skill_dir)

            self.assertEqual(result.returncode, 3)
            self.assertIn("invalid UTF-8 at byte", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
