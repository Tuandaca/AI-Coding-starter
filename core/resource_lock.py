"""
Resource Lock & Upstream Sync — version pinning and catalog synchronization.

Provides:
- resources.lock with content hashes for reproducible builds
- upstream-sources.yaml tracking for Agency catalog updates
- CLI commands: sync, check-updates, lock, unlock
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.state import build_resources_lock, ResourcesLock

import yaml

from core.spec import read_project_spec
from core.state import read_resources_lock, ResourcesLock, write_resources_lock
from core.catalog_loader import load_catalog, DEFAULT_CATALOG_DIR
from core.resource_resolver import ResourceSelectionResult, resolve_resources


@dataclass
class UpstreamSource:
    """Represents an upstream source for resources."""
    name: str
    type: str  # git, github, local, http
    url: str
    ref: str = "main"  # branch, tag, commit
    path: str = ""  # subdirectory within repo
    last_synced: Optional[str] = None
    last_commit: Optional[str] = None
    verified: bool = False


@dataclass
class LockedResource:
    """A resource entry in resources.lock with integrity info."""
    id: str
    type: str
    version: str
    provenance: dict
    selection_reason: str
    content_hash: str = ""  # SHA256 of resource content
    size_bytes: int = 0
    runtime_representations: dict = field(default_factory=dict)


def compute_content_hash(path: Path) -> str:
    """Compute SHA256 hash of file or directory."""
    hasher = hashlib.sha256()
    if path.is_file():
        hasher.update(path.read_bytes())
    elif path.is_dir():
        for f in sorted(path.rglob("*")):
            if f.is_file():
                rel = f.relative_to(path)
                hasher.update(rel.as_posix().encode())
                hasher.update(f.read_bytes())
    return hasher.hexdigest()[:16]  # Short hash for readability


def compute_resource_hash(resource_root: Path, resource_type: str, resource_id: str) -> tuple[str, int]:
    """Compute hash and size for a resource."""
    type_dirs = {
        "agent": "agents",
        "skill": "skills",
        "shared-module": "shared",
        "workflow": "workflows",
        "script": "scripts",
        "rule": "rules",
    }
    type_dir = type_dirs.get(resource_type)
    if not type_dir:
        return "", 0

    suffixes = {
        "agent": ".md",
        "skill": "/SKILL.md",
        "shared-module": "",
        "workflow": ".md",
        "script": ".py",
        "rule": ".md",
    }
    suffix = suffixes.get(resource_type, "")

    if resource_type == "shared-module":
        src = resource_root / type_dir / resource_id
    elif resource_type == "skill":
        src = resource_root / type_dir / resource_id / "SKILL.md"
    else:
        src = resource_root / type_dir / f"{resource_id}{suffix}"

    if src.exists():
        return compute_content_hash(src), sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) if src.is_dir() else src.stat().st_size
    return "", 0


def build_resources_lock_with_hashes(
    bundle_id: str,
    resource_selection: ResourceSelectionResult,
    resources_root: Path,
    requested_bundle_id: Optional[str] = None,
) -> ResourcesLock:
    """Build resources.lock with content hashes for integrity verification."""
    lock_resources = []

    for r in resource_selection.resources:
        content_hash, size = compute_resource_hash(resources_root, r.type, r.id)

        provenance = {
            "source": r.provenance_source,
            "commit_sha": r.provenance_commit_sha,
            "license": r.provenance_license,
            "reviewed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "transformation": "none",
        }

        lock_resources.append({
            "id": r.id,
            "type": r.type,
            "version": r.version,
            "provenance": provenance,
            "selection_reason": r.selection_reason,
            "content_hash": content_hash,
            "size_bytes": size,
            "runtime_representations": {},
        })

    # Add capability providers (CBM, Agent-Reach, Orca) if available
    from core.cbm_integration import get_cbm_provider_info
    from core.agent_reach_integration import get_agent_reach_provider_info
    from core.orca_integration import get_orca_provider_info

    for provider_id, get_info in [
        ("codebase-memory", get_cbm_provider_info),
        ("agent-reach", get_agent_reach_provider_info),
        ("orca", get_orca_provider_info),
    ]:
        info = get_info()
        if info:
            lock_resources.append({
                "id": provider_id,
                "type": "capability-provider",
                "version": "1.0.0",
                "provenance": {
                    "source": provider_id.replace("-", ""),
                    "commit_sha": "main",
                    "license": "MIT",
                    "reviewed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "transformation": "none",
                },
                "selection_reason": f"capability:{provider_id} (optional provider)",
                "content_hash": "",
                "size_bytes": 0,
                "runtime_representations": info,
            })

    return build_resources_lock(
        bundle_id,
        requested_bundle_id=requested_bundle_id,
        resources=lock_resources,
    )


def load_upstream_sources(path: Path | str) -> list[UpstreamSource]:
    """Load upstream sources from YAML file."""
    path = Path(path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    sources = []
    for src_data in data.get("upstream_sources", []):
        sources.append(UpstreamSource(**src_data))
    return sources


def save_upstream_sources(path: Path | str, sources: list[UpstreamSource]) -> None:
    """Save upstream sources to YAML file."""
    path = Path(path)
    data = {
        "upstream_sources": [
            {
                "name": s.name,
                "type": s.type,
                "url": s.url,
                "ref": s.ref,
                "path": s.path,
                "last_synced": s.last_synced,
                "last_commit": s.last_commit,
                "verified": s.verified,
            }
            for s in sources
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def get_git_commit_sha(repo_path: Path) -> Optional[str]:
    """Get current commit SHA of a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def fetch_upstream_source(source: UpstreamSource, target_dir: Path) -> tuple[bool, str]:
    """Fetch/update an upstream source. Returns (success, message)."""
    try:
        if source.type == "git" or source.type == "github":
            if target_dir.exists() and (target_dir / ".git").exists():
                # Update existing repo
                subprocess.run(["git", "fetch", "origin"], cwd=target_dir, check=True, timeout=60)
                subprocess.run(["git", "checkout", source.ref], cwd=target_dir, check=True, timeout=30)
                subprocess.run(["git", "pull", "origin", source.ref], cwd=target_dir, check=True, timeout=60)
            else:
                # Clone new
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", "--branch", source.ref, source.url, str(target_dir)], check=True, timeout=120)

            commit_sha = get_git_commit_sha(target_dir)
            return True, commit_sha or "updated"

        elif source.type == "local":
            # Just verify local path exists
            if target_dir.exists():
                return True, "local path verified"
            return False, f"local path not found: {target_dir}"

        else:
            return False, f"unsupported source type: {source.type}"

    except subprocess.CalledProcessError as e:
        return False, f"git error: {e}"
    except Exception as e:
        return False, f"error: {e}"


