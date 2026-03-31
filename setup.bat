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

:: Check Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git chua duoc cai dat! / Git is not installed!
    echo Vui long cai dat Git tu / Please install Git from: https://git-scm.com
    pause
    exit /b 1
)
echo [OK] Git da cai dat

:: Setup Directories
echo.
echo ============================================
echo    CAU HINH DUONG DAN / PATH CONFIGURATION
echo ============================================
set "DEFAULT_BASE=%USERPROFILE%\VibeCoding"
set /p "USER_BASE=Nhap thu muc lam viec (Enter de dung mac dinh: %DEFAULT_BASE%) / Enter workspace folder [Default]: "
if "%USER_BASE%"=="" set "USER_BASE=%DEFAULT_BASE%"

set "TEMPLATE_DIR=%USER_BASE%\Template"
set "PROJECTS_DIR=%USER_BASE%\Projects"

if not exist "%TEMPLATE_DIR%" mkdir "%TEMPLATE_DIR%" 2>nul
if not exist "%PROJECTS_DIR%" mkdir "%PROJECTS_DIR%" 2>nul
echo [OK] Thu muc lam viec / Workspace: %USER_BASE%

:: GitHub Template Setup
echo.
echo ============================================
echo    CLONE MASTER TEMPLATE
echo ============================================
set "TEMPLATE_URL=https://github.com/Dokhacgiakhoa/antigravity-ide.git"

:CLONE_RETRY
if exist "%TEMPLATE_DIR%\.agent" (
    echo [OK] Master template da ton tai / Master template already exists in: %TEMPLATE_DIR%
    goto CLONE_DONE
)

echo Dang clone master template tu %TEMPLATE_URL%...
git clone "%TEMPLATE_URL%" "%TEMPLATE_DIR%"
if errorlevel 1 (
    echo.
    echo [ERROR] Khong the clone template tu %TEMPLATE_URL%!
    echo [ERROR] Cannot clone template!
    set "NEW_URL="
    set /p "NEW_URL=Nhap link github moi hoac nhan Enter de thu lai / Enter new GitHub URL or press Enter to retry: "
    goto HANDLE_URL_INPUT
) else (
    echo [OK] Da clone master template thanh cong.
    goto CLONE_DONE
)

:HANDLE_URL_INPUT
if not "%NEW_URL%"=="" set "TEMPLATE_URL=%NEW_URL%"
goto CLONE_RETRY

:CLONE_DONE

:: Create config.json
echo.
echo Dang tao file cau hinh / Creating config file...
echo {> "%~dp0config.json"
:: Replace backslashes with double backslashes for JSON
set "JSON_TEMPLATE_DIR=%TEMPLATE_DIR:\=\\%"
set "JSON_PROJECTS_DIR=%PROJECTS_DIR:\=\\%"
echo   "MASTER_TEMPLATE_PATH": "%JSON_TEMPLATE_DIR%\\.agent",>> "%~dp0config.json"
echo   "DEFAULT_PROJECT_PATH": "%JSON_PROJECTS_DIR%">> "%~dp0config.json"
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
echo 2. Chon cac template agents phu hop theo giao dien.
echo.
pause
