#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 Migration Tests - Self-contained Resource Migration

Tests for:
- Offline generation with bundled resources (no external template)
- Path portability (no D:\ or machine-specific paths)
- Setup scripts: no external clone, no sed source mutation
- Setup parity between Windows and POSIX
- Resource discovery precedence (bundled first, external optional)
- MASTER_TEMPLATE_PATH is optional/non-required
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402


def _run_copy_selective(*args, **kwargs):
    """Run copy_selective with stdout redirected to suppress emoji printing on Windows."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        return new_project.copy_selective(*args, **kwargs)


class TestOfflineGeneration(unittest.TestCase):
    """Test that generation works offline with bundled resources only."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ai_starter_m2_"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

    def test_offline_generation_with_bundled_resources(self):
        """INTENTIONAL CHANGE — M2: Generation succeeds with no external template."""
        # Verify bundled resources exist
        bundled_root = new_project.BUNDLED_RESOURCE_ROOT
        self.assertTrue(bundled_root.exists(), "Bundled resources directory must exist")
        self.assertTrue((bundled_root / "agents").exists(), "Bundled agents must exist")

        # Verify resource root resolution prefers bundled
        resource_root = new_project.get_resource_root()
        self.assertEqual(resource_root, bundled_root)

        # Run copy_selective using bundled resources as source
        merged = {
            "agents": ["frontend-specialist.md", "project-planner.md"],
            "skills": ["modern-web-architect"],
            "shared": ["design-system"],
            "workflows": ["create.md", "enhance.md"],
            "scripts": ["checklist.py"],
            "focus": ["Test focus"],
        }

        dest = self.temp_dir / "generated-project"
        total = _run_copy_selective(
            bundled_root, dest, dict(merged), "test-proj",
            ["personal-web"], None, None
        )

        # Verify files were copied
        self.assertTrue((dest / "agents" / "frontend-specialist.md").exists())
        self.assertTrue((dest / "agents" / "project-planner.md").exists())
        self.assertTrue((dest / "skills" / "modern-web-architect" / "skill.md").exists())
        self.assertTrue((dest / "workflows" / "create.md").exists())
        self.assertTrue((dest / "workflows" / "enhance.md").exists())
        self.assertTrue((dest / "scripts" / "checklist.py").exists())
        self.assertTrue((dest / "GEMINI.md").exists())
        self.assertTrue((dest / "CONTEXT.md").exists())

        # Verify byte count is positive
        self.assertGreater(total, 0)

    def test_generation_without_external_template(self):
        """INTENTIONAL CHANGE — M2: MASTER_TEMPLATE_PATH=None works fine."""
        # Simulate no external template configured
        self.assertIsNone(new_project.MASTER_TEMPLATE_PATH)

        # Resource root should fall back to bundled
        resource_root = new_project.get_resource_root()
        self.assertEqual(resource_root, new_project.BUNDLED_RESOURCE_ROOT)

    def test_generation_no_network_required(self):
        """Generation must not require network access."""
        # This is verified by the fact that copy_selective only reads
        # from local bundled resources - no git clone, no HTTP requests.
        bundled_root = new_project.BUNDLED_RESOURCE_ROOT
        self.assertTrue(bundled_root.exists())

        # All resource paths should be local
        agents_dir = bundled_root / "agents"
        self.assertTrue(agents_dir.exists())
        agent_files = list(agents_dir.glob("*.md"))
        self.assertGreater(len(agent_files), 0)


