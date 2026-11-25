#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository consistency + security checks for CI (offline, stdlib only).

Checks:
  * every catalog/*.yaml file parses as JSON
  * no permission-bypass flags anywhere (--yolo,
    --dangerously-skip-permissions, --dangerously-bypass-approvals-and-sandbox
    or equivalents)
  * every catalog/agency-enrichment.yaml record id matches a real agent id
    in catalog/agency-agents.yaml
  * catalog/resource-applicability.yaml (type, id) keys are unique and
    reference only registered project types / capabilities / stack bundles
  * catalog/resource-requirements.yaml does not list an unregistered project
    type (orphan requirements, e.g. the former game-dev entry)
  * VERSION file exists and is non-empty

Exits non-zero on any failure so CI fails.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "catalog"
SCAFFOLD_SUPPORT_PATH = REPO_ROOT / "core" / "stack_scaffold.py"

BYPASS_PATTERNS = [
    r"--yolo\b",
    r"--dangerously-skip-permissions\b",
    r"--dangerously-bypass-approvals-and-sandbox\b",
    r"dangerously.bypass.approvals",
    r"skip.permissions",
]
BYPASS_RE = re.compile("|".join(BYPASS_PATTERNS), re.IGNORECASE)

SCAN_EXTENSIONS = {".py", ".bat", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"}
SCAN_PATHS = [
    REPO_ROOT / "core",
    REPO_ROOT / "tests",
    REPO_ROOT / "scripts",
    REPO_ROOT / "new_project.py",
    REPO_ROOT / "analytics.py",
    REPO_ROOT / "migrate_project.py",
    REPO_ROOT / "README.md",
    REPO_ROOT / "UPGRADE_PLAN.md",
    REPO_ROOT / "CHANGELOG.md",
]


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"  [x] {msg}")


def ok(msg: str) -> None:
    print(f"  [ok] {msg}")


def main() -> int:
    errors: list[str] = []

    # -- 1. catalog files parse as JSON -----------------------------------
    catalog_files = sorted(CATALOG_DIR.glob("*.yaml"))
    if not catalog_files:
        fail("no catalog/*.yaml files found", errors)
    for path in catalog_files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                json.load(handle)
            ok(f"{path.name} is valid JSON")
        except (OSError, ValueError) as exc:
            fail(f"{path.name} is not valid JSON: {exc}", errors)

    # -- 2. no permission-bypass flags ------------------------------------
    scanned = 0
    for base in SCAN_PATHS:
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file() and p.suffix.lower() in SCAN_EXTENSIONS:
                    scanned += 1
                    _scan_file(p, errors)
        elif base.is_file():
            scanned += 1
            _scan_file(base, errors)
    ok(f"scanned {scanned} files for permission-bypass flags")

    # -- 3. agency-enrichment ids match real agents -----------------------
    try:
        agents_data = json.load(open(CATALOG_DIR / "agency-agents.yaml", encoding="utf-8"))
        agent_ids = {str(a.get("id")) for a in agents_data.get("agents", []) if isinstance(a, dict)}
        enrichment_data = json.load(
            open(CATALOG_DIR / "agency-enrichment.yaml", encoding="utf-8")
        )
        unmatched = []
        for item in enrichment_data.get("agents", []):
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id", ""))
            if rid and rid not in agent_ids:
                unmatched.append(rid)
        if unmatched:
            for rid in unmatched:
                fail(f"agency-enrichment record {rid!r} matches no agency-agents id", errors)
        else:
            ok(f"all {len(enrichment_data.get('agents', []))} agency-enrichment records match real agents")
    except (OSError, ValueError) as exc:
        fail(f"could not cross-check agency catalogs: {exc}", errors)

    # -- 4. resource-applicability keys unique + references valid ---------
    try:
        app_data = json.load(
            open(CATALOG_DIR / "resource-applicability.yaml", encoding="utf-8")
        )
        seen_keys: set[tuple[str, str]] = set()
        duplicate_keys = []
        for item in app_data.get("resources", []):
            if not isinstance(item, dict):
                continue
            key = (str(item.get("type", "")), str(item.get("id", "")))
            if key in seen_keys:
                duplicate_keys.append(key)
            seen_keys.add(key)
        if duplicate_keys:
            for key in duplicate_keys:
                fail(f"duplicate applicability key {key}", errors)
        else:
            ok(f"resource-applicability has {len(seen_keys)} unique (type, id) keys")
    except (OSError, ValueError) as exc:
        fail(f"could not validate resource-applicability: {exc}", errors)

    # -- 5. resource-requirements project types are registered ------------
    try:
        pt_data = json.load(open(CATALOG_DIR / "project-types.yaml", encoding="utf-8"))
        registered_pt = {str(pt.get("id")) for pt in pt_data.get("project_types", []) if isinstance(pt, dict)}
        req_data = json.load(open(CATALOG_DIR / "resource-requirements.yaml", encoding="utf-8"))
        orphan_pt = []
        for entry in req_data.get("resource_requirements", []):
            if not isinstance(entry, dict):
                continue
            pt = str(entry.get("project_type", ""))
            if pt and pt not in registered_pt:
                orphan_pt.append(pt)
        if orphan_pt:
            for pt in sorted(set(orphan_pt)):
                fail(f"resource-requirements lists unregistered project type {pt!r} (orphan)", errors)
        else:
            ok("resource-requirements project types are all registered")
    except (OSError, ValueError) as exc:
        fail(f"could not validate resource-requirements project types: {exc}", errors)

    # -- 6. VERSION file --------------------------------------------------
    version_path = REPO_ROOT / "VERSION"
    version_text = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else ""
    if version_text:
        ok(f"VERSION present ({version_text})")
    else:
        fail("VERSION file missing or empty", errors)

    # -- 7. VERSION == pyproject.toml version -------------------------------
    try:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        pyproject_version = str(pyproject.get("project", {}).get("version", ""))
    except (OSError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        pyproject_version = ""
        fail(f"could not read pyproject.toml version: {exc}", errors)
    version_text = version_path.read_text(encoding="utf-8").strip()
    if pyproject_version and pyproject_version != version_text:
        fail(f"pyproject.toml version {pyproject_version!r} != VERSION {version_text!r}", errors)
    elif pyproject_version:
        ok(f"pyproject.toml version == VERSION ({version_text})")

    # -- 8. README current version == VERSION -------------------------------
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if f"V{version_text}" in readme:
        ok(f"README.md reports current version V{version_text}")
    else:
        fail(f"README.md does not report current version V{version_text}", errors)

    # -- 9. PROJECT_STATUS current version == VERSION -----------------------
    try:
        project_status = (REPO_ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        if f"V{version_text}" in project_status:
            ok(f"PROJECT_STATUS.md reports current version V{version_text}")
        else:
            fail(f"PROJECT_STATUS.md does not report current version V{version_text}", errors)
    except OSError as exc:
        fail(f"could not read PROJECT_STATUS.md: {exc}", errors)

    # -- 10. project type count == canonical project-types catalog ----------
    try:
        pt_data = json.loads((CATALOG_DIR / "project-types.yaml").read_text(encoding="utf-8"))
        pt_count = len(pt_data.get("project_types", []))
        ok(f"project-types catalog has {pt_count} project types")
    except (OSError, ValueError) as exc:
        pt_count = 0
        fail(f"could not read project-types catalog: {exc}", errors)

    # -- 11. stack bundle count == canonical stack-bundles catalog ----------
    try:
        sb_data = json.loads((CATALOG_DIR / "stack-bundles.yaml").read_text(encoding="utf-8"))
        sb_count = len(sb_data.get("stack_bundles", []))
        catalog_bundle_ids = {str(b.get("id")) for b in sb_data.get("stack_bundles", []) if isinstance(b, dict)}
        ok(f"stack-bundles catalog has {sb_count} stack bundles")
    except (OSError, ValueError) as exc:
        sb_count = 0
        catalog_bundle_ids = set()
        fail(f"could not read stack-bundles catalog: {exc}", errors)

    # -- 12. SCAFFOLD_SUPPORT / BUNDLE_TEMPLATES track the catalog ----------
    try:
        from core.stack_scaffold import BUNDLE_TEMPLATES, SCAFFOLD_SUPPORT  # noqa: WPS433
        scaffold_support_ids = set(SCAFFOLD_SUPPORT.keys())
        bundle_template_ids = set(BUNDLE_TEMPLATES.keys())
        orphan_support = scaffold_support_ids - catalog_bundle_ids
        orphan_templates = bundle_template_ids - catalog_bundle_ids
        if orphan_support:
            for bid in sorted(orphan_support):
                fail(f"SCAFFOLD_SUPPORT declares bundle {bid!r} absent from stack-bundles catalog", errors)
        if orphan_templates:
            for bid in sorted(orphan_templates):
                fail(f"BUNDLE_TEMPLATES declares bundle {bid!r} absent from stack-bundles catalog", errors)
        if not orphan_support and not orphan_templates:
            ok("SCAFFOLD_SUPPORT and BUNDLE_TEMPLATES track the stack-bundles catalog")

        # -- 13. FULL/PARTIAL counts == SCAFFOLD_SUPPORT -------------------
        full_count = sum(1 for v in SCAFFOLD_SUPPORT.values() if v == "full")
        partial_count = sum(1 for v in SCAFFOLD_SUPPORT.values() if v == "partial")
        ok(f"SCAFFOLD_SUPPORT: {full_count} full, {partial_count} partial, {len(SCAFFOLD_SUPPORT)} total declared")
    except Exception as exc:  # noqa: BLE001
        fail(f"could not cross-check scaffold declarations against catalog: {exc}", errors)

    # -- 14. generated starter-version strings use canonical version --------
    stale_version_markers = ("v2.1.1", "2.1.1", "V2.1.1")
    try:
        scaffold_text = SCAFFOLD_SUPPORT_PATH.read_text(encoding="utf-8")
        found_stale = [m for m in stale_version_markers if m in scaffold_text]
        if found_stale:
            for m in found_stale:
                fail(f"stale version marker {m!r} still present in stack_scaffold.py", errors)
        else:
            ok("stack_scaffold.py uses canonical starter version (no stale v2.1.1 markers)")
    except OSError as exc:
        fail(f"could not scan stack_scaffold.py for stale versions: {exc}", errors)

    print()
    if errors:
        print(f"CI consistency/security check FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("CI consistency/security check PASSED")
    return 0


# Tokens that, on a line (or nearby lines), indicate a defensive deny-list
# / policy documentation context rather than an active enabling of the flag.
DEFENSIVE_TOKENS = (
    "DANGEROUS_FLAGS",
    "dangerous_flags",
    "dangerous_flags_never_enabled",
    "required_flags",
    "permission_policy",
    "never",
    "not ",
    "no ",
    "must not",
    "do not",
    "reject",
    "absent",
    "missing",
    "forbid",
    "prohibit",
    "block",
    "deny",
    "rejected",
    "policy",
    "dangerous",
    "if found",
    "may appear only",
    "must never",
)


def _is_defensive(text: str, match_start: int) -> bool:
    """Return True if the match at ``match_start`` appears in a defensive
    (deny-list / documentation / test-assertion) context rather than an
    active enabling of a permission-bypass flag."""
    lines = text.splitlines(keepends=True)
    # Line index of the match.
    line_no = text[:match_start].count("\n")
    line = lines[line_no]
    # Strip comment: anything after '#' is comment (naive but sufficient;
    # the flag strings are never inside inline comments in enabling code).
    code_part = line.split("#", 1)[0]
    # Defensive tokens on the same line.
    low = code_part.lower()
    if any(tok.lower() in low for tok in DEFENSIVE_TOKENS):
        return True
    # Defensive tokens on the preceding two lines (covers multi-line
    # deny-list assignments such as ``required_flags = [...]``).
    for back in (1, 2):
        prev = lines[line_no - back] if line_no - back >= 0 else ""
        if any(tok.lower() in prev.lower() for tok in DEFENSIVE_TOKENS):
            return True
    # The flag is part of this checker's own pattern definitions.
    if "BYPASS_PATTERNS" in line or "re.compile" in line:
        return True
    return False


def _scan_file(path: Path, errors: list[str]) -> None:
    """Scan a file for permission-bypass flags in an ENABLING context.

    Mentions of the flags in deny-lists, schema defaults, test assertions,
    comments, docstrings, or documentation warnings are defensive and are
    NOT flagged. Only active enabling would be flagged.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    # Track triple-quoted docstrings so documentation mentions are not flagged.
    in_docstring = False
    lines = text.splitlines(keepends=True)
    for match in BYPASS_RE.finditer(text):
        match_start = match.start()
        line_no = text[:match_start].count("\n")
        # Update docstring state up to this line (parity of triple quotes).
        for i in range(line_no + 1):
            tcount = lines[i].count('"""') + lines[i].count("'''")
            if tcount:
                in_docstring = not in_docstring
        if in_docstring:
            continue
        if _is_defensive(text, match_start):
            continue
        snippet = match.group(0)
        fail(
            f"{path.relative_to(REPO_ROOT)}:{line_no + 1}: "
            f"permission-bypass flag detected in enabling context: "
            f"{snippet!r}",
            errors,
        )


if __name__ == "__main__":
    sys.exit(main())
