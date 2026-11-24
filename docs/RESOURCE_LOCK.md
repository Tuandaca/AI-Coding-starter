# Resource Lock & Upstream Sync

## Overview

The resource lock system provides **reproducible builds** and **catalog synchronization** for AI-Coding-starter projects.

```
resources.lock (pinned versions + content hashes)
       │
       ├── Integrity verification
       ├── Upstream sync (GitHub/git)
       └── Update checking
```

## Resources Lock (`resources.lock`)

### Purpose

- **Content hashing**: SHA256 of each resource for tamper detection
- **Version pinning**: Exact resource versions locked per project
- **Provenance tracking**: Source, commit SHA, license, review date
- **Reproducibility**: Same lock = same resources

### Structure

```json
{
  "schema_version": "1.0.0",
  "lockfile_version": 1,
  "generated_at": "2026-11-24T06:11:36Z",
  "generated_by": "ai-coding-starter-generator",
  "resources": [
    {
      "id": "frontend-specialist",
      "type": "agent",
      "version": "1.0.0",
      "provenance": {
        "source": "bundled",
        "commit_sha": "8b61d297dc07772a000b85fc93138c8aefd21c45",
        "license": "MIT",
        "reviewed_date": "2026-11-06",
        "transformation": "none"
      },
      "selection_reason": "project-type:business-website",
      "content_hash": "7ba14a62b1b596d0",
      "size_bytes": 681,
      "runtime_representations": {}
    }
  ],
  "stack_bundle_resolution": {
    "requested_bundle": "nextjs-dotnet-postgres",
    "resolved_bundle": "nextjs-dotnet-postgres"
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `id` | Resource identifier |
| `type` | `agent`, `skill`, `workflow`, `script`, `rule`, `shared-module`, `capability-provider` |
| `version` | Resource version |
| `provenance.source` | `bundled`, `agency-agents`, `custom`, `community` |
| `provenance.commit_sha` | Git commit for traceability |
| `provenance.license` | SPDX license identifier |
| `provenance.reviewed_date` | Last human review (ISO 8601) |
| `content_hash` | SHA256 prefix (16 chars) of resource content |
| `size_bytes` | File/directory size |
| `runtime_representations` | Optional provider-specific config (CBM, Agent-Reach, Orca) |

### Generation

Automatic during `new_project.py`:

```python
from core.resource_lock import build_resources_lock_with_hashes

lock = build_resources_lock_with_hashes(
    bundle_id="nextjs-dotnet-postgres",
    resource_selection=resource_selection,
    resources_root=resource_root,
    requested_bundle_id=bundle_id,
)
```

## Upstream Sources (`upstream-sources.yaml`)

### Purpose

Track external catalog sources for updates:

- **Agency catalog** (268 agents, 18 divisions)
- **Starter resources** (bundled agents, skills, workflows)
- **Custom sources** (organization-specific)

### Structure

```yaml
upstream_sources:
  - name: agency-catalog
    type: github
    url: https://github.com/agency-ai/agents
    ref: main
    path: catalog
    last_synced: "2026-11-24T06:35:18Z"
    last_commit: "a1b2c3d4"
    verified: true

  - name: starter-resources
    type: github
    url: https://github.com/ai-coding-starter/resources
    ref: main
    path: ""
    last_synced: null
    last_commit: null
    verified: false

  - name: internal-catalog
    type: local
    url: ""
    ref: ""
    path: /opt/org/agents
    last_synced: "2026-11-20T10:00:00Z"
    last_commit: null
    verified: true
```

### Source Types

| Type | Description | Example |
|------|-------------|---------|
| `github` | GitHub repository (clone/pull) | `https://github.com/agency-ai/agents` |
| `git` | Generic git repository | `https://gitlab.com/org/agents.git` |
| `local` | Local filesystem path | `/opt/org/agents` |

## CLI Commands

### Initialize Default Sources

```bash
python new_project.py --init-upstream --project /path/to/project
```

Creates `.ai-coding-starter/upstream-sources.yaml` with defaults.

### Sync Upstream

```bash
python new_project.py --sync-upstream --project /path/to/project
```

Clones/updates all sources to `.upstream/{name}/` in project root.

Output:
```
Synced: 2
  OK agency-catalog: a1b2c3d4e5f6...
  OK starter-resources: 7f8e9d0a1b2c...
```

