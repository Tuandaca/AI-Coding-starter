#!/usr/bin/env python3
"""
Auto Preview Script
Automatically builds and serves a preview of the project for development.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def detect_project_type(project_path):
    """Detect the project type based on files present."""
    path = Path(project_path)

    if (path / "package.json").exists():
        with open(path / "package.json") as f:
            import json
            pkg = json.load(f)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                return "nextjs"
            elif "vite" in deps:
                return "vite"
            elif "react" in deps:
                return "react"
            elif "vue" in deps:
                return "vue"
            else:
                return "node"
    elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return "python"
    elif (path / "Cargo.toml").exists():
        return "rust"
    elif (path / "go.mod").exists():
        return "go"
    else:
        return "unknown"


def build_project(project_path, project_type):
    """Build the project based on its type."""
    commands = {
        "nextjs": "npm run build",
        "vite": "npm run build",
        "react": "npm run build",
        "vue": "npm run build",
        "node": "npm run build",
        "python": "echo 'Python project - no build step typically needed'",
        "rust": "cargo build --release",
        "go": "go build ./...",
    }

    cmd = commands.get(project_type)
    if cmd:
        run_command(cmd, cwd=project_path)
    else:
        print(f"Unknown project type: {project_type}")


def serve_preview(project_path, project_type, port=3000):
    """Serve the preview based on project type."""
    commands = {
        "nextjs": f"npm run start -- -p {port}",
        "vite": f"npm run preview -- --port {port}",
        "react": f"npx serve -s build -l {port}",
        "vue": f"npx serve -s dist -l {port}",
        "python": f"python -m http.server {port}",
    }

    cmd = commands.get(project_type)
    if cmd:
        print(f"Starting preview server on port {port}...")
        print(f"Open http://localhost:{port} in your browser")
        run_command(cmd, cwd=project_path, check=False)
    else:
        print(f"No preview command for project type: {project_type}")


def main():
    parser = argparse.ArgumentParser(description="Auto Preview - Build and serve project preview")
    parser.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")
    parser.add_argument("--port", type=int, default=3000, help="Preview server port (default: 3000)")
    parser.add_argument("--build-only", action="store_true", help="Only build, don't serve")
    parser.add_argument("--serve-only", action="store_true", help="Only serve, don't build")

    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}")
        sys.exit(1)

    print(f"Project path: {project_path}")

    project_type = detect_project_type(project_path)
    print(f"Detected project type: {project_type}")

    if not args.serve_only:
        print("Building project...")
        build_project(project_path, project_type)
        print("Build complete!")

    if not args.build_only:
        serve_preview(project_path, project_type, args.port)


if __name__ == "__main__":
    main()
