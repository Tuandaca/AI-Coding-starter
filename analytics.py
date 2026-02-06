#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analytics Dashboard for VibeCoding
Track project creation and progress across all projects.

Usage:
    python new_project.py --stats    # View dashboard
    python analytics.py              # Direct run
"""

import os
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================

def get_analytics_dir():
    """Get analytics directory path (~/.vibecoding)"""
    home = Path.home()
    return home / ".vibecoding"

def get_analytics_path():
    """Get analytics JSON file path"""
    return get_analytics_dir() / "analytics.json"

# ============================================
# CORE FUNCTIONS
# ============================================

def load_analytics():
    """Load analytics data from JSON file."""
    path = get_analytics_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"projects": [], "version": "1.0"}
    return {"projects": [], "version": "1.0"}

def save_analytics(data):
    """Save analytics data to JSON file."""
    path = get_analytics_path()
    # Create directory if not exists
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def track_project(project_data):
    """
    Track a new project creation.
    
    project_data: dict with keys:
        - project_name: str
        - project_path: str
        - project_types: list[str]
        - tech_stack: dict
        - environment: dict (optional)
    """
    analytics = load_analytics()
    
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "project_name": project_data.get("project_name", "Unknown"),
        "project_path": project_data.get("project_path", ""),
        "project_types": project_data.get("project_types", []),
        "tech_stack": project_data.get("tech_stack", {}),
        "environment": project_data.get("environment", {})
    }
    
    analytics["projects"].append(record)
    save_analytics(analytics)
    return record["id"]

# ============================================
# PROGRESS TRACKER
# ============================================

def calculate_progress(context_path):
    """
    Parse CONTEXT.md to calculate project progress.
    
    Returns dict with:
        - progress: int (0-100)
        - done: int (completed tasks)
        - total: int (total tasks)
        - current_phase: str
        - status: str ('complete', 'in-progress', 'paused')
    """
    try:
        with open(context_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, FileNotFoundError):
        return None
    
    # Count checkboxes
    done = content.count("[x]") + content.count("[X]")
    pending = content.count("[ ]")
    in_progress = content.count("[/]")
    total = done + pending + in_progress
    
    # Calculate percentage
    progress = round((done / total * 100)) if total > 0 else 0
    
    # Determine status
    if progress >= 100:
        status = "complete"
    elif in_progress > 0 or done > 0:
        status = "in-progress"
    else:
        status = "paused"
    
    # Find Current Focus
    current_phase = "Unknown"
    # Try different patterns
    patterns = [
        r"## 🎯 Current Focus\s*\n+>\s*\*?\*?(.+?)(?:\*?\*?)(?:\n|$)",
        r"## Current Focus\s*\n+>\s*(.+?)(?:\n|$)",
        r"\*\*Current Focus\*\*[:\s]+(.+?)(?:\n|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            current_phase = match.group(1).strip()
            # Clean up markdown
            current_phase = re.sub(r'\*+', '', current_phase).strip()
            break
    
    return {
        "progress": progress,
        "done": done,
        "total": total,
        "in_progress": in_progress,
        "current_phase": current_phase,
        "status": status
    }

def get_all_projects_progress():
    """Get progress for all tracked projects."""
    analytics = load_analytics()
    results = []
    
    for project in analytics.get("projects", []):
        path = project.get("project_path", "")
        context_path = Path(path) / ".agent" / "CONTEXT.md"
        
        # Check if project still exists
        if not Path(path).exists():
            status_info = {
                "progress": 0,
                "status": "deleted",
                "current_phase": "Project not found"
            }
        else:
            status_info = calculate_progress(context_path)
            if status_info is None:
                status_info = {
                    "progress": 0,
                    "status": "no-context",
                    "current_phase": "No CONTEXT.md"
                }
        
        results.append({
            "id": project.get("id"),
            "name": project.get("project_name"),
            "path": path,
            "types": project.get("project_types", []),
            "created": project.get("timestamp"),
            **status_info
        })
    
    return results

# ============================================
# STATISTICS
# ============================================

def get_stats_summary():
    """Get summary statistics."""
    analytics = load_analytics()
    projects = analytics.get("projects", [])
    progress_data = get_all_projects_progress()
    
    # Count by status
    complete = sum(1 for p in progress_data if p.get("status") == "complete")
    in_progress = sum(1 for p in progress_data if p.get("status") == "in-progress")
    paused = sum(1 for p in progress_data if p.get("status") == "paused")
    
    # Tech stack frequency
    tech_counts = {}
    for p in projects:
        stack = p.get("tech_stack", {})
        for key, value in stack.items():
            if value and value != "None":
                # Extract main tech name
                tech_name = value.split("+")[0].strip()
                tech_counts[tech_name] = tech_counts.get(tech_name, 0) + 1
    
    # Sort by frequency
    top_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Project types frequency
    type_counts = {}
    for p in projects:
        for t in p.get("project_types", []):
            type_counts[t] = type_counts.get(t, 0) + 1
    
    return {
        "total": len(projects),
        "complete": complete,
        "in_progress": in_progress,
        "paused": paused,
        "top_tech": top_tech,
        "type_counts": type_counts,
        "projects": progress_data
    }

# ============================================
# DASHBOARD DISPLAY
# ============================================

def create_progress_bar(percent, width=20):
    """Create ASCII progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    return "#" * filled + "-" * empty

