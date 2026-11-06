#!/usr/bin/env python3
"""
Checklist Script
Interactive checklist for project setup, review, and deployment tasks.
"""

import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from enum import Enum


class CheckStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class ChecklistItem:
    id: str
    title: str
    description: str
    category: str
    status: CheckStatus = CheckStatus.PENDING
    notes: str = ""
    assignee: str = ""


class Checklist:
    def __init__(self, name: str):
        self.name = name
        self.items: List[ChecklistItem] = []

    def add_item(self, item: ChecklistItem):
        self.items.append(item)

    def get_by_id(self, item_id: str) -> Optional[ChecklistItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_by_status(self, status: CheckStatus) -> List[ChecklistItem]:
        return [item for item in self.items if item.status == status]

    def get_by_category(self, category: str) -> List[ChecklistItem]:
        return [item for item in self.items if item.category == category]

    def categories(self) -> List[str]:
        return sorted(set(item.category for item in self.items))

    def progress(self) -> dict:
        total = len(self.items)
        if total == 0:
            return {"total": 0, "done": 0, "percentage": 0}
        done = len(self.get_by_status(CheckStatus.DONE))
        return {
            "total": total,
            "done": done,
            "in_progress": len(self.get_by_status(CheckStatus.IN_PROGRESS)),
            "pending": len(self.get_by_status(CheckStatus.PENDING)),
            "blocked": len(self.get_by_status(CheckStatus.BLOCKED)),
            "percentage": round((done / total) * 100, 1)
        }

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "items": [asdict(item) for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Checklist':
        checklist = cls(data["name"])
        for item_data in data["items"]:
            item_data["status"] = CheckStatus(item_data["status"])
            checklist.add_item(ChecklistItem(**item_data))
        return checklist


# Predefined checklists
PROJECT_SETUP_CHECKLIST = Checklist("Project Setup")
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-001",
    title="Initialize Git Repository",
    description="Create git repo with initial commit",
    category="Version Control"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-002",
    title="Configure .gitignore",
    description="Add appropriate ignore patterns for project type",
    category="Version Control"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-003",
    title="Set up Package Manager",
    description="Configure npm/pip/cargo/go mod with lockfile",
    category="Dependencies"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-004",
    title="Configure Linting & Formatting",
    description="ESLint/Prettier, Ruff/Black, Clippy, golangci-lint",
    category="Code Quality"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-005",
    title="Set up Type Checking",
    description="TypeScript, mypy, or equivalent",
    category="Code Quality"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-006",
    title="Configure Testing Framework",
    description="Unit, integration, and E2E test setup",
    category="Testing"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-007",
    title="Set up CI/CD Pipeline",
    description="GitHub Actions, GitLab CI, or equivalent",
    category="CI/CD"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-008",
    title="Configure Environment Variables",
    description="Create .env.example with all required vars",
    category="Configuration"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-009",
    title="Set up Database (if needed)",
    description="Local dev DB, migrations, seed data",
    category="Infrastructure"
))
PROJECT_SETUP_CHECKLIST.add_item(ChecklistItem(
    id="setup-010",
    title="Create README",
    description="Project overview, quick start, contributing guide",
    category="Documentation"
))


DEPLOYMENT_CHECKLIST = Checklist("Deployment")
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-001",
    title="All Tests Passing",
    description="Unit, integration, and E2E tests green",
    category="Pre-deployment"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-002",
    title="Security Scan Clean",
    description="SAST, dependency audit, container scan",
    category="Pre-deployment"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-003",
    title="Performance Baseline Verified",
    description="No significant regression vs previous deploy",
    category="Pre-deployment"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-004",
    title="Staging Deployment Successful",
    description="Deployed to staging, smoke tests pass",
    category="Staging"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-005",
    title="Stakeholder Approval",
    description="Product/design sign-off on staging",
    category="Staging"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-006",
    title="Production Deploy Strategy",
    description="Blue-green, canary, or rolling configured",
    category="Production"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-007",
    title="Health Checks Passing",
    description="Liveness, readiness, and deep checks green",
    category="Production"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-008",
    title="Monitoring Active",
    description="Alerts, dashboards, logs verified",
    category="Post-deployment"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-009",
    title="Rollback Plan Ready",
    description="Tested rollback procedure documented",
    category="Post-deployment"
))
DEPLOYMENT_CHECKLIST.add_item(ChecklistItem(
    id="deploy-010",
    title="Post-Deploy Validation",
    description="30-min heightened monitoring, key metrics verified",
    category="Post-deployment"
))