### Check Updates

```bash
python new_project.py --check-updates --project /path/to/project
```

Fetches remote refs, compares with local commits.

Output:
```
Checked at: 2026-11-24T06:35:40Z
  -- agency-catalog: not synced
  -- starter-resources: not synced
```

After sync:
```
Checked at: 2026-11-24T06:40:00Z
  OK agency-catalog: up to date (a1b2c3d4)
  UP starter-resources: 7f8e9d0a -> 3c4d5e6f
```

### Verify Lock Integrity

```bash
python new_project.py --verify-lock --project /path/to/project
```

Compares `content_hash` in lock with actual bundled resources.

Output:
```
Verified: 8
Skipped: 5
```

**Skipped** = capability providers + agency agents (no bundled source to verify).

## Programmatic API

### Sync

```python
from core.resource_lock import sync_upstream_sources

results = sync_upstream_sources("/path/to/project")
# {'synced': [...], 'failed': [], 'skipped': []}
```

### Check Updates

```python
from core.resource_lock import check_updates

results = check_updates("/path/to/project")
# {
#   'updates': [
#     {'name': 'agency-catalog', 'status': 'up_to_date', 'current_commit': 'a1b2c3d4', 'remote_commit': 'a1b2c3d4'},
#     {'name': 'starter-resources', 'status': 'update_available', 'current_commit': '7f8e9d0a', 'remote_commit': '3c4d5e6f'}
#   ],
#   'checked_at': '2026-11-24T06:40:00Z'
# }
```

### Verify

```python
from core.resource_lock import verify_resources_lock

results = verify_resources_lock("/path/to/project")
# {
#   'verified': ['frontend-specialist', 'orchestrator', ...],
#   'mismatched': [],
#   'missing': [],
#   'skipped': ['design-ui-designer', ...]
# }
```

### Build Lock with Hashes

```python
from core.resource_lock import build_resources_lock_with_hashes
from core.resource_resolver import resolve_resources

resource_selection = resolve_resources(...)
lock = build_resources_lock_with_hashes(
    bundle_id=bundle_id,
    resource_selection=resource_selection,
    resources_root=resource_root,
)
```

## Content Hashing

### Algorithm

```python
def compute_content_hash(path: Path) -> str:
    """SHA256 of file/directory content, truncated to 16 chars."""
    hasher = hashlib.sha256()
    if path.is_file():
        hasher.update(path.read_bytes())
    elif path.is_dir():
        for f in sorted(path.rglob("*")):
            if f.is_file():
                rel = f.relative_to(path)
                hasher.update(rel.as_posix().encode())  # Include path
                hasher.update(f.read_bytes())            # Include content
    return hasher.hexdigest()[:16]
```

### What Gets Hashed

| Resource Type | Source Location |
|---------------|-----------------|
| `agent` | `resources/agents/{id}.md` |
| `skill` | `resources/skills/{id}/SKILL.md` |
| `workflow` | `resources/workflows/{id}.md` |
| `script` | `resources/scripts/{id}.py` |
| `rule` | `resources/rules/{id}.md` |
| `shared-module` | `resources/shared/{id}/**` (entire tree) |

### Agency Agents

Agency agents (`provenance.source == "agency-agents"`) are **not verified** against bundled resources since they come from external catalog. They're marked as `skipped` during verification.

## Updating Lock

When upstream sources change:

```bash
# 1. Sync to get latest
python new_project.py --sync-upstream --project /path/to/project

# 2. Re-resolve resources (regenerates lock with new hashes)
# This happens automatically on next project generation

# 3. Verify new lock
python new_project.py --verify-lock --project /path/to/project
```

## Security Considerations

1. **Commit SHA pinning**: Each resource locked to specific commit
2. **License tracking**: SPDX identifiers for compliance
3. **Review dates**: Human review cadence enforced
4. **Content hashes**: Detects tampering/corruption
5. **Fail-open providers**: CBM/Agent-Reach/Orca optional, non-blocking

## Integration with CI/CD

```yaml
# .github/workflows/verify-lock.yml
- name: Verify resource lock
  run: |
    python new_project.py --verify-lock --project ${{ github.workspace }}
```

```yaml
# .github/workflows/check-updates.yml
- name: Check upstream updates
  run: |
    python new_project.py --check-updates --project ${{ github.workspace }}
  # Fail if updates available (optional)
```