def print_dashboard():
    """Print beautiful dashboard to terminal."""
    import sys
    
    # Configure stdout for UTF-8 on Windows
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass  # Python < 3.7
    
    stats = get_stats_summary()
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print()
    print("+" + "=" * 62 + "+")
    print("|" + " VIBECODING ANALYTICS DASHBOARD ".center(62) + "|")
    print("+" + "=" * 62 + "+")
    print("|" + " " * 62 + "|")
    
    # Overview section
    print("|  TONG QUAN" + " " * 51 + "|")
    print(f"|  +-- Tong projects: {stats['total']:<40}|")
    print(f"|  +-- Hoan thanh: {stats['complete']:<43}|")
    print(f"|  +-- Dang lam: {stats['in_progress']:<45}|")
    print(f"|  +-- Tam dung: {stats['paused']:<45}|")
    print("|" + " " * 62 + "|")
    
    # Projects progress section
    if stats['projects']:
        print("|  TIEN DO TUNG PROJECT" + " " * 40 + "|")
        print("|  +" + "-" * 58 + "+  |")
        
        for i, p in enumerate(stats['projects'][:5], 1):  # Show top 5
            name = p['name'][:25]
            progress = p.get('progress', 0)
            bar = create_progress_bar(progress, 15)
            phase = p.get('current_phase', 'Unknown')[:20]
            
            if p.get('status') == 'complete':
                phase = "[DONE]"
            elif p.get('status') == 'deleted':
                phase = "[DELETED]"
            
            print(f"|  | {i}. {name:<25}" + " " * (28 - len(name)) + "|  |")
            print(f"|  |    {bar} {progress:>3}%  |  {phase:<18}|  |")
            if i < len(stats['projects'][:5]):
                print("|  |" + " " * 58 + "|  |")
        
        print("|  +" + "-" * 58 + "+  |")
        print("|" + " " * 62 + "|")
    
    # Tech stack section
    if stats['top_tech']:
        print("|  TECH STACK PHO BIEN" + " " * 41 + "|")
        total = stats['total'] if stats['total'] > 0 else 1
        for tech, count in stats['top_tech'][:3]:
            percent = round(count / total * 100)
            bar = create_progress_bar(percent, 15)
            tech_display = tech[:12]
            print(f"|  +-- {tech_display:<12} {bar} {percent:>3}%" + " " * (23 - len(tech_display)) + "|")
        print("|" + " " * 62 + "|")
    
    print("+" + "=" * 62 + "+")
    print()

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("VibeCoding Analytics Dashboard")
        print("Usage:")
        print("  python analytics.py          # Show dashboard")
        print("  python analytics.py --help   # Show this help")
    else:
        print_dashboard()