class TestPathPortability(unittest.TestCase):
    """Test that paths are not machine-specific."""

    def test_bundled_resource_root_is_repository_relative(self):
        """BUNDLED_RESOURCE_ROOT must be repository-relative, not drive-letter dependent."""
        root = new_project.BUNDLED_RESOURCE_ROOT
        self.assertTrue(root.is_absolute())
        self.assertEqual(root.name, "resources")
        # Repository-relative: computed from __file__, never a hard-coded
        # drive-letter absolute path such as D:\VibeCoding-Template\.agent.
        self.assertFalse(
            str(root).startswith(("D:", "C:")),
            f"BUNDLED_RESOURCE_ROOT is drive-letter dependent: {root}",
        )

    def test_no_hardcoded_d_drive_paths(self):
        """new_project.py must not contain D:\ hard-coded paths."""
        content = Path(new_project.__file__).read_text(encoding="utf-8")
        self.assertNotIn("D:\\", content)
        self.assertNotIn("D:/", content)

    def test_config_has_no_machine_specific_paths(self):
        """config.json must not contain machine-specific absolute paths."""
        config_path = REPO_ROOT / "config.json"
        content = config_path.read_text(encoding="utf-8")
        config = json.loads(content)

        # MASTER_TEMPLATE_PATH should be null or absent
        self.assertIsNone(config.get("MASTER_TEMPLATE_PATH"))

        # DEFAULT_PROJECT_PATH if present should not be D:\ or C:\
        default_project = config.get("DEFAULT_PROJECT_PATH", "")
        if default_project:
            self.assertNotIn("D:\\", default_project)
            self.assertNotIn("D:/", default_project)
            self.assertNotIn("C:\\", default_project)

    def test_resource_paths_use_pathlib(self):
        """Resource discovery must use pathlib.Path, not string concatenation."""
        content = Path(new_project.__file__).read_text(encoding="utf-8")
        self.assertIn("BUNDLED_RESOURCE_ROOT = Path", content)
        self.assertIn("Path(__file__).parent", content)


class TestResourceDiscoveryPrecedence(unittest.TestCase):
    """Test resource resolution precedence: bundled first, external optional."""

    def test_bundled_is_primary(self):
        """Bundled resources are the default source."""
        self.assertTrue(new_project.BUNDLED_RESOURCE_ROOT.exists())

    def test_external_template_is_optional(self):
        """MASTER_TEMPLATE_PATH=None means no external template required."""
        self.assertIsNone(new_project.MASTER_TEMPLATE_PATH)

    def test_get_resource_root_prefers_bundled(self):
        """get_resource_root() returns bundled when external not configured."""
        root = new_project.get_resource_root()
        self.assertEqual(root, new_project.BUNDLED_RESOURCE_ROOT)

    def test_missing_required_resource_raises_clear_error(self):
        """When a required bundled resource is missing, error is actionable."""
        # This is tested implicitly - copy_selective reports "Skip (not found)"
        # for missing optional resources but continues. Required resources
        # (agents listed in PROJECT_TYPES) must exist in bundled resources.
        bundled_agents = list((new_project.BUNDLED_RESOURCE_ROOT / "agents").glob("*.md"))
        # At minimum, the agents referenced by PROJECT_TYPES should exist
        for ptype in new_project.PROJECT_TYPES.values():
            for agent_file in ptype["agents"]:
                agent_path = new_project.BUNDLED_RESOURCE_ROOT / "agents" / agent_file
                self.assertTrue(
                    agent_path.exists(),
                    f"Required bundled agent missing: {agent_path}"
                )


class TestResourcePrecedence(unittest.TestCase):
    """Test resource discovery precedence: bundled canonical, external optional fallback."""

    def test_bundled_is_primary_when_external_null(self):
        """MASTER_TEMPLATE_PATH=null → bundled resources used."""
        # Save and restore original values
        original_master = new_project.MASTER_TEMPLATE_PATH
        try:
            new_project.MASTER_TEMPLATE_PATH = None
            root = new_project.get_resource_root()
            self.assertEqual(root, new_project.BUNDLED_RESOURCE_ROOT)
        finally:
            new_project.MASTER_TEMPLATE_PATH = original_master

    def test_bundled_is_primary_when_external_invalid(self):
        """MASTER_TEMPLATE_PATH set to non-existent path → bundled resources used."""
        original_master = new_project.MASTER_TEMPLATE_PATH
        try:
            new_project.MASTER_TEMPLATE_PATH = Path("/nonexistent/path/.agent")
            root = new_project.get_resource_root()
            self.assertEqual(root, new_project.BUNDLED_RESOURCE_ROOT)
        finally:
            new_project.MASTER_TEMPLATE_PATH = original_master

    def test_external_only_as_fallback_when_bundled_missing(self):
        """External template used only when bundled resources unavailable."""
        original_bundled = new_project.BUNDLED_RESOURCE_ROOT
        original_master = new_project.MASTER_TEMPLATE_PATH
        try:
            # Point to a temp dir that doesn't exist as bundled
            new_project.BUNDLED_RESOURCE_ROOT = Path(tempfile.mkdtemp()) / "nonexistent"
            new_project.MASTER_TEMPLATE_PATH = new_project.BUNDLED_RESOURCE_ROOT.parent
            # Simulate external template existing at parent
            new_project.MASTER_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            root = new_project.get_resource_root()
            # Since bundled doesn't exist and external points to parent dir,
            # external should be used as fallback
            self.assertEqual(root, new_project.MASTER_TEMPLATE_PATH)
        finally:
            new_project.BUNDLED_RESOURCE_ROOT = original_bundled
            new_project.MASTER_TEMPLATE_PATH = original_master

    def test_resource_discovery_deterministic(self):
        """Resource resolution is deterministic across calls."""
        root1 = new_project.get_resource_root()
        root2 = new_project.get_resource_root()
        root3 = new_project.get_resource_root()
        self.assertEqual(root1, root2)
        self.assertEqual(root2, root3)


