"""
Deterministic, offline stack-bundle resolver for AI-Coding-starter V2 M3.

The resolver consumes canonical concepts (project type ID, selected capability
IDs, catalog data, compatibility rules) and returns a deterministic ranked list
of coherent stack-bundle candidates, or a clear rejection for
invalid/conflicting input. The wizard presents these candidates and records ONE
selected bundle; ranking never permits an incompatible bundle to pass.

Properties:
  * Deterministic: identical input always yields identical ranked output.
  * Offline: no network, no AI API, no LLM, no subprocess, no file writes.
  * Pure where practical: no side effects, runtime-agnostic.
  * LLM-independent: no calls to Codex / OpenCode / Antigravity / etc.

Public entry point: :func:`resolve`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from core.domain.contracts import (
    Compatibility,
    CompatibilityRule,
    StackBundle,
    make_id,
)

# Fixed, deterministic profile preference order. Lower rank = more preferred.
PROFILE_RANK = {
    "fastest-mvp": 0,
    "balanced": 1,
    "scalable": 2,
    "minimal": 3,
    "custom": 4,
}

NOT_DECIDED = "not-decided"
OTHER = "other"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BundleRecommendation:
    """A single recommended stack bundle with resolution metadata."""

    bundle: StackBundle
    coverage: int
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    reason_codes: List[str]
    profile: str

    @property
    def bundle_id(self) -> str:
        return str(self.bundle.id)

    @property
    def name(self) -> str:
        return self.bundle.name

    @property
    def description(self) -> str:
        return self.bundle.description

    @property
    def technologies(self) -> Dict[str, str]:
        return {role: str(tid) for role, tid in self.bundle.technologies.items()}

    @property
    def tradeoffs(self) -> List[str]:
        return list(self.bundle.tradeoffs)

    @property
    def constraints(self) -> List[str]:
        return list(self.bundle.constraints)


@dataclass(frozen=True)
class ResolutionResult:
    """Result of resolving project type + capabilities to stack bundles."""

    ok: bool
    project_type_id: str
    selected_capability_ids: List[str]
    bundles: List[BundleRecommendation] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    reason_codes: List[str] = field(default_factory=list)
    profile_used: Optional[str] = None

    @property
    def recommended_bundle(self) -> Optional[BundleRecommendation]:
        """The top-ranked bundle, or None when there is no recommendation."""
        return self.bundles[0] if self.bundles else None

    @property
    def bundle_count(self) -> int:
        return len(self.bundles)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_str_id(value) -> str:
    """Normalise an ID-like value to a plain string."""
    return str(value)


def _sorted_unique(values: Iterable[str]) -> List[str]:
    """Return deduplicated, sorted values for deterministic iteration."""
    return sorted({str(v) for v in values})


def _profile_rank(profile: str) -> int:
    return PROFILE_RANK.get(profile, len(PROFILE_RANK))


def _error_rules_for(
    subject_set: Set[str],
    rules: Sequence[CompatibilityRule],
    rule_type: Optional[str] = None,
) -> List[CompatibilityRule]:
    """Return error-severity rules whose subject and target are both present.

    ``rule_type`` optionally restricts matching to one compatibility rule type
    (e.g. only ``capability-capability`` when checking selected capabilities).
    """
    hits: List[CompatibilityRule] = []
    for rule in rules:
        if rule.severity != "error":
            continue
        if rule_type is not None and rule.rule_type != rule_type:
            continue
        if _as_str_id(rule.subject) in subject_set and _as_str_id(rule.target) in subject_set:
            hits.append(rule)
    return hits


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def resolve(
    project_type_id: str,
    selected_capability_ids: Sequence[str],
    catalog,
    preferred_bundle_id: Optional[str] = None,
    profile_preference: Optional[str] = None,
) -> ResolutionResult:
    """
    Resolve a project type and selected capabilities to ranked stack bundles.

    Args:
        project_type_id: Canonical project type ID (e.g. ``saas``).
        selected_capability_ids: Canonical capability IDs chosen by the user.
        catalog: Loaded :class:`core.catalog_loader.Catalog`.
        preferred_bundle_id: Optional bundle the user prefers; still validated
            and ranked alongside the rest rather than forced.
        profile_preference: Optional preferred profile; used only as a tie-break
            hint when present, never to override compatibility.

    Returns:
        A :class:`ResolutionResult`. ``ok`` is False when the input is
        invalid or no coherent bundle exists.
    """
    project_type_id = _as_str_id(project_type_id)
    selected = _sorted_unique(selected_capability_ids)

    reason_codes: List[str] = []

    # --- Validate project type --------------------------------------------
    if project_type_id not in catalog.project_types:
        return ResolutionResult(
            ok=False,
            project_type_id=project_type_id,
            selected_capability_ids=selected,
            rejection_reason=(
                f"Unknown project type '{project_type_id}'. "
                f"Available: {', '.join(sorted(catalog.project_types))}"
            ),
            reason_codes=["unknown-project-type"],
        )

    # --- Validate capabilities are known ----------------------------------
    known_capability_ids = {str(c.id) for c in catalog.capabilities.values()}
    unknown_caps = [c for c in selected if c not in known_capability_ids]
    if unknown_caps:
        return ResolutionResult(
            ok=False,
            project_type_id=project_type_id,
            selected_capability_ids=selected,
            rejection_reason=(
                f"Unknown capability IDs: {', '.join(unknown_caps)}. "
                f"Available: {', '.join(sorted(known_capability_ids))}"
            ),
            reason_codes=["unknown-capability"],
        )

    # --- Expand with implied capabilities (transitively) -------------------
    full_selected: Set[str] = set(selected)
    pending: List[str] = list(selected)
    while pending:
        cap_id = pending.pop()
        cap = catalog.capabilities[cap_id]
        for implied_id in cap.implies:
            implied_id = _as_str_id(implied_id)
            if implied_id not in full_selected:
                full_selected.add(implied_id)
                pending.append(implied_id)

    # --- Requires check: every required capability must be present --------
    missing_required: List[str] = []
    for cap_id in sorted(full_selected):
        cap = catalog.capabilities[cap_id]
        for required in cap.requires:
            required_id = _as_str_id(required)
            if required_id not in full_selected:
                missing_required.append(required_id)
    if missing_required:
        missing_required = sorted(set(missing_required))
        return ResolutionResult(
            ok=False,
            project_type_id=project_type_id,
            selected_capability_ids=selected,
            rejection_reason=(
                f"Missing required capability(s): {', '.join(missing_required)} "
                f"for selected capability(s)."
            ),
            reason_codes=["missing-required-capability"] + missing_required,
        )

    # --- Capability-capability conflicts ----------------------------------
    # Two sources are authoritative: explicit capability.conflicts declarations
    # and compatibility rules of type capability-capability.
    conflict_pairs: Set[Tuple[str, str]] = set()
    conflict_reasons: Dict[Tuple[str, str], str] = {}
    for cap_id in full_selected:
        cap = catalog.capabilities[cap_id]
        for other in cap.conflicts:
            other_id = _as_str_id(other)
            if other_id in full_selected:
                pair = tuple(sorted((cap_id, other_id)))
                conflict_pairs.add(pair)
                conflict_reasons.setdefault(
                    pair, "declared as conflicting capabilities"
                )

    all_rules = list(catalog.compatibility.rules)
    for rule in _error_rules_for(
        full_selected, all_rules, rule_type="capability-capability"
    ):
        pair = tuple(sorted((_as_str_id(rule.subject), _as_str_id(rule.target))))
        conflict_pairs.add(pair)
        conflict_reasons.setdefault(pair, rule.reason)

    if conflict_pairs:
        codes = ["capability-conflict"]
        details = []
        for left, right in sorted(conflict_pairs):
            reason = conflict_reasons[(left, right)]
            details.append(f"{left} conflicts with {right} ({reason})")
            codes.append(f"conflict:{left}:{right}")
        return ResolutionResult(
            ok=False,
            project_type_id=project_type_id,
            selected_capability_ids=selected,
            rejection_reason=(
                "Conflicting capabilities selected: " + "; ".join(details)
            ),
            reason_codes=codes,
        )

    # --- Candidate bundles -------------------------------------------------
    if project_type_id == NOT_DECIDED:
        candidate_bundles = list(catalog.stack_bundles.values())
        # Conservative policy for undecided: show broad starters, no rejection.
        reason_codes.append("not-decided-broad-options")
    elif project_type_id == OTHER:
        candidate_bundles = list(catalog.stack_bundles.values())
        # "Other" has no dedicated bundle by definition. Rank all coherent
        # starters by the selected capabilities so the wizard never dead-ends.
        reason_codes.append("other-broad-options")
    else:
        candidate_bundles = [
            b for b in catalog.stack_bundles.values()
            if project_type_id in {str(p) for p in b.project_types}
        ]

    # --- Filter out bundles that violate internal technology conflicts -----
    compatible_bundles: List[StackBundle] = []
    for bundle in candidate_bundles:
        values = {str(tid) for tid in bundle.technologies.values()}
        violations = _error_rules_for(
            values, all_rules, rule_type="technology-technology"
        )
        if violations:
            # Bundle is internally incompatible; exclude it.
            reason_codes.append(f"bundle-internal-conflict:{bundle.id}")
            continue
        compatible_bundles.append(bundle)

    if not compatible_bundles:
        return ResolutionResult(
            ok=False,
            project_type_id=project_type_id,
            selected_capability_ids=selected,
            rejection_reason=(
                "No coherent stack bundle matches the selected project type "
                "and capabilities."
            ),
            reason_codes=reason_codes or ["no-compatible-bundle"],
        )

    # --- Preferred bundle hint (validated, not forced) --------------------
    if preferred_bundle_id is not None:
        preferred_bundle_id = _as_str_id(preferred_bundle_id)
        if preferred_bundle_id not in {str(b.id) for b in compatible_bundles}:
            # Unknown/unsupported preference is ignored deterministically.
            reason_codes.append("preferred-bundle-ignored")
            preferred_bundle_id = None

    # --- Score and rank ----------------------------------------------------
    profile_hint = profile_preference if profile_preference in PROFILE_RANK else None

    scored: List[Tuple[int, int, int, str, StackBundle]] = []
    for bundle in compatible_bundles:
        bundle_caps = {str(c) for c in bundle.capabilities}
        coverage = len(full_selected & bundle_caps)
        # Deterministic sort key:
        #   1. Higher capability coverage first (negated).
        #   2. A valid preferred bundle first (hint, never forced over coverage).
        #   3. Preferred profile first (if a hint is given), else fixed rank.
        #   4. Bundle id ascending (final tie-break).
        preferred_sort = 0 if str(bundle.id) == preferred_bundle_id else 1
        profile_rank = _profile_rank(bundle.profile)
        if profile_hint is not None and bundle.profile == profile_hint:
            profile_sort = 0
        else:
            profile_sort = profile_rank
        scored.append(
            (-coverage, preferred_sort, profile_sort, str(bundle.id), bundle)
        )

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]))

    # --- Build recommendations ---------------------------------------------
    recommendations: List[BundleRecommendation] = []
    for _neg_coverage, _preferred_sort, _profile_sort, _bundle_id, bundle in scored:
        bundle_caps = {str(c) for c in bundle.capabilities}
        matched = sorted(full_selected & bundle_caps)
        missing = sorted(full_selected - bundle_caps)
        bundle_reason_codes: List[str] = []
        if str(bundle.id) == preferred_bundle_id:
            bundle_reason_codes.append("preferred")
        if matched:
            bundle_reason_codes.append("capability-match")
        if not matched:
            bundle_reason_codes.append("no-capability-match")
        recommendations.append(
            BundleRecommendation(
                bundle=bundle,
                coverage=len(matched),
                matched_capabilities=matched,
                missing_capabilities=missing,
                reason_codes=bundle_reason_codes,
                profile=bundle.profile,
            )
        )

    return ResolutionResult(
        ok=True,
        project_type_id=project_type_id,
        selected_capability_ids=selected,
        bundles=recommendations,
        reason_codes=reason_codes,
        profile_used=profile_hint,
    )


def resolve_top(
    project_type_id: str,
    selected_capability_ids: Sequence[str],
    catalog,
    preferred_bundle_id: Optional[str] = None,
    profile_preference: Optional[str] = None,
    limit: int = 5,
) -> ResolutionResult:
    """Convenience: resolve and cap the number of returned bundles."""
    result = resolve(
        project_type_id,
        selected_capability_ids,
        catalog,
        preferred_bundle_id=preferred_bundle_id,
        profile_preference=profile_preference,
    )
    if result.ok and limit is not None and limit >= 0:
        result = ResolutionResult(
            ok=result.ok,
            project_type_id=result.project_type_id,
            selected_capability_ids=result.selected_capability_ids,
            bundles=result.bundles[:limit],
            rejection_reason=result.rejection_reason,
            reason_codes=result.reason_codes,
            profile_used=result.profile_used,
        )
    return result


__all__ = [
    "resolve",
    "resolve_top",
    "ResolutionResult",
    "BundleRecommendation",
    "PROFILE_RANK",
    "NOT_DECIDED",
    "OTHER",
]
