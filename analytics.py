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

# Error log file
def get_error_log_path():
    """Get error log file path."""
    return get_analytics_dir() / "errors.log"

def log_error(message, error=None):
    """Log error to file for debugging."""
    try:
        log_path = get_error_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
            if error:
                f.write(f"  Error: {type(error).__name__}: {error}\n")
    except:
        pass  # Silently fail - logging should never break the app

def load_analytics():
    """Load analytics data from JSON file with robust error handling."""
    path = get_analytics_path()
    
    if not path.exists():
        return {"projects": [], "version": "1.0"}
    
    # Try multiple encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
                
            # Validate JSON structure
            data = json.loads(content)
            
            # Ensure required keys exist
            if not isinstance(data, dict):
                log_error(f"Analytics file is not a dict: {type(data)}")
                return {"projects": [], "version": "1.0"}
            
            if "projects" not in data:
                data["projects"] = []
            
            if not isinstance(data["projects"], list):
                log_error(f"Projects is not a list: {type(data['projects'])}")
                data["projects"] = []
            
            return data
            
        except json.JSONDecodeError as e:
            log_error(f"JSON decode error with {encoding} encoding", e)
            continue
        except UnicodeDecodeError as e:
            log_error(f"Unicode decode error with {encoding} encoding", e)
            continue
        except Exception as e:
            log_error(f"Unexpected error loading analytics", e)
            continue
    
    # All encodings failed - backup corrupted file and start fresh
    log_error("All encodings failed, backing up corrupted file")
    try:
        backup_path = path.with_suffix('.json.corrupted')
        if path.exists():
            import shutil
            shutil.copy(path, backup_path)
    except:
        pass
    
    return {"projects": [], "version": "1.0"}

def save_analytics(data):
    """Save analytics data to JSON file with error handling."""
    path = get_analytics_path()
    
    try:
        # Validate data before saving
        if not isinstance(data, dict):
            log_error(f"Attempted to save non-dict data: {type(data)}")
            return False
        
        # Create directory if not exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first, then rename (atomic write)
        temp_path = path.with_suffix('.json.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Verify the temp file is valid JSON before replacing
        with open(temp_path, 'r', encoding='utf-8') as f:
            json.load(f)  # Will raise if invalid
        
        # Replace original with temp
        if path.exists():
            path.unlink()
        temp_path.rename(path)
        return True
        
    except Exception as e:
        log_error("Error saving analytics", e)
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except:
            pass
        return False

def track_project(project_data):
    """
    Track a new project creation with validation.
    
    project_data: dict with keys:
        - project_name: str
        - project_path: str
        - project_types: list[str]
        - tech_stack: dict
        - environment: dict (optional)
    
    Returns: project ID on success, None on failure
    """
    try:
        analytics = load_analytics()
        
        # Validate required fields
        project_name = str(project_data.get("project_name", "Unknown"))
        project_path = str(project_data.get("project_path", ""))
        
        if not project_name or project_name == "Unknown":
            log_error("Track project called with invalid project_name")
        
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "project_name": project_name,
            "project_path": project_path,
            "project_types": list(project_data.get("project_types", [])),
            "tech_stack": dict(project_data.get("tech_stack", {})),
            "environment": dict(project_data.get("environment", {}))
        }
        
        analytics["projects"].append(record)
        
        if save_analytics(analytics):
            return record["id"]
        else:
            log_error("Failed to save analytics after tracking project")
            return None
            
    except Exception as e:
        log_error("Error tracking project", e)
        return None

# ============================================
# PROGRESS TRACKER
# ============================================

def validate_context_content(content):
    """
    Validate CONTEXT.md content structure.
    Returns (is_valid, issues_list)
    """
    issues = []
    
    # Check if content is too short (likely empty or corrupted)
    if len(content) < 50:
        issues.append("File too short (< 50 chars)")
    
    # Check for required sections
    required_sections = ["Project Status", "Completed", "Current Focus"]
    for section in required_sections:
        if section.lower() not in content.lower():
            issues.append(f"Missing section: {section}")
    
    # Check for binary/garbage content
    try:
        # Count printable vs non-printable chars
        printable = sum(1 for c in content if c.isprintable() or c in '\n\r\t')
        ratio = printable / len(content) if content else 0
        if ratio < 0.9:
            issues.append(f"Too many non-printable chars ({ratio:.0%} printable)")
    except:
        issues.append("Could not validate content characters")
    
    return (len(issues) == 0, issues)

