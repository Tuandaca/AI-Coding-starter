#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V1 → V2 portable state migration CLI (M8).

One-time, safe enhancement path for existing V1 projects:

    V1 project  →  detect  →  analyze  →  preview  →  confirm  →  apply

Usage:
    python migrate_project.py <project-path>        # interactive (default: NO)
    python migrate_project.py <project-path> --yes  # confirm without prompt
    python migrate_project.py <project-path> --dry-run  # detect + preview, zero writes

Migration is opt-in, non-destructive, offline, and reversible (delete
.ai-coding-starter/ to roll back). Legacy V1 files (.agent/**, GEMINI.md,
CONTEXT.md, user source) are never modified; only .ai-coding-starter/ is
written, and only after explicit confirmation.

Business logic lives in core.migration; this module is a thin CLI boundary.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.migration import (
    MigrationResult,
    analyze_v1_project,
    apply_plan,
    build_migration_plan,
    detect_v1_project,
    preview_plan,
    rollback_migration,
)


def _confirm_interactive() -> bool:
    """Ask for explicit confirmation. Default is NO.

    Empty / EOF / any non-"y" answer means NO. Returns True only on "y"/"yes".
    """
    try:
        answer = input("Proceed? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print("Migration cancelled (no input).")
        return False
    return answer in ("y", "yes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate a V1 project to V2 portable canonical state (M8).",
    )
    parser.add_argument(
        "project",
        help="Path to the V1 project directory to migrate.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation and apply the migration directly.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect, analyze, and preview without writing anything.",
    )
    args = parser.parse_args(argv)

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(f"Error: not a directory: {project_path}", file=sys.stderr)
        return 2

    # Step 1: detect (read-only, side-effect free).
    detection = detect_v1_project(project_path)
    print(f"Detection: {detection.confidence} confidence")
    for r in detection.reasons:
        print(f"  - {r}")

    if detection.already_migrated:
        print("Already migrated: .ai-coding-starter/project.yaml exists. No action needed.")
        return 0

    if detection.partial_v2_state:
        print(
            "Partial V2 canonical state detected (.ai-coding-starter/ without "
            "project.yaml). Manual review required; refusing to migrate.",
        )
        return 3

    if not detection.is_v1_project:
        print("Not a V1 project (no legacy markers detected). No action needed.")
        return 0

    # Step 2: analyze (conservative inference).
    analysis = analyze_v1_project(project_path, detection)

    # Step 3: build plan (in memory, validate before writing).
    plan = build_migration_plan(project_path, analysis, dry_run=args.dry_run)

    # Step 4: preview.
    print()
    print(preview_plan(plan))

    if args.dry_run:
        print("Dry run complete: zero writes performed.")
        return 0

    # Step 5: confirmation.
    confirmed = args.yes or _confirm_interactive()
    if not confirmed:
        print("Migration cancelled (no confirmation).")
        return 0

    # Step 6: apply.
    result = apply_plan(plan, confirmed=True)
    if result.errors:
        for e in result.errors:
            print(f"Error: {e}", file=sys.stderr)
        return 4

    print()
    print("Migration applied successfully.")
    print(f"  Created: {', '.join(result.created_files) or '(none)'}")
    print(f"  Preserved: {', '.join(result.preserved_files)}")
    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    print("Rollback: delete .ai-coding-starter/ to restore V1 behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
