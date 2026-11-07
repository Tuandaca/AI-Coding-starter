#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Project Creator for VibeCoding
Creates new projects with selective agent/skill copying based on project types.

Usage:
    python new_project.py           # Create new project
    python new_project.py --stats   # View analytics dashboard

Or via Antigravity chat:
    /new
    new project
"""

import os
import sys
import shutil
import importlib
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================

import json

# M3: catalog + resolver integration (new authoritative selection flow).
# These are imported (not executed) at module load so the legacy functions
# below remain available for backward-compatible characterization tests.
from core.catalog_loader import load_catalog, DEFAULT_CATALOG_DIR
from core.resolver import resolve_top, NOT_DECIDED
from core.resource_resolver import resolve_resources

# M4: portable canonical state + derived Markdown (separate layer; the M3
# resolver stays pure and never writes files).
from core.spec import (
    build_project_spec,
    read_project_spec,
    write_project_spec,
)  # noqa: E402
from core.state import (
    build_initial_state,
    build_resources_lock,
    read_state,
    read_resources_lock,
    write_resources_lock,
    write_state,
)  # noqa: E402
from core.portable_renderer import render_all  # noqa: E402

# generic-renderer.py has a hyphen in its file name, so use importlib.
_generic_renderer_mod = importlib.import_module("core.generic-renderer")  # noqa: E402
GenericRenderer = _generic_renderer_mod.GenericRenderer  # noqa: E402

CONFIG_FILE = Path(__file__).parent / "config.json"
# Bundled resources are the DEFAULT source
BUNDLED_RESOURCE_ROOT = Path(__file__).parent / "resources"

# MASTER_TEMPLATE_PATH is now OPTIONAL compatibility fallback
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            _config = json.load(f)
        # External template is optional - only used as fallback if bundled resources unavailable
        _external = _config.get("MASTER_TEMPLATE_PATH")
        MASTER_TEMPLATE_PATH = Path(_external) if _external else None
        DEFAULT_PROJECT_PATH = Path(_config.get("DEFAULT_PROJECT_PATH", str(Path.home() / "Projects")))
    except Exception:
        MASTER_TEMPLATE_PATH = None
        DEFAULT_PROJECT_PATH = Path.home() / "Projects"
else:
    MASTER_TEMPLATE_PATH = None
    DEFAULT_PROJECT_PATH = Path.home() / "Projects"

# Determine effective resource root (bundled canonical, external as optional fallback)
def get_resource_root() -> Path:
    """Get the effective resource root. Bundled is canonical; external is optional fallback."""
    # Bundled resources are the default source (works offline by default)
    if BUNDLED_RESOURCE_ROOT.exists():
        return BUNDLED_RESOURCE_ROOT
    # External template only as fallback when bundled resources unavailable
    if MASTER_TEMPLATE_PATH and MASTER_TEMPLATE_PATH.exists():
        return MASTER_TEMPLATE_PATH
    return BUNDLED_RESOURCE_ROOT

MAX_TYPES = 3
STARTER_PATH = Path(__file__).parent
EXTRA_WORKFLOWS = [
    "status.md",
    "progress.md",
    "fix.md",
    "commit.md",
    "deploy.md"
]

# ============================================
# TECH STACK PRESETS
# ============================================
# Each project type has optimized presets
# Multi-type projects will show merged/combined presets

TECH_PRESETS = {
    "personal-web": {
        "presets": [
            {
                "id": "modern-static",
                "name": "🚀 Modern Static",
                "desc": "Next.js + TailwindCSS - SEO tối ưu, deploy nhanh",
                "frontend": "Next.js 14 + TypeScript",
                "backend": "None (Static Export)",
                "database": "None",
                "styling": "TailwindCSS + Framer Motion",
                "hosting": "Vercel",
                "recommended": True
            },
            {
                "id": "minimal",
                "name": "🎯 Minimal Pure",
                "desc": "HTML/CSS/JS thuần - Nhẹ, đơn giản, dễ maintain",
                "frontend": "HTML + CSS + Vanilla JS",
                "backend": "None",
                "database": "None",
                "styling": "Custom CSS",
                "hosting": "GitHub Pages / Netlify"
            },
            {
                "id": "astro",
                "name": "⚡ Astro Islands",
                "desc": "Astro - Tốc độ cực nhanh, content-focused",
                "frontend": "Astro + React/Vue components",
                "backend": "None (Static)",
                "database": "None",
                "styling": "TailwindCSS",
                "hosting": "Vercel / Cloudflare"
            }
        ]
    },
    "e-commerce": {
        "presets": [
            {
                "id": "nextjs-fullstack",
                "name": "🛒 Next.js Fullstack",
                "desc": "Next.js + Prisma + Stripe - Production-ready",
                "frontend": "Next.js 14 + TypeScript",
                "backend": "Next.js API Routes",
                "database": "PostgreSQL + Prisma ORM",
                "styling": "TailwindCSS + shadcn/ui",
                "hosting": "Vercel + Supabase",
                "extras": ["Stripe Payments", "NextAuth", "Redis Cache"],
                "recommended": True
            },
            {
                "id": "mern-stack",
                "name": "🔥 MERN Stack",
                "desc": "React + Node + MongoDB - Linh hoạt, phổ biến",
                "frontend": "React + TypeScript",
                "backend": "Node.js + Express",
                "database": "MongoDB + Mongoose",
                "styling": "TailwindCSS",
                "hosting": "Railway / Render",
                "extras": ["JWT Auth", "Stripe/PayOS"]
            },
            {
                "id": "python-fastapi",
                "name": "🐍 Python FastAPI",
                "desc": "FastAPI + React - Performance cao, type-safe",
                "frontend": "React + TypeScript",
                "backend": "Python FastAPI",
                "database": "PostgreSQL + SQLAlchemy",
                "styling": "TailwindCSS",
                "hosting": "Railway + Vercel",
                "extras": ["OAuth2", "Celery Tasks"]
            }
        ]
    },
    "saas-platform": {
        "presets": [
            {
                "id": "nextjs-saas",
                "name": "☁️ Next.js SaaS Starter",
                "desc": "Next.js + Supabase + Stripe - Launch nhanh",
                "frontend": "Next.js 14 + TypeScript",
                "backend": "Next.js API + Supabase Edge Functions",
                "database": "Supabase PostgreSQL",
                "styling": "TailwindCSS + shadcn/ui",
                "hosting": "Vercel",
                "extras": ["Supabase Auth", "Stripe Subscriptions", "Resend Email"],
                "recommended": True
            },
            {
                "id": "t3-stack",
                "name": "🔷 T3 Stack",
                "desc": "tRPC + Prisma + NextAuth - Type-safe end-to-end",
                "frontend": "Next.js + TypeScript",
                "backend": "tRPC + Prisma",
                "database": "PostgreSQL / PlanetScale",
                "styling": "TailwindCSS",
                "hosting": "Vercel",
                "extras": ["NextAuth", "Zod Validation"]
            },
            {
                "id": "enterprise",
                "name": "🏢 Enterprise Grade",
                "desc": "Microservices - Scale lớn, team nhiều người",
                "frontend": "Next.js / React",
                "backend": "Node.js + NestJS (or Go/Python)",
                "database": "PostgreSQL + Redis + ElasticSearch",
                "styling": "Design System (custom)",
                "hosting": "AWS / GCP / Azure",
                "extras": ["Kubernetes", "CI/CD", "Monitoring"]
            }
        ]
    },
    "mobile-app": {
        "presets": [
            {
                "id": "react-native",
                "name": "📱 React Native + Expo",
                "desc": "Cross-platform - iOS & Android từ 1 codebase",
                "frontend": "React Native + Expo",
                "backend": "Supabase / Firebase",
                "database": "Supabase PostgreSQL / Firestore",
                "styling": "NativeWind (TailwindCSS)",
                "hosting": "Expo EAS + Supabase",
                "recommended": True
            },
            {
                "id": "flutter",
                "name": "🦋 Flutter + Firebase",
                "desc": "Google's toolkit - UI đẹp, performance tốt",
                "frontend": "Flutter + Dart",
                "backend": "Firebase / Supabase",
                "database": "Firestore / Supabase",
                "styling": "Material Design / Cupertino",
                "hosting": "Firebase Hosting"
            },
            {
                "id": "native",
                "name": "🎯 Native (Swift/Kotlin)",
                "desc": "Performance tối đa - Cho app phức tạp",
                "frontend": "Swift (iOS) / Kotlin (Android)",
                "backend": "Node.js / Python / Go",
                "database": "PostgreSQL / MongoDB",
                "styling": "Native UI",
                "hosting": "AWS / GCP"
            }
        ]
    },
    "game-dev": {
        "presets": [
            {
                "id": "web-phaser",
                "name": "🎮 Web Game (Phaser)",
                "desc": "HTML5 game - Chạy trên browser, dễ share",
                "frontend": "Phaser 3 + TypeScript",
                "backend": "None / Supabase (leaderboard)",
                "database": "None / Supabase",
                "styling": "Canvas/WebGL",
                "hosting": "itch.io / Vercel",
                "recommended": True
            },
            {
                "id": "godot",
                "name": "🤖 Godot Engine",
                "desc": "2D/3D game - Open source, lightweight",
                "frontend": "Godot + GDScript/C#",
                "backend": "None",
                "database": "Local / Nakama",
                "styling": "Godot UI",
                "hosting": "itch.io / Steam"
            },
            {
                "id": "unity",
                "name": "🎯 Unity 3D",
                "desc": "Industry standard - Mobile/PC/Console",
                "frontend": "Unity + C#",
                "backend": "PlayFab / Firebase",
                "database": "Cloud Save",
                "styling": "Unity UI Toolkit",
                "hosting": "Unity Gaming Services"
            }
        ]
    },
    "ai-ml": {
        "presets": [
            {
                "id": "rag-app",
                "name": "🤖 RAG Application",
                "desc": "Chat với documents - LangChain + Vector DB",
                "frontend": "Next.js + TypeScript",
                "backend": "Python FastAPI + LangChain",
                "database": "PostgreSQL + pgvector / Pinecone",
                "styling": "TailwindCSS",
                "hosting": "Modal / Railway + Vercel",
                "extras": ["OpenAI/Anthropic API", "LangSmith"],
                "recommended": True
            },
            {
                "id": "ai-agent",
                "name": "🧠 AI Agent Platform",
                "desc": "Multi-agent system - Autonomous AI",
                "frontend": "Next.js / Streamlit",
                "backend": "Python + CrewAI / AutoGen",
                "database": "PostgreSQL + Redis",
                "styling": "TailwindCSS / Streamlit",
                "hosting": "Modal / AWS Lambda",
                "extras": ["Tool Calling", "Memory Systems"]
            },
            {
                "id": "ml-api",
                "name": "📊 ML API Service",
                "desc": "Deploy ML models - API for inference",
                "frontend": "None / React Dashboard",
                "backend": "Python FastAPI + MLflow",
                "database": "PostgreSQL + S3 (models)",
                "styling": "None",
                "hosting": "AWS SageMaker / Modal",
                "extras": ["Model Versioning", "A/B Testing"]
            }
        ]
    },
    "fullstack": {
        "presets": [
            {
                "id": "nextjs-prisma",
                "name": "🔥 Next.js + Prisma",
                "desc": "Modern fullstack - Type-safe, fast iteration",
                "frontend": "Next.js 14 + TypeScript",
                "backend": "Next.js API Routes + Prisma",
                "database": "PostgreSQL (Supabase/Neon)",
                "styling": "TailwindCSS + shadcn/ui",
                "hosting": "Vercel",
                "recommended": True
            },
            {
                "id": "mern",
                "name": "💚 MERN Stack",
                "desc": "Classic combo - React + Node + MongoDB",
                "frontend": "React + TypeScript + Vite",
                "backend": "Node.js + Express",
                "database": "MongoDB + Mongoose",
                "styling": "TailwindCSS",
                "hosting": "Railway / Render"
            },
            {
                "id": "python-react",
                "name": "🐍 Python + React",
                "desc": "FastAPI backend - Strong typing, great DX",
                "frontend": "React + TypeScript + Vite",
                "backend": "Python FastAPI",
                "database": "PostgreSQL + SQLAlchemy",
                "styling": "TailwindCSS",
                "hosting": "Railway + Vercel"
            },
            {
                "id": "go-react",
                "name": "🚀 Go + React",
                "desc": "High performance - Golang backend",
                "frontend": "React + TypeScript",
                "backend": "Go + Fiber/Gin",
                "database": "PostgreSQL",
                "styling": "TailwindCSS",
                "hosting": "Railway / Fly.io"
            }
        ]
    }
}

# Custom stack options for manual selection
CUSTOM_STACK_OPTIONS = {
    "frontend": [
        ("nextjs", "Next.js 14 + TypeScript"),
        ("react", "React + Vite + TypeScript"),
        ("vue", "Vue 3 + Vite + TypeScript"),
        ("svelte", "SvelteKit + TypeScript"),
        ("astro", "Astro"),
        ("html", "HTML + CSS + Vanilla JS"),
        ("none", "None (API only)")
    ],
    "backend": [
        ("nextjs-api", "Next.js API Routes"),
        ("express", "Node.js + Express"),
        ("fastapi", "Python FastAPI"),
        ("django", "Python Django"),
        ("go", "Go + Fiber/Gin"),
        ("nestjs", "NestJS"),
        ("supabase", "Supabase (BaaS)"),
        ("firebase", "Firebase (BaaS)"),
        ("none", "None (Static/Frontend only)")
    ],
    "database": [
        ("postgresql", "PostgreSQL"),
        ("mysql", "MySQL"),
        ("mongodb", "MongoDB"),
        ("supabase", "Supabase PostgreSQL"),
        ("firebase", "Firebase Firestore"),
        ("sqlite", "SQLite"),
        ("none", "None")
    ],
    "styling": [
        ("tailwind", "TailwindCSS"),
        ("shadcn", "TailwindCSS + shadcn/ui"),
        ("chakra", "Chakra UI"),
        ("mui", "Material UI"),
        ("css", "Custom CSS/SCSS"),
        ("styled", "Styled Components")
    ],
    "hosting": [
        ("vercel", "Vercel"),
        ("netlify", "Netlify"),
        ("railway", "Railway"),
        ("render", "Render"),
        ("aws", "AWS"),
        ("gcp", "Google Cloud"),
        ("vps", "VPS (DigitalOcean, etc.)"),
        ("github-pages", "GitHub Pages")
    ]
}

# Project Type Matrix - Maps project types to required agents, skills, and shared modules
# Based on actual files in the bundled resources/ directory
PROJECT_TYPES = {
    "personal-web": {
        "name": "🌐 Personal Web / Portfolio",
        "description": "Website cá nhân, portfolio, landing page",
        "agents": [
            "frontend-specialist.md",
            "project-planner.md",
            "orchestrator.md",
            "seo-specialist.md"
        ],
        "skills": [
            "modern-web-architect",
            "seo-expert-kit",
            "cro-expert-kit"
        ],
        "shared": [
            "design-system",
            "ui-ux-pro-max",
            "vitals-templates",
            "seo-master"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "preview.md",
            "ui-ux-pro-max.md",
            "seo.md"
        ],
        "scripts": [
            "auto_preview.py",
            "checklist.py"
        ],
        "focus": "Premium UI/UX, SEO optimization, fast performance"
    },
    "e-commerce": {
        "name": "🛒 E-commerce",
        "description": "Cửa hàng online, marketplace, bán hàng",
        "agents": [
            "backend-specialist.md",
            "frontend-specialist.md",
            "security-auditor.md",
            "project-planner.md",
            "orchestrator.md",
            "test-engineer.md"
        ],
        "skills": [
            "modern-web-architect",
            "api-documenter",
            "database-migration",
            "security-auditor",
            "cro-expert-kit",
            "tdd-master-workflow"
        ],
        "shared": [
            "api-standards",
            "database-master",
            "security-armor",
            "design-system",
            "testing-master"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "preview.md",
            "test.md",
            "deploy.md",
            "security.md"
        ],
        "scripts": [
            "auto_preview.py",
            "checklist.py",
            "verify_all.py"
        ],
        "focus": "Secure payments, product management, user authentication"
    },
    "saas-platform": {
        "name": "☁️ SaaS Platform",
        "description": "Software as a Service, subscription-based apps",
        "agents": [
            "backend-specialist.md",
            "frontend-specialist.md",
            "cloud-architect.md",
            "performance-optimizer.md",
            "project-planner.md",
            "orchestrator.md",
            "security-auditor.md"
        ],
        "skills": [
            "modern-web-architect",
            "api-documenter",
            "deployment-engineer",
            "performance-engineer",
            "cloud-architect-master",
            "security-auditor"
        ],
        "shared": [
            "api-standards",
            "database-master",
            "infra-blueprints",
            "metrics",
            "security-armor",
            "resilience-patterns"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "preview.md",
            "test.md",
            "deploy.md",
            "monitor.md"
        ],
        "scripts": [
            "auto_preview.py",
            "checklist.py",
            "verify_all.py"
        ],
        "focus": "Scalability, multi-tenancy, subscription management"
    },
    "mobile-app": {
        "name": "📱 Mobile App",
        "description": "iOS, Android, React Native, Flutter",
        "agents": [
            "mobile-developer.md",
            "backend-specialist.md",
            "project-planner.md",
            "orchestrator.md",
            "test-engineer.md"
        ],
        "skills": [
            "mobile-design",
            "api-documenter",
            "performance-engineer"
        ],
        "shared": [
            "api-standards",
            "design-system",
            "ui-ux-pro-max",
            "testing-master"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "test.md"
        ],
        "scripts": [
            "checklist.py"
        ],
        "focus": "Cross-platform, native performance, mobile UX"
    },
    "game-dev": {
        "name": "🎮 Game Development",
        "description": "2D/3D games, Unity, Godot, Phaser",
        "agents": [
            "game-developer.md",
            "project-planner.md",
            "orchestrator.md",
            "performance-optimizer.md"
        ],
        "skills": [
            "game-development"
        ],
        "shared": [
            "design-system",
            "design-philosophy"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "debug.md"
        ],
        "scripts": [
            "checklist.py"
        ],
        "focus": "Game mechanics, physics, asset management"
    },
    "ai-ml": {
        "name": "🤖 AI/ML Project",
        "description": "Machine Learning, LLM apps, RAG systems",
        "agents": [
            "backend-specialist.md",
            "project-planner.md",
            "orchestrator.md",
            "test-engineer.md"
        ],
        "skills": [
            "ai-engineer",
            "api-documenter",
            "mcp-builder"
        ],
        "shared": [
            "ai-master",
            "api-standards"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "test.md",
            "debug.md"
        ],
        "scripts": [
            "checklist.py",
            "verify_all.py"
        ],
        "focus": "LLM integration, RAG pipelines, AI agents"
    },
    "fullstack": {
        "name": "🔥 Full-Stack Web App",
        "description": "Frontend + Backend + Database hoàn chỉnh",
        "agents": [
            "backend-specialist.md",
            "frontend-specialist.md",
            "project-planner.md",
            "orchestrator.md",
            "test-engineer.md",
            "debugger.md"
        ],
        "skills": [
            "modern-web-architect",
            "full-stack-scaffold",
            "api-documenter",
            "database-migration",
            "tdd-master-workflow"
        ],
        "shared": [
            "api-standards",
            "database-master",
            "design-system",
            "testing-master"
        ],
        "workflows": [
            "create.md",
            "enhance.md",
            "preview.md",
            "test.md",
            "deploy.md",
            "debug.md"
        ],
        "scripts": [
            "auto_preview.py",
            "checklist.py",
            "verify_all.py"
        ],
        "focus": "Complete web application with API, database, and modern frontend"
    }
}

# ============================================
# AUTO-DISCOVERY
# ============================================

def get_cmd_output(cmd):
    """Run command and return output string."""
    try:
        if sys.platform == "win32":
            # Windows specific handling
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        else:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip()
    except:
        return None

def get_git_user():
    """Get Git user name and email."""
    name = get_cmd_output("git config user.name")
    email = get_cmd_output("git config user.email")
    return {"name": name or "Unknown User", "email": email or "unknown@example.com"}

def check_tools():
    """Check installed tools and versions."""
    tools = {}

    # Checkers map: name -> specific command flag
    checkers = {
        "node": "node -v",
        "python": "python --version",
        "git": "git --version",
        "gh": "gh --version",
        "npm": "npm -v",
        "pnpm": "pnpm -v",
        "yarn": "yarn -v",
        "bun": "bun -v",
        "docker": "docker -v"
    }

    print("\n  🕵️‍♂️  Auto-Discovery System:")

    for tool, cmd in checkers.items():
        ver = get_cmd_output(cmd)
        if ver:
            # Clean version string
            ver = ver.split('\n')[0]  # First line only
            # Remove "v" prefix if mostly numbers
            if ver.startswith('v') and ver[1].isdigit():
                ver = ver[1:]

            tools[tool] = ver
            print(f"    ✅ {tool.ljust(10)} : {ver}")
        else:
            print(f"    ❌ {tool.ljust(10)} : Not found")

    return tools

def detect_os_info():
    """Detect OS and Shell info."""
    import platform
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC") or "Unknown"
    }
    return info

# ============================================
# UTILITY FUNCTIONS
# ============================================

import subprocess  # Ensure subprocess is available

def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print beautiful header."""
    clear_screen()
    print("\n" + "=" * 60)
    print("   🚀 VIBECODING - Interactive Project Creator")
    print("=" * 60)
    print()

