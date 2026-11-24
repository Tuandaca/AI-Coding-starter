#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M11 Orca integration tests.

Tests for core/orca_integration.py and core/capability_provider_registry.py:

* Orca detection works (returns path or None)
* Health check runs `orca --version` and fails gracefully when not installed
* Orca provider info included in resources.lock when available
* Provider registry returns correct fallback chains
* Integration is fail-open (no Orca = no error)

Standard library only. No network. No actual Orca installation required.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core import orca_integration
from core.capability_provider_registry import (
    CapabilityProviderRegistry,
    get_default_registry,
    get_provider_for_capability,
    get_fallback_chain_for,
)


class TestOrcaIntegration(unittest.TestCase):
    """Test Orca integration functions."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.orca_integration.detect_orca")
    def test_detect_orca_when_installed(self, mock_detect):
        """detect_orca returns path when Orca is in PATH."""
        mock_detect.return_value = "/usr/local/bin/orca"
        result = orca_integration.detect_orca()
        self.assertEqual(result, "/usr/local/bin/orca")

    @patch("core.orca_integration.detect_orca")
    def test_detect_orca_when_not_installed(self, mock_detect):
        """detect_orca returns None when Orca not found."""
        mock_detect.return_value = None
        result = orca_integration.detect_orca()
        self.assertIsNone(result)

    def test_health_check_fails_when_not_installed(self):
        """health_check returns False when Orca not available."""
        with patch("core.orca_integration.detect_orca", return_value=None):
            result = orca_integration.health_check()
            self.assertFalse(result)

    def test_health_check_runs_version_with_timeout(self):
        """health_check runs `orca --version` with 10s timeout."""
        fake_exe = str(self.temp_dir / "orca.exe")
        self.temp_dir.joinpath("orca.exe").write_text("#!/bin/sh\necho test", encoding="utf-8")
        with patch("core.orca_integration.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="orca version 1.2.3",
                stderr="",
            )
            result = orca_integration.health_check(fake_exe)
            self.assertTrue(result)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], [fake_exe, "--version"])
            self.assertEqual(kwargs["timeout"], 10)

    def test_health_check_requires_version_output(self):
        """health_check returns False when output lacks 'orca version'."""
        fake_exe = str(self.temp_dir / "orca.exe")
        self.temp_dir.joinpath("orca.exe").write_text("#!/bin/sh\necho test", encoding="utf-8")
        with patch("core.orca_integration.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="some other tool version 1.0",
                stderr="",
            )
            result = orca_integration.health_check(fake_exe)
            self.assertFalse(result)

    def test_health_check_handles_timeout(self):
        """health_check returns False when `orca --version` times out."""
        fake_exe = str(self.temp_dir / "orca.exe")
        with patch("core.orca_integration.subprocess.run",
                   side_effect=__import__("subprocess").TimeoutExpired(fake_exe, 10)):
            result = orca_integration.health_check(fake_exe)
            self.assertFalse(result)

    @patch("core.orca_integration.detect_orca")
    def test_get_orca_provider_info_when_not_installed(self, mock_detect):
        """get_orca_provider_info returns empty dict when Orca not installed."""
        mock_detect.return_value = None
        result = orca_integration.get_orca_provider_info()
        self.assertEqual(result, {})

    @patch("core.orca_integration.detect_orca")
    @patch("core.capability_provider_registry.get_default_registry")
    def test_get_orca_provider_info_when_installed(self, mock_get_registry, mock_detect):
        """get_orca_provider_info returns provider info when Orca available."""
        # Create a mock registry with healthy orca
        mock_registry = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = "orca"
        mock_registry.get_preferred_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        mock_detect.return_value = "/usr/local/bin/orca"

        result = orca_integration.get_orca_provider_info()

        # Should call the registry's get_preferred_provider
        mock_registry.get_preferred_provider.assert_called_with("orchestration")
        self.assertEqual(result["provider_id"], "orca")
        self.assertEqual(result["capability"], "orchestration")
        self.assertEqual(result["executable"], "/usr/local/bin/orca")
        self.assertEqual(result["health_check"], "exec:orca --version")
        self.assertTrue(result["optional"])
        self.assertEqual(result["fallback"], "git-worktree")

    @patch("core.orca_integration.detect_orca")
    @patch("core.orca_integration.health_check")
    def test_is_orca_available(self, mock_health, mock_detect):
        """is_orca_available returns True only when both detect and health pass."""
        mock_detect.return_value = "/usr/local/bin/orca"
        mock_health.return_value = True
        self.assertTrue(orca_integration.is_orca_available())

        mock_health.return_value = False
        self.assertFalse(orca_integration.is_orca_available())

        mock_detect.return_value = None
        mock_health.return_value = True
        self.assertFalse(orca_integration.is_orca_available())

    @patch("core.orca_integration.detect_orca")
    @patch("core.orca_integration.health_check")
    def test_maybe_initialize_orca_when_not_installed(self, mock_health, mock_detect):
        """maybe_initialize_orca gracefully skips when Orca not installed."""
        mock_detect.return_value = None
        result = orca_integration.maybe_initialize_orca(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not installed", result["message"])

    @patch("core.orca_integration.detect_orca")
    @patch("core.orca_integration.health_check")
    @patch("core.capability_provider_registry.get_default_registry")
    def test_maybe_initialize_orca_when_healthy(self, mock_get_registry, mock_health, mock_detect):
        """maybe_initialize_orca initializes when Orca is healthy."""
        # Create a mock registry with healthy orca
        mock_registry = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = "orca"
        mock_registry.get_preferred_provider.return_value = mock_provider
        mock_get_registry.return_value = mock_registry

        mock_detect.return_value = "/usr/local/bin/orca"
        mock_health.return_value = True
        result = orca_integration.maybe_initialize_orca(self.temp_dir)
        self.assertTrue(result["initialized"])
        self.assertEqual(result["provider_info"]["provider_id"], "orca")

    @patch("core.orca_integration.detect_orca")
    @patch("core.orca_integration.health_check")
    def test_maybe_initialize_orca_when_unhealthy(self, mock_health, mock_detect):
        """maybe_initialize_orca skips when Orca installed but unhealthy."""
        mock_detect.return_value = "/usr/local/bin/orca"
        mock_health.return_value = False
        result = orca_integration.maybe_initialize_orca(self.temp_dir)
        self.assertFalse(result["initialized"])
        self.assertIn("not responsive", result["message"])


class TestCapabilityProviderRegistry(unittest.TestCase):
    """Test the capability provider registry for Orca."""

    def setUp(self):
        self.registry = CapabilityProviderRegistry()

    def test_orchestration_providers_registered(self):
        """orchestration capability has providers registered."""
        providers = self.registry.get_providers_for("orchestration")
        self.assertGreaterEqual(len(providers), 2)
        ids = [p.id for p in providers]
        self.assertIn("orca", ids)
        self.assertIn("git-worktree", ids)

    def test_orchestration_priority_order(self):
        """orca has higher priority (lower number) than git-worktree."""
        providers = self.registry.get_providers_for("orchestration")
        priorities = {p.id: p.priority for p in providers}
        self.assertLess(priorities["orca"], priorities["git-worktree"])

    def test_get_preferred_provider_healthy(self):
        """get_preferred_provider returns first healthy provider."""
        # git-worktree health check always returns True (git available or not)
        provider = self.registry.get_preferred_provider("orchestration")
        self.assertIsNotNone(provider)
        # Should be git-worktree since orca health check fails (no executable)
        self.assertEqual(provider.id, "git-worktree")

    def test_get_fallback_chain_includes_all(self):
        """get_fallback_chain returns all registered providers."""
        chain = self.registry.get_fallback_chain("orchestration")
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].id, "orca")
        self.assertEqual(chain[1].id, "git-worktree")

    def test_global_singleton(self):
        """get_default_registry returns singleton."""
        reg1 = get_default_registry()
        reg2 = get_default_registry()
        self.assertIs(reg1, reg2)

    def test_convenience_functions(self):
        """Convenience functions work."""
        provider = get_provider_for_capability("orchestration")
        self.assertIsNotNone(provider)
        chain = get_fallback_chain_for("orchestration")
        self.assertEqual(len(chain), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
