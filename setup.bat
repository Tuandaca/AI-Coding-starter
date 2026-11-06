@echo off
setlocal enabledelayedexpansion

title AI Coding Starter - Setup Wizard
echo.
echo ============================================
echo    AI Coding Starter - Setup Wizard
echo ============================================
echo.

:: Check Python (try python3, python, py)
set "PYTHON_CMD="
python3 --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        py --version >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Python is not installed!
            echo Please install Python from: https://python.org
            pause
            exit /b 1
        ) else (
            set "PYTHON_CMD=py"
        )
    ) else (
        set "PYTHON_CMD=python"
    )
) else (
    set "PYTHON_CMD=python3"
)
echo [OK] Python found: !PYTHON_CMD!

:: Check bundled resources availability
if exist "%~dp0resources\agents" (
    echo [OK] Bundled resources available: resources\
) else (
    echo [ERROR] Bundled resources missing! resources\agents not found.
    echo Please ensure the resources/ directory is present in this repository.
    pause
    exit /b 1
)

:: Run shared setup helper (prompts for projects dir, writes config.json)
echo.
echo ============================================
echo    CONFIGURATION
echo ============================================
echo.

"%PYTHON_CMD%" "%~dp0scripts\setup_portable.py" --python "!PYTHON_CMD!"
if errorlevel 1 (
    echo [ERROR] Setup helper failed.
    pause
    exit /b 1
)

:: Create Windows launcher
echo.
echo ============================================
echo    CREATING SHORTCUTS
echo ============================================
echo @echo off > "%~dp0NewPJ.bat"
echo title VibeCoding - New Project Creator >> "%~dp0NewPJ.bat"
echo cd /d "%%~dp0" >> "%~dp0NewPJ.bat"
echo cls >> "%~dp0NewPJ.bat"
echo color 0B >> "%~dp0NewPJ.bat"
echo "!PYTHON_CMD!" new_project.py >> "%~dp0NewPJ.bat"
echo pause >> "%~dp0NewPJ.bat"
echo [OK] Created: NewPJ.bat

echo.
echo ============================================
echo    SETUP COMPLETED!
echo ============================================
echo.
echo Next steps:
echo 1. Double-click "NewPJ.bat" in this folder to create a new project.
echo 2. Choose project type and tech stack via the UI.
echo.
pause