#!/usr/bin/env python3
"""Release validation script - validates all FULL scaffolds build successfully."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stack_scaffold import scaffold_stack

FULL_BUNDLES = [
    "react-static", "nextjs-supabase", "nextjs-dotnet-postgres",
    "fastapi-postgres", "ai-rag-python", "dotnet-postgres",
    "nestjs-postgres", "nextjs-vercel", "vue-lite", "expo-supabase-mobile",
]


def build_bundle(bundle: str) -> bool:
    dest = Path("/tmp/release-" + bundle)
    dest.mkdir(parents=True, exist_ok=True)
    scaffold_stack(dest, bundle, "release-test")
    print(f"Generated {bundle}")

    build_ok = False
    if (dest / "package.json").exists():
        r1 = subprocess.run(["npm", "ci"], cwd=dest, capture_output=True, text=True)
        r2 = subprocess.run(["npm", "run", "build"], cwd=dest, capture_output=True, text=True)
        build_ok = r1.returncode == 0 and r2.returncode == 0
        if not build_ok:
            print(f"  npm build FAILED: {r2.stderr[-500:]}")
    elif list(dest.glob("**/*.csproj")):
        csproj = str(next(dest.glob("**/*.csproj")))
        r1 = subprocess.run(["dotnet", "restore", csproj], capture_output=True, text=True)
        r2 = subprocess.run(["dotnet", "build", csproj, "--no-restore"], capture_output=True, text=True)
        build_ok = r1.returncode == 0 and r2.returncode == 0
        if not build_ok:
            print(f"  dotnet build FAILED: {r2.stderr[-500:]}")
    elif (dest / "requirements.txt").exists():
        r1 = subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=dest, capture_output=True, text=True)
        r2 = subprocess.run(["python", "-m", "compileall", "."], cwd=dest, capture_output=True, text=True)
        build_ok = r1.returncode == 0 and r2.returncode == 0
        if not build_ok:
            print(f"  python build FAILED: {r2.stderr[-500:]}")

    if build_ok:
        print(f"  {bundle}: PASS")
    else:
        print(f"  {bundle}: FAIL")
    return build_ok


def main():
    failures = []
    for bundle in FULL_BUNDLES:
        if not build_bundle(bundle):
            failures.append(bundle)

    if failures:
        print(f"\nFAILED bundles: {failures}")
        sys.exit(1)
    else:
        print("\nAll FULL scaffold bundles built successfully")


if __name__ == "__main__":
    main()
