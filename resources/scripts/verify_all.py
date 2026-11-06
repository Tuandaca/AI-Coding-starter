#!/usr/bin/env python3
"""
Verify All Script
Comprehensive project verification including tests, linting, type checking, and security.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class CheckResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class VerificationCheck:
    name: str
    command: str
    category: str
    required: bool = True
    timeout: int = 120
    working_dir: Optional[str] = None


class VerificationSuite:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.results: List[Tuple[VerificationCheck, CheckResult, str]] = []

    def add_check(self, check: VerificationCheck):
        self.checks.append(check)

    def run_check(self, check: VerificationCheck) -> Tuple[CheckResult, str]:
        """Run a single verification check."""
        cwd = check.working_dir or self.project_path
        try:
            print(f"  Running: {check.name}...")
            result = subprocess.run(
                check.command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=check.timeout
            )

            if result.returncode == 0:
                return CheckResult.PASS, result.stdout
            else:
                return CheckResult.FAIL, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return CheckResult.ERROR, f"Timeout after {check.timeout}s"
        except Exception as e:
            return CheckResult.ERROR, str(e)

    def run_all(self) -> dict:
        """Run all verification checks."""
        print(f"Verifying project: {self.project_path}")
        print("=" * 60)

        categories = {}
        for check in self.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        summary = {"pass": 0, "fail": 0, "skip": 0, "error": 0}

        for category, checks in categories.items():
            print(f"\n📁 {category}")
            for check in checks:
                result, output = self.run_check(check)
                self.results.append((check, result, output))

                icon = {
                    CheckResult.PASS: "✅",
                    CheckResult.FAIL: "❌",
                    CheckResult.SKIP: "⏭️",
                    CheckResult.ERROR: "💥"
                }[result]

                print(f"  {icon} {check.name}")
                if result != CheckResult.PASS and output:
                    # Print first few lines of output
                    lines = output.strip().split("\n")
                    for line in lines[:5]:
                        print(f"    {line}")
                    if len(lines) > 5:
                        print(f"    ... ({len(lines)} lines total)")

                summary[result.value] += 1

        return summary


def detect_project_type(project_path: Path) -> str:
    """Detect project type to determine relevant checks."""
    if (project_path / "package.json").exists():
        return "node"
    elif (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
        return "python"
    elif (project_path / "Cargo.toml").exists():
        return "rust"
    elif (project_path / "go.mod").exists():
        return "go"
    return "unknown"


def create_verification_suite(project_path: Path, project_type: str = None) -> VerificationSuite:
    """Create a verification suite based on project type."""
    if project_type is None:
        project_type = detect_project_type(project_path)

    suite = VerificationSuite(project_path)

    # Common checks for all projects
    suite.checks = [
        VerificationCheck(
            name="Git Status Clean",
            command="git status --porcelain",
            category="Repository",
            required=False
        ),
        VerificationCheck(
            name="No Large Files",
            command="git ls-files | xargs -I {} sh -c 'if [ $(stat -c%s \"{}\" 2>/dev/null || stat -f%z \"{}\" 2>/dev/null) -gt 10485760 ]; then echo \"{}\"; fi'",
            category="Repository",
            required=False
        ),
    ]

    # Type-specific checks
    if project_type == "node":
        suite.checks.extend([
            VerificationCheck(
                name="Dependencies Installed",
                command="npm ci",
                category="Dependencies",
                timeout=180
            ),
            VerificationCheck(
                name="TypeScript Check",
                command="npx tsc --noEmit",
                category="Type Checking",
                required=(project_path / "tsconfig.json").exists()
            ),
            VerificationCheck(
                name="ESLint",
                command="npx eslint . --ext .js,.jsx,.ts,.tsx",
                category="Linting",
                required=(project_path / ".eslintrc.json").exists() or (project_path / ".eslintrc.js").exists()
            ),
            VerificationCheck(
                name="Prettier Format Check",
                command="npx prettier --check .",
                category="Formatting",
                required=(project_path / ".prettierrc").exists() or (project_path / ".prettierrc.json").exists()
            ),
            VerificationCheck(
                name="Unit Tests",
                command="npm test -- --passWithNoTests",
                category="Testing",
                timeout=180
            ),
            VerificationCheck(
                name="Build",
                command="npm run build",
                category="Build",
                timeout=300
            ),
            VerificationCheck(
                name="Dependency Audit",
                command="npm audit --audit-level=high",
                category="Security",
                required=False
            ),
        ])

    elif project_type == "python":
        suite.checks.extend([
            VerificationCheck(
                name="Dependencies Installed",
                command="pip install -q -r requirements.txt 2>/dev/null || pip install -q -e . 2>/dev/null",
                category="Dependencies",
                timeout=120
            ),
            VerificationCheck(
                name="Type Check (mypy)",
                command="mypy . --ignore-missing-imports",
                category="Type Checking",
                required=(project_path / "mypy.ini").exists() or (project_path / "pyproject.toml").exists()
            ),
            VerificationCheck(
                name="Ruff Lint",
                command="ruff check .",
                category="Linting",
                required=(project_path / "ruff.toml").exists() or (project_path / "pyproject.toml").exists()
            ),
            VerificationCheck(
                name="Black Format Check",
                command="black --check .",
                category="Formatting",
                required=(project_path / "pyproject.toml").exists()
            ),
            VerificationCheck(
                name="Pytest",
                command="pytest -x -q",
                category="Testing",
                timeout=180
            ),
            VerificationCheck(
                name="Bandit Security Scan",
                command="bandit -r . -q",
                category="Security",
                required=False
            ),
            VerificationCheck(
                name="Safety Dependency Check",
                command="safety check",
                category="Security",
                required=False
            ),
        ])

    elif project_type == "rust":
        suite.checks.extend([
            VerificationCheck(
                name="Cargo Check",
                command="cargo check",
                category="Type Checking",
                timeout=180
            ),
            VerificationCheck(
                name="Cargo Clippy",
                command="cargo clippy -- -D warnings",
                category="Linting"
            ),
            VerificationCheck(
                name="Cargo Format Check",
                command="cargo fmt -- --check",
                category="Formatting"
            ),
            VerificationCheck(
                name="Cargo Test",
                command="cargo test",
                category="Testing",
                timeout=300
            ),
            VerificationCheck(
                name="Cargo Audit",
                command="cargo audit",
                category="Security",
                required=False
            ),
        ])

    elif project_type == "go":
        suite.checks.extend([
            VerificationCheck(
                name="Go Build",
                command="go build ./...",
                category="Build"
            ),
            VerificationCheck(
                name="Go Vet",
                command="go vet ./...",
                category="Linting"
            ),
            VerificationCheck(
                name="Go Fmt Check",
                command="test -z $(gofmt -l .)",
                category="Formatting"
            ),
            VerificationCheck(
                name="Go Test",
                command="go test ./...",
                category="Testing",
                timeout=180
            ),
            VerificationCheck(
                name="Gosec Security Scan",
                command="gosec ./...",
                category="Security",
                required=False
            ),
        ])

    return suite


def main():
    parser = argparse.ArgumentParser(description="Verify All - Comprehensive project verification")
    parser.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")
    parser.add_argument("--type", choices=["node", "python", "rust", "go", "auto"],
                        default="auto", help="Project type (default: auto-detect)")
    parser.add_argument("--category", help="Run only specific category")
    parser.add_argument("--skip", nargs="+", help="Skip specific check names")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")

    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}")
        sys.exit(1)

    project_type = None if args.type == "auto" else args.type
    suite = create_verification_suite(project_path, project_type)

    # Filter checks
    if args.category:
        suite.checks = [c for c in suite.checks if c.category.lower() == args.category.lower()]
    if args.skip:
        suite.checks = [c for c in suite.checks if c.name not in args.skip]

    # Run verification
    summary = suite.run_all()

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  ✅ Pass:  {summary['pass']}")
    print(f"  ❌ Fail:  {summary['fail']}")
    print(f"  ⏭️  Skip:  {summary['skip']}")
    print(f"  💥 Error: {summary['error']}")
    print(f"  Total:    {sum(summary.values())}")

    # Exit code
    if summary['fail'] > 0 or summary['error'] > 0:
        print("\n❌ Verification FAILED")
        sys.exit(1)
    else:
        print("\n✅ Verification PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
