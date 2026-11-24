# Agent Manager Integration

## Overview

The Agent Manager Bridge (`core/agent_manager_bridge.py`) connects AI-Coding-starter projects to **Codex Agent Manager** (origin.cursor.com), enabling programmatic spawning of specialist agents based on the project's team pack.

```
project.yaml (canonical)
    │
    ├── project_type: "saas"
    ├── team_pack: "startup-mvp"
    └── specialists: [...]
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ AgentManagerBridge                                          │
├─────────────────────────────────────────────────────────────┤
│ • get_core_team()           → 8 always-active agents        │
│ • get_specialists_for_pack() → as-needed specialists        │
│ • deploy_team_pack(task)    → spawn all via origin CLI      │
│ • list_specialists()        → show available agents         │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    origin agent create --prompt-file --worktree
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Manager Sessions (bounded, project-aware)             │
├─────────────────────┬───────────────────────────────────────┤
│ Core Team (always)  │ Specialists (as-needed per pack)      │
├─────────────────────┼───────────────────────────────────────┤
│ • code-reviewer     │ • backend-architect (startup-mvp)     │
│ • devops-automator  │ • database-optimizer (prod-feature)   │
│ • senior-dev        │ • security-auditor (security-audit)   │
│ • software-architect│ • incident-commander (incident-fix)   │
│ • product-manager   │ • performance-architect (perf-invest) │
│ • sprint-prioritizer│ • minimal-change-engineer (bug-fix)   │
│ • project-shepherd  │ • codebase-archaeologist (refactor)   │
│ • senior-pm         │ • reality-checker (all packs)         │
└─────────────────────┴───────────────────────────────────────┘
```

## Architecture

### Core Classes

```python
from core.agent_manager_bridge import AgentManagerBridge, AgentSession, TeamDeployment

# Create bridge from project root
bridge = AgentManagerBridge("/path/to/project")

# List available specialists
info = bridge.list_specialists()
# {
#   "core_team": [...],
#   "specialists": [...],
#   "available_packs": ["startup-mvp", "production-feature", ...]
# }

# Deploy full team pack
deployment = bridge.deploy_team_pack("Build authentication API")
# TeamDeployment(
#   project_id="my-project",
#   project_type="saas",
#   team_pack="startup-mvp",
#   core_agents=[AgentSession(...)],
#   specialist_agents=[AgentSession(...)]
# )

# Deploy specific specialists
sessions = bridge.deploy_specialists(
    task="Optimize database queries",
    specialist_ids=["engineering-database-optimizer", "engineering-senior-developer"]
)
```

### AgentSession

```python
@dataclass
class AgentSession:
    specialist_id: str      # e.g., "engineering-backend-architect"
    session_id: str         # Agent Manager session ID
    task: str               # Task description
    status: str             # "running" | "completed" | "failed"
    worktree: Optional[str] # Git worktree path if created
    result: Optional[str]   # Completion summary
```

### TeamDeployment

```python
@dataclass
class TeamDeployment:
    project_id: str
    project_type: str
    team_pack: str
    core_agents: list[AgentSession] = field(default_factory=list)
    specialist_agents: list[AgentSession] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

## Team Packs

| Pack | Trigger | Core + Specialists | Use Case |
|------|---------|-------------------|----------|
| **startup-mvp** | saas, mobile-app, ai-rag | 8 core + 3 specialists | Greenfield MVP, speed focus |
| **production-feature** | saas, fullstack-api | 8 core + 3 specialists | Feature work on production code |
| **bug-fix** | all types | 8 core + 3 specialists | Minimal, targeted fixes |
| **refactor** | all types | 8 core + 3 specialists | Code modernization, debt paydown |
| **security-audit** | saas, fintech, healthtech | 8 core + 4 specialists | Security review, compliance |
| **performance-investigation** | saas, fullstack-api, ai-rag | 8 core + 3 specialists | Bottleneck analysis, optimization |
| **incident-fix** | saas, fintech, devops-platform | 8 core + 3 specialists | Production incident response |

### Core Team (Always Active — 8 agents)

| Agent | Division | Role |
|-------|----------|------|
| `engineering-code-reviewer` | engineering | Constructive, actionable code review |
| `engineering-devops-automator` | engineering | CI/CD, infrastructure automation |
| `engineering-senior-developer` | engineering | Premium implementation (Laravel/Livewire/FluxUI) |
| `engineering-software-architect` | engineering | System design, DDD, architectural patterns |
| `product-manager` | product | Full lifecycle: discovery → GTM → outcomes |
| `product-sprint-prioritizer` | product | Agile sprint planning, prioritization frameworks |
| `project-management-project-shepherd` | project-management | Cross-functional coordination, timeline mgmt |
| `project-manager-senior` | project-management | Spec→tasks, realistic scope, historical context |

### Specialists (As-Needed — 108 agents across 6 divisions)

Divisions: `engineering`, `product`, `security`, `testing`, `project-management`, `specialized`

Examples:
- `engineering-backend-architect` — System design, APIs, databases
- `security-ai-generated-code-auditor` — AI code security review
- `testing-reality-checker` — Evidence-based certification
- `specialized-codebase-archaeologist` — Multi-tool drift detection

## CLI Commands

### List Specialists

```bash
python new_project.py --list-agents --project /path/to/project
```

Output:
```
Project: my-project (my-project)
Type: saas
Team Pack: startup-mvp

