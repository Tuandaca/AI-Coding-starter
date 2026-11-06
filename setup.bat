@echo off
setlocal
title AI Coding Starter - Setup
echo.
echo ============================================
echo    AI Coding Starter - Setup Wizard
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat! / Python is not installed!
    echo Vui long cai dat Python tu / Please install Python from: https://python.org
    pause
    exit /b 1
)
echo [OK] Python da cai dat

:: Check bundled resources availability
if exist "%~dp0resources\agents" (
    echo [OK] Bundled resources available: resources\
) else (
    echo [ERROR] Bundled resources missing! resources\agents not found.
    echo [ERROR] Please ensure the resources/ directory is present in this repository.
    pause
    exit /b 1
)

:: Setup Directories
echo.
echo ============================================
echo    CAU HINH DUONG DAN / PATH CONFIGURATION
echo ============================================

set "PROJECTS_DIR="
set "DEFAULT_BASE=%USERPROFILE%"

set /p "PROJECTS_DIR=Nhap thu muc luu du an (Enter de dung mac dinh: %DEFAULT_BASE%\Projects) / Enter projects folder [Default: %%DEFAULT_BASE%%\Projects]: "
if "%PROJECTS_DIR%"=="" set "PROJECTS_DIR=%DEFAULT_BASE%\Projects"

:: Normalize path separators
set "PROJECTS_DIR=%PROJECTS_DIR:/=\%"

if not exist "%PROJECTS_DIR%" mkdir "%PROJECTS_DIR%" 2>nul
echo [OK] Thu muc Projects: %PROJECTS_DIR%

:: Create config.json (portable, machine-agnostic)
echo.
echo Dang tao file cau hinh / Creating config file...
set "JSON_PROJECTS_DIR=%PROJECTS_DIR:\=\%"

echo {> "%~dp0config.json"
echo   "MASTER_TEMPLATE_PATH": null,>> "%~dp0config.json"
echo   "DEFAULT_PROJECT_PATH": "%JSON_PROJECTS_DIR%",>> "%~dp0config.json"
echo   "bundled_resources_enabled": true,>> "%~dp0config.json"
echo   "external_template_optional": true>> "%~dp0config.json"
echo }>> "%~dp0config.json"

echo [OK] Da luu cau hinh vao / Saved configuration to: config.json

:: Set up shortcuts
echo.
echo ============================================
echo    TAO SHORTCUT / CREATING SHORTCUTS
echo ============================================

:: Create local NewPJ.bat
echo @echo off > "%~dp0NewPJ.bat"
echo title VibeCoding - New Project Creator >> "%~dp0NewPJ.bat"
echo cd /d "%%~dp0" >> "%~dp0NewPJ.bat"
echo cls >> "%~dp0NewPJ.bat"
echo color 0B >> "%~dp0NewPJ.bat"
echo python new_project.py >> "%~dp0NewPJ.bat"
echo pause >> "%~dp0NewPJ.bat"
echo [OK] Da tao / Created: NewPJ.bat

echo.
echo ============================================
echo    SETUP HOAN TAT! / SETUP COMPLETED!
echo ============================================
echo.
echo Cac buoc tiep theo / Next steps:
echo 1. Double-click "NewPJ.bat" trong thu muc nay de tao du an moi.
echo 2. Chon loai du an va tech stack qua giao dien.
echo 3. Du an se duoc tao tai: %PROJECTS_DIR%
echo.
pause