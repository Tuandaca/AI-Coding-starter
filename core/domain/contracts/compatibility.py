"""
Domain model for Compatibility rules.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult


@dataclass(frozen=True)
class CompatibilityCondition:
    """Optional condition for when a compatibility rule applies."""
    when: Optional[str] = None
    context: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'CompatibilityCondition':
        return cls(
            when=data.get("when"),
            context=data.get("context", [])
        )

    def to_dict(self) -> dict:
        result = {}
        if self.when:
            result["when"] = self.when
        if self.context:
            result["context"] = self.context
        return result


@dataclass(frozen=True)
class CompatibilityRule:
    """
    A single compatibility rule between two entities.
    """
    rule_type: str
    subject: CanonicalId
    target: CanonicalId
    severity: str
    reason: str
    condition: CompatibilityCondition = field(default_factory=CompatibilityCondition)

    VALID_RULE_TYPES = frozenset([
        "technology-technology", "technology-capability", "capability-capability",
        "bundle-bundle", "bundle-capability", "bundle-technology", "technology-project-type"
    ])

    VALID_SEVERITIES = frozenset(["error", "warning", "info"])

    def __post_init__(self):
        if self.rule_type not in self.VALID_RULE_TYPES:
            raise ValueError(f"Invalid rule_type: {self.rule_type}. Valid: {self.VALID_RULE_TYPES}")
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}. Valid: {self.VALID_SEVERITIES}")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason cannot be empty")
        if not isinstance(self.subject, CanonicalId):
            raise TypeError("subject must be CanonicalId")
        if not isinstance(self.target, CanonicalId):
            raise TypeError("target must be CanonicalId")
        if not isinstance(self.condition, CompatibilityCondition):
            raise TypeError("condition must be CompatibilityCondition")

    @classmethod
    def from_dict(cls, data: dict) -> 'CompatibilityRule':
        return cls(
            rule_type=data["type"],
            subject=make_id(data["subject"]),
            target=make_id(data["target"]),
            severity=data["severity"],
            reason=data["reason"],
            condition=CompatibilityCondition.from_dict(data.get("condition", {}))
        )

    def to_dict(self) -> dict:
        result = {
            "type": self.rule_type,
            "subject": str(self.subject),
            "target": str(self.target),
            "severity": self.severity,
            "reason": self.reason
        }
        cond_dict = self.condition.to_dict()
        if cond_dict:
            result["condition"] = cond_dict
        return result


@dataclass(frozen=True)
class Compatibility:
    """
    Collection of compatibility rules.
    """
    schema_version: str = "1.0.0"
    rules: List[CompatibilityRule] = field(default_factory=list)

    def __post_init__(self):
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        for rule in self.rules:
            if not isinstance(rule, CompatibilityRule):
                raise TypeError("All rules must be CompatibilityRule instances")

    @classmethod
    def from_dict(cls, data: dict) -> 'Compatibility':
        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            rules=[CompatibilityRule.from_dict(r) for r in data.get("rules", [])]
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "rules": [r.to_dict() for r in self.rules]
        }

    def validate(self, known_technologies: List[CanonicalId],
                 known_capabilities: List[CanonicalId],
                 known_bundles: List[CanonicalId],
                 known_project_types: List[CanonicalId]) -> ValidationResult:
        """Validate all rules reference known entities."""
        from core.domain.contracts.errors import UnknownReferenceError

        result = ValidationResult.success()

        known_tech = set(known_technologies)
        known_cap = set(known_capabilities)
        known_bundles = set(known_bundles)
        known_pts = set(known_project_types)

        for rule in self.rules:
            # Determine which sets to check based on rule_type
            subject_set = self._get_reference_set(rule.rule_type, "subject",
                                                  known_tech, known_cap, known_bundles, known_pts)
            target_set = self._get_reference_set(rule.rule_type, "target",
                                                 known_tech, known_cap, known_bundles, known_pts)

            if subject_set and rule.subject not in subject_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(rule.subject),
                    reference_type=self._get_ref_type(rule.rule_type, "subject"),
                    available=[str(x) for x in subject_set] if subject_set else []
                ))

            if target_set and rule.target not in target_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(rule.target),
                    reference_type=self._get_ref_type(rule.rule_type, "target"),
                    available=[str(x) for x in target_set] if target_set else []
                ))

        return result

    def _get_reference_set(self, rule_type: str, which: str,
                           tech: set, cap: set, bundles: set, pts: set) -> Optional[set]:
        """Get the appropriate reference set for a rule type and position."""
        mapping = {
            "technology-technology": (tech, tech),
            "technology-capability": (tech, cap),
            "capability-capability": (cap, cap),
            "bundle-bundle": (bundles, bundles),
            "bundle-capability": (bundles, cap),
            "bundle-technology": (bundles, tech),
            "technology-project-type": (tech, pts),
        }
        if rule_type in mapping:
            return mapping[rule_type][0 if which == "subject" else 1]
        return None

    def _get_ref_type(self, rule_type: str, which: str) -> str:
        """Get human-readable reference type for error messages."""
        mapping = {
            "technology-technology": "technology",
            "technology-capability": "technology" if which == "subject" else "capability",
            "capability-capability": "capability",
            "bundle-bundle": "stack_bundle",
            "bundle-capability": "stack_bundle" if which == "subject" else "capability",
            "bundle-technology": "stack_bundle" if which == "subject" else "technology",
            "technology-project-type": "technology" if which == "subject" else "project_type",
        }
        return mapping.get(rule_type, "entity")
