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

# Check Git
if ! command -v git &> /dev/null; then
    echo "[ERROR] Git chưa được cài đặt!"
    echo "Vui lòng cài đặt Git từ: https://git-scm.com"
    exit 1
fi
echo "[OK] Git đã cài đặt"

# Set default paths
TEMPLATE_PATH="$HOME/VibeCoding-Template"
PROJECTS_PATH="$HOME/Projects"

echo ""
echo "Đang tạo các thư mục mặc định..."

# Clone template if not exists
if [ ! -d "$TEMPLATE_PATH" ]; then
    echo "Đang clone master template..."
    git clone https://github.com/Dokhacgiakhoa/google-antigravity.git "$TEMPLATE_PATH"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể clone template!"
        exit 1
    fi
    echo "[OK] Đã clone master template"
else
    echo "[OK] Master template đã tồn tại"
fi

# Create Projects folder
if [ ! -d "$PROJECTS_PATH" ]; then
    mkdir -p "$PROJECTS_PATH"
    echo "[OK] Đã tạo thư mục $PROJECTS_PATH"
else
    echo "[OK] Thư mục $PROJECTS_PATH đã tồn tại"
fi

# Update paths in new_project.py for Mac/Linux
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed -i.bak "s|D:\\\\VibeCoding-Template|$TEMPLATE_PATH|g" "$SCRIPT_DIR/new_project.py"
sed -i.bak "s|D:\\\\Projects|$PROJECTS_PATH|g" "$SCRIPT_DIR/new_project.py"

# Copy to Projects
cp "$SCRIPT_DIR/new_project.py" "$PROJECTS_PATH/"

echo ""
echo "============================================"
echo "   SETUP HOÀN TẤT!"
echo "============================================"
echo ""
echo "Các bước tiếp theo:"
echo ""
echo "1. Mở thư mục $PROJECTS_PATH"
echo "2. Chạy: python3 new_project.py"
echo "3. Mở dự án trong Antigravity IDE"
echo ""
echo "============================================"
echo ""
