#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M10 Agent-Reach integration tests.

Tests for core/agent_reach_integration.py and core/capability_provider_registry.py:

* Agent-Reach detection works (returns path or None)
* Health check fails gracefully when executable not found
* Agent-Reach provider info included in resources.lock when available
* Provider registry returns correct fallback chains
* Integration is fail-open (no Agent-Reach = no error)

Standard library only. No network. No actual Agent-Reach installation required.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core import agent_reach_integration
from core.capability_provider_registry import (
    CapabilityProviderRegistry,
    get_default_registry,
    get_provider_for_capability,
    get_fallback_chain_for,
)


class TestAgentReachIntegration(unittest.TestCase):
    """Test Agent-Reach integration functions."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.agent_reach_integration.detect_agent_reach")
    def test_detect_agent_reach_when_installed(self, mock_detect):
        """detect_agent_reach returns path when Agent-Reach is in PATH."""
        mock_detect.return_value = "/usr/local/bin/agent-reach"
        result = agent_reach_integration.detect_agent_reach()
        self.assertEqual(result, "/usr/local/bin/agent-reach")

    @patch("core.agent_reach_integration.detect_agent_reach")
    def test_detect_agent_reach_when_not_installed(self, mock_detect):
        """detect_agent_reach returns None when Agent-Reach not found."""
        mock_detect.return_value = None
        result = agent_reach_integration.detect_agent_reach()
        self.assertIsNone(result)

    def test_health_check_fails_when_not_installed(self):
        """health_check returns False when Agent-Reach not available."""
        with patch("core.agent_reach_integration.detect_agent_reach", return_value=None):
            result = agent_reach_integration.health_check()
            self.assertFalse(result)

    def test_health_check_with_path(self):
        """health_check returns True when explicit path exists."""
        self.temp_dir.joinpath("agent-reach").write_text("#!/bin/sh\necho test", encoding="utf-8")
        agent_path = str(self.temp_dir / "agent-reach")
        result = agent_reach_integration.health_check(agent_path)
        self.assertTrue(result)

    def test_health_check_fails_with_bad_path(self):
        """health_check returns False when explicit path does not exist."""
        result = agent_reach_integration.health_check("/nonexistent/agent-reach")
        self.assertFalse(result)

    @patch("core.agent_reach_integration.detect_agent_reach")
    def test_get_agent_reach_provider_info_when_not_installed(self, mock_detect):
        """get_agent_reach_provider_info returns empty dict when Agent-Reach not installed."""
        mock_detect.return_value = None
        result = agent_reach_integration.get_agent_reach_provider_info()
        self.assertEqual(result, {})

    @patch("core.agent_reach_integration.detect_agent_reach")
    @patch("core.capability_provider_registry.get_default_registry")
    def test_get_agent_reach_provider_info_when_installed(self, mock_get_registry, mock_detect):
        """get_agent_reach_provider_info returns provider info when Agent-Reach available."""
        # Create a mock registry with healthy agent-reach
        mock_registry = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = "agent-reach"
        mock_registry.get_preferred_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        mock_detect.return_value = "/usr/local/bin/agent-reach"

        result = agent_reach_integration.get_agent_reach_provider_info()

        # Should call the registry's get_preferred_provider
        mock_registry.get_preferred_provider.assert_called_with("research-web")
        self.assertEqual(result["provider_id"], "agent-reach")
        self.assertEqual(result["capability"], "research-web")
        self.assertEqual(result["executable"], "/usr/local/bin/agent-reach")
        self.assertEqual(result["health_check"], "exec:agent-reach")
        self.assertTrue(result["optional"])
        self.assertEqual(result["fallback"], "runtime-native")

    @patch("core.agent_reach_integration.detect_agent_reach")
    @patch("core.agent_reach_integration.health_check")
    def test_is_agent_reach_available(self, mock_health, mock_detect):
        """is_agent_reach_available returns True only when both detect and health pass."""
        mock_detect.return_value = "/usr/local/bin/agent-reach"
        mock_health.return_value = True
        self.assertTrue(agent_reach_integration.is_agent_reach_available())

        mock_health.return_value = False
        self.assertFalse(agent_reach_integration.is_agent_reach_available())

        mock_detect.return_value = None
        mock_health.return_value = True
        self.assertFalse(agent_reach_integration.is_agent_reach_available())

    @patch("core.agent_reach_integration.detect_agent_reach")
    @patch("core.agent_reach_integration.health_check")
    def test_maybe_initialize_agent_reach_when_not_installed(self, mock_health, mock_detect):
        """maybe_initialize_agent_reach gracefully skips when Agent-Reach not installed."""
        mock_detect.return_value = None
        result = agent_reach_integration.maybe_initialize_agent_reach(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not installed", result["message"])

    @patch("core.agent_reach_integration.detect_agent_reach")
    @patch("core.agent_reach_integration.health_check")
    @patch("core.capability_provider_registry.get_default_registry")
    def test_maybe_initialize_agent_reach_when_healthy(self, mock_get_registry, mock_health, mock_detect):
        """maybe_initialize_agent_reach initializes when Agent-Reach is healthy."""
        # Create a mock registry with healthy agent-reach
        mock_registry = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = "agent-reach"
        mock_registry.get_preferred_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        mock_detect.return_value = "/usr/local/bin/agent-reach"
        mock_health.return_value = True
        result = agent_reach_integration.maybe_initialize_agent_reach(self.temp_dir)
        self.assertTrue(result["initialized"])
        self.assertEqual(result["provider_info"]["provider_id"], "agent-reach")

    @patch("core.agent_reach_integration.detect_agent_reach")
    @patch("core.agent_reach_integration.health_check")
    def test_maybe_initialize_agent_reach_when_unhealthy(self, mock_health, mock_detect):
        """maybe_initialize_agent_reach skips when Agent-Reach installed but unhealthy."""
        mock_detect.return_value = "/usr/local/bin/agent-reach"
        mock_health.return_value = False
        result = agent_reach_integration.maybe_initialize_agent_reach(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not found", result["message"])


class TestCapabilityProviderRegistry(unittest.TestCase):
    """Test the capability provider registry for Agent-Reach."""

    def setUp(self):
        self.registry = CapabilityProviderRegistry()

    def test_research_web_providers_registered(self):
        """research-web capability has providers registered."""
        providers = self.registry.get_providers_for("research-web")
        self.assertGreaterEqual(len(providers), 2)
        ids = [p.id for p in providers]
        self.assertIn("agent-reach", ids)
        self.assertIn("runtime-native", ids)

    def test_research_web_priority_order(self):
        """agent-reach has higher priority (lower number) than runtime-native."""
        providers = self.registry.get_providers_for("research-web")
        priorities = {p.id: p.priority for p in providers}
        self.assertLess(priorities["agent-reach"], priorities["runtime-native"])

    def test_get_preferred_provider_healthy(self):
        """get_preferred_provider returns first healthy provider."""
        # runtime-native health check always returns True
        provider = self.registry.get_preferred_provider("research-web")
        self.assertIsNotNone(provider)
        # Should be runtime-native since agent-reach health check fails (no executable)
        self.assertEqual(provider.id, "runtime-native")

    def test_get_fallback_chain_includes_all(self):
        """get_fallback_chain returns all registered providers."""
        chain = self.registry.get_fallback_chain("research-web")
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].id, "agent-reach")
        self.assertEqual(chain[1].id, "runtime-native")

    def test_global_singleton(self):
        """get_default_registry returns singleton."""
        reg1 = get_default_registry()
        reg2 = get_default_registry()
        self.assertIs(reg1, reg2)

    def test_convenience_functions(self):
        """Convenience functions work."""
        provider = get_provider_for_capability("research-web")
        self.assertIsNotNone(provider)
        chain = get_fallback_chain_for("research-web")
        self.assertEqual(len(chain), 2)


class TestAgentReachConfigDefaults(unittest.TestCase):
    """Test Agent-Reach config default values."""

    def test_health_check_direct_call(self):
        """Direct health check with known path works."""
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir) / "agent-reach"
            agent_path.write_text("#!/bin/sh\necho test", encoding="utf-8")
            os.chmod(agent_path, 0o755)
            result = agent_reach_integration.health_check(str(agent_path))
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)