def print_success(msg):
    """Print success message."""
    print(f"  ✅ {msg}")

def print_error(msg):
    """Print error message."""
    print(f"  ❌ {msg}")

def print_info(msg):
    """Print info message."""
    print(f"  ℹ️  {msg}")

def get_input(prompt, default=None):
    """Get user input with optional default."""
    if default:
        user_input = input(f"  {prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"  {prompt}: ").strip()

def select_multiple(options, max_select=3):
    """
    Simple multi-select using numbers.
    Returns list of selected keys.
    """
    print("\n  Chọn loại dự án (nhập số, cách nhau bởi dấu phẩy):")
    print(f"  ⚠️  Tối đa {max_select} loại\n")

    keys = list(options.keys())
    for i, key in enumerate(keys, 1):
        info = options[key]
        print(f"    {i}. {info['name']}")
        print(f"       {info['description']}\n")

    while True:
        selection = get_input("Nhập lựa chọn (ví dụ: 1,2)")

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_keys = [keys[i] for i in indices if 0 <= i < len(keys)]

            if not selected_keys:
                print_error("Vui lòng chọn ít nhất 1 loại!")
                continue

            if len(selected_keys) > max_select:
                print_error(f"Chỉ được chọn tối đa {max_select} loại!")
                continue

            return selected_keys

        except (ValueError, IndexError):
            print_error("Lựa chọn không hợp lệ! Nhập số cách nhau bởi dấu phẩy.")

def get_presets_for_types(selected_types):
    """
    Get available presets for selected project types.
    For multi-type: show presets from primary type + combined recommendations.
    """
    all_presets = []
    seen_ids = set()

    for type_key in selected_types:
        if type_key in TECH_PRESETS:
            for preset in TECH_PRESETS[type_key]["presets"]:
                if preset["id"] not in seen_ids:
                    preset_copy = preset.copy()
                    preset_copy["from_type"] = type_key
                    all_presets.append(preset_copy)
                    seen_ids.add(preset["id"])

    # Sort: recommended first, then by name
    all_presets.sort(key=lambda x: (not x.get("recommended", False), x["name"]))

    return all_presets

def merge_tech_stacks(preset_list):
    """
    Merge multiple preset tech stacks into one combined stack.
    Unique values are joined with ' + '.
    """
    fields = ["frontend", "backend", "database", "styling", "hosting"]
    merged = {"type": "preset", "extras": []}

    # Collect preset names
    names = [p["name"] for p in preset_list]
    merged["preset_name"] = " + ".join(names)

    # Merge each field, keeping unique values in order
    for field in fields:
        seen = []
        for preset in preset_list:
            val = preset.get(field, "")
            if val and val not in seen:
                seen.append(val)
        merged[field] = " + ".join(seen) if seen else "TBD"

    # Merge extras
    seen_extras = []
    for preset in preset_list:
        for extra in preset.get("extras", []):
            if extra not in seen_extras:
                seen_extras.append(extra)
    merged["extras"] = seen_extras

    return merged

def select_tech_stack(selected_types):
    """
    Interactive tech stack selection.
    Supports selecting up to 3 presets (comma-separated).
    Returns dict with frontend, backend, database, styling, hosting, extras.
    """
    print("\n" + "=" * 60)
    print("  🔧 CHỌN TECH STACK")
    print("=" * 60)

    # Get available presets for selected types
    presets = get_presets_for_types(selected_types)

    if len(selected_types) > 1:
        type_names = [PROJECT_TYPES[t]["name"] for t in selected_types]
        print(f"\n  📌 Multi-type: {', '.join(type_names)}")
        print("  ℹ️  Hiển thị presets phù hợp với tất cả types đã chọn")

    max_presets = min(3, len(presets))
    print(f"\n  Chọn preset (tối đa {max_presets}, cách nhau bởi dấu phẩy) hoặc tự custom:\n")

    for i, preset in enumerate(presets, 1):
        recommended = " ⭐ RECOMMENDED" if preset.get("recommended") else ""
        print(f"    [{i}] {preset['name']}{recommended}")
        print(f"        {preset['desc']}")
        if len(selected_types) > 1:
            from_type = PROJECT_TYPES[preset['from_type']]['name']
            print(f"        📁 From: {from_type}")
        print()

    # Additional options
    custom_idx = len(presets) + 1
    skip_idx = len(presets) + 2

    print(f"    [{custom_idx}] 🔧 Custom (Tự chọn từng thành phần)")
    print(f"    [{skip_idx}] ⏭️  Skip (Để AI tự đề xuất sau)\n")

    while True:
        selection = get_input(f"Lựa chọn (ví dụ: 1 hoặc 1,3) [1-{skip_idx}]", "1")

        try:
            # Parse comma-separated input
            indices = [int(x.strip()) for x in selection.split(",")]

            # Check for custom or skip (must be standalone)
            if len(indices) == 1:
                idx = indices[0]
                if idx == custom_idx:
                    return select_custom_stack()
                elif idx == skip_idx:
                    return {
                        "type": "skip",
                        "frontend": "TBD (AI will recommend)",
                        "backend": "TBD (AI will recommend)",
                        "database": "TBD (AI will recommend)",
                        "styling": "TBD (AI will recommend)",
                        "hosting": "TBD (AI will recommend)",
                        "extras": []
                    }

            # Validate: custom/skip cannot be combined with presets
            if any(idx in (custom_idx, skip_idx) for idx in indices) and len(indices) > 1:
                print_error("Custom và Skip không thể kết hợp với preset khác!")
                continue

            # Validate preset indices
            selected_presets = []
            valid = True
            for idx in indices:
                if 1 <= idx <= len(presets):
                    selected_presets.append(presets[idx - 1])
                else:
                    print_error(f"Số {idx} không hợp lệ! Chọn từ 1-{skip_idx}")
                    valid = False
                    break

            if not valid:
                continue

            if not selected_presets:
                print_error("Vui lòng chọn ít nhất 1 preset!")
                continue

            if len(selected_presets) > 3:
                print_error("Chỉ được chọn tối đa 3 presets!")
                continue

            # Remove duplicates while keeping order
            seen_ids = set()
            unique_presets = []
            for p in selected_presets:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    unique_presets.append(p)
            selected_presets = unique_presets

            # Show confirmation for multi-preset
            if len(selected_presets) > 1:
                print(f"\n  📦 Đã chọn {len(selected_presets)} presets:")
                for p in selected_presets:
                    print(f"     • {p['name']}")
                merged_stack = merge_tech_stacks(selected_presets)
                print(f"\n  🔀 Tech stack kết hợp:")
                print(f"     Frontend: {merged_stack['frontend']}")
                print(f"     Backend:  {merged_stack['backend']}")
                print(f"     Database: {merged_stack['database']}")
                print(f"     Styling:  {merged_stack['styling']}")
                print(f"     Hosting:  {merged_stack['hosting']}")
                if merged_stack['extras']:
                    print(f"     Extras:   {', '.join(merged_stack['extras'])}")

                confirm = get_input("\n  Xác nhận? (y/n)", "y")
                if confirm.lower() != 'y':
                    continue
                return merged_stack
            else:
                # Single preset
                preset = selected_presets[0]
                return {
                    "type": "preset",
                    "preset_name": preset["name"],
                    "frontend": preset["frontend"],
                    "backend": preset["backend"],
                    "database": preset["database"],
                    "styling": preset["styling"],
                    "hosting": preset["hosting"],
                    "extras": preset.get("extras", [])
                }

        except ValueError:
            print_error("Vui lòng nhập số hợp lệ! (ví dụ: 1 hoặc 1,3)")

def select_custom_stack():
    """
    Manual tech stack selection.
    Returns dict with selected options.
    """
    print("\n  🔧 CUSTOM STACK - Chọn từng thành phần:\n")

    result = {"type": "custom", "extras": []}

    # Frontend
    print("  Frontend:")
    for i, (key, name) in enumerate(CUSTOM_STACK_OPTIONS["frontend"], 1):
        print(f"    [{i}] {name}")
    idx = int(get_input("Chọn frontend", "1")) - 1
    result["frontend"] = CUSTOM_STACK_OPTIONS["frontend"][idx][1]

    # Backend
    print("\n  Backend:")
    for i, (key, name) in enumerate(CUSTOM_STACK_OPTIONS["backend"], 1):
        print(f"    [{i}] {name}")
    idx = int(get_input("Chọn backend", "1")) - 1
    result["backend"] = CUSTOM_STACK_OPTIONS["backend"][idx][1]

    # Database
    print("\n  Database:")
    for i, (key, name) in enumerate(CUSTOM_STACK_OPTIONS["database"], 1):
        print(f"    [{i}] {name}")
    idx = int(get_input("Chọn database", "1")) - 1
    result["database"] = CUSTOM_STACK_OPTIONS["database"][idx][1]

    # Styling
    print("\n  Styling:")
    for i, (key, name) in enumerate(CUSTOM_STACK_OPTIONS["styling"], 1):
        print(f"    [{i}] {name}")
    idx = int(get_input("Chọn styling", "1")) - 1
    result["styling"] = CUSTOM_STACK_OPTIONS["styling"][idx][1]

    # Hosting
    print("\n  Hosting:")
    for i, (key, name) in enumerate(CUSTOM_STACK_OPTIONS["hosting"], 1):
        print(f"    [{i}] {name}")
    idx = int(get_input("Chọn hosting", "1")) - 1
    result["hosting"] = CUSTOM_STACK_OPTIONS["hosting"][idx][1]

    return result

def merge_requirements(selected_types):
    """
    Merge all requirements from selected types.
    Returns dict with merged agents, skills, shared, workflows, scripts.
    """
    merged = {
        "agents": set(),
        "skills": set(),
        "shared": set(),
        "workflows": set(),
        "scripts": set(),
        "focus": []
    }

    for type_key in selected_types:
        config = PROJECT_TYPES[type_key]
        merged["agents"].update(config.get("agents", []))
        merged["skills"].update(config.get("skills", []))
        merged["shared"].update(config.get("shared", []))
        merged["workflows"].update(config.get("workflows", []))
        merged["scripts"].update(config.get("scripts", []))
        merged["focus"].append(config.get("focus", ""))

    # Add extra workflows (VibeCoding enhancements)
    merged["workflows"].update(EXTRA_WORKFLOWS)

    # Convert sets to sorted lists
    for key in ["agents", "skills", "shared", "workflows", "scripts"]:
        merged[key] = sorted(list(merged[key]))

    return merged


# M7: Bundled resource provenance (from catalog/upstream-sources.yaml,
# source "ai-coding-starter-bundled"). All bundled resources are
# locally-authored, introduced in M2 snapshot 8b61d29, covered by MIT.
BUNDLED_PROVENANCE = {
    "source": "bundled",
    "commit_sha": "8b61d297dc07772a000b85fc93138c8aefd21c45",
    "license": "MIT",
    "reviewed_date": "2026-11-06",
    "transformation": "none",
}

# Reviewed date applied to bundled resource provenance in the resources lock.
BUNDLED_REVIEWED_DATE = "2026-11-06"

# Resource categories always copied into every generated project (not
# driven by project-type selection), mapped to canonical resource IDs.
ALWAYS_INCLUDED = [
    ("config.yaml", "template", "core-config"),
    ("lint.md", "rule", "core-rules"),
]


def _strip_ext(filename: str) -> str:
    """Strip a known file extension to obtain the canonical resource id."""
    for ext in (".md", ".py", ".yaml", ".json"):
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


def _build_lock_resources(
    merged: dict, selected_types: list, bundle_id: str
) -> list:
    """Build lock resource entries from merged requirements.

    Maps filesystem resource names (from PROJECT_TYPES / copy_selective) to
    canonical resource IDs with bundled provenance. Always-included core and
    rules resources are appended. Each entry carries the bundled-source
    provenance and a selection reason.
    """
    entries: list = []
    type_reason = "project-type:" + ",".join(selected_types) if selected_types else "manual"

    def add(item: str, rtype: str, reason: str) -> None:
        entries.append(
            {
                "id": _strip_ext(item),
                "type": rtype,
                "version": "1.0.0",
                "provenance": dict(BUNDLED_PROVENANCE),
                "selection_reason": reason,
            }
        )

    for agent in merged.get("agents", []):
        add(agent, "agent", type_reason)
    for skill in merged.get("skills", []):
        add(skill, "skill", type_reason)
    for shared in merged.get("shared", []):
        add(shared, "shared-module", type_reason)
    for workflow in merged.get("workflows", []):
        add(workflow, "workflow", type_reason)
    for script in merged.get("scripts", []):
        add(script, "script", type_reason)

    for item, rtype, reason in ALWAYS_INCLUDED:
        add(item, rtype, reason)

    return entries


def copy_selective(source_base, dest_base, merged_req, project_name, selected_types, tech_stack=None, env_info=None):
    """
    Copy only required files from source to destination.
    Returns total bytes copied.
    """
    total_bytes = 0

    # Ensure destination exists
    dest_base = Path(dest_base)
    dest_base.mkdir(parents=True, exist_ok=True)

    source_base = Path(source_base)

    # Copy agents
    print("\n  📁 Copying agents...")
    agents_src = source_base / "agents"
    agents_dest = dest_base / "agents"
    agents_dest.mkdir(exist_ok=True)

    for agent in merged_req["agents"]:
        src_file = agents_src / agent
        if src_file.exists():
            shutil.copy2(src_file, agents_dest / agent)
            total_bytes += src_file.stat().st_size
            print_success(f"agents/{agent}")
        else:
            print_info(f"Skip (not found): agents/{agent}")

    # Copy skills
    print("\n  📁 Copying skills...")
    skills_src = source_base / "skills"
    skills_dest = dest_base / "skills"
    skills_dest.mkdir(exist_ok=True)

    for skill in merged_req["skills"]:
        src_dir = skills_src / skill
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, skills_dest / skill, dirs_exist_ok=True)
            size = sum(f.stat().st_size for f in src_dir.rglob('*') if f.is_file())
            total_bytes += size
            print_success(f"skills/{skill}/")
        else:
            print_info(f"Skip (not found): skills/{skill}")

    # Copy shared modules
    print("\n  📁 Copying shared modules...")
    shared_src = source_base / "shared"
    shared_dest = dest_base / ".shared"
    shared_dest.mkdir(exist_ok=True)

    for module in merged_req["shared"]:
        src_dir = shared_src / module
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, shared_dest / module, dirs_exist_ok=True)
            size = sum(f.stat().st_size for f in src_dir.rglob('*') if f.is_file())
            total_bytes += size
            print_success(f".shared/{module}/")
        else:
            print_info(f"Skip (not found): .shared/{module}")

    # Copy workflows
    print("\n  📁 Copying workflows...")
    workflows_src = source_base / "workflows"
    starter_workflows_src = STARTER_PATH / ".agent" / "workflows"

    workflows_dest = dest_base / "workflows"
    workflows_dest.mkdir(exist_ok=True)

    for workflow in merged_req["workflows"]:
        # Try finding in master template
        src_file = workflows_src / workflow

        # If not found, try finding in starter .agent
        if not src_file.exists():
            src_file = starter_workflows_src / workflow

        if src_file.exists():
            shutil.copy2(src_file, workflows_dest / workflow)
            total_bytes += src_file.stat().st_size
            print_success(f"workflows/{workflow}")
        else:
            print_info(f"Skip (not found): workflows/{workflow}")

    # Copy scripts
    print("\n  📁 Copying scripts...")
    scripts_src = source_base / "scripts"
    scripts_dest = dest_base / "scripts"
    scripts_dest.mkdir(exist_ok=True)

    for script in merged_req["scripts"]:
        src_file = scripts_src / script
        if src_file.exists():
            shutil.copy2(src_file, scripts_dest / script)
            total_bytes += src_file.stat().st_size
            print_success(f"scripts/{script}")
        else:
            print_info(f"Skip (not found): scripts/{script}")

    # Copy core folder (rules, etc.)
    print("\n  📁 Copying core configuration...")
    core_src = source_base / "core"
    rules_src = source_base / "rules"

    if core_src.exists():
        core_dest = dest_base / "core"
        shutil.copytree(core_src, core_dest, dirs_exist_ok=True)
        size = sum(f.stat().st_size for f in core_src.rglob('*') if f.is_file())
        total_bytes += size
        print_success("core/")

    if rules_src.exists():
        rules_dest = dest_base / "rules"
        shutil.copytree(rules_src, rules_dest, dirs_exist_ok=True)
        size = sum(f.stat().st_size for f in rules_src.rglob('*') if f.is_file())
        total_bytes += size
        print_success("rules/")

    # Generate GEMINI.md
    print("\n  📄 Generating GEMINI.md...")
    generate_gemini_md(dest_base, project_name, selected_types, merged_req, tech_stack, env_info)
    print_success("GEMINI.md")

    # Generate CONTEXT.md for project memory
    print("\n  📄 Generating CONTEXT.md...")
    generate_context_md(dest_base, project_name, selected_types, tech_stack)
    print_success("CONTEXT.md")

    return total_bytes

