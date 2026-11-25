#!/usr/bin/env python3
"""Validate release identity: the tag being published must match VERSION.

Checks:
  * tag == "v" + VERSION
  * pyproject.toml version == VERSION

Exits non-zero on any mismatch so a release cannot be published from a
ref whose identity does not agree with the canonical version files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _read_version() -> str:
    return Path("VERSION").read_text(encoding="utf-8").strip()


def _read_pyproject_version() -> str | None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def main(argv: list[str]) -> int:
    ref = argv[1] if len(argv) > 1 else ""
    tag = ref
    if tag.startswith("refs/tags/"):
        tag = tag[len("refs/tags/"):]
    tag = tag.strip()

    version = _read_version()
    pyproject_version = _read_pyproject_version()

    errors: list[str] = []
    if pyproject_version is None:
        errors.append("pyproject.toml has no version field")
    elif pyproject_version != version:
        errors.append(
            f"pyproject version {pyproject_version!r} != VERSION {version!r}"
        )

    expected_tag = "v" + version
    if tag != expected_tag:
        errors.append(f"tag {tag!r} != expected {expected_tag!r}")

    if errors:
        for error in errors:
            print(f"RELEASE IDENTITY MISMATCH: {error}", file=sys.stderr)
        return 1

    print(f"Release identity OK: tag={tag} version={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
