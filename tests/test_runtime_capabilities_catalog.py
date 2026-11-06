#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Runtime capability catalog metadata tests.

Covers requirement 44 (TEST PLAN — METADATA):
  - runtime capability catalog loads
  - adapter files load
  - runtime IDs unique
  - all adapter runtime references resolve
  - M1 RuntimeAdapter contract validation passes
  - required permission policy is safe

Standard library only. No network.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.domain.contracts import RuntimeAdapter  # noqa: E402

CATALOG_PATH = REPO_ROOT / "catalog" / "runtime-capabilities.yaml"
ADAPTERS_DIR = REPO_ROOT / "runtime-adapters"
CANONICAL_RUNTIME_IDS = ["codex", "opencode", "antigravity", "claude-code", "cursor"]

VALID_INSTRUCTION_FORMATS = {
    "agents-md", "claude-md", "codex-md", "gemini-md", "cursor-md", "custom"
}

DANGEROUS_FLAGS = (
    "--dangerously-skip-permissions",
    "--dangerously-bypass-approvals-and-sandbox",
    "--yolo",
)


def _load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


class TestRuntimeCapabilityCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = _load_catalog()
        cls.runtimes = cls.data.get("runtimes", [])

    def test_catalog_loads_and_has_schema_version(self):
        self.assertEqual(self.data.get("schema_version"), "1.0.0")
        self.assertIsInstance(self.runtimes, list)
        self.assertGreaterEqual(len(self.runtimes), 4)

    def test_catalog_runtime_ids_are_unique(self):
        ids = [rt.get("id") for rt in self.runtimes]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate runtime ids: {ids}")

    def test_catalog_runtime_ids_match_canonical_set(self):
        ids = {rt.get("id") for rt in self.runtimes}
        self.assertEqual(ids, set(CANONICAL_RUNTIME_IDS))

    def test_every_runtime_entry_is_valid_m1_runtime_adapter(self):
        for rt in self.runtimes:
            with self.subTest(runtime=rt.get("id")):
                adapter = RuntimeAdapter.from_dict(rt)
                self.assertEqual(str(adapter.id), rt["id"])
                result = adapter.validate()
                self.assertTrue(result.is_valid, msg=result.errors)

    def test_instruction_format_is_valid_enum(self):
        for rt in self.runtimes:
            with self.subTest(runtime=rt.get("id")):
                self.assertIn(
                    rt.get("instruction_format"), VALID_INSTRUCTION_FORMATS,
                    f"invalid instruction_format for {rt.get('id')}",
                )

    def test_permission_policy_is_safe(self):
        for rt in self.runtimes:
            with self.subTest(runtime=rt.get("id")):
                policy = rt.get("permission_policy", {})
                self.assertIs(policy.get("modifies_global_config"), False)
                self.assertIs(policy.get("requires_explicit_consent"), True)
                enabled = policy.get("dangerous_flags_never_enabled", [])
                for flag in DANGEROUS_FLAGS:
                    self.assertIn(flag, enabled)

    def test_detection_is_metadata_only(self):
        for rt in self.runtimes:
            with self.subTest(runtime=rt.get("id")):
                detection = rt.get("detection", {})
                self.assertIsInstance(detection.get("executables", []), list)
                self.assertIsInstance(detection.get("config_files", []), list)
                self.assertIsInstance(detection.get("environment_variables", []), list)


class TestRuntimeAdapterFiles(unittest.TestCase):
    """Each runtime-adapters/<id>.yaml loads and references a known runtime."""

    @classmethod
    def setUpClass(cls):
        cls.catalog_ids = {rt.get("id") for rt in _load_catalog().get("runtimes", [])}

    def test_adapter_files_exist_for_every_catalog_runtime(self):
        for runtime_id in CANONICAL_RUNTIME_IDS:
            adapter_path = ADAPTERS_DIR / f"{runtime_id}.yaml"
            self.assertTrue(
                adapter_path.exists(), f"missing adapter file: {adapter_path}"
            )

    def test_adapter_loads_and_matches_catalog(self):
        for runtime_id in CANONICAL_RUNTIME_IDS:
            with self.subTest(runtime=runtime_id):
                adapter_path = ADAPTERS_DIR / f"{runtime_id}.yaml"
                with open(adapter_path, "r", encoding="utf-8") as handle:
                    adapter = json.load(handle)
                self.assertEqual(adapter.get("id"), runtime_id)
                self.assertEqual(adapter.get("runtime_id"), runtime_id)
                self.assertIn(adapter.get("runtime_id"), self.catalog_ids)
                self.assertIsInstance(adapter.get("name"), str)
                self.assertTrue(adapter["name"].strip())
                self.assertIn(adapter.get("instruction_format"), VALID_INSTRUCTION_FORMATS)
                # instruction_source: shared consumers consume M4 root AGENTS.md
                # (no owned output); antigravity owns .agent/GEMINI.md.
                source = adapter.get("instruction_source")
                self.assertIsInstance(source, dict)
                self.assertIn(source.get("ownership"), ("shared", "owned"))
                render_block = adapter.get("render", {})
                self.assertIsInstance(render_block.get("outputs"), list)
                if runtime_id == "antigravity":
                    self.assertEqual(len(render_block["outputs"]), 1)
                    output = render_block["outputs"][0]
                    self.assertEqual(output.get("path"), ".agent/GEMINI.md")
                    self.assertTrue(output.get("mark_owned"))
                else:
                    # Shared consumers declare no owned render outputs.
                    self.assertEqual(len(render_block["outputs"]), 0)
                for output in render_block["outputs"]:
                    self.assertIsInstance(output.get("path"), str)
                    self.assertTrue(output["path"])
                    self.assertNotIn("..", Path(output["path"]).parts)
                    self.assertFalse(Path(output["path"]).is_absolute())

    def test_adapter_permission_policy_is_safe(self):
        for runtime_id in CANONICAL_RUNTIME_IDS:
            with self.subTest(runtime=runtime_id):
                with open(ADAPTERS_DIR / f"{runtime_id}.yaml", "r",
                          encoding="utf-8") as handle:
                    adapter = json.load(handle)
                policy = adapter.get("permission_policy", {})
                self.assertIs(policy.get("modifies_global_config"), False)
                self.assertIs(policy.get("requires_explicit_consent"), True)
                enabled = policy.get("dangerous_flags_never_enabled", [])
                for flag in DANGEROUS_FLAGS:
                    self.assertIn(flag, enabled)

    def test_no_duplicate_adapter_runtime_ids(self):
        ids = []
        for adapter_path in ADAPTERS_DIR.glob("*.yaml"):
            with open(adapter_path, "r", encoding="utf-8") as handle:
                adapter = json.load(handle)
            ids.append(adapter.get("id"))
        self.assertEqual(len(ids), len(set(ids)), f"duplicate adapter ids: {ids}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
