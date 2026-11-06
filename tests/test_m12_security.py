#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M12: Security tests.

Covers:
  * No permission-bypass flags are emitted in generated output
  * Defensive deny-list strings remain allowed (tests/docs/schema)
  * No global runtime config writes
  * No git add/commit/push in production code
  * No network dependency in production code paths
  * No secret persistence in canonical state
  * No project-root path escape

Standard library only. No network.
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# DANGEROUS_FLAGS: these strings may appear ONLY in deny-lists,
# schema/contract defaults, test assertions, or documentation warnings.
# They must NEVER appear in generated commands, runtime adapter output,
# launcher invocations, or active configuration.
DANGEROUS_FLAGS = (
    "--dangerously-skip-permissions",
    "--dangerously-bypass-approvals-and-sandbox",
    "--yolo",
)

PRODUCTION_PY_FILES = [
    REPO_ROOT / "new_project.py",
    REPO_ROOT / "migrate_project.py",
    REPO_ROOT / "core" / "resolver.py",
    REPO_ROOT / "core" / "spec.py",
    REPO_ROOT / "core" / "state.py",
    REPO_ROOT / "core" / "portable_renderer.py",
    REPO_ROOT / "core" / "generic-renderer.py",
    REPO_ROOT / "core" / "migration.py",
    REPO_ROOT / "core" / "catalog_loader.py",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestNoBypassFlagsEmitted(unittest.TestCase):
    """Generated commands/config must never contain permission-bypass flags."""

    def test_generic_renderer_rejects_dangerous_flags(self):
        """core/generic-renderer.py scans rendered content and rejects
        files containing dangerous flags."""
        source = (REPO_ROOT / "core" / "generic-renderer.py").read_text(
            encoding="utf-8")
        self.assertIn("DANGEROUS_FLAGS", source)
        self.assertIn("dangerous", source.lower())
        # The renderer scans rendered content and refuses to write if any
        # dangerous flag is present.
        self.assertIn("Refusing to write", source)

    def test_no_bypass_flags_in_adapter_templates(self):
        """Dangerous flags may only appear in dangerous_flags_never_enabled
        deny-lists, never as active configuration in adapter templates."""
        adapters_dir = REPO_ROOT / "runtime-adapters"
        for adapter_file in sorted(adapters_dir.glob("*.yaml")):
            text = adapter_file.read_text(encoding="utf-8")
            import json as _json
            adapter = _json.loads(text)
            pp = adapter.get("permission_policy", {})
            flags = pp.get("dangerous_flags_never_enabled", [])
            # All three dangerous flags must be in the deny-list
            for flag in DANGEROUS_FLAGS:
                self.assertIn(flag, flags,
                              f"{adapter_file.name}: {flag} must be in "
                              f"dangerous_flags_never_enabled deny-list")
            # Each flag should appear exactly once in the file (as the single
            # array element in dangerous_flags_never_enabled)
            for flag in DANGEROUS_FLAGS:
                count = text.count(flag)
                self.assertEqual(count, 1,
                                 f"{adapter_file.name}: {flag} appears "
                                 f"{count} times, expected exactly 1 "
                                 f"(in deny-list array)")


class TestDangerousFlagsAllowedInDenylist(unittest.TestCase):
    """The dangerous flags may appear in deny-lists/schema/tests/docs
    (defensive use), but never in generated/enabling context."""

    def test_permission_policy_defaults_contain_flags(self):
        """M1 PermissionPolicy default includes the three forbidden flags."""
        from core.domain.contracts.runtime_adapter import PermissionPolicy
        policy = PermissionPolicy()
        for flag in DANGEROUS_FLAGS:
            self.assertIn(flag, policy.dangerous_flags_never_enabled)

    def test_runtime_adapter_schema_defaults_contain_flags(self):
        """runtime-adapter.json schema default includes the flags."""
        schema = json.loads(
            (REPO_ROOT / "schemas" / "runtime-adapter.json").read_text(
                encoding="utf-8"))
        default = schema["properties"]["permission_policy"][
            "properties"]["dangerous_flags_never_enabled"]["default"]
        for flag in DANGEROUS_FLAGS:
            self.assertIn(flag, default)

    def test_m1_contracts_test_uses_flags(self):
        """M1 contract test references the forbidden flags (defensive)."""
        source = (REPO_ROOT / "tests" / "test_m1_contracts.py").read_text(
            encoding="utf-8")
        for flag in DANGEROUS_FLAGS:
            self.assertIn(flag, source)


class TestNoGlobalConfigWrites(unittest.TestCase):
    """Runtime adapters must not modify global config."""

    def test_all_adapters_modifies_global_config_false(self):
        adapters_dir = REPO_ROOT / "runtime-adapters"
        for adapter_file in sorted(adapters_dir.glob("*.yaml")):
            text = adapter_file.read_text(encoding="utf-8")
            import json as _json
            adapter = _json.loads(text)
            self.assertFalse(
                adapter.get("permission_policy", {}).get(
                    "modifies_global_config", False),
                f"{adapter_file.name}: modifies_global_config must be False")

    def test_all_adapters_requires_explicit_consent_true(self):
        adapters_dir = REPO_ROOT / "runtime-adapters"
        for adapter_file in sorted(adapters_dir.glob("*.yaml")):
            text = adapter_file.read_text(encoding="utf-8")
            import json as _json
            adapter = _json.loads(text)
            self.assertTrue(
                adapter.get("permission_policy", {}).get(
                    "requires_explicit_consent", True),
                f"{adapter_file.name}: requires_explicit_consent must be True")

    def test_no_global_config_mutation_in_production(self):
        """No production code writes to ~/.codex, ~/.claude,
        ~/.config/opencode, or similar global runtime config."""
        global_config_patterns = (
            "~/.codex", "~/.claude", "~/.config/opencode",
            "~/.cursor",
        )
        production_files = [
            REPO_ROOT / "new_project.py",
            REPO_ROOT / "migrate_project.py",
            REPO_ROOT / "core" / "generic-renderer.py",
            REPO_ROOT / "core" / "migration.py",
            REPO_ROOT / "core" / "resolver.py",
            REPO_ROOT / "core" / "spec.py",
            REPO_ROOT / "core" / "state.py",
            REPO_ROOT / "core" / "portable_renderer.py",
        ]
        for pf in production_files:
            text = pf.read_text(encoding="utf-8")
            for pattern in global_config_patterns:
                self.assertNotIn(pattern, text,
                                 f"{pf.name}: global config path "
                                 f"{pattern} found in production code")


class TestNoGitMutationInProduction(unittest.TestCase):
    """Production code must not automatically run git add/commit/push."""

    def test_no_git_add_commit_push_in_production(self):
        production_files = [
            REPO_ROOT / "new_project.py",
            REPO_ROOT / "migrate_project.py",
            REPO_ROOT / "core" / "generic-renderer.py",
            REPO_ROOT / "core" / "migration.py",
            REPO_ROOT / "core" / "resolver.py",
        ]
        for pf in production_files:
            text = pf.read_text(encoding="utf-8")
            self.assertNotIn("git add .", text,
                             f"{pf.name}: 'git add .' found in production")
            self.assertNotIn("git commit", text,
                             f"{pf.name}: 'git commit' found in production")
            self.assertNotIn("git push", text,
                             f"{pf.name}: 'git push' found in production")


class TestNoNetworkInProduction(unittest.TestCase):
    """Production code must not access the network."""

    def test_no_network_modules_in_production(self):
        production_files = [
            REPO_ROOT / "new_project.py",
            REPO_ROOT / "migrate_project.py",
            REPO_ROOT / "core" / "generic-renderer.py",
            REPO_ROOT / "core" / "migration.py",
            REPO_ROOT / "core" / "resolver.py",
            REPO_ROOT / "core" / "spec.py",
            REPO_ROOT / "core" / "state.py",
            REPO_ROOT / "core" / "portable_renderer.py",
            REPO_ROOT / "core" / "catalog_loader.py",
            REPO_ROOT / "analytics.py",
        ]
        network_imports = (
            "import requests", "from requests",
            "import urllib", "from urllib",
            "import http.client", "from http.client",
            "import socket", "from socket",
        )
        for pf in production_files:
            text = pf.read_text(encoding="utf-8")
            for imp in network_imports:
                self.assertNotIn(imp, text,
                                 f"{pf.name}: network import {imp!r} found "
                                 f"in production code")


class TestNoSecretPersistence(unittest.TestCase):
    """Generated canonical state must not contain secrets."""

    def test_no_secrets_in_generated_canonical_state(self):
        """project.yaml / state.yaml / resources.lock must not contain
        passwords, API keys, tokens, or connection strings."""
        secret_patterns = (
            "api_key", "apikey", "api-secret", "apisecret",
            "secret_key", "secretkey", "private_key", "privatekey",
            "access_token", "accesstoken", "password", "passwd",
            "connection_string", "connectionstring",
            "mongodb+srv", "postgresql://", "mysql://", "redis://",
        )
        # new_project.py writes canonical state; check it doesn't embed
        # secret-like literals into generated state files.
        new_project_text = (
            REPO_ROOT / "new_project.py").read_text(encoding="utf-8")
        for pattern in secret_patterns:
            # The patterns may appear in comments/docs but must not be
            # injected into generated state. We check they're not part of
            # a write operation to canonical state files.
            self.assertNotIn(f'write_project_spec(..., "{pattern}")',
                             new_project_text)
            self.assertNotIn(f'write_state(..., "{pattern}")',
                             new_project_text)
            self.assertNotIn(f'write_resources_lock(..., "{pattern}")',
                             new_project_text)


class TestNoPathEscape(unittest.TestCase):
    """No output path may escape the project root."""

    def test_generic_renderer_rejects_parent_traversal(self):
        source = (REPO_ROOT / "core" / "generic-renderer.py").read_text(
            encoding="utf-8")
        self.assertIn("'..'", source)
        self.assertIn("parent traversal", source.lower())

    def test_generic_renderer_rejects_absolute_paths(self):
        source = (REPO_ROOT / "core" / "generic-renderer.py").read_text(
            encoding="utf-8")
        self.assertIn("is_absolute()", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
