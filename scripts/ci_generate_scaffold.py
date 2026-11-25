#!/usr/bin/env python3
"""CI scaffold generation script."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stack_scaffold import scaffold_stack


def main():
    bundle = os.environ.get("BUNDLE", "")
    if not bundle:
        print("ERROR: BUNDLE environment variable not set", file=sys.stderr)
        sys.exit(1)

    dest = Path("/tmp/scaffold-" + bundle)
    dest.mkdir(parents=True, exist_ok=True)
    scaffold_stack(dest, bundle, "ci-test")
    print(f"Generated {bundle}")


if __name__ == "__main__":
    main()