def generate_gemini_md(dest_base, project_name, selected_types, merged_req, tech_stack=None, env_info=None):
    """Generate customized GEMINI.md based on project types and tech stack."""

    type_names = [PROJECT_TYPES[t]["name"] for t in selected_types]
    if not type_names and tech_stack:
        project_type_name = tech_stack.get("project_type")
        if project_type_name:
            type_names = [project_type_name]
    focus_areas = " | ".join(merged_req["focus"])

    agent_list = "\n".join([f"- `{a.replace('.md', '')}`" for a in merged_req["agents"]])
    skill_list = "\n".join([f"- `{s}`" for s in merged_req["skills"]])
    workflow_list = "\n".join([f"- `/{w.replace('.md', '')}`" for w in merged_req["workflows"]])

    # Tech stack section
    if tech_stack and tech_stack.get("type") != "skip":
        extras_str = ", ".join(tech_stack.get("extras", [])) if tech_stack.get("extras") else "None"
        tech_stack_section = f'''## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | {tech_stack.get("frontend", "TBD")} |
| **Backend** | {tech_stack.get("backend", "TBD")} |
| **Database** | {tech_stack.get("database", "TBD")} |
| **Styling** | {tech_stack.get("styling", "TBD")} |
| **Hosting** | {tech_stack.get("hosting", "TBD")} |
| **Extras** | {extras_str} |

> ⚠️ **IMPORTANT**: Always use the technologies defined above unless user explicitly requests changes.
'''
    else:
        tech_stack_section = '''## 🛠️ Tech Stack

> 💡 Tech stack chưa được định nghĩa. AI sẽ đề xuất dựa trên yêu cầu của bạn.
>
> Để định nghĩa, hãy trả lời các câu hỏi sau khi AI hỏi, hoặc edit file này trực tiếp.
'''

    # Environment Context Section
    env_section = ""
    if env_info:
        git_user = env_info.get("git_user", {})
        tools = env_info.get("tools", {})
        os_info = env_info.get("os_info", {})

        tools_list = "\n".join([f"- **{k.capitalize()}**: {v}" for k, v in tools.items()])

        env_section = f'''
## 🌍 Environment Context

> **System**: {os_info.get("os", "Unknown")} | **Shell**: {os_info.get("shell", "Unknown")}
> **Author**: {git_user.get("name", "Unknown")} <{git_user.get("email", "Unknown")}>

### 🛠️ Available Tools:
{tools_list}
'''

    content = f'''---
trigger: always_on
---

# GEMINI.md - {project_name}

## 🤖 Agent Identity: {project_name}Agent

> **Identity Verification**: You are {project_name}Agent. Always embody this identity in your decisions and style.
> If asked "Bạn là ai?", respond with your identity and project focus.

{env_section}

---

## 📋 Project Context

> **IMPORTANT**: Đọc file `CONTEXT.md` trong thư mục `.agent` để hiểu:
> - Tiến độ project hiện tại
> - Các quyết định đã thực hiện
> - Issues đang tồn tại
> - Các bước tiếp theo
>
> Luôn update `CONTEXT.md` sau mỗi session làm việc!

---

## 🎯 Project Focus: {", ".join(type_names)}

> **Priority**: {focus_areas}

---

{tech_stack_section}

---

## Active Agents
{agent_list}

## Active Skills
{skill_list}

## Available Workflows
{workflow_list}

---

## Behavior Rules

### Auto-run Commands
- **Safe operations**: Auto-run read operations, file viewing, searches
- **Destructive operations**: Always ask for confirmation

### Code Quality
- Follow clean code principles
- Write meaningful commit messages
- Document complex logic

### Communication
- Respond in Vietnamese by default
- Be concise but thorough
- Ask clarifying questions when needed

---

## Custom Project Guidelines

Add your project-specific guidelines here:

1. **Coding Standards**: (Define your code style preferences)
2. **Git Workflow**: (Define branching strategy)
3. **Testing**: (Define testing requirements)

---

*Generated by VibeCoding Project Creator*
*Types: {", ".join(selected_types)}*
*Created: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}*
'''

    gemini_path = Path(dest_base) / "GEMINI.md"
    gemini_path.write_text(content, encoding="utf-8")

    # Also copy rules/GEMINI.md if it contains important base rules
    rules_gemini = Path(dest_base) / "rules" / "GEMINI.md"
    if rules_gemini.exists():
        # Read and append important rules
        pass  # Keep generated one as primary

