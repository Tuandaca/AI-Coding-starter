#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M8: V1 -> V2 safe migration tests.

Covers M8 acceptance criteria:

  * Detection: clean V1, GEMINI-only, CONTEXT-only, non-V1, already-migrated
    V2, partial V2 state, side-effect-free detection.
  * Confirmation / dry-run: dry run writes nothing, apply without confirmation
    writes nothing, confirmation defaults to NO.
  * Non-destructive: legacy files byte-identical after migration; only
    .ai-coding-starter/ is written.
  * Canonical validity: project.yaml / state.yaml / resources.lock round trips.
  * Provenance honesty: matched resources use bundled M7 provenance, unknown
    resources are absent from the lock, no fabricated commit SHAs.
  * Collision safety: same id, different type coexist as separate lock entries.
  * Secrets / paths: secrets and absolute developer paths are not persisted.
  * Rollback: removing .ai-coding-starter/ restores V1 behavior.
  * Idempotence: a second run reports already-migrated and writes nothing new.
  * Failure safety: no confirmation means no partial lock on disk.
  * Offline: core/migration.py uses no network modules.

Standard library only (unittest, json, pathlib, tempfile, shutil, hashlib, re).
No network. Fixtures under tests/fixtures/v1_* are copied into temp dirs before
any mutation, so fixtures stay pristine.
"""
import hashlib
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.migration import (  # noqa: E402
    BUNDLED_LICENSE,
    BUNDLED_PROVENANCE_COMMIT_SHA,
    CANONICAL_STATE_DIR,
    PROJECT_YAML,
    RESOURCES_LOCK,
    STATE_YAML,
    analyze_v1_project,
    apply_plan,
    build_migration_plan,
    detect_v1_project,
    rollback_migration,
)
from core.spec import read_project_spec  # noqa: E402
from core.state import read_resources_lock, read_state  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
CANON = CANONICAL_STATE_DIR
SHA40 = re.compile(r"^[a-f0-9]{40}$")
ZERO_SHA = "0" * 40
CANON_FILES = (PROJECT_YAML, STATE_YAML, RESOURCES_LOCK)


def _snapshot(root: Path) -> dict:
    """Hash every file under ``root``, keyed by posix-relative path."""
    root = Path(root)
    snap = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            snap[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return snap


class MigrationTestBase(unittest.TestCase):
    """Base class that copies a fixture into a fresh temp dir per test."""

    def copy_fixture(self, name: str) -> Path:
        src = FIXTURES / name
        self.assertTrue(src.is_dir(), f"missing fixture: {src}")
        dst = Path(tempfile.mkdtemp(prefix=f"m8-{name}-")) / name
        shutil.copytree(src, dst)
        self.addCleanup(shutil.rmtree, dst.parent, ignore_errors=True)
        return dst

    def _migrate(self, root: Path):
        detection = detect_v1_project(root)
        analysis = analyze_v1_project(root, detection)
        plan = build_migration_plan(root, analysis)
        result = apply_plan(plan, confirmed=True)
        return detection, analysis, plan, result


class TestMigrationDetection(MigrationTestBase):
    """Detection must be read-only and report V1 / V2 / partial states."""

    def test_detects_clean_v1_project(self):
        root = self.copy_fixture("v1_clean")
        detection = detect_v1_project(root)

        self.assertTrue(detection.is_v1_project)
        self.assertEqual(detection.confidence, "high")
        self.assertFalse(detection.already_migrated)
        self.assertFalse(detection.partial_v2_state)
        self.assertFalse(detection.existing_canonical_state)
        self.assertIn(".agent/ directory present", detection.signals)
        self.assertIn("GEMINI.md present", detection.signals)
        self.assertIn("CONTEXT.md present", detection.signals)
        self.assertTrue(detection.v1_signals["agent_dir"])

    def test_detects_v1_by_gemini_only(self):
        dst = Path(tempfile.mkdtemp(prefix="m8-gemini-only-"))
        self.addCleanup(shutil.rmtree, dst, ignore_errors=True)
        (dst / "GEMINI.md").write_text(
            "# GEMINI.md\n\nOnly a GEMINI.md legacy marker.\n",
            encoding="utf-8",
        )
        detection = detect_v1_project(dst)

        self.assertTrue(detection.is_v1_project)
        self.assertEqual(detection.confidence, "medium")
        self.assertIn("GEMINI.md present", detection.signals)
        self.assertFalse(detection.already_migrated)

    def test_detects_v1_by_context_only(self):
        dst = Path(tempfile.mkdtemp(prefix="m8-context-only-"))
        self.addCleanup(shutil.rmtree, dst, ignore_errors=True)
        (dst / "CONTEXT.md").write_text(
            "# CONTEXT.md\nPhase: planning\nFocus: anything\n",
            encoding="utf-8",
        )
        detection = detect_v1_project(dst)

        self.assertTrue(detection.is_v1_project)
        self.assertEqual(detection.confidence, "medium")
        self.assertFalse(detection.already_migrated)

    def test_non_v1_not_detected(self):
        root = self.copy_fixture("non_v1")
        detection = detect_v1_project(root)

        self.assertFalse(detection.is_v1_project)
        self.assertEqual(detection.confidence, "none")
        self.assertFalse(detection.already_migrated)
        self.assertFalse(detection.partial_v2_state)
        self.assertEqual(detection.signals, [])
        self.assertEqual(detection.reasons[-1], "no V1 legacy markers detected")

    def test_v2_already_migrated(self):
        root = self.copy_fixture("v2_migrated")
        detection = detect_v1_project(root)

        self.assertTrue(detection.already_migrated)
        self.assertFalse(detection.is_v1_project)
        self.assertFalse(detection.partial_v2_state)
        self.assertTrue(detection.existing_canonical_state)

    def test_partial_v2_fails_safely(self):
        root = self.copy_fixture("v2_partial")
        detection = detect_v1_project(root)

        self.assertTrue(detection.partial_v2_state)
        self.assertFalse(detection.is_v1_project)
        self.assertFalse(detection.already_migrated)
        self.assertFalse(detection.existing_canonical_state)
        self.assertIn("partial V2 state", detection.reasons[-1])

    def test_detection_side_effect_free(self):
        root = self.copy_fixture("v1_clean")
        before = _snapshot(root)
        detect_v1_project(root)
        after = _snapshot(root)
        self.assertEqual(before, after)


class TestMigrationConfirmation(MigrationTestBase):
    """No filesystem writes happen without explicit confirmation."""

    def test_dry_run_writes_nothing(self):
        root = self.copy_fixture("v1_clean")
        before = _snapshot(root)
        detection = detect_v1_project(root)
        analysis = analyze_v1_project(root, detection)
        plan = build_migration_plan(root, analysis, dry_run=True)
        result = apply_plan(plan, confirmed=True)

        self.assertTrue(plan.dry_run)
        self.assertEqual(result.created_files, [])
        self.assertFalse((root / CANON).exists())
        self.assertEqual(before, _snapshot(root))

    def test_apply_without_confirmation_no_writes(self):
        root = self.copy_fixture("v1_clean")
        before = _snapshot(root)
        detection = detect_v1_project(root)
        analysis = analyze_v1_project(root, detection)
        plan = build_migration_plan(root, analysis)
        result = apply_plan(plan)  # confirmed defaults to False

        self.assertFalse(result.confirmed)
        self.assertFalse(result.applied)
        self.assertEqual(result.created_files, [])
        self.assertEqual(result.errors, [])
        self.assertFalse((root / CANON).exists())
        self.assertEqual(before, _snapshot(root))

    def test_confirmation_default_no(self):
        root = self.copy_fixture("v1_clean")
        detection = detect_v1_project(root)
        analysis = analyze_v1_project(root, detection)
        plan = build_migration_plan(root, analysis)
        result = apply_plan(plan)

        self.assertFalse(result.confirmed)
        self.assertFalse(result.applied)
        self.assertEqual(result.created_files, [])


class TestMigrationNonDestructive(MigrationTestBase):
    """Legacy files are never modified; only .ai-coding-starter/ is written."""

    def test_legacy_files_byte_identical_after_migration(self):
        root = self.copy_fixture("v1_edited_md")
        before = _snapshot(root)
        detection, analysis, plan, result = self._migrate(root)

        self.assertTrue(result.applied)
        self.assertTrue((root / CANON).is_dir())
        after = _snapshot(root)

        # Every legacy (non-canonical) file must be byte-identical.
        legacy_before = {
            k: v for k, v in before.items() if not k.startswith(CANON + "/")
        }
        legacy_after = {
            k: v for k, v in after.items() if not k.startswith(CANON + "/")
        }
        self.assertEqual(legacy_before, legacy_after)
        self.assertTrue((root / "GEMINI.md").exists())
        self.assertTrue((root / "CONTEXT.md").exists())
        self.assertTrue((root / ".agent" / "agents" / "project-planner.md").exists())
        self.assertTrue((root / "src" / "main.py").exists())

    def test_only_ai_coding_starter_written(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)

        self.assertTrue(result.applied)
        for created in result.created_files:
            self.assertIn(
                CANON,
                Path(created).parts,
                f"migration wrote outside .ai-coding-starter/: {created}",
            )
        written = sorted(
            p.name for p in (root / CANON).iterdir() if p.is_file()
        )
        self.assertEqual(written, sorted(CANON_FILES))


class TestMigrationCanonicalValidity(MigrationTestBase):
    """Migrated canonical documents must round-trip through their readers."""

    def test_migrated_project_spec_valid_round_trip(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)

        path = root / CANON / PROJECT_YAML
        spec_back = read_project_spec(path)
        self.assertEqual(spec_back.to_dict(), plan.spec.to_dict())
        self.assertEqual(spec_back.schema_version, "1.0.0")

    def test_migrated_state_valid_round_trip(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)

        path = root / CANON / STATE_YAML
        state_back = read_state(path)
        self.assertEqual(state_back.to_dict(), plan.state.to_dict())
        self.assertEqual(state_back.schema_version, "1.0.0")

    def test_migrated_lock_valid_round_trip(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)

        path = root / CANON / RESOURCES_LOCK
        lock_back = read_resources_lock(path)
        self.assertEqual(lock_back.to_dict(), plan.lock.to_dict())
        self.assertEqual(lock_back.schema_version, "1.0.0")


class TestMigrationProvenance(MigrationTestBase):
    """Provenance must be honest (M7 rules): bundled or absent, never fake."""

    def test_known_resource_uses_m7_provenance(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)

        matches = [
            r
            for r in plan.lock.resources
            if r.id == "project-planner" and r.type == "agent"
        ]
        self.assertTrue(matches, "project-planner agent should be locked")
        res = matches[0]
        self.assertEqual(res.provenance.source, "bundled")
        self.assertEqual(res.provenance.commit_sha, BUNDLED_PROVENANCE_COMMIT_SHA)
        self.assertRegex(res.provenance.commit_sha, SHA40)
        self.assertEqual(res.provenance.license, BUNDLED_LICENSE)
        self.assertEqual(res.selection_reason, "migrated_from_v1_legacy")

    def test_unknown_resource_not_in_lock(self):
        root = self.copy_fixture("v1_unknown_resource")
        detection, analysis, plan, result = self._migrate(root)

        locked = [(r.id, r.type) for r in plan.lock.resources]
        self.assertNotIn(("unknown-custom-agent", "agent"), locked)
        # The unknown legacy resource is preserved physically on disk.
        self.assertTrue(
            (root / ".agent" / "agents" / "unknown-custom-agent.md").exists()
        )

    def test_no_fabricated_provenance(self):
        for fixture in ("v1_clean", "v1_same_id_diff_type"):
            root = self.copy_fixture(fixture)
            detection, analysis, plan, result = self._migrate(root)
            for res in plan.lock.resources:
                self.assertRegex(
                    res.provenance.commit_sha,
                    SHA40,
                    f"invalid commit_sha for {res.type}:{res.id} in {fixture}",
                )
                self.assertNotEqual(
                    res.provenance.commit_sha,
                    ZERO_SHA,
                    f"all-zeros commit_sha for {res.type}:{res.id} in {fixture}",
                )
                self.assertEqual(res.provenance.source, "bundled")


class TestMigrationCollisionSafety(MigrationTestBase):
    """Same id, different type must be collision-safe ((type, id) identity)."""

    def test_same_id_different_type_both_in_lock(self):
        root = self.copy_fixture("v1_same_id_diff_type")
        detection, analysis, plan, result = self._migrate(root)

        entries = {(r.type, r.id) for r in plan.lock.resources}
        self.assertIn(("agent", "security-auditor"), entries)
        self.assertIn(("skill", "security-auditor"), entries)
        self.assertEqual(
            [r.id for r in plan.lock.resources].count("security-auditor"), 2
        )


class TestMigrationSecretsAndPaths(MigrationTestBase):
    """Secrets and absolute developer paths must not reach canonical state."""

    def test_secrets_not_migrated(self):
        root = self.copy_fixture("v1_secrets")
        detection, analysis, plan, result = self._migrate(root)

        canonical = "".join(
            (root / CANON / fname).read_text(encoding="utf-8")
            for fname in CANON_FILES
        ).lower()
        self.assertNotIn("api_key", canonical)
        self.assertNotIn("password", canonical)
        self.assertNotIn("connection_string", canonical)

        # The legacy file still contains the secret (preserved, never scanned
        # into canonical state).
        legacy = (root / "GEMINI.md").read_text(encoding="utf-8").lower()
        self.assertIn("api_key", legacy)
        self.assertIn("password", legacy)

    def test_absolute_paths_not_persisted(self):
        root = self.copy_fixture("v1_absolutepath")
        detection, analysis, plan, result = self._migrate(root)

        canonical = "".join(
            (root / CANON / fname).read_text(encoding="utf-8")
            for fname in CANON_FILES
        )
        self.assertNotIn("D:\\", canonical)
        self.assertNotIn("C:\\", canonical)
        self.assertIsNone(re.search(r"[A-Z]:\\", canonical))


class TestMigrationRollback(MigrationTestBase):
    """Rollback removes .ai-coding-starter/ and leaves V1 files intact."""

    def test_rollback_restores_v1(self):
        root = self.copy_fixture("v1_clean")
        before = _snapshot(root)
        self._migrate(root)
        self.assertTrue((root / CANON).is_dir())

        rollback = rollback_migration(root)
        self.assertTrue(rollback.applied)
        self.assertFalse((root / CANON).exists())

        after = _snapshot(root)
        self.assertEqual(before, after)
        self.assertTrue((root / "GEMINI.md").exists())
        self.assertTrue((root / "CONTEXT.md").exists())
        self.assertTrue((root / "src" / "main.py").exists())
        self.assertTrue((root / ".agent" / "agents" / "project-planner.md").exists())


class TestMigrationIdempotence(MigrationTestBase):
    """A second migration run reports already-migrated and writes nothing."""

    def test_idempotent_second_run_reports_already_migrated(self):
        root = self.copy_fixture("v1_clean")
        detection, analysis, plan, result = self._migrate(root)
        self.assertTrue(result.applied)

        # Re-detection sees canonical state: already migrated, not a V1 project.
        redetect = detect_v1_project(root)
        self.assertTrue(redetect.already_migrated)
        self.assertFalse(redetect.is_v1_project)

        # Second apply creates no new files.
        canon_before = _snapshot(root / CANON)
        second_analysis = analyze_v1_project(root, redetect)
        second_plan = build_migration_plan(root, second_analysis)
        result2 = apply_plan(second_plan, confirmed=True)

        self.assertFalse(result2.applied)
        self.assertEqual(result2.created_files, [])
        self.assertEqual(canon_before, _snapshot(root / CANON))


class TestMigrationFailureSafety(MigrationTestBase):
    """Failure paths must not leave a partial lock on disk."""

    def test_failure_no_partial_lock(self):
        root = self.copy_fixture("v1_clean")
        detection = detect_v1_project(root)
        analysis = analyze_v1_project(root, detection)
        plan = build_migration_plan(root, analysis)
        result = apply_plan(plan)  # no confirmation

        self.assertFalse(result.confirmed)
        self.assertFalse(result.applied)
        self.assertEqual(result.created_files, [])
        self.assertFalse((root / CANON).exists())


class TestMigrationOffline(MigrationTestBase):
    """Migration must be fully offline (no network modules)."""

    def test_no_network_in_migration(self):
        migration_source = (
            REPO_ROOT / "core" / "migration.py"
        ).read_text(encoding="utf-8")
        for token in (
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "http.client",
            "urlopen",
            "subprocess",
        ):
            self.assertNotIn(
                token,
                migration_source,
                f"core/migration.py must not use network module {token!r}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
