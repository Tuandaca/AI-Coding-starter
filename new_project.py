#!/usr/bin/env python3
"""
Interactive Project Creator for VibeCoding
Creates new projects with selective agent/skill copying based on project types.

Usage:
    python new_project.py
    
Or via Antigravity chat:
    /new
    new project
"""

import os
import sys
import shutil
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================

MASTER_TEMPLATE_PATH = Path(r"D:\VibeCoding-Template\.agent")
DEFAULT_PROJECT_PATH = Path(r"D:\Projects")
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
# Based on actual files in D:\VibeCoding-Template\.agent
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

def select_tech_stack(selected_types):
    """
    Interactive tech stack selection.
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
        print("  ℹ️  Hiển thị presets phù hợp với tất cả types đã chọn\n")
    
    # Display presets
    print("\n  Chọn preset hoặc tự custom:\n")
    
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
        selection = get_input(f"Lựa chọn [1-{skip_idx}]", "1")
        
        try:
            idx = int(selection.strip())
            
            if 1 <= idx <= len(presets):
                # Selected a preset
                preset = presets[idx - 1]
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
            elif idx == custom_idx:
                # Custom selection
                return select_custom_stack()
            elif idx == skip_idx:
                # Skip - let AI decide later
                return {
                    "type": "skip",
                    "frontend": "TBD (AI will recommend)",
                    "backend": "TBD (AI will recommend)",
                    "database": "TBD (AI will recommend)",
                    "styling": "TBD (AI will recommend)",
                    "hosting": "TBD (AI will recommend)",
                    "extras": []
                }
            else:
                print_error(f"Vui lòng nhập số từ 1-{skip_idx}")
                
        except ValueError:
            print_error("Vui lòng nhập số hợp lệ!")

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
    shared_src = source_base / ".shared"
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
| **Phase** | 🟡 Planning |
| **Started** | {today} |
| **Last Updated** | {today} |
| **Project Types** | {", ".join(type_names)} |

### Phases:
- 🔴 Not Started
- 🟡 Planning
- 🔵 Development  
- 🟣 Testing
- 🟢 Production

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
# MAIN WIZARD
# ============================================

def main():
    """Main wizard flow."""
    print_header()
    
    # Step 1: Check master template
    if not MASTER_TEMPLATE_PATH.exists():
        print_error(f"Master template not found at: {MASTER_TEMPLATE_PATH}")
        print()
        print_info("Please clone the template first:")
        print()
        print(f'    git clone https://github.com/Dokhacgiakhoa/google-antigravity.git "D:\\VibeCoding-Template"')
        print()
        sys.exit(1)
    
    print_success(f"Master template found: {MASTER_TEMPLATE_PATH}")
    print_header()
    
    # Check if starter path exists
    if not MASTER_TEMPLATE_PATH.exists():
        # Fallback to current directory for standalone usage
        global MASTER_TEMPLATE_PATH
        if (Path.cwd() / ".agent").exists():
            MASTER_TEMPLATE_PATH = Path.cwd() / ".agent"
    
    # Step 0: Auto-Discovery
    env_info = {
        "git_user": get_git_user(),
        "tools": check_tools(),
        "os_info": detect_os_info()
    }
    print(f"    🖥️  System: {env_info['os_info']['os']} | Shell: {env_info['os_info']['shell']}")
    print(f"    👤 Git User: {env_info['git_user']['name']} <{env_info['git_user']['email']}>\n")
    
    # Step 1: Get project name
    project_name = get_input("Tên dự án", "my-project")
    
    # Validate project name
    project_name = project_name.replace(" ", "-").lower()
    
    # Step 3: Get project path
    project_path = get_input("Đường dẫn dự án", str(DEFAULT_PROJECT_PATH))
    project_path = Path(project_path)
    
    # Ensure project path exists
    project_path.mkdir(parents=True, exist_ok=True)
    
    full_project_path = project_path / project_name
    agent_path = full_project_path / ".agent"
    
    # Check if already exists
    if agent_path.exists():
        overwrite = get_input(f"Dự án đã tồn tại! Ghi đè? (y/n)", "n")
        if overwrite.lower() != 'y':
            print_info("Đã hủy.")
            sys.exit(0)
        shutil.rmtree(agent_path)
    
    # Step 4: Select project types
    selected_types = select_multiple(PROJECT_TYPES, MAX_TYPES)
    
    # Step 5: Select tech stack
    tech_stack = select_tech_stack(selected_types)
    
    # Step 6: Show summary and confirm
    print("\n" + "-" * 60)
    print("  📋 TÓM TẮT")
    print("-" * 60)
    print(f"  Tên dự án: {project_name}")
    print(f"  Đường dẫn: {full_project_path}")
    print(f"  Loại dự án: {', '.join([PROJECT_TYPES[t]['name'] for t in selected_types])}")
    
    # Show tech stack summary
    if tech_stack.get("type") == "preset":
        print(f"  Tech Stack: {tech_stack.get('preset_name', 'Preset')}")
    elif tech_stack.get("type") == "custom":
        print(f"  Tech Stack: Custom ({tech_stack.get('frontend', '')})")
    else:
        print("  Tech Stack: Skip (AI sẽ đề xuất sau)")
    
    merged = merge_requirements(selected_types)
    print(f"\n  Agents: {len(merged['agents'])}")
    print(f"  Skills: {len(merged['skills'])}")
    print(f"  Shared: {len(merged['shared'])}")
    print(f"  Workflows: {len(merged['workflows'])}")
    print(f"  Scripts: {len(merged['scripts'])}")
    print("-" * 60)
    
    confirm = get_input("\nTạo dự án? (y/n)", "y")
    if confirm.lower() != 'y':
        print_info("Đã hủy.")
        sys.exit(0)
    
    # Create project folder
    full_project_path.mkdir(parents=True, exist_ok=True)
    
    # Step 7: Copy files
    print("\n" + "=" * 60)
    print("  🚀 ĐANG TẠO DỰ ÁN...")
    print("=" * 60)
    
    total_bytes = copy_selective(
        MASTER_TEMPLATE_PATH,
        agent_path,
        merged,
        project_name,
        selected_types,
        tech_stack,
        env_info  # Pass env_info to copy_selective
    )
    
    # Create README.md for the project
    readme_content = f'''# {project_name.replace("-", " ").title()}

> Created with VibeCoding Project Creator

## Project Types
{chr(10).join([f"- {PROJECT_TYPES[t]['name']}" for t in selected_types])}

## Quick Start

1. Open this folder in Antigravity IDE
2. Type: "Đọc nội dung .agent/GEMINI.md"
3. Start building! 🚀

## Available Commands

{chr(10).join([f"- `/{w.replace('.md', '')}`" for w in merged['workflows']])}

---
*Generated by VibeCoding*
'''
    readme_path = full_project_path / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    
    # Create .gitignore
    print("\n  📄 Creating .gitignore...")
    gitignore_content = '''# ===================================
# VibeCoding Project .gitignore
# ===================================

# Dependencies
node_modules/
vendor/
.pnpm-store/

# Build outputs
dist/
build/
out/
.next/
.nuxt/
.output/

# Environment files (NEVER commit these!)
.env
.env.local
.env.*.local
*.env

# IDE & Editor
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db
Desktop.ini

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Cache
.cache/
*.cache
.parcel-cache/
.eslintcache
.stylelintcache

# Testing
coverage/
.nyc_output/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/

# Temporary files
tmp/
temp/
*.tmp
*.temp

# ===================================
# VibeCoding Agent Notes
# ===================================
# The .agent folder IS safe to commit!
# It contains AI configuration, not secrets.
# 
# DO NOT add .agent to gitignore unless you
# specifically don't want to share AI config.
# ===================================
'''
    gitignore_path = full_project_path / ".gitignore"
    gitignore_path.write_text(gitignore_content, encoding="utf-8")
    print_success(".gitignore")
    
    # Step 7: Show success
    print("\n" + "=" * 60)
    print("  ✅ HOÀN TẤT!")
    print("=" * 60)
    print(f"\n  📂 Dự án: {full_project_path}")
    print(f"  📦 Kích thước: {format_size(total_bytes)}")
    
    # Calculate savings (assume full template is ~10MB)
    full_size = 10 * 1024 * 1024
    savings = max(0, 100 - (total_bytes / full_size * 100))
    print(f"  💾 Tiết kiệm: ~{savings:.0f}% so với full template")
    
    print("\n  📌 Bước tiếp theo:")
    print(f"     1. Mở folder '{full_project_path}' trong Antigravity")
    print("     2. Gõ: \"Đọc nội dung .agent/GEMINI.md\"")
    print("     3. Bắt đầu VibeCoding! 🎉")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 Đã hủy.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n  ❌ Lỗi: {e}")
        sys.exit(1)