def generate_context_md(dest_base, project_name, selected_types, tech_stack=None):
    """Generate CONTEXT.md for project memory/context tracking."""
    from datetime import datetime

    type_names = [PROJECT_TYPES[t]["name"] for t in selected_types]
    if not type_names and tech_stack:
        project_type_name = tech_stack.get("project_type")
        if project_type_name:
            type_names = [project_type_name]
    today = datetime.now().strftime("%Y-%m-%d")

    # Tech stack info for context
    if tech_stack and tech_stack.get("type") != "skip":
        tech_info = f"""- Frontend: {tech_stack.get("frontend", "TBD")}
- Backend: {tech_stack.get("backend", "TBD")}
- Database: {tech_stack.get("database", "TBD")}
- Styling: {tech_stack.get("styling", "TBD")}
- Hosting: {tech_stack.get("hosting", "TBD")}"""
    else:
        tech_info = "- (Chưa định nghĩa - AI sẽ đề xuất)"

    content = f'''# 📋 PROJECT CONTEXT - {project_name}

> **QUAN TRỌNG**: File này giúp AI nhớ context dự án giữa các sessions.
> Hãy update thường xuyên để AI hiểu được tiến độ và những gì đã làm.

---

## 📊 Project Status

| Field | Value |
|-------|-------|
| **Phase** | Planning |
| **Started** | {today} |
| **Last Updated** | {today} |
| **Project Types** | {", ".join(type_names)} |

### Phases:
- Not Started
- Planning
- Development
- Testing
- Production

---

## 🛠️ Tech Stack

{tech_info}

---

## 🎯 Current Focus

> Đang làm gì? Viết vào đây để AI biết context hiện tại.

(Chưa có focus cụ thể - mới khởi tạo project)

---

## ✅ Completed Features

Đánh dấu [x] khi hoàn thành:

- [ ] Project setup
- [ ] Basic UI/Layout
- [ ] Core functionality
- [ ] Database integration
- [ ] Authentication (nếu cần)
- [ ] Testing
- [ ] Deployment

---

## 📝 Important Decisions

Ghi lại các quyết định quan trọng để AI và team nhớ:

| Decision | Reason | Date |
|----------|--------|------|
| (Ví dụ: Dùng PostgreSQL) | (Ví dụ: Cần ACID, quan hệ) | {today} |

---

## 🐛 Known Issues

Các lỗi/issues đang tồn tại:

- (Chưa có issues - project mới tạo)

---

## 📌 Next Steps

Các bước tiếp theo cần làm:

1. Đọc GEMINI.md để hiểu project configuration
2. Bắt đầu với `/create` hoặc yêu cầu AI setup project
3. Update file này khi có tiến triển

---

## 💬 Notes

Ghi chú thêm:

- Project được tạo bởi VibeCoding Project Creator
- Xem GEMINI.md để biết tech stack và AI configuration
- Update file này để AI có context tốt hơn!

---

*Auto-generated by VibeCoding*
*Update this file regularly for better AI context!*
'''

    context_path = Path(dest_base) / "CONTEXT.md"
    context_path.write_text(content, encoding="utf-8")