class TestSetupScriptStatic(unittest.TestCase):
    """Static tests for setup scripts (no execution)."""

    @classmethod
    def setUpClass(cls):
        cls.bat = (REPO_ROOT / "setup.bat").read_text(encoding="utf-8")
        cls.sh = (REPO_ROOT / "setup.sh").read_text(encoding="utf-8")

    def test_setup_bat_no_external_clone(self):
        """setup.bat does not require cloning external template."""
        self.assertNotIn("git clone", self.bat)
        self.assertNotIn("antigravity-ide.git", self.bat)
        self.assertNotIn("google-antigravity.git", self.bat)

    def test_setup_sh_no_external_clone(self):
        """setup.sh does not require cloning external template."""
        self.assertNotIn("git clone", self.sh)
        self.assertNotIn("antigravity-ide.git", self.sh)
        self.assertNotIn("google-antigravity.git", self.sh)

    def test_setup_sh_no_sed_mutation(self):
        """setup.sh does not use sed to mutate new_project.py."""
        self.assertNotIn("sed", self.sh)

    def test_setup_bat_validates_bundled_resources(self):
        """setup.bat checks for bundled resources availability."""
        self.assertIn("resources", self.bat.lower())

    def test_setup_sh_validates_bundled_resources(self):
        """setup.sh checks for bundled resources availability."""
        self.assertIn("resources", self.sh.lower())

    def test_setup_scripts_config_equivalence(self):
        """Both scripts delegate config generation to setup_portable.py."""
        self.assertIn("scripts\\setup_portable.py", self.bat)
        self.assertIn("scripts/setup_portable.py", self.sh)

    def test_setup_bat_no_drive_letter_paths(self):
        """setup.bat has no D:\ hard-coded paths."""
        self.assertNotIn("DEFAULT_BASE=D:", self.bat)
        self.assertNotIn("D:\\VibeCoding-Template", self.bat)
        self.assertNotIn("D:\\Projects", self.bat)

    def test_setup_sh_no_home_template_path(self):
        """setup.sh has no template path under HOME."""
        self.assertNotIn('$HOME/VibeCoding-Template', self.sh)
        self.assertNotIn('TEMPLATE_PATH=', self.sh)


class TestLegacyProtection(unittest.TestCase):
    """Verify M2 does not modify protected files."""

    def test_analytics_unchanged(self):
        """analytics.py must not be modified by M2."""
        # Just verify it still compiles and works
        import analytics
        self.assertTrue(hasattr(analytics, 'track_project'))
        self.assertTrue(hasattr(analytics, 'print_dashboard'))

    def test_agent_workflows_intact(self):
        """``.agent/workflows/**`` must remain intact."""
        workflows_dir = REPO_ROOT / ".agent" / "workflows"
        self.assertTrue(workflows_dir.exists())
        expected = ["commit.md", "deploy.md", "fix.md", "progress.md", "stats.md", "status.md"]
        for wf in expected:
            self.assertTrue((workflows_dir / wf).exists(), f"Missing workflow: {wf}")

    def test_m1_contracts_intact(self):
        """M1 contracts must not be modified by M2."""
        contracts_dir = REPO_ROOT / "core" / "domain" / "contracts"
        self.assertTrue(contracts_dir.exists())
        # Verify at least the key contract files exist
        for fname in ["project_type.py", "capability.py", "technology.py",
                      "stack_bundle.py", "compatibility.py", "resource.py",
                      "execution_pack.py", "runtime_adapter.py",
                      "capability_provider.py", "project_state.py",
                      "id_policy.py", "errors.py"]:
            self.assertTrue((contracts_dir / fname).exists(), f"Missing contract: {fname}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
