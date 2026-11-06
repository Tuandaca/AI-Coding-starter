#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 compatibility catalog tests.

Coverage:
  - compatibility rules load and validate
  - valid combinations accepted
  - conflicts rejected (error severity)
  - rules reference only known entities
  - no executable code in catalog data

Deterministic, offline, read-only on catalog data.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import load_catalog
from core.domain.contracts import is_valid_id, make_id

CATALOG_DIR = REPO_ROOT / "catalog"

VALID_SEVERITIES = {"error", "warning", "info"}
VALID_RULE_TYPES = {
    "technology-technology", "technology-capability", "capability-capability",
    "bundle-bundle", "bundle-capability", "bundle-technology",
    "technology-project-type",
}


class TestCompatibilityCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_rules_have_valid_structure(self):
        known_tech = self.catalog.technology_ids()
        known_caps = {str(c.id) for c in self.catalog.capabilities.values()}
        known_bundles = {str(b.id) for b in self.catalog.stack_bundles.values()}
        known_pts = {str(p.id) for p in self.catalog.project_types.values()}
        for rule in self.catalog.compatibility.rules:
            self.assertIn(rule.rule_type, VALID_RULE_TYPES,
                          f"Invalid rule type: {rule.rule_type}")
            self.assertIn(rule.severity, VALID_SEVERITIES,
                          f"Invalid severity: {rule.severity}")
            self.assertTrue(rule.reason.strip())
            self.assertTrue(is_valid_id(str(rule.subject)))
            self.assertTrue(is_valid_id(str(rule.target)))

    def test_rule_references_point_to_known_entities(self):
        """No unknown references in compatibility rules."""
        result = self.catalog.compatibility.validate(
            known_technologies=[make_id(t) for t in self.catalog.technology_ids()],
            known_capabilities=[make_id(c) for c in {str(c.id) for c in self.catalog.capabilities.values()}],
            known_bundles=[make_id(b) for b in {str(b.id) for b in self.catalog.stack_bundles.values()}],
            known_project_types=[make_id(p) for p in {str(p.id) for p in self.catalog.project_types.values()}],
        )
        self.assertTrue(result.is_valid, f"Compatibility validation errors: {[e.message for e in result.errors]}")

    def test_error_conflicts_are_encoded(self):
        """Explicitly encoded error-severity conflicts exist (e.g. two frontends)."""
        error_rules = [r for r in self.catalog.compatibility.rules if r.severity == "error"]
        self.assertTrue(error_rules, "Expected at least one error-severity conflict rule")
        # The two-primary-frontends conflict (nextjs vs vue) must be catalog-encoded.
        frontend_conflicts = [r for r in error_rules
                              if {str(r.subject), str(r.target)} == {"nextjs", "vue"}]
        self.assertTrue(frontend_conflicts,
                        "Expected nextjs-vs-vue frontend conflict rule in catalog")

    def test_requirements_are_not_encoded_as_conflicts(self):
        """Capability dependencies belong in capability.requires/implies,
        not compatibility conflicts at any severity."""
        dependency_pairs: set[tuple[str, str]] = set()
        implied_pairs: set[tuple[str, str]] = set()
        for cap in self.catalog.capabilities.values():
            for req in cap.requires:
                dependency_pairs.add((str(cap.id), str(req)))
            for impl in cap.implies:
                implied_pairs.add((str(cap.id), str(impl)))
        for rule in self.catalog.compatibility.rules:
            if rule.rule_type != "capability-capability":
                continue
            pair = (str(rule.subject), str(rule.target))
            self.assertNotIn(pair, dependency_pairs,
                             f"Requirement {pair} encoded as compatibility conflict")
            self.assertNotIn(pair, implied_pairs,
                             f"Implication {pair} encoded as compatibility conflict")

    def test_no_executable_code_in_catalog(self):
        """Catalog data is data only: no eval/exec/shell/import."""
        import json
        for name in ["project-types.yaml", "capabilities.yaml", "stack-bundles.yaml",
                     "compatibility.yaml"]:
            with open(REPO_ROOT / "catalog" / name, encoding="utf-8") as f:
                text = f.read()
            for token in ["eval(", "exec(", "shell=True", "__import__", "import ",
                          "subprocess", "os.system"]:
                self.assertNotIn(token, text, f"Executable token {token!r} found in {name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
