"""
Agency Specialist Catalog for AI-Coding-starter.

Filters the imported Agency Agents catalog (268 agents, 18 divisions) to a
bounded set of coding specialists, organized into execution/team packs.

Only activates specialists relevant to the project type/capabilities.
Core team agents are always active; specialists are as-needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json


@dataclass(frozen=True)
class SpecialistAgent:
    """A specialist agent from the Agency catalog."""
    id: str
    name: str
    division: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    project_types: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    activation: str = "as-needed"  # "always" or "as-needed"


# Coding-relevant divisions (from Agency catalog)
CODING_DIVISIONS = {
    "engineering",
    "security",
    "testing",
    "project-management",
    "product",
}

# Additional coding-relevant agents from specialized division
SPECIALIZED_CODING_AGENTS = {
    "specialized-codebase-archaeologist",
    "specialized-developer-advocate",
    "specialized-mcp-builder",
    "specialized-model-qa",
    "specialized-workflow-architect",
    "lsp-index-engineer",
    "data-privacy-officer",
    "automation-governance-architect",
}


def load_agency_catalog() -> list[dict]:
    """Load the full Agency agents catalog."""
    catalog_path = Path(__file__).parent.parent / "catalog" / "agency-agents.yaml"
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("agents", [])


def filter_coding_specialists(agents: list[dict]) -> list[SpecialistAgent]:
    """Filter agents to coding-relevant specialists."""
    specialists = []

    for agent in agents:
        agent_id = agent.get("id", "")
        division = agent.get("division", "")

        # Include if in coding division
        if division in CODING_DIVISIONS:
            # Core team: only key orchestration/leadership roles
            core_ids = {
                "engineering-senior-developer",
                "engineering-software-architect",
                "engineering-devops-automator",
                "engineering-code-reviewer",
                "project-management-project-shepherd",
                "project-manager-senior",
                "product-manager",
                "product-sprint-prioritizer",
            }
            activation = "always" if agent_id in core_ids else "as-needed"
            specialists.append(SpecialistAgent(
                id=agent_id,
                name=agent.get("name", ""),
                division=division,
                description=agent.get("description", ""),
                capabilities=agent.get("capabilities", []),
                project_types=agent.get("project_types", []),
                tags=agent.get("tags", []),
                activation=activation,
            ))
        # Include specific specialized agents
        elif agent_id in SPECIALIZED_CODING_AGENTS:
            specialists.append(SpecialistAgent(
                id=agent_id,
                name=agent.get("name", ""),
                division="specialized",
                description=agent.get("description", ""),
                capabilities=agent.get("capabilities", []),
                project_types=agent.get("project_types", []),
                tags=agent.get("tags", []),
                activation="as-needed",
            ))

    return specialists


def get_specialist_by_id(specialists: list[SpecialistAgent], agent_id: str) -> Optional[SpecialistAgent]:
    """Get a specialist by ID."""
    for s in specialists:
        if s.id == agent_id:
            return s
    return None


# Team Pack Definitions (aligned with UPGRADE_PLAN.md M6)
TEAM_PACKS = {
    "startup-mvp": {
        "name": "Startup MVP",
        "description": "Rapid MVP delivery with core team + key specialists",
        "core": [
            "engineering-senior-developer",
            "engineering-software-architect",
            "engineering-devops-automator",
            "project-management-project-shepherd",
        ],
        "specialists": [
            "engineering-rapid-prototyper",
            "engineering-frontend-developer",
            "engineering-backend-architect",
            "engineering-api-platform-engineer",
            "security-appsec-engineer",
            "testing-api-tester",
            "product-sprint-prioritizer",
        ],
        "activation_triggers": ["saas", "e-commerce", "fullstack-application"],
    },
    "production-feature": {
        "name": "Production Feature",
        "description": "Feature development for production systems",
        "core": [
            "engineering-senior-developer",
            "engineering-code-reviewer",
            "engineering-devops-automator",
            "project-management-project-shepherd",
        ],
        "specialists": [
            "engineering-backend-architect",
            "engineering-frontend-developer",
            "engineering-database-optimizer",
            "engineering-minimal-change-engineer",
            "security-appsec-engineer",
            "testing-api-tester",
            "testing-performance-benchmarker",
        ],
        "activation_triggers": ["saas", "fullstack-application", "backend-api", "dashboard"],
    },
    "bug-fix": {
        "name": "Bug Fix",
        "description": "Rapid bug investigation and fix",
        "core": [
            "engineering-senior-developer",
            "engineering-code-reviewer",
        ],
        "specialists": [
            "engineering-minimal-change-engineer",
            "testing-reality-checker",
            "testing-evidence-collector",
            "specialized-codebase-archaeologist",
        ],
        "activation_triggers": ["all"],
    },
    "refactor": {
        "name": "Refactor",
        "description": "Code modernization and technical debt reduction",
        "core": [
            "engineering-senior-developer",
            "engineering-code-reviewer",
            "engineering-software-architect",
        ],
        "specialists": [
            "engineering-rust-refactoring-specialist",
            "engineering-minimal-change-engineer",
            "specialized-codebase-archaeologist",
            "testing-performance-benchmarker",
        ],
        "activation_triggers": ["all"],
    },
    "security-audit": {
        "name": "Security Audit",
        "description": "Security review and hardening",
        "core": [
            "engineering-senior-developer",
            "security-appsec-engineer",
            "security-architect",
        ],
        "specialists": [
            "security-ai-generated-code-auditor",
            "security-cloud-security-architect",
            "security-penetration-tester",
            "security-secrets-credential-engineer",
            "security-incident-responder",
            "data-privacy-officer",
        ],
        "activation_triggers": ["saas", "e-commerce", "fullstack-application", "ai-rag", "ai-agent"],
    },
    "performance-investigation": {
        "name": "Performance Investigation",
        "description": "Performance profiling and optimization",
        "core": [
            "engineering-senior-developer",
            "engineering-software-architect",
        ],
        "specialists": [
            "engineering-database-optimizer",
            "engineering-performance-engineer",
            "testing-performance-benchmarker",
            "engineering-sre",
            "engineering-autonomous-optimization-architect",
        ],
        "activation_triggers": ["saas", "fullstack-application", "backend-api", "dashboard", "realtime-application"],
    },
    "incident-fix": {
        "name": "Incident Fix",
        "description": "Production incident response and resolution",
        "core": [
            "engineering-senior-developer",
            "engineering-devops-automator",
            "engineering-incident-response-commander",
            "security-incident-responder",
        ],
        "specialists": [
            "engineering-sre",
            "engineering-database-reliability-engineer",
            "specialized-codebase-archaeologist",
            "testing-reality-checker",
        ],
        "activation_triggers": ["saas", "fullstack-application", "backend-api", "realtime-application", "dashboard"],
    },
}


def get_pack(pack_id: str) -> Optional[dict]:
    """Get a team pack by ID."""
    return TEAM_PACKS.get(pack_id)


def get_packs_for_project_type(project_type: str) -> list[str]:
    """Get recommended team packs for a project type."""
    packs = []
    for pack_id, pack in TEAM_PACKS.items():
        triggers = pack.get("activation_triggers", [])
        if "all" in triggers or project_type in triggers:
            packs.append(pack_id)
    return packs


def get_core_team(specialists: list[SpecialistAgent]) -> list[SpecialistAgent]:
    """Get core team agents (always active)."""
    return [s for s in specialists if s.activation == "always"]


def get_specialists_for_pack(pack_id: str, all_specialists: list[SpecialistAgent]) -> list[SpecialistAgent]:
    """Get all specialists for a team pack (core + pack specialists)."""
    pack = get_pack(pack_id)
    if not pack:
        return []

    specialist_ids = set(pack["core"] + pack["specialists"])
    return [s for s in all_specialists if s.id in specialist_ids]


def get_all_specialists() -> list[SpecialistAgent]:
    """Get all coding specialists from the catalog."""
    agents = load_agency_catalog()
    return filter_coding_specialists(agents)