def calculate_progress(context_path):
    """
    Parse CONTEXT.md to calculate project progress.
    
    Returns dict with:
        - progress: int (0-100)
        - done: int (completed tasks)
        - total: int (total tasks)
        - current_phase: str
        - status: str ('complete', 'in-progress', 'paused', 'error')
        - error: str (optional, only if status is 'error')
    """
    context_path = Path(context_path)
    
    # Check file exists
    if not context_path.exists():
        return {
            "progress": 0,
            "status": "no-context",
            "current_phase": "No CONTEXT.md",
            "done": 0,
            "total": 0
        }
    
    # Check file is readable and not too large
    try:
        file_size = context_path.stat().st_size
        if file_size > 1024 * 1024:  # > 1MB is suspicious
            log_error(f"CONTEXT.md too large: {file_size} bytes at {context_path}")
            return {
                "progress": 0,
                "status": "error",
                "current_phase": "File too large",
                "error": f"File size: {file_size} bytes",
                "done": 0,
                "total": 0
            }
    except Exception as e:
        log_error(f"Cannot stat file: {context_path}", e)
        return {
            "progress": 0,
            "status": "error", 
            "current_phase": "Cannot access file",
            "done": 0,
            "total": 0
        }
    
    # Try multiple encodings
    content = None
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(context_path, 'r', encoding=encoding) as f:
                content = f.read()
            break  # Success
        except UnicodeDecodeError:
            continue
        except PermissionError as e:
            log_error(f"Permission denied: {context_path}", e)
            return {
                "progress": 0,
                "status": "error",
                "current_phase": "Permission denied",
                "done": 0,
                "total": 0
            }
        except Exception as e:
            log_error(f"Error reading {context_path}", e)
            continue
    
    if content is None:
        log_error(f"Could not read CONTEXT.md with any encoding: {context_path}")
        return {
            "progress": 0,
            "status": "error",
            "current_phase": "Cannot read file",
            "done": 0,
            "total": 0
        }
    
    # Validate content
    is_valid, issues = validate_context_content(content)
    if not is_valid:
        log_error(f"Invalid CONTEXT.md at {context_path}: {issues}")
        # Continue anyway - try to extract what we can
    
    # Count checkboxes with error handling
    try:
        done = content.count("[x]") + content.count("[X]")
        pending = content.count("[ ]")
        in_progress = content.count("[/]")
        total = done + pending + in_progress
    except Exception as e:
        log_error(f"Error counting checkboxes", e)
        done, pending, in_progress, total = 0, 0, 0, 0
    
    # Calculate percentage safely
    try:
        progress = round((done / total * 100)) if total > 0 else 0
        progress = max(0, min(100, progress))  # Clamp to 0-100
    except Exception:
        progress = 0
    
    # Determine status
    if progress >= 100:
        status = "complete"
    elif in_progress > 0 or done > 0:
        status = "in-progress"
    else:
        status = "paused"
    
    # Find Current Focus with error handling
    current_phase = "Unknown"
    try:
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
                # Limit length
                if len(current_phase) > 50:
                    current_phase = current_phase[:47] + "..."
                break
    except Exception as e:
        log_error("Error extracting current phase", e)
        current_phase = "Parse error"
    
    return {
        "progress": progress,
        "done": done,
        "total": total,
        "in_progress": in_progress,
        "current_phase": current_phase,
        "status": status
    }

def get_all_projects_progress():
    """Get progress for all tracked projects with error handling."""
    try:
        analytics = load_analytics()
    except Exception as e:
        log_error("Error loading analytics for progress", e)
        return []
    
    results = []
    
    for project in analytics.get("projects", []):
        try:
            path = project.get("project_path", "")
            context_path = Path(path) / ".agent" / "CONTEXT.md"
            
            # Check if project directory still exists
            if not path or not Path(path).exists():
                status_info = {
                    "progress": 0,
                    "status": "deleted",
                    "current_phase": "Project not found",
                    "done": 0,
                    "total": 0
                }
            else:
                status_info = calculate_progress(context_path)
            
            results.append({
                "id": project.get("id", "unknown"),
                "name": project.get("project_name", "Unknown"),
                "path": path,
                "types": project.get("project_types", []),
                "created": project.get("timestamp", ""),
                **status_info
            })
            
        except Exception as e:
            log_error(f"Error processing project: {project.get('project_name', 'unknown')}", e)
            # Add a placeholder for this project
            results.append({
                "id": project.get("id", "unknown"),
                "name": project.get("project_name", "Unknown"),
                "path": project.get("project_path", ""),
                "types": [],
                "created": "",
                "progress": 0,
                "status": "error",
                "current_phase": "Error loading",
                "done": 0,
                "total": 0
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