def format_size(bytes_count):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"

# ============================================
# M3: CATALOG-BASED WIZARD FLOW
# ============================================
# New authoritative selection flow:
#   project type -> capabilities -> resolver -> ONE coherent stack bundle
# These functions replace select_multiple/select_tech_stack/merge_tech_stacks
# in the normal path. The legacy functions are retained (deprecated) solely
# for backward-compatible characterization tests.

TECH_DISPLAY_NAMES = {
    "nextjs": "Next.js",
    "react": "React",
    "react-native": "React Native",
    "vue": "Vue",
    "aspnet-core": "ASP.NET Core",
    "fastapi": "FastAPI",
    "nestjs": "NestJS",
    "tauri": "Tauri",
    "postgresql": "PostgreSQL",
    "sqlite": "SQLite",
    "supabase-client": "Supabase Client",
    "supabase-auth": "Supabase Auth",
    "aspnet-identity": "ASP.NET Identity",
    "ef-core": "EF Core",
    "sqlalchemy": "SQLAlchemy",
    "prisma": "Prisma",
    "redis": "Redis",
    "celery": "Celery",
    "rabbitmq": "RabbitMQ",
    "pgvector": "pgvector",
    "vercel": "Vercel",
    "railway": "Railway",
    "aws": "AWS",
    "netlify": "Netlify",
    "tailwindcss": "TailwindCSS",
    "css": "CSS",
    "pytest": "Pytest",
    "xunit": "xUnit",
    "none": "None",
}


