#!/bin/bash

echo ""
echo "============================================"
echo "   AI Coding Starter - Setup Wizard"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 chưa được cài đặt!"
    echo "Vui lòng cài đặt Python từ: https://python.org"
    exit 1
fi
echo "[OK] Python đã cài đặt"

# Check bundled resources availability
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/resources/agents" ]; then
    echo "[OK] Bundled resources available: resources/"
else
    echo "[ERROR] Bundled resources missing! resources/agents not found."
    echo "[ERROR] Please ensure the resources/ directory is present in this repository."
    exit 1
fi

# Set default projects path
PROJECTS_PATH="$HOME/Projects"

echo ""
echo "============================================"
echo "   CAU HINH DUONG DAN / PATH CONFIGURATION"
echo "============================================"
echo ""

read -p "Nhap thu muc luu du an (Enter de dung mac dinh: $PROJECTS_PATH) / Enter projects folder [Default: $PROJECTS_PATH]: " INPUT_PATH
if [ -n "$INPUT_PATH" ]; then
    PROJECTS_PATH="$INPUT_PATH"
fi

# Create Projects folder
mkdir -p "$PROJECTS_PATH" 2>/dev/null
echo "[OK] Thu muc Projects: $PROJECTS_PATH"

# Create config.json (portable, machine-agnostic)
echo ""
echo "Dang tao file cau hinh / Creating config file..."

cat > "$SCRIPT_DIR/config.json" << EOF
{
  "MASTER_TEMPLATE_PATH": null,
  "DEFAULT_PROJECT_PATH": "$PROJECTS_PATH",
  "bundled_resources_enabled": true,
  "external_template_optional": true
}
EOF

echo "[OK] Da luu cau hinh vao / Saved configuration to: config.json"

# Set up shortcuts
echo ""
echo "============================================"
echo "   TAO SHORTCUT / CREATING SHORTCUTS"
echo "============================================"

# Create local NewPJ launcher
cat > "$SCRIPT_DIR/NewPJ.bat" << 'SHORTCUT'
@echo off
title VibeCoding - New Project Creator
cd /d "%~dp0"
cls
color 0B
python new_project.py
pause
SHORTCUT

echo "[OK] Da tao / Created: NewPJ.bat"

echo ""
echo "============================================"
echo "   SETUP HOAN TAT! / SETUP COMPLETED!"
echo "============================================"
echo ""
echo "Cac buoc tiep theo / Next steps:"
echo ""
echo "1. Chay: python3 new_project.py"
echo "2. Chon loai du an va tech stack qua giao dien."
echo "3. Du an se duoc tao tai: $PROJECTS_PATH"
echo ""
echo "============================================"
echo ""