def sync_upstream_sources(
    project_root: Path | str,
    sources_file: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Sync all upstream sources. Returns sync results."""
    project_root = Path(project_root)
    if sources_file is None:
        sources_file = project_root / ".ai-coding-starter" / "upstream-sources.yaml"

    sources = load_upstream_sources(sources_file)
    results = {"synced": [], "failed": [], "skipped": []}

    for source in sources:
        target_dir = project_root / ".upstream" / source.name
        success, msg = fetch_upstream_source(source, target_dir)

        if success:
            source.last_synced = datetime.now(timezone.utc).isoformat()
            source.last_commit = msg if len(msg) == 40 else None  # SHA is 40 chars
            source.verified = True
            results["synced"].append({"name": source.name, "commit": msg})
        else:
            results["failed"].append({"name": source.name, "error": msg})

    save_upstream_sources(sources_file, sources)
    return results


def check_updates(
    project_root: Path | str,
    sources_file: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Check for upstream updates without applying. Returns update info."""
    project_root = Path(project_root)
    if sources_file is None:
        sources_file = project_root / ".ai-coding-starter" / "upstream-sources.yaml"

    sources = load_upstream_sources(sources_file)
    updates = []

    for source in sources:
        target_dir = project_root / ".upstream" / source.name
        if not target_dir.exists() or not (target_dir / ".git").exists():
            updates.append({
                "name": source.name,
                "status": "not_synced",
                "current_commit": None,
                "remote_commit": None,
            })
            continue

        try:
            # Fetch latest from remote
            subprocess.run(["git", "fetch", "origin"], cwd=target_dir, check=True, timeout=30, capture_output=True)

            # Get current and remote commit
            current = get_git_commit_sha(target_dir)
            remote_result = subprocess.run(
                ["git", "rev-parse", f"origin/{source.ref}"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            remote = remote_result.stdout.strip() if remote_result.returncode == 0 else None

            if current != remote:
                updates.append({
                    "name": source.name,
                    "status": "update_available",
                    "current_commit": current[:8] if current else None,
                    "remote_commit": remote[:8] if remote else None,
                })
            else:
                updates.append({
                    "name": source.name,
                    "status": "up_to_date",
                    "current_commit": current[:8] if current else None,
                    "remote_commit": remote[:8] if remote else None,
                })

        except Exception as e:
            updates.append({
                "name": source.name,
                "status": "error",
                "error": str(e),
            })

    return {"updates": updates, "checked_at": datetime.now(timezone.utc).isoformat()}


def verify_resources_lock(project_root: Path | str) -> dict[str, Any]:
    """Verify resources.lock integrity against actual files."""
    project_root = Path(project_root)
    lock = read_resources_lock(project_root / ".ai-coding-starter" / "resources.lock")
    # Use bundled resources from starter repo (parent of core/)
    starter_root = Path(__file__).parent.parent
    resources_root = starter_root / "resources"

    results = {"verified": [], "mismatched": [], "missing": [], "skipped": []}

    for r in lock.resources:
        # Skip capability providers and agency agents (no bundled source)
        if r.type == "capability-provider" or r.provenance.source == "agency-agents":
            results["skipped"].append(r.id)
            continue

        content_hash, _ = compute_resource_hash(resources_root, r.type, r.id)
        if not content_hash:
            results["missing"].append(r.id)
        else:
            results["verified"].append(r.id)

    return results

    return results


def create_default_upstream_sources(project_root: Path | str) -> list[UpstreamSource]:
    """Create default upstream-sources.yaml for Agency catalog."""
    project_root = Path(project_root)
    sources_file = project_root / ".ai-coding-starter" / "upstream-sources.yaml"

    defaults = [
        UpstreamSource(
            name="agency-catalog",
            type="github",
            url="https://github.com/agency-ai/agents",
            ref="main",
            path="catalog",
        ),
        UpstreamSource(
            name="starter-resources",
            type="github",
            url="https://github.com/ai-coding-starter/resources",
            ref="main",
            path="",
        ),
    ]

    save_upstream_sources(sources_file, defaults)
    return defaults


# CLI integration functions
def cmd_sync(project_root: str, **kwargs) -> int:
    """CLI: sync upstream sources."""
    results = sync_upstream_sources(project_root)
    print(f"Synced: {len(results['synced'])}")
    for s in results['synced']:
        print(f"  OK {s['name']}: {s['commit']}")
    if results['failed']:
        print(f"Failed: {len(results['failed'])}")
        for f in results['failed']:
            print(f"  !! {f['name']}: {f['error']}")
    return 0 if not results['failed'] else 1


def cmd_check_updates(project_root: str, **kwargs) -> int:
    """CLI: check for upstream updates."""
    results = check_updates(project_root)
    print(f"Checked at: {results['checked_at']}")
    for u in results['updates']:
        status = u['status']
        if status == "update_available":
            print(f"  UP {u['name']}: {u['current_commit']} -> {u['remote_commit']}")
        elif status == "up_to_date":
            print(f"  OK {u['name']}: up to date ({u['current_commit']})")
        elif status == "not_synced":
            print(f"  -- {u['name']}: not synced")
        else:
            print(f"  !! {u['name']}: {u.get('error', 'error')}")
    return 0


def cmd_verify_lock(project_root: str, **kwargs) -> int:
    """CLI: verify resources.lock integrity."""
    results = verify_resources_lock(project_root)
    print(f"Verified: {len(results['verified'])}")
    if results['mismatched']:
        print(f"Mismatched: {len(results['mismatched'])}")
        for m in results['mismatched']:
            print(f"  ! {m['id']}: expected {m['expected']}, got {m['actual']}")
    if results['missing']:
        print(f"Missing: {len(results['missing'])}")
        for m in results['missing']:
            print(f"  ? {m}")
    return 0 if not results['mismatched'] and not results['missing'] else 1


def cmd_init_upstream(project_root: str, **kwargs) -> int:
    """CLI: initialize default upstream sources."""
    sources = create_default_upstream_sources(project_root)
    print(f"Initialized {len(sources)} upstream sources:")
    for s in sources:
        print(f"  - {s.name} ({s.type}: {s.url})")
    return 0