def display_id(value: str) -> str:
    """Human-readable display name for a technology ID (UI only, not identity)."""
    return TECH_DISPLAY_NAMES.get(value, value.replace("-", " ").title())


def load_starter_catalog():
    """Load the M3 catalog offline and deterministically."""
    return load_catalog(DEFAULT_CATALOG_DIR)


def select_project_type(catalog):
    """Step 1: choose a project type from the catalog."""
    types = sorted(catalog.project_types.values(), key=lambda pt: str(pt.id))
    print("\n" + "=" * 60)
    print("  📦 BƯỚC 1: LOẠI DỰ ÁN (Project Type)")
    print("=" * 60)
    for i, pt in enumerate(types, 1):
        marker = "  ⚠️  (chưa quyết định)" if str(pt.id) == NOT_DECIDED else ""
        print(f"    [{i}] {pt.name}{marker}")
        print(f"        {pt.description}")
    while True:
        selection = get_input("Chọn loại dự án (hoặc Enter để chọn 'Not Decided')", "")
        if not selection:
            return NOT_DECIDED
        try:
            idx = int(selection.strip()) - 1
            if 0 <= idx < len(types):
                return str(types[idx].id)
        except ValueError:
            pass
        print_error("Lựa chọn không hợp lệ!")


def select_capabilities(catalog, project_type_id):
    """Step 2: choose relevant capabilities for the project type.

    Progressive disclosure: only capabilities relevant to the selected project
    type are shown, defaults are preselected, and skipping is allowed.
    """
    pt = catalog.project_types[project_type_id]
    relevant = sorted({
        str(c) for c in (
            list(pt.default_capabilities) + list(pt.recommended_capabilities)
        )
    })
    defaults = {str(c) for c in pt.default_capabilities}
    print("\n" + "=" * 60)
    print("  🎯 BƯỚC 2: KHẢ NĂNG (Capabilities)")
    print("=" * 60)
    print(f"  Loại dự án: {pt.name}")
    print("  Mặc định đã được chọn (bổ sung hoặc bỏ chọn bằng số):")
    for i, cap_id in enumerate(relevant, 1):
        cap = catalog.capabilities[cap_id]
        marked = "✅" if cap_id in defaults else "⭕"
        print(f"    [{i}] {marked} {cap.name} — {cap.description}")
    selection = get_input(
        "Chọn năng lực bổ sung (số, cách nhau bởi dấu phẩy; -số để bỏ chọn) "
        "hoặc Enter để dùng mặc định: ",
        "",
    )
    if not selection:
        return sorted(defaults)
    chosen = set(defaults)
    try:
        for raw in selection.split(","):
            token = raw.strip()
            if not token:
                continue
            remove = token.startswith("-")
            if remove:
                token = token[1:].strip()
            idx = int(token) - 1
            if not 0 <= idx < len(relevant):
                raise ValueError(token)
            cap_id = relevant[idx]
            if remove:
                chosen.discard(cap_id)
            else:
                chosen.add(cap_id)
        return sorted(chosen)
    except ValueError:
        print_error("Lựa chọn không hợp lệ, dùng mặc định.")
        return sorted(defaults)


def resolve_stacks(catalog, project_type_id, cap_ids):
    """Step 3: resolve compatible, ranked stack bundles (offline, deterministic)."""
    return resolve_top(project_type_id, cap_ids, catalog, limit=5)


def select_bundle(result, catalog):
    """Step 4: choose ONE bundle from the ranked recommendations."""
    print("\n" + "=" * 60)
    print("  🗄️  BƯỚC 3: STACK BUNDLE (chọn MỘT bundle duy nhất)")
    print("=" * 60)
    if not result.ok:
        print_error(result.rejection_reason or "Không thể giải quyết stack.")
        return None
    for i, rec in enumerate(result.bundles, 1):
        print(f"    [{i}] {rec.name} ({rec.profile})")
        print(f"        {rec.description}")
        if rec.matched_capabilities:
            print(f"        ✅ Khả năng khớp: {', '.join(rec.matched_capabilities)}")
        if rec.missing_capabilities:
            print(f"        ⚠️  Chưa có: {', '.join(rec.missing_capabilities)}")
    while True:
        selection = get_input(
            "Chọn một bundle (số) hoặc Enter để chọn bundle đầu tiên: ", ""
        )
        if not selection:
            return result.bundles[0].bundle_id if result.bundles else None
        try:
            idx = int(selection.strip()) - 1
            if 0 <= idx < len(result.bundles):
                return result.bundles[idx].bundle_id
        except ValueError:
            pass
        print_error("Lựa chọn không hợp lệ!")


def bundle_to_tech_stack(bundle, project_type_name=None):
    """Convert a StackBundle into the legacy tech_stack dict shape."""
    techs = bundle.technologies

    def show(role: str) -> str:
        val = str(techs.get(role, "none"))
        return "None" if val == "none" else display_id(val)

    stack = {
        "type": "bundle",
        "bundle_id": str(bundle.id),
        "bundle_name": bundle.name,
        "frontend": show("frontend"),
        "backend": show("backend"),
        "database": show("database"),
        "orm": show("orm") if "orm" in techs else "None",
        "cache": show("cache") if "cache" in techs else "None",
        "hosting": show("hosting") if "hosting" in techs else "None",
        "styling": show("styling") if "styling" in techs else "None",
        "extras": [str(c) for c in bundle.capabilities],
    }
    if project_type_name is not None:
        stack["project_type"] = project_type_name
    return stack


# ============================================
# MAIN WIZARD
# ============================================

def main():
    """Main wizard flow for AI-Coding-starter V2.

    Flow:
      1. Detect environment (Python, resources, etc.)
      2. Collect project identity (name, path)
      3. Select project type -> capabilities -> resolver -> ONE bundle
      4. Resolve resources using declarative adapter model
      5. Select runtime adapter (portable/codex/opencode/antigravity/claude-code/cursor)
      6. Build canonical state IN MEMORY (spec, state, lock)
      7. Show preview of what will be created
      8. Get explicit user confirmation
      9. AFTER confirmation: write canonical state, copy resources,
         render Markdown, install runtime adapter
    """

    print_header()

    # Step 1: Resolve resource root (bundled is default, external is optional)
    resource_root = get_resource_root()

    if resource_root is BUNDLED_RESOURCE_ROOT:
        print_success(f"Using bundled resources: {resource_root}")
    elif MASTER_TEMPLATE_PATH is not None:
        print_success(f"Using external template (compatibility override): {resource_root}")
    else:
        print_error("No resource root available. Bundled resources are missing.")
        print()
        print_info("Ensure the 'resources/' directory exists in the starter repository.")
        print()
        sys.exit(1)

    print_header()

    # Step 0: Auto-Discovery
    env_info = {
        "git_user": get_git_user(),
        "tools": check_tools(),
        "os_info": detect_os_info()
    }
    print(f"    System: {env_info['os_info']['os']} | Shell: {env_info['os_info']['shell']}")
    _gu = env_info['git_user']
    _name = _gu['name']
    _email = _gu['email']
    print(f"    Git User: {_name} <{_email}>\n")

    # Step 1: Get project name
    project_name = get_input("Ten du an", "my-project")

    # Validate project name
    project_name = project_name.replace(" ", "-").lower()

    # Step 2: Get project path
    project_path = get_input("Duong dan du an", str(DEFAULT_PROJECT_PATH))
    project_path = Path(project_path)

    full_project_path = project_path / project_name

    # Check if already exists - reject if non-empty directory.
    # NOTE: we deliberately do NOT create project_path here (CF-1):
    # nothing is written to disk before explicit user confirmation.
    if full_project_path.exists() and any(full_project_path.iterdir()):
        print_error(f"Thu muc '{full_project_path}' da ton tai va khong trong!")
        print_info("Vui long chon ten du an khac hoac thu muc khac.")
        sys.exit(0)

    # Step 3 (M3): Project type -> capabilities -> resolver -> ONE bundle.
    catalog = load_starter_catalog()
    project_type_id = select_project_type(catalog)
    selected_cap_ids = select_capabilities(catalog, project_type_id)
    resolution = resolve_stacks(catalog, project_type_id, selected_cap_ids)
    bundle_id = select_bundle(resolution, catalog)
    if bundle_id is None:
        print_info("Da huy.")
        sys.exit(0)
    bundle = catalog.stack_bundles[bundle_id]
    project_type_display = catalog.project_types[project_type_id].name
    tech_stack = bundle_to_tech_stack(bundle, project_type_display)

    # Step 3b (M7): Resolve resources using declarative adapter model.
    # CF-5: the same effective resource root (bundled or external fallback)
    # is used by both the resolver and the copier so authority is consistent.
    resource_selection = resolve_resources(
        project_type_id,
        selected_cap_ids,
        bundle_id,
        catalog_dir=DEFAULT_CATALOG_DIR,
        resources_root=resource_root,
    )
    if not resource_selection.ok:
        for err in resource_selection.errors:
            print_error(err)
        sys.exit(1)

    # Step 4 (M4): Build canonical state IN MEMORY (no writes yet)
    spec = build_project_spec(
        project_name,
        project_type_id=project_type_id,
        capabilities=selected_cap_ids,
        stack_bundle_id=bundle_id,
        description="",
    )
    state = build_initial_state(
        str(spec.id),
        phase="planning",
        focus="",
        canonical_branch=None,
    )
    lock = build_resources_lock(
        bundle_id,
        requested_bundle_id=bundle_id,
        resources=[
            {
                "id": r.id,
                "type": r.type,
                "version": r.version,
                "provenance": {
                    "source": r.provenance_source,
                    "commit_sha": r.provenance_commit_sha,
                    "license": r.provenance_license,
                    "reviewed_date": BUNDLED_REVIEWED_DATE,
                    "transformation": "none",
                },
                "selection_reason": r.selection_reason,
            }
            for r in resource_selection.resources
        ]
    )

    # Step 5: Runtime selection
    runtime_id = select_runtime()

    # Step 6: Preview (show what will be created)
    print_preview(
        project_name, project_type_id, selected_cap_ids,
        bundle_id, tech_stack, resource_selection, runtime_id,
        full_project_path
    )

    # Step 7: Confirm
    confirm = get_input("\nTao du an? (y/n)", "y")
    if confirm.lower() != 'y':
        print_info("Da huy.")
        sys.exit(0)

    # Step 8: WRITE EVERYTHING (after confirmation only)
    # Transactional strategy (CF-2): build into a staging directory, then
    # atomically finalize into the target. On any failure, staging is removed
    # and the target / user files are never touched.

    # Create parent directory now that the user has confirmed (CF-1: nothing
    # is created before confirmation).
    project_path.mkdir(parents=True, exist_ok=True)

    staging = project_path / f".staging-{project_name}-{os.getpid()}"
    staging.mkdir(parents=True, exist_ok=True)
    staging_proj = staging / project_name

    runtime_ok = True
    runtime_errors: list[str] = []
    total_bytes = 0

    try:
        # Create project folder inside staging
        staging_proj.mkdir(parents=True, exist_ok=True)

        # Write canonical state files
        write_project_spec(staging_proj, spec)
        write_state(staging_proj, state)
        write_resources_lock(staging_proj, lock)

        # Copy resources using resource selection
        merged_req = _build_merge_req_from_selection(resource_selection)
        total_bytes = copy_selective(
            resource_root,
            staging_proj,
            merged_req,
            project_name,
            [],
            tech_stack,
            env_info
        )

        # Render derived Markdown files
        render_all(staging_proj, spec, state)

        # Install runtime adapter (into staging)
        if runtime_id != "portable":
            renderer = GenericRenderer(
                staging_proj, adapters_dir=str(STARTER_PATH / "runtime-adapters")
            )
            render_result = renderer.install(runtime_id)
            if not render_result.ok:
                runtime_ok = False
                runtime_errors = list(render_result.errors)
                for err in render_result.errors:
                    print_error(err)
            else:
                print_success(f"Runtime adapter '{runtime_id}' installed")

            # Render selected agents for the chosen runtime (M6.6).
            agents_data = []
            for r in resource_selection.resources:
                if r.type == "agent":
                    agents_data.append({
                        "id": r.id,
                        "name": r.name,
                        "description": r.description,
                        "division": r.division,
                        "body": r.description,
                    })
            if agents_data:
                agent_render_result = renderer.render_agents(runtime_id, agents_data)
                if not agent_render_result.ok:
                    runtime_ok = False
                    runtime_errors.extend(agent_render_result.errors)
                    for err in agent_render_result.errors:
                        print_error(err)
                else:
                    print_success(
                        f"Rendered {len(agents_data)} agent(s) for {runtime_id}"
                    )

    except Exception as exc:
        # Rollback: remove staging, never touch the target or user files.
        shutil.rmtree(staging, ignore_errors=True)
        print_error(f"Loi tao du an: {exc}")
        print_info("Da hoan tat bo dau; khong file nao duoc ghi vao muc tieu.")
        sys.exit(1)

    # Commit staging into target (atomic rename where possible; copy fallback).
    try:
        if full_project_path.exists():
            # Target exists (must be empty per pre-confirmation check); merge.
            _merge_dir_contents(staging_proj, full_project_path)
        else:
            os.replace(staging_proj, full_project_path)
    except OSError:
        # Cross-device rename fallback: copy then remove staging.
        try:
            if full_project_path.exists():
                _merge_dir_contents(staging_proj, full_project_path)
            else:
                shutil.copytree(staging_proj, full_project_path)
        except OSError:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    # Step 9: Show completion with honest status (CF-4).
    print("\n" + "=" * 60)
    if runtime_id != "portable" and not runtime_ok:
        print("  HOAN TAT (PHAN LOI CAI DAT RUNTIME)")
    else:
        print("  HOAN TAT!")
    print("=" * 60)
    print(f"\n  Du an: {full_project_path}")
    print(f"  Kich thuoc: {format_size(total_bytes)}")

    if runtime_id != "portable" and not runtime_ok:
        print("\n  Trang thai: PARTIAL_SUCCESS")
        print("  Trang thai can duoc cap nhat va chay lai de cai dat runtime adapter.")
        if runtime_errors:
            print(f"  Loi cai dat runtime: {'; '.join(runtime_errors)}")
        print("\n  Buoc tiep theo:")
        print(f"     1. Mo thu muc '{full_project_path}' trong {runtime_id}")
        print(f"     2. Xem .ai-coding-starter/project.yaml")
        print(f"     3. Bat dau VibeCoding!")
        print(f"     4. Cai dat runtime adapter sau (chay lai new_project.py va chon runtime).")
        print()
    else:
        full_size = 10 * 1024 * 1024
        savings = max(0, 100 - (total_bytes / full_size * 100))
        print(f"  Tiet kiem: ~{savings:.0f}% so voi full template")

        print("\n  Buoc tiep theo:")
        print(f"     1. Mo thu muc '{full_project_path}' trong {runtime_id}")
        print(f"     2. Xem .ai-coding-starter/project.yaml")
        print(f"     3. Bat dau VibeCoding!")
        print(f"     4. Xem dashboard: python new_project.py --stats")
        print()


