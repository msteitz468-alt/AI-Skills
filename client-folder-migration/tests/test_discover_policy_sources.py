from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "discover_policy_sources.py"
)
SPEC = importlib.util.spec_from_file_location("discover_policy_sources", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
discover_policy_sources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discover_policy_sources)


class DiscoverPolicySourcesTests(unittest.TestCase):
    def test_collect_under_prunes_legacy_files_before_descent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            safe = root / "visible.json"
            safe.write_text("{}", encoding="utf-8")
            protected = root / "Legacy Files"
            protected.mkdir()
            (protected / "hidden.json").write_text("{}", encoding="utf-8")
            nested_protected = root / "year" / "LEGACY FILES"
            nested_protected.mkdir(parents=True)
            (nested_protected / "also-hidden.md").write_text("hidden", encoding="utf-8")

            visited: list[Path] = []
            real_walk = os.walk

            def recording_walk(*args, **kwargs):
                for current, dirs, files in real_walk(*args, **kwargs):
                    visited.append(Path(current))
                    yield current, dirs, files

            with patch.object(discover_policy_sources.os, "walk", recording_walk):
                sources = discover_policy_sources.collect_under(root, root)

            self.assertEqual([safe], sources)
            self.assertFalse(
                any(
                    part.casefold() == "legacy files"
                    for current in visited
                    for part in current.relative_to(root).parts
                )
            )

    def test_main_never_hashes_sources_below_legacy_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            visible = root / "visible.json"
            visible.write_text("{}", encoding="utf-8")
            protected = root / "legacy files"
            protected.mkdir()
            (protected / "hidden.json").write_text("{}", encoding="utf-8")
            hashed: list[Path] = []

            def fake_sha256(path: Path) -> str:
                self.assertNotIn("legacy files", {part.casefold() for part in path.parts})
                hashed.append(path)
                return "0" * 64

            stdout = io.StringIO()
            with (
                patch.object(discover_policy_sources, "sha256", fake_sha256),
                patch.object(sys, "argv", [str(SCRIPT_PATH), str(root)]),
                redirect_stdout(stdout),
            ):
                result = discover_policy_sources.main()

            manifest = json.loads(stdout.getvalue())
            self.assertEqual(0, result)
            self.assertEqual([visible], hashed)
            self.assertEqual(
                ["visible.json"],
                [item["relative_path"] for item in manifest["sources"]],
            )

    def test_direct_collection_of_protected_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "Legacy Files"
            protected.mkdir()
            (protected / "hidden.md").write_text("hidden", encoding="utf-8")

            with patch.object(
                discover_policy_sources.os,
                "walk",
                side_effect=AssertionError("protected directory was traversed"),
            ):
                sources = discover_policy_sources.collect_under(protected, root)

            self.assertEqual([], sources)


if __name__ == "__main__":
    unittest.main()