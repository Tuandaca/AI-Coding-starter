#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic security validation for Node-based FULL scaffold bundles.

For every canonical FULL bundle that ships a ``package.json`` (root or
``client/`` for nextjs-dotnet-postgres), this:

  1. Generates the scaffold from offline templates.
  2. Runs ``npm install --no-audit --no-fund``.
  3. Runs ``npm audit --audit-level=high --json``.

Exits non-zero if any bundle reports a high or critical advisory, so CI is a
real fail-closed security gate (advisories are NOT silently downgraded).

Direct-dependency findings are printed so they can be triaged for user risk
acceptance or a compatible dependency upgrade.

Offline after the templates are generated; requires Node.js + npm.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.stack_scaffold import (  # noqa: E402
    BUNDLE_TEMPLATES,
    SCAFFOLD_SUPPORT,
    scaffold_stack,
)

NPM = [
    "C:\\Program Files\\nodejs\\node.exe",
    "C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js",
] if sys.platform == "win32" else ["npm"]

FULL_NODE_BUNDLES = [
    b for b, level in SCAFFOLD_SUPPORT.items()
    if level == "full" and b in BUNDLE_TEMPLATES
]


def _find_package_json(root: Path) -> Path | None:
    if (root / "package.json").is_file():
        return root / "package.json"
    if (root / "client" / "package.json").is_file():
        return root / "client" / "package.json"
    return None


def _npm(cwd: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        NPM + args, cwd=cwd, capture_output=True, text=True, timeout=420
    )


def _audit_bundle(bundle_id: str) -> list[str]:
    """Audit a single Node FULL bundle; return list of error messages."""
    errors: list[str] = []
    td = Path(tempfile.mkdtemp())
    try:
        dest = td / bundle_id
        try:
            scaffold_stack(dest, bundle_id, "sec-audit")
        except Exception as exc:
            return [f"{bundle_id}: scaffold generation failed: {exc}"]
        pkg_dir = None
        for cand in (dest, dest / "client"):
            if (cand / "package.json").is_file():
                pkg_dir = cand
                break
        if pkg_dir is None:
            print(f"  [skip] {bundle_id}: no package.json (not a Node scaffold)")
            return errors
        print(f"  [audit] {bundle_id} ({pkg_dir.relative_to(dest)})")
        install = _npm(pkg_dir, ["install", "--no-audit", "--no-fund"])
        if install.returncode != 0:
            errors.append(f"{bundle_id}: npm install failed: {install.stderr[-300:]}")
            return errors
        audit = _npm(pkg_dir, ["audit", "--audit-level=high", "--json"])
        try:
            data = json.loads(audit.stdout)
        except Exception:
            errors.append(f"{bundle_id}: npm audit JSON parse failed")
            return errors
        meta = data.get("metadata", {}).get("vulnerabilities", {})
        high = meta.get("high", 0)
        critical = meta.get("critical", 0)
        print(
            f"      vulnerabilities high={high} critical={critical} "
            f"moderate={meta.get('moderate', 0)}"
        )
        direct_findings = []
        for mod, v in (data.get("vulnerabilities") or {}).items():
            if (v.get("severity") or "").lower() in ("high", "critical"):
                direct_findings.append(
                    f"        - {mod} (direct={v.get('isDirect')}): "
                    f"{v.get('severity')} - {v.get('title')}"
                )
        if direct_findings:
            print("      direct-dependency findings:")
            for line in direct_findings:
                print(line)
        if high or critical:
            errors.append(
                f"{bundle_id}: {critical} critical + {high} high "
                f"npm advisory(ies) at --audit-level=high"
            )
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return errors


def main() -> int:
    errors: list[str] = []
    for bundle_id in FULL_NODE_BUNDLES:
        errors.extend(_audit_bundle(bundle_id))

    print()
    if errors:
        print(f"SECURITY AUDIT FAILED ({len(errors)} finding(s)):")
        for e in errors:
            print(f"  - {e}")
        print()
        print("No high/critical advisory was silently downgraded.")
        print("Resolve by upgrading direct dependencies to compatible secure")
        print("versions, or obtain explicit user risk acceptance before release.")
        return 1
    print("SECURITY AUDIT PASSED (no high/critical npm advisories)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