Core Team (8):
  - engineering-code-reviewer (engineering) [always]: Expert code reviewer...

Specialists (3):
  - engineering-backend-architect (engineering) [as-needed]: Expert backend architect...
  - engineering-devops-automator (engineering) [as-needed]: Expert DevOps engineer...
  - engineering-api-platform-engineer (engineering) [as-needed]: API platform specialist...

Available Packs: startup-mvp, production-feature, bug-fix, refactor, security-audit, performance-investigation, incident-fix
```

### Deploy Team Pack

```bash
# Requires origin CLI (https://origin.cursor.com)
python new_project.py --deploy-agents --project /path/to/project --agent-task "Build user authentication"
```

Output:
```
Deployed team pack 'startup-mvp' for project 'my-project'
Core agents: 8
Specialist agents: 3
```

## Agent Prompt Construction

Each specialist receives a structured prompt:

```markdown
# Specialist: Engineering Backend Architect (engineering-backend-architect)
# Division: engineering
# Activation: as-needed

## Project Context
- Project: my-project (my-project)
- Type: saas
- Stack: nextjs-dotnet-postgres
- Team Pack: startup-mvp
- Capabilities: email, search

## Your Role
Expert backend architect specializing in system design, API architecture,
database modeling, and scalability patterns for high-throughput services.

## Task
Build user authentication API with JWT tokens and refresh mechanism.

## Additional Context
{
  "phase": "implementation",
  "requirements": ["JWT", "refresh tokens", "rate limiting"]
}

## Instructions
- Work within the project directory
- Read .ai-coding-starter/project.yaml for canonical state
- Read .ai-workspace/ for activated resources
- Write outputs to appropriate locations
- Report completion with summary
```

## Requirements

1. **origin CLI** installed: `https://origin.cursor.com`
2. **Authentication**: `origin auth login`
3. **Project** must have `.ai-coding-starter/project.yaml` with `team_pack` and `specialists`

Check availability:
```python
bridge = AgentManagerBridge(project_root)
if bridge.check_agent_manager_available():
    print("Agent Manager ready")
else:
    print("Install origin CLI from https://origin.cursor.com")
```

## Bounded Activation

- **Core team** (8 agents): Always spawned, maintain project context
- **Specialists** (as-needed): Spawned per task, terminate after completion
- **Worktrees**: Each agent gets isolated git worktree (`{project-id}-{specialist-id}`)
- **Context**: Agents read `.ai-coding-starter/` + `.ai-workspace/` for project state

## Error Handling

```python
deployment = bridge.deploy_team_pack("Task")
if deployment.errors:
    for err in deployment.errors:
        print(f"Failed: {err}")
# Check individual sessions
for session in deployment.core_agents + deployment.specialist_agents:
    if session.status == "failed":
        print(f"{session.specialist_id}: {session.result}")
```

## Extending Team Packs

Edit `core/agency_specialists.py`:

```python
TEAM_PACKS = {
    "my-custom-pack": TeamPack(
        id="my-custom-pack",
        name="My Custom Pack",
        description="Custom team for X",
        specialist_ids=["engineering-backend-architect", "security-auditor"],
        project_types=["saas", "fintech"],
        trigger="custom-trigger",
    ),
}
```

Then register in `PACK_TRIGGERS` mapping.