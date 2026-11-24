"""
Performance benchmarks for AI-Coding-Starter.

Run with: python -m core.benchmarks
"""

from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import new_project
from core.spec import read_project_spec
from core.runtime_adapters import apply_all_adapters
from core.resource_lock import verify_resources_lock, check_updates
from core.agent_manager_bridge import AgentManagerBridge


class BenchmarkResult:
    def __init__(self, name: str):
        self.name = name
        self.times: list[float] = []
    
    def add(self, duration: float):
        self.times.append(duration)
    
    def summary(self) -> dict[str, Any]:
        if not self.times:
            return {"name": self.name, "runs": 0}
        return {
            "name": self.name,
            "runs": len(self.times),
            "mean_ms": statistics.mean(self.times) * 1000,
            "median_ms": statistics.median(self.times) * 1000,
            "stdev_ms": statistics.stdev(self.times) * 1000 if len(self.times) > 1 else 0,
            "min_ms": min(self.times) * 1000,
            "max_ms": max(self.times) * 1000,
        }


def create_test_project() -> Path:
    """Create a test project for benchmarking."""
    temp_dir = Path(tempfile.mkdtemp(prefix="bench_"))
    project_root = temp_dir / "bench-project"
    project_root.mkdir()
    
    ai_dir = project_root / ".ai-coding-starter"
    ai_dir.mkdir()
    
    project_data = {
        "schema_version": "1.0.0",
        "project": {
            "id": "bench-project",
            "name": "bench-project",
            "description": "Benchmark test project",
            "created_at": "2026-11-24T00:00:00Z",
            "updated_at": "2026-11-24T00:00:00Z",
            "project_type": "saas",
            "capabilities": ["email", "search", "auth", "database"],
            "stack_bundle": "nextjs-dotnet-postgres",
            "team_pack": "startup-mvp",
            "specialists": [
                "engineering-backend-architect",
                "engineering-devops-automator",
                "engineering-api-platform-engineer"
            ],
            "technology_overrides": {},
            "runtime_preferences": {"project_local_only": True},
            "provider_preferences": {}
        }
    }
    (ai_dir / "project.yaml").write_text(json.dumps(project_data, indent=2))
    
    state_data = {
        "schema_version": "1.0.0",
        "state": {
            "phase": "planning",
            "focus": "",
            "decisions_pointer": "DECISIONS.md",
            "handoff_pointer": "HANDOFF.md",
            "canonical_branch": "",
            "active_worktrees": [],
            "active_tasks": [],
            "completed_tasks": []
        }
    }
    (ai_dir / "state.yaml").write_text(json.dumps(state_data, indent=2))
    
    lock_data = {
        "schema_version": "1.0.0",
        "lockfile_version": 1,
        "generated_at": "2026-11-24T00:00:00Z",
        "generated_by": "ai-coding-starter-generator",
        "resources": [],
        "stack_bundle_resolution": {
            "requested_bundle": "nextjs-dotnet-postgres",
            "resolved_bundle": "nextjs-dotnet-postgres"
        }
    }
    (ai_dir / "resources.lock").write_text(json.dumps(lock_data, indent=2))
    
    # Create .ai-workspace
    ws_dir = project_root / ".ai-workspace"
    ws_dir.mkdir()
    for d in ["agents", "skills", "workflows", "rules", "scripts", "shared"]:
        (ws_dir / d).mkdir()
    
    # Add some test agents
    for agent_id in ["test-agent-1", "test-agent-2", "test-agent-3"]:
        (ws_dir / "agents" / f"{agent_id}.md").write_text(
            f"# {agent_id}\n\nTest agent description."
        )
    
    return project_root


def benchmark_project_creation(runs: int = 5) -> BenchmarkResult:
    """Benchmark full project creation via new_project.py."""
    result = BenchmarkResult("project_creation")
    
    def fake_get_input(prompt, default=None):
        inputs = {
            "Ten du an": "bench-project",
            "Duong dan du an": str(tempfile.gettempdir()),
        }
        for k, v in inputs.items():
            if k in prompt:
                return v
        if "project type" in prompt.lower() or "loai" in prompt.lower():
            return "5"
        if "capabilit" in prompt.lower():
            return ""
        if "stack" in prompt.lower() or "bundle" in prompt.lower():
            return ""
        if "team pack" in prompt.lower() or "nhom" in prompt.lower():
            return "1"
        if "runtime" in prompt.lower():
            return "1"
        if "confirm" in prompt.lower() or "tao du an" in prompt.lower():
            return "y"
        return default if default else ""
    
    for i in range(runs):
        temp_dir = Path(tempfile.mkdtemp(prefix=f"bench_create_{i}_"))
        
        # Disable color to avoid encoding issues
        import core.cli_ui as cli_ui
        cli_ui.set_color_enabled(False)
        
        with patch("new_project.get_input", side_effect=fake_get_input):
            start = time.perf_counter()
            try:
                new_project.main()
            except SystemExit:
                pass
            duration = time.perf_counter() - start
            result.add(duration)
    
    return result


def benchmark_adapter_application(runs: int = 10) -> BenchmarkResult:
    """Benchmark runtime adapter application."""
    result = BenchmarkResult("adapter_application")
    
    for i in range(runs):
        project_root = create_test_project()
        start = time.perf_counter()
        apply_all_adapters(project_root, force=True)
        duration = time.perf_counter() - start
        result.add(duration)
    
    return result


def benchmark_schema_validation(runs: int = 100) -> BenchmarkResult:
    """Benchmark JSON schema validation."""
    from core.schema_validator import validate_project_spec
    
    project_root = create_test_project()
    spec_path = project_root / ".ai-coding-starter" / "project.yaml"
    raw_data = json.loads(spec_path.read_text())
    
    result = BenchmarkResult("schema_validation")
    
    for _ in range(runs):
        start = time.perf_counter()
        validate_project_spec(raw_data)
        duration = time.perf_counter() - start
        result.add(duration)
    
    return result


def benchmark_lock_verification(runs: int = 20) -> BenchmarkResult:
    """Benchmark resources.lock verification."""
    project_root = create_test_project()
    
    result = BenchmarkResult("lock_verification")
    
    for _ in range(runs):
        start = time.perf_counter()
        verify_resources_lock(project_root)
        duration = time.perf_counter() - start
        result.add(duration)
    
    return result


def benchmark_agent_bridge(runs: int = 10) -> BenchmarkResult:
    """Benchmark AgentManagerBridge operations."""
    project_root = create_test_project()
    
    result = BenchmarkResult("agent_bridge")
    
    for _ in range(runs):
        start = time.perf_counter()
        bridge = AgentManagerBridge(project_root)
        bridge.list_specialists()
        duration = time.perf_counter() - start
        result.add(duration)
    
    return result


def run_all_benchmarks():
    """Run all benchmarks and print summary."""
    print("=" * 70)
    print("AI-Coding-Starter Performance Benchmarks")
    print("=" * 70)
    print()
    
    benchmarks = [
        ("Adapter Application (10 runs)", benchmark_adapter_application, {"runs": 10}),
        ("Schema Validation (100 runs)", benchmark_schema_validation, {"runs": 100}),
        ("Lock Verification (20 runs)", benchmark_lock_verification, {"runs": 20}),
        ("Agent Bridge (10 runs)", benchmark_agent_bridge, {"runs": 10}),
    ]
    
    results = []
    for name, func, kwargs in benchmarks:
        print(f"Running {name}...")
        result = func(**kwargs)
        results.append(result)
        print(f"  Done: {result.summary()['mean_ms']:.1f}ms avg")
        print()
    
    # Summary table
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Benchmark':<35} {'Runs':>5} {'Mean':>10} {'Median':>10} {'Min':>10} {'Max':>10}")
    print("-" * 70)
    for r in results:
        s = r.summary()
        print(f"{s['name']:<35} {s['runs']:>5} {s['mean_ms']:>9.1f}ms {s['median_ms']:>9.1f}ms {s['min_ms']:>9.1f}ms {s['max_ms']:>9.1f}ms")
    print("=" * 70)
    
    # Check targets
    print("\nTARGET CHECKS:")
    targets = {
        "project_creation": 30000,  # 30 seconds
        "adapter_application": 5000,  # 5 seconds
        "schema_validation": 50,  # 50ms
        "lock_verification": 1000,  # 1 second
        "agent_bridge": 100,  # 100ms
    }
    
    for r in results:
        target = targets.get(r.name, 0)
        mean_ms = r.summary()["mean_ms"]
        status = "PASS" if mean_ms < target else "FAIL"
        print(f"  {r.name}: {mean_ms:.1f}ms (target: {target}ms) [{status}]")


if __name__ == "__main__":
    run_all_benchmarks()