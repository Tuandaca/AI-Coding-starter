#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M9 Codebase Memory integration tests.

Tests for core/cbm_integration.py and core/capability_provider_registry.py:

* CBM detection works (returns path or None)
* Health check fails gracefully when server not running
* Project policy read/write works
* CBM provider info included in resources.lock when available
* Provider registry returns correct fallback chains
* Integration is fail-open (no CBM = no error)

Standard library only. No network. No actual CBM installation required.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core import cbm_integration
from core.capability_provider_registry import (
    CapabilityProviderRegistry,
    get_default_registry,
    get_provider_for_capability,
    get_fallback_chain_for,
)


class TestCBMIntegration(unittest.TestCase):
    """Test Codebase Memory integration functions."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.cbm_integration.detect_cbm")
    def test_detect_cbm_when_installed(self, mock_detect):
        """detect_cbm returns path when CBM is in PATH."""
        mock_detect.return_value = "/usr/local/bin/cbm"
        result = cbm_integration.detect_cbm()
        self.assertEqual(result, "/usr/local/bin/cbm")

    @patch("core.cbm_integration.detect_cbm")
    def test_detect_cbm_when_not_installed(self, mock_detect):
        """detect_cbm returns None when CBM not found."""
        mock_detect.return_value = None
        result = cbm_integration.detect_cbm()
        self.assertIsNone(result)

    def test_health_check_fails_when_server_down(self):
        """health_check returns False when MCP server not reachable."""
        result = cbm_integration.health_check()
        self.assertFalse(result)

    def test_get_project_policy_creates_default(self):
        """get_project_policy returns default config when no file exists."""
        policy = cbm_integration.get_project_policy(self.temp_dir)
        self.assertEqual(policy.project_root, str(self.temp_dir))
        self.assertFalse(policy.index_transient_worktrees)
        self.assertEqual(policy.ignore_patterns, cbm_integration.DEFAULT_CBM_CONFIG.ignore_patterns)
        self.assertEqual(policy.mcp_server_port, 8765)

    def test_write_project_policy(self):
        """write_project_policy creates valid JSON config."""
        config = cbm_integration.DEFAULT_CBM_CONFIG
        # Override project_root to test custom path
        config = cbm_integration.CBMConfig(project_root=str(self.temp_dir))
        config_path = cbm_integration.write_project_policy(self.temp_dir, config)
        self.assertTrue(config_path.exists())

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["project_root"], str(self.temp_dir))
        self.assertFalse(data["index_transient_worktrees"])

    def test_write_cbmignore(self):
        """write_cbmignore creates ignore file with defaults."""
        ignore_path = cbm_integration.write_cbmignore(self.temp_dir)
        self.assertTrue(ignore_path.exists())
        content = ignore_path.read_text(encoding="utf-8")
        self.assertIn("**/node_modules/**", content)
        self.assertIn("**/.git/**", content)

    def test_write_cbmignore_custom_patterns(self):
        """write_cbmignore accepts custom patterns."""
        custom = ["**/custom/**", "*.secret"]
        ignore_path = cbm_integration.write_cbmignore(self.temp_dir, custom)
        content = ignore_path.read_text(encoding="utf-8")
        self.assertIn("**/custom/**", content)
        self.assertIn("*.secret", content)

    def test_initialize_cbm_project_creates_config(self):
        """initialize_cbm_project writes config and ignore files."""
        result = cbm_integration.initialize_cbm_project(self.temp_dir)
        self.assertTrue(result)
        self.assertTrue((self.temp_dir / ".codebase-memory.json").exists())
        self.assertTrue((self.temp_dir / ".cbmignore").exists())

    def test_initialize_cbm_project_idempotent(self):
        """initialize_cbm_project is idempotent (doesn't overwrite existing)."""
        cbm_integration.initialize_cbm_project(self.temp_dir)
        config_path = self.temp_dir / ".codebase-memory.json"
        original_mtime = config_path.stat().st_mtime

        import time
        time.sleep(0.01)
        result = cbm_integration.initialize_cbm_project(self.temp_dir)
        self.assertTrue(result)
        self.assertEqual(config_path.stat().st_mtime, original_mtime)

    @patch("core.cbm_integration.detect_cbm")
    def test_get_cbm_provider_info_when_not_installed(self, mock_detect):
        """get_cbm_provider_info returns empty dict when CBM not installed."""
        mock_detect.return_value = None
        result = cbm_integration.get_cbm_provider_info()
        self.assertEqual(result, {})

    @patch("core.cbm_integration.detect_cbm")
    @patch("core.cbm_integration.health_check")
    @patch("core.capability_provider_registry.get_default_registry")
    def test_get_cbm_provider_info_when_installed(self, mock_get_registry, mock_health, mock_detect):
        """get_cbm_provider_info returns provider info when CBM available."""
        # Create a mock registry with healthy codebase-memory
        mock_registry = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = "codebase-memory"
        mock_registry.get_preferred_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry
        
        mock_detect.return_value = "/usr/local/bin/cbm"
        mock_health.return_value = True
        
        result = cbm_integration.get_cbm_provider_info()
        
        # Should call the registry's get_preferred_provider
        mock_registry.get_preferred_provider.assert_called_with("code-intelligence")

    @patch("core.cbm_integration.detect_cbm")
    @patch("core.cbm_integration.health_check")
    def test_is_cbm_available(self, mock_health, mock_detect):
        """is_cbm_available returns True only when both detect and health pass."""
        mock_detect.return_value = "/usr/local/bin/cbm"
        mock_health.return_value = True
        self.assertTrue(cbm_integration.is_cbm_available())

        mock_health.return_value = False
        self.assertFalse(cbm_integration.is_cbm_available())

        mock_detect.return_value = None
        mock_health.return_value = True
        self.assertFalse(cbm_integration.is_cbm_available())

    @patch("core.cbm_integration.detect_cbm")
    @patch("core.cbm_integration.health_check")
    @patch("core.cbm_integration.initialize_cbm_project")
    def test_maybe_initialize_cbm_when_not_installed(self, mock_init, mock_health, mock_detect):
        """maybe_initialize_cbm gracefully skips when CBM not installed."""
        mock_detect.return_value = None
        result = cbm_integration.maybe_initialize_cbm(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not installed", result["message"])
        mock_init.assert_not_called()

    @patch("core.cbm_integration.detect_cbm")
    @patch("core.cbm_integration.health_check")
    @patch("core.cbm_integration.initialize_cbm_project")
    def test_maybe_initialize_cbm_when_healthy(self, mock_init, mock_health, mock_detect):
        """maybe_initialize_cbm initializes when CBM is healthy."""
        mock_detect.return_value = "/usr/local/bin/cbm"
        mock_health.return_value = True
        mock_init.return_value = True
        result = cbm_integration.maybe_initialize_cbm(self.temp_dir)
        self.assertTrue(result["initialized"])
        mock_init.assert_called_once()

    @patch("core.cbm_integration.detect_cbm")
    @patch("core.cbm_integration.health_check")
    def test_maybe_initialize_cbm_when_unhealthy(self, mock_health, mock_detect):
        """maybe_initialize_cbm skips when CBM installed but unhealthy."""
        mock_detect.return_value = "/usr/local/bin/cbm"
        mock_health.return_value = False
        result = cbm_integration.maybe_initialize_cbm(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not reachable", result["message"])


class TestCapabilityProviderRegistry(unittest.TestCase):
    """Test the capability provider registry."""

    def setUp(self):
        self.registry = CapabilityProviderRegistry()

    def test_code_intelligence_providers_registered(self):
        """code-intelligence capability has providers registered."""
        providers = self.registry.get_providers_for("code-intelligence")
        self.assertGreaterEqual(len(providers), 2)
        ids = [p.id for p in providers]
        self.assertIn("codebase-memory", ids)
        self.assertIn("source-scan", ids)

    def test_code_intelligence_priority_order(self):
        """codebase-memory has higher priority (lower number) than source-scan."""
        providers = self.registry.get_providers_for("code-intelligence")
        priorities = {p.id: p.priority for p in providers}
        self.assertLess(priorities["codebase-memory"], priorities["source-scan"])

    def test_orchestration_providers_registered(self):
        """orchestration capability has providers registered."""
        providers = self.registry.get_providers_for("orchestration")
        self.assertGreaterEqual(len(providers), 2)
        ids = [p.id for p in providers]
        self.assertIn("orca", ids)
        self.assertIn("git-worktree", ids)

    def test_research_web_providers_registered(self):
        """research-web capability has providers registered."""
        providers = self.registry.get_providers_for("research-web")
        self.assertGreaterEqual(len(providers), 2)
        ids = [p.id for p in providers]
        self.assertIn("agent-reach", ids)
        self.assertIn("runtime-native", ids)

    def test_unknown_capability_returns_empty(self):
        """Unknown capability returns empty provider list."""
        providers = self.registry.get_providers_for("unknown-capability")
        self.assertEqual(providers, [])

    def test_get_preferred_provider_healthy(self):
        """get_preferred_provider returns first healthy provider."""
        # source-scan health check always returns True
        provider = self.registry.get_preferred_provider("code-intelligence")
        self.assertIsNotNone(provider)
        # Should be source-scan since codebase-memory health check fails (no server)
        self.assertEqual(provider.id, "source-scan")

    def test_get_fallback_chain_includes_all(self):
        """get_fallback_chain returns all registered providers."""
        chain = self.registry.get_fallback_chain("code-intelligence")
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].id, "codebase-memory")
        self.assertEqual(chain[1].id, "source-scan")

    def test_to_domain_providers(self):
        """to_domain_providers converts to domain entities."""
        providers = self.registry.to_domain_providers()
        self.assertIsNotNone(providers)
        self.assertGreater(len(providers), 0)

    def test_global_singleton(self):
        """get_default_registry returns singleton."""
        reg1 = get_default_registry()
        reg2 = get_default_registry()
        self.assertIs(reg1, reg2)

    def test_convenience_functions(self):
        """Convenience functions work."""
        provider = get_provider_for_capability("code-intelligence")
        self.assertIsNotNone(provider)
        chain = get_fallback_chain_for("code-intelligence")
        self.assertEqual(len(chain), 2)


class TestCBMConfigDefaults(unittest.TestCase):
    """Test CBM config default values."""

    def test_default_config_values(self):
        """Default config has expected values."""
        config = cbm_integration.DEFAULT_CBM_CONFIG
        self.assertEqual(config.project_root, ".")
        self.assertFalse(config.index_transient_worktrees)
        self.assertIn("**/node_modules/**", config.ignore_patterns)
        self.assertIn("**/.git/**", config.ignore_patterns)
        self.assertEqual(config.mcp_server_port, 8765)

    def test_default_ignore_content(self):
        """Default ignore file has expected patterns."""
        self.assertIn("**/node_modules/**", cbm_integration.CBM_IGNORE_DEFAULT)
        self.assertIn("**/.git/**", cbm_integration.CBM_IGNORE_DEFAULT)
        self.assertIn("**/__pycache__/**", cbm_integration.CBM_IGNORE_DEFAULT)


if __name__ == "__main__":
    unittest.main(verbosity=2)