@echo off
title AI Coding Starter - Setup
echo.
echo ============================================
echo    AI Coding Starter - Setup Wizard
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat!
    echo Vui long cai dat Python tu: https://python.org
    pause
    exit /b 1
)
echo [OK] Python da cai dat

:: Check Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git chua duoc cai dat!
    echo Vui long cai dat Git tu: https://git-scm.com
    pause
    exit /b 1
)
echo [OK] Git da cai dat

:: Create default folders
echo.
echo Dang tao cac thu muc mac dinh...

if not exist "D:\VibeCoding-Template" (
    echo Dang clone master template...
    git clone https://github.com/Dokhacgiakhoa/google-antigravity.git "D:\VibeCoding-Template"
    if errorlevel 1 (
        echo [ERROR] Khong the clone template!
        pause
        exit /b 1
    )
    echo [OK] Da clone master template
) else (
    echo [OK] Master template da ton tai
)

if not exist "D:\Projects" (
    mkdir "D:\Projects"
    echo [OK] Da tao thu muc D:\Projects
) else (
    echo [OK] Thu muc D:\Projects da ton tai
)

:: Copy new_project.py to accessible location
echo.
echo Dang setup...

:: Create shortcut in Projects folder
copy "%~dp0new_project.py" "D:\Projects\new_project.py" >nul 2>&1

:: Create batch shortcut
echo @echo off > "D:\Projects\NewProject.bat"
echo title VibeCoding - New Project Creator >> "D:\Projects\NewProject.bat"
echo python "%~dp0new_project.py" >> "D:\Projects\NewProject.bat"
echo pause >> "D:\Projects\NewProject.bat"

echo.
echo ============================================
echo    SETUP HOAN TAT!
echo ============================================
echo.
echo Cac buoc tiep theo:
echo.
echo 1. Mo thu muc D:\Projects
echo 2. Double-click "NewProject.bat" de tao du an moi
echo 3. Mo du an trong Antigravity IDE
echo.
echo Hoac chay truc tiep:
echo    python new_project.py
echo.
echo ============================================
echo.
pause
