#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capability-gating tests for V2.1.1 (DEFECT A).

Verifies that capability-gated resources are activated ONLY when their
explicit `when` condition matches the resolved project context, and never
from a free-form `selection_reason` alone.

Standard library only. No network.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.resource_resolver import resolve_resources


class TestCapabilityGating(unittest.TestCase):
    """Capability-gated resources must not activate without matching capability."""

    def _ids(self, result):
        return {(r.type, r.id) for r in result.resources}

    def test_portfolio_without_auth_does_not_select_security_auditor(self):
        """DEFECT A: portfolio must not select security-auditor without authentication."""
        result = resolve_resources(
            "portfolio", [], "react-static",
            catalog_dir=REPO_ROOT / "catalog",
            resources_root=REPO_ROOT / "resources",
        )
        self.assertTrue(result.ok, result.errors)
        ids = self._ids(result)
        self.assertNotIn(("agent", "security-auditor"), ids,
                         "security-auditor agent must not be active without authentication")
        self.assertNotIn(("skill", "security-auditor"), ids,
                         "security-auditor skill must not be active without authentication")
        self.assertNotIn(("skill", "api-documenter"), ids,
                         "api-documenter must not be active for a static portfolio")
        self.assertNotIn(("shared-module", "api-standards"), ids,
                         "api-standards must not be active for a static portfolio")
        self.assertNotIn(("agent", "backend-specialist"), ids,
                         "backend-specialist must not be active for a static portfolio")

    def test_portfolio_with_authentication_selects_security_auditor(self):
        """When authentication is selected, security-auditor activates with an honest reason."""
        result = resolve_resources(
            "portfolio", ["authentication"], "react-static",
            catalog_dir=REPO_ROOT / "catalog",
            resources_root=REPO_ROOT / "resources",
        )
        self.assertTrue(result.ok, result.errors)
        ids = self._ids(result)
        self.assertIn(("agent", "security-auditor"), ids)
        auditor = [r for r in result.resources if r.id == "security-auditor" and r.type == "agent"][0]
        self.assertEqual(auditor.selection_reason, "capability:authentication",
                         f"Expected honest capability reason, got {auditor.selection_reason!r}")

    def test_selection_reason_never_claims_unselected_capability(self):
        """No selection_reason may reference a capability that was not selected."""
        result = resolve_resources(
            "portfolio", ["accessibility", "i18n"], "react-static",
            catalog_dir=REPO_ROOT / "catalog",
            resources_root=REPO_ROOT / "resources",
        )
        self.assertTrue(result.ok, result.errors)
        selected = {"accessibility", "i18n"}
        for res in result.resources:
            self.assertNotIn("capability:authentication", res.selection_reason)
            self.assertNotIn("capability:payments", res.selection_reason)
            # Any capability-prefixed reason must reference a selected capability.
            for token in res.selection_reason.split():
                if token.startswith("capability:"):
                    cap = token[len("capability:"):]
                    self.assertIn(cap, selected,
                                  f"{res.type}:{res.id} claims unselected capability {cap}")

    def test_saas_with_authentication_selects_security_auditor(self):
        """SaaS (authentication default) still selects security-auditor via capability gating."""
        result = resolve_resources(
            "saas", ["authentication", "payments"], "nextjs-supabase",
            catalog_dir=REPO_ROOT / "catalog",
            resources_root=REPO_ROOT / "resources",
        )
        self.assertTrue(result.ok, result.errors)
        ids = self._ids(result)
        self.assertIn(("agent", "security-auditor"), ids)
        auditor = [r for r in result.resources if r.id == "security-auditor" and r.type == "agent"][0]
        self.assertEqual(auditor.selection_reason, "capability:authentication")


if __name__ == "__main__":
    unittest.main(verbosity=2)
