#!/bin/bash

echo ""
echo "============================================"
echo "   AI Coding Starter - Setup Wizard"
echo "============================================"
echo ""

# Check Python (try python3 first, then python)
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "[ERROR] Python is not installed!"
    echo "Please install Python from: https://python.org"
    exit 1
fi
echo "[OK] Python found: $PYTHON_CMD"

# Check bundled resources availability
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/resources/agents" ]; then
    echo "[OK] Bundled resources available: resources/"
else
    echo "[ERROR] Bundled resources missing! resources/agents not found."
    echo "Please ensure the resources/ directory is present in this repository."
    exit 1
fi

# Run shared setup helper (prompts for projects dir, writes config.json)
echo ""
echo "============================================"
echo "   CONFIGURATION"
echo "============================================"
echo ""

"$PYTHON_CMD" "$SCRIPT_DIR/scripts/setup_portable.py" --python "$PYTHON_CMD"
if [ $? -ne 0 ]; then
    echo "[ERROR] Setup helper failed."
    exit 1
fi

# Create POSIX launcher
echo ""
echo "============================================"
echo "   CREATING SHORTCUTS"
echo "============================================"
cat > "$SCRIPT_DIR/NewPJ.sh" << SHORTCUT
#!/bin/bash
cd "$(dirname "$0")"
"$PYTHON_CMD" new_project.py
SHORTCUT
chmod +x "$SCRIPT_DIR/NewPJ.sh"
echo "[OK] Created: NewPJ.sh"

echo ""
echo "============================================"
echo "   SETUP COMPLETED!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Run: ./NewPJ.sh (or $PYTHON_CMD new_project.py)"
echo "2. Choose project type and tech stack via the UI."
echo "3. Your project will be created in the selected projects folder."
echo ""