def _merge_dir_contents(src: Path, dst: Path) -> None:
    """Copy all contents of ``src`` into existing directory ``dst``."""
    src = Path(src)
    dst = Path(dst)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def select_runtime():
    """Select runtime adapter for the project.

    Returns:
        Runtime ID string (codex, opencode, antigravity, claude-code, cursor)
        or "portable" for portable-only (no runtime-specific files).
    """
    runtimes = [
        ("portable", "Portable / Shared instructions only", "Portable AGENTS.md only - no runtime-specific files"),
        ("codex", "Codex CLI", "OpenAI Codex CLI - .codex/AGENTS.md"),
        ("opencode", "OpenCode", "OpenCode - .opencode/OpenCode.md"),
        ("antigravity", "Antigravity IDE", "Antigravity IDE - .agent/GEMINI.md"),
        ("claude-code", "Claude Code", "Anthropic Claude Code - .claude/CLAUDE.md"),
        ("cursor", "Cursor", "Cursor IDE - .cursor/AGENTS.md"),
    ]

    print("\n  SELECT RUNTIME ADAPTER")
    print("-" * 60)
    print("  Select how project instructions will be represented:")
    print()
    for i, (rid, name, desc) in enumerate(runtimes, 1):
        print(f"    [{i}] {name}")
        print(f"        {desc}")
    print()

    while True:
        selection = get_input(f"Select runtime (1-{len(runtimes)})", "1")
        try:
            idx = int(selection.strip()) - 1
            if 0 <= idx < len(runtimes):
                return runtimes[idx][0]
            print_error(f"Invalid selection! Choose 1-{len(runtimes)}")
        except ValueError:
            print_error("Invalid selection! Please enter a number.")


def print_preview(project_name, project_type_id, selected_cap_ids,
                  bundle_id, tech_stack, resource_selection, runtime_id,
                  project_root):
    """Show preview of what will be generated."""
    print()
    print("=" * 60)
    print("  PREVIEW")
    print("=" * 60)
    print(f"  Project: {project_name}")
    print(f"  Location: {project_root}")
    print(f"  Type: {project_type_id}")
    print(f"  Capabilities: {', '.join(selected_cap_ids) if selected_cap_ids else '(none)'}")
    print(f"  Stack: {tech_stack.get('bundle_name', bundle_id)} ({bundle_id})")
    print(f"  Runtime: {runtime_id}")
    print()
    print("  Resources to be created:")
    for r in resource_selection.resources:
        print(f"    - {r.type}:{r.id} ({r.selection_reason})")
    print()


def _build_merge_req_from_selection(resource_selection):
    """Build merged_req dict from ResourceSelection for copy_selective.

    Converts ResourceSelection objects (id, type) into the format expected
    by copy_selective():
      - agents: ["project-planner.md", ...]
      - skills: ["modern-web-architect", ...]
      - shared: ["design-system", ...]
      - workflows: ["create.md", ...]
      - scripts: ["auto_preview.py", ...]
    """
    merged = {
        "agents": [],
        "skills": [],
        "shared": [],
        "workflows": [],
        "scripts": [],
        "focus": []
    }
    for r in resource_selection.resources:
        if r.type == "agent":
            merged["agents"].append(f"{r.id}.md")
        elif r.type == "skill":
            merged["skills"].append(r.id)
        elif r.type == "shared-module":
            merged["shared"].append(r.id)
        elif r.type == "workflow":
            merged["workflows"].append(f"{r.id}.md")
        elif r.type == "script":
            if r.id.endswith(".py"):
                merged["scripts"].append(r.id)
            else:
                merged["scripts"].append(f"{r.id}.py")
        elif r.type == "template":
            merged["scripts"].append(f"{r.id}.yaml")
        elif r.type == "rule":
            merged["scripts"].append(f"{r.id}.md")
    for key in ["agents", "skills", "shared", "workflows", "scripts"]:
        merged[key] = sorted(merged[key])
    return merged


if __name__ == "__main__":
    # Check for --stats flag
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        try:
            from analytics import print_dashboard
            print_dashboard()
        except ImportError:
            print("\n  ❌ analytics.py not found. Please check installation.")
            sys.exit(1)
        sys.exit(0)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 Đã hủy.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n  ❌ Lỗi: {e}")
        sys.exit(1)
