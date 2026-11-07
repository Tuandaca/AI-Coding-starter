#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maintainer-side release packaging script (M6/V2.1).

Builds a deterministic, end-user-ready release ZIP for AI-Coding-starter.

Usage:
    python scripts/build_release.py --version 2.1.0

Output:
    dist/AI-Coding-Starter-v2.1.0.zip

Stdlib-only. No network. No mutation outside `dist/`.

Release ZIP contents (runtime-required tree):

    README.md
    LICENSE
    THIRD_PARTY_NOTICES.md
    CHANGELOG.md
    VERSION
    setup.bat
    setup.sh
    new_project.py
    migrate_project.py
    analytics.py
    config.json
    core/
    catalog/
    resources/
    runtime-adapters/
    scripts/
    schemas/

Development-only content is excluded:

    .git/, .github/, tests/, __pycache__/, *.pyc, dist/, IDE settings,
    local config, temporary files.

The ZIP uses a deterministic top-level folder:

    AI-Coding-Starter-v2.1.0/
        README.md
        ...
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files at repo root that are runtime-required (always included).
ROOT_RUNTIME_FILES = (
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "VERSION",
    "setup.bat",
    "setup.sh",
    "new_project.py",
    "migrate_project.py",
    "analytics.py",
    "config.json",
)

# Directory trees that are runtime-required.
RUNTIME_DIRS = (
    "core",
    "catalog",
    "resources",
    "runtime-adapters",
    "scripts",
    "schemas",
)

# Name fragments that mark development-only content to exclude.
DEVELOPMENT_ONLY = (
    ".git",
    ".github",
    "tests",
    "__pycache__",
    "dist",
    ".vscode",
    ".idea",
    ".DS_Store",
)

# Extensions that mark development-only artifacts.
DEVELOPMENT_EXTENSIONS = (
    ".pyc",
    ".pyo",
    ".egg-info",
)


def _is_development_only(path: Path, relative_to: Path) -> bool:
    """Return True if ``path`` is development-only content to exclude."""
    rel = path.relative_to(relative_to)
    parts = set(rel.parts)
    if parts & set(DEVELOPMENT_ONLY):
        return True
    if path.suffix in DEVELOPMENT_EXTENSIONS:
        return True
    return False


def _collect_tree(tree_rel: str) -> list[Path]:
    """Collect all files under a runtime-required directory tree."""
    tree_root = REPO_ROOT / tree_rel
    if not tree_root.is_dir():
        print(f"WARNING: runtime-required directory not found: {tree_rel}")
        return []
    found: list[Path] = []
    for root, dirs, files in os.walk(tree_root):
        # Prune development-only directories in-place.
        dirs[:] = [d for d in dirs if not _is_development_only(
            Path(root) / d, REPO_ROOT
        )]
        for name in files:
            file_path = Path(root) / name
            if _is_development_only(file_path, REPO_ROOT):
                continue
            found.append(file_path)
    return found


def _collect_root_files() -> list[Path]:
    """Collect runtime-required root files."""
    found: list[Path] = []
    for name in ROOT_RUNTIME_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            found.append(path)
        else:
            print(f"WARNING: runtime-required root file not found: {name}")
    return found


def _copy_into_staging(files: list[Path], staging_folder: Path) -> list[Path]:
    """Copy collected files into the staging folder, preserving relative
    repo structure. Returns the list of staged paths."""
    staged: list[Path] = []
    for src in files:
        rel = src.relative_to(REPO_ROOT)
        dest = staging_folder / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        staged.append(dest)
    return staged


def _zip_entry_name(path: Path, zip_root: Path) -> str:
    """Compute the ZIP entry name (top-level folder included)."""
    rel = path.relative_to(zip_root)
    return f"{zip_root.name}/{rel.as_posix()}"


def build_release(version: str) -> Path:
    """Build the release ZIP and return its path."""
    if not version:
        raise ValueError("version must not be empty")

    zip_folder_name = f"AI-Coding-Starter-v{version}"
    zip_name = f"{zip_folder_name}.zip"

    # Build into a temporary staging directory (deterministic, outside repo).
    staging_root = Path(tempfile.mkdtemp(prefix="build_release_"))
    try:
        staging_folder = staging_root / zip_folder_name
        staging_folder.mkdir(parents=True, exist_ok=False)

        files: list[Path] = []
        files.extend(_collect_root_files())
        for tree_rel in RUNTIME_DIRS:
            files.extend(_collect_tree(tree_rel))

        # Deterministic ordering (by repo-relative path).
        files.sort(key=lambda p: p.relative_to(REPO_ROOT).as_posix())

        # Copy into staging so ZIP is built from the package layout.
        staged = _copy_into_staging(files, staging_folder)

        dist_dir = REPO_ROOT / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        zip_path = dist_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for staged_path in staged:
                # Reject symlink escape (safety guard).
                if staged_path.is_symlink():
                    target = os.readlink(staged_path)
                    resolved = (staged_path.parent / target).resolve()
                    if resolved != staging_folder and \
                            staging_folder not in resolved.parents:
                        print(
                            f"WARNING: skipping symlink that escapes "
                            f"package: {staged_path}"
                        )
                        continue
                arcname = _zip_entry_name(staged_path, staging_folder)
                zf.write(staged_path, arcname=arcname)

        # SHA-256 companion file.
        sha_path = dist_dir / f"{zip_name}.sha256"
        h = hashlib.sha256()
        with open(zip_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        sha_path.write_text(h.hexdigest() + "\n", encoding="utf-8")

        print(f"Built release ZIP: {zip_path}")
        print(f"SHA-256:           {h.hexdigest()}")
        print(f"Files included:    {len(files)}")
        return zip_path
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, end-user-ready release ZIP for AI-Coding-starter.",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Release version (e.g. 2.1.0).",
    )
    args = parser.parse_args(argv)

    build_release(args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