def save_checklist(checklist: Checklist, filepath: Path):
    """Save checklist to JSON file."""
    with open(filepath, "w") as f:
        json.dump(checklist.to_dict(), f, indent=2)


def load_checklist(filepath: Path) -> Checklist:
    """Load checklist from JSON file."""
    with open(filepath) as f:
        return Checklist.from_dict(json.load(f))


def print_checklist(checklist: Checklist):
    """Print checklist with status indicators."""
    status_icons = {
        CheckStatus.PENDING: "⬜",
        CheckStatus.IN_PROGRESS: "🔄",
        CheckStatus.DONE: "✅",
        CheckStatus.SKIPPED: "⏭️",
        CheckStatus.BLOCKED: "🚫"
    }

    print(f"\n=== {checklist.name} ===")
    progress = checklist.progress()
    print(f"Progress: {progress['done']}/{progress['total']} ({progress['percentage']}%)")
    print()

    for category in checklist.categories():
        items = checklist.get_by_category(category)
        print(f"  📁 {category}")
        for item in items:
            icon = status_icons[item.status]
            print(f"    {icon} [{item.id}] {item.title}")
            if item.notes:
                print(f"      💬 {item.notes}")
        print()


def interactive_mode(checklist: Checklist):
    """Run interactive checklist mode."""
    while True:
        print_checklist(checklist)
        print("\nCommands:")
        print("  <id>       - Toggle item status")
        print("  <id> note  - Add/edit note for item")
        print("  save       - Save checklist to file")
        print("  load       - Load checklist from file")
        print("  quit       - Exit")

        cmd = input("\n> ").strip().lower()

        if cmd == "quit":
            break
        elif cmd == "save":
            filepath = Path(f"{checklist.name.lower().replace(' ', '_')}.json")
            save_checklist(checklist, filepath)
            print(f"Saved to {filepath}")
        elif cmd == "load":
            filepath = Path(f"{checklist.name.lower().replace(' ', '_')}.json")
            if filepath.exists():
                checklist = load_checklist(filepath)
                print(f"Loaded from {filepath}")
            else:
                print("No saved file found")
        else:
            parts = cmd.split(maxsplit=1)
            item_id = parts[0]
            item = checklist.get_by_id(item_id)
            if item:
                if len(parts) > 1 and parts[1] == "note":
                    note = input(f"Note for {item_id}: ")
                    item.notes = note
                else:
                    # Cycle status
                    statuses = list(CheckStatus)
                    current_idx = statuses.index(item.status)
                    item.status = statuses[(current_idx + 1) % len(statuses)]
            else:
                print(f"Unknown item: {item_id}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Checklist - Interactive task tracking")
    parser.add_argument("checklist", nargs="?", choices=["setup", "deploy"],
                        help="Checklist to use (default: interactive selection)")
    parser.add_argument("--file", help="Load checklist from file")
    parser.add_argument("--list", action="store_true", help="List available checklists")
    parser.add_argument("--progress", action="store_true", help="Show progress and exit")

    args = parser.parse_args()

    if args.list:
        print("Available checklists:")
        print("  setup   - Project Setup Checklist")
        print("  deploy  - Deployment Checklist")
        return

    if args.file:
        checklist = load_checklist(Path(args.file))
    elif args.checklist == "setup":
        checklist = PROJECT_SETUP_CHECKLIST
    elif args.checklist == "deploy":
        checklist = DEPLOYMENT_CHECKLIST
    else:
        print("Select checklist:")
        print("1. Project Setup")
        print("2. Deployment")
        choice = input("> ").strip()
        if choice == "1":
            checklist = PROJECT_SETUP_CHECKLIST
        elif choice == "2":
            checklist = DEPLOYMENT_CHECKLIST
        else:
            print("Invalid choice")
            return

    if args.progress:
        progress = checklist.progress()
        print(f"{checklist.name}: {progress['done']}/{progress['total']} ({progress['percentage']}%)")
        return

    interactive_mode(checklist)


if __name__ == "__main__":
    main()
