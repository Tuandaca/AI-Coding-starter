"""
Integration test matrix: 10 project types × 4 runtimes.

Run with: python -m core.integration_test_matrix
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import new_project


# Test matrix: project_type -> (type_index, expected_bundle)
# Uses canonical project type IDs from catalog/project-types.yaml
TEST_MATRIX = [
    ("saas", "16", "nextjs-dotnet-postgres"),
    ("portfolio", "14", "react-static"),
    ("blog-content", "4", "nextjs-dotnet-postgres"),
    ("landing-page", "10", "react-static"),
    ("mobile-application", "11", "expo-supabase-mobile"),
    ("desktop-application", "7", "tauri-react-sqlite"),
    ("ai-rag", "2", "ai-rag-python"),
    ("backend-api", "3", "fastapi-postgres"),
    ("fullstack-application", "9", "nestjs-postgres"),
    ("dashboard", "6", "react-static"),
]

RUNTIMES = ["portable", "codex", "opencode", "claude-code", "cursor"]


def run_wizard(project_name: str, project_path: Path, type_index: str, bundle_index: str = "", runtime: str = "1") -> tuple[bool, str]:
    """Run the new_project wizard with mocked inputs."""
    inputs = iter([
        project_name,
        str(project_path),
        type_index,
        "",   # capabilities (defaults)
        bundle_index,  # bundle (first)
        "1",  # team pack (first)
        runtime,  # runtime
        "y",  # confirm
    ])
    
    def fake_get_input(prompt, default=None):
        try:
            return next(inputs)
        except StopIteration:
            return default if default else ""
    
    with patch("new_project.get_input", side_effect=fake_get_input):
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            new_project.main()
            return True, ""
        except SystemExit as e:
            return e.code == 0, ""
        except Exception as e:
            return False, str(e)
        finally:
            sys.stdout = old_stdout


def check_project_structure(project_root: Path, runtime: str) -> dict[str, bool]:
    """Verify generated project has expected structure."""
    checks = {}
    
    # Canonical state
    checks["project.yaml"] = (project_root / ".ai-coding-starter" / "project.yaml").exists()
    checks["state.yaml"] = (project_root / ".ai-coding-starter" / "state.yaml").exists()
    checks["resources.lock"] = (project_root / ".ai-coding-starter" / "resources.lock").exists()
    
    # Portable workspace
    checks["ai-workspace"] = (project_root / ".ai-workspace").exists()
    checks["ai-workspace/agents"] = (project_root / ".ai-workspace" / "agents").exists()
    
    # Derived markdown
    checks["AGENTS.md"] = (project_root / "AGENTS.md").exists()
    checks["CONTEXT.md"] = (project_root / "CONTEXT.md").exists()
    checks["HANDOFF.md"] = (project_root / "HANDOFF.md").exists()
    
    # Runtime adapters (if not portable)
    if runtime != "portable":
        if runtime == "codex":
            checks[".codex"] = (project_root / ".codex").exists()
        elif runtime == "opencode":
            checks[".opencode"] = (project_root / ".opencode").exists()
        elif runtime == "antigravity":
            checks[".agent"] = (project_root / ".agent").exists()
        elif runtime == "claude-code":
            checks[".claude"] = (project_root / ".claude").exists()
        elif runtime == "cursor":
            checks[".cursor"] = (project_root / ".cursor").exists()
    
    return checks


def run_integration_test(project_type: str, type_index: str, expected_bundle: str, runtime: str, runtime_index: str) -> dict[str, Any]:
    """Run a single integration test."""
    project_name = f"test-{project_type}-{runtime}"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"integration_{project_type}_{runtime}_"))
    
    start = time.perf_counter()
    success, error = run_wizard(project_name, temp_dir, type_index, "", runtime_index)
    duration = time.perf_counter() - start
    
    result = {
        "project_type": project_type,
        "runtime": runtime,
        "success": success,
        "error": error,
        "duration_sec": duration,
        "checks": {},
    }
    
    if success:
        project_root = temp_dir / project_name
        if project_root.exists():
            result["checks"] = check_project_structure(project_root, runtime)
            result["checks"]["all_passed"] = all(result["checks"].values())
            
            # TEST-02: Verify expected_bundle against generated canonical state
            import yaml
            spec_path = project_root / ".ai-coding-starter" / "project.yaml"
            if spec_path.exists():
                try:
                    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
                    actual_bundle = spec.get("project", {}).get("stack_bundle", "")
                    bundle_match = (actual_bundle == expected_bundle)
                    result["checks"]["expected_bundle"] = bundle_match
                    result["checks"]["all_passed"] = all(result["checks"].values())
                    if not bundle_match:
                        result["error"] = f"Bundle mismatch: expected {expected_bundle}, got {actual_bundle}"
                except Exception as e:
                    result["checks"]["expected_bundle"] = False
                    result["error"] = f"Failed to read project.yaml: {e}"
        else:
            result["success"] = False
            result["error"] = "Project directory not created"
    
    return result


def run_matrix():
    """Run full integration test matrix."""
    print("=" * 80)
    print("Integration Test Matrix: Project Types × Runtimes")
    print("=" * 80)
    print()
    
    results = []
    
    # Test each project type with portable runtime (fastest)
    for project_type, type_index, expected_bundle in TEST_MATRIX:
        print(f"Testing {project_type} (portable)...")
        result = run_integration_test(project_type, type_index, expected_bundle, "portable", "1")
        results.append(result)
        status = "PASS" if result["success"] and result["checks"].get("all_passed", False) else "FAIL"
        print(f"  {status} ({result['duration_sec']:.1f}s)")
        if not result["success"]:
            print(f"    Error: {result['error']}")
        elif not result["checks"].get("all_passed", False):
            failed = [k for k, v in result["checks"].items() if not v]
            print(f"    Failed checks: {failed}")
    
    RUNTIME_INDEX = {
        "portable": "1",
        "codex": "2",
        "opencode": "3",
        "antigravity": "4",
        "claude-code": "5",
        "cursor": "6",
    }

    # Test one project type with all runtimes
    print("\nTesting saas with all runtimes...")
    for runtime in RUNTIMES:
        runtime_index = RUNTIME_INDEX[runtime]
        print(f"  Testing saas ({runtime})...")
        result = run_integration_test("saas", "16", "nextjs-dotnet-postgres", runtime, runtime_index)
        results.append(result)
        status = "PASS" if result["success"] and result["checks"].get("all_passed", False) else "FAIL"
        print(f"    {status} ({result['duration_sec']:.1f}s)")
        if not result["success"]:
            print(f"      Error: {result['error']}")
        elif not result["checks"].get("all_passed", False):
            failed = [k for k, v in result["checks"].items() if not v]
            print(f"      Failed checks: {failed}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["success"] and r["checks"].get("all_passed", False))
    total = len(results)
    
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print()
    
    # Group by project type
    by_type = {}
    for r in results:
        key = f"{r['project_type']}/{r['runtime']}"
        by_type[key] = r
    
    print(f"{'Project Type':<15} {'Runtime':<12} {'Status':<6} {'Time':>8} {'Details'}")
    print("-" * 80)
    for key, r in by_type.items():
        status = "PASS" if r["success"] and r["checks"].get("all_passed", False) else "FAIL"
        details = ""
        if not r["success"]:
            details = f"Error: {r['error'][:50]}"
        elif not r["checks"].get("all_passed", False):
            failed = [k for k, v in r["checks"].items() if not v]
            details = f"Failed: {', '.join(failed[:3])}"
        print(f"{r['project_type']:<15} {r['runtime']:<12} {status:<6} {r['duration_sec']:>7.1f}s  {details}")
    
    # Save results
    output_path = Path("integration_test_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "total": total,
            "passed": passed,
            "results": results
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")
    
    return passed == total


if __name__ == "__main__":
    success = run_matrix()
    sys.exit(0 if success else 1)