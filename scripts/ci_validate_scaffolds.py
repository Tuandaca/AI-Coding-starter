#!/usr/bin/env python3
"""Canonical scaffold validator.

Single source of truth for validating every canonical FULL scaffold bundle.

Which bundles are FULL is derived from ``core.stack_scaffold.SCAFFOLD_SUPPORT``
(never a hand-maintained list).  How each bundle is validated is defined in
``VALIDATION_REGISTRY`` below.  A bundle missing from the registry fails
closed -- there is no implicit PASS path.

Usage:

    # validate every canonical FULL bundle
    python scripts/ci_validate_scaffolds.py

    # validate a single bundle
    python scripts/ci_validate_scaffolds.py --bundle nextjs-supabase
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stack_scaffold import SCAFFOLD_SUPPORT, scaffold_stack, scaffold_support_for  # noqa: E402

# ---------------------------------------------------------------------------
# Canonical validation registry.
#
# Each entry maps a FULL bundle id to a list of validation steps.  A step is
# ``(cwd_rel, [argv, ...])`` where ``cwd_rel`` is relative to the generated
# scaffold root and ``argv`` is executed with subprocess (list form, no shell).
#
# All entries run sequentially; the bundle passes only if every step returns 0.
# A FULL bundle not present here fails closed.
# ---------------------------------------------------------------------------

ValidationStep = tuple[str, list[str]]

VALIDATION_REGISTRY: dict[str, list[ValidationStep]] = {
    "react-static": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "build"]),
    ],
    "nextjs-supabase": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "build"]),
    ],
    "vue-lite": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "build"]),
    ],
    "nextjs-vercel": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "build"]),
    ],
    "nestjs-postgres": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "build"]),
    ],
    "expo-supabase-mobile": [
        (".", ["npm", "install"]),
        (".", ["npm", "run", "typecheck"]),
    ],
    "fastapi-postgres": [
        (".", ["python", "-m", "pip", "install", "-r", "requirements.txt"]),
        (".", ["python", "-m", "compileall", "."]),
        (".", ["python", "-c", "from src.main import app"]),
    ],
    "ai-rag-python": [
        (".", ["python", "-m", "pip", "install", "-r", "requirements.txt"]),
        (".", ["python", "-m", "compileall", "."]),
        (".", ["python", "-c", "from src.main import app"]),
        (
            ".",
            [
                "python",
                "-c",
                "import src.api.routes.documents, src.api.routes.chat, "
                "src.services.embedding, src.services.vector_search, "
                "src.services.rag, src.models.document",
            ],
        ),
    ],
    "dotnet-postgres": [
        (".", ["dotnet", "restore", "App.csproj"]),
        (".", ["dotnet", "build", "App.csproj", "--no-restore"]),
    ],
    "nextjs-dotnet-postgres": [
        ("client", ["npm", "install"]),
        ("client", ["npm", "run", "build"]),
        ("server", ["dotnet", "restore", "App.csproj"]),
        ("server", ["dotnet", "build", "App.csproj", "--no-restore"]),
    ],
}

# Project name used when generating scaffolds for validation.  ``ci-test``
# deliberately exercises the identifier-normalization layer (hyphens, dots,
# etc. must not leak into C# namespaces, npm names, etc.).
VALIDATION_PROJECT_NAME = "ci-test"


def full_bundles() -> list[str]:
    """Return every bundle declared FULL in canonical scaffold support data."""
    return sorted(b for b, level in SCAFFOLD_SUPPORT.items() if level == "full")


def run_step(scaffold_root: Path, cwd_rel: str, argv: list[str]) -> tuple[int, str, str]:
    """Run one validation step; return (returncode, stdout, stderr).

    The executable is resolved via :func:`shutil.which` so Windows shim
    scripts (``npm.cmd``) are found without invoking a shell.
    """
    executable = shutil.which(argv[0])
    cmd = [executable] + argv[1:] if executable else argv
    cwd = scaffold_root / cwd_rel
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def validate_bundle(bundle_id: str) -> tuple[bool, str]:
    """Validate one FULL bundle.  Returns (ok, message)."""
    if scaffold_support_for(bundle_id) != "full":
        return False, f"{bundle_id} is not declared FULL"
    if bundle_id not in VALIDATION_REGISTRY:
        return False, f"{bundle_id}: no validation strategy registered (fail closed)"

    scaffold_root = Path(tempfile.mkdtemp(prefix=f"validate-{bundle_id}-"))
    try:
        scaffold_stack(scaffold_root, bundle_id, VALIDATION_PROJECT_NAME)
        for cwd_rel, argv in VALIDATION_REGISTRY[bundle_id]:
            code, out, err = run_step(scaffold_root, cwd_rel, argv)
            if code != 0:
                tail = (err or out or "").strip()[-800:]
                return False, f"{bundle_id}: step {' '.join(argv)} failed in {cwd_rel}\\n{tail}"
        return True, f"{bundle_id}: PASS"
    except Exception as exc:  # noqa: BLE001 - report any infrastructure failure
        return False, f"{bundle_id}: validation error: {exc}"
    finally:
        shutil.rmtree(scaffold_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical FULL scaffolds.")
    parser.add_argument("--bundle", help="Validate a single bundle id instead of all FULL bundles.")
    args = parser.parse_args(argv)

    if args.bundle:
        bundles = [args.bundle]
    else:
        bundles = full_bundles()

    failures: list[str] = []
    for bundle_id in bundles:
        ok, message = validate_bundle(bundle_id)
        print(message)
        if not ok:
            failures.append(bundle_id)

    if failures:
        print(f"\\nFAILED bundles: {failures}", file=sys.stderr)
        return 1
    print(f"\\nAll {len(bundles)} FULL scaffold bundle(s) validated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
