@echo off
chcp 65001 >nul
title Video Task System - Starter

echo ========================================
echo     Video Task Sentinel v1.0.0
echo ========================================
echo.

echo [Check] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%scripts"

echo [Check] Checking dependencies...
python -c "import flask,flask_cors,mysql.connector,paramiko,psutil" >nul 2>&1
if errorlevel 1 (
    echo [Install] Installing dependencies...
    pip install flask flask-cors mysql-connector-python paramiko psutil -q
)
echo [OK] Dependencies ready
echo.

echo ========================================
echo     Starting Server...
echo ========================================
echo.
echo Access URLs:
echo   Dashboard: http://localhost:5000/
echo   Tencent MPS: http://localhost:5000/mps
echo   Logs: http://localhost:5000/logs
echo   Server Monitor: http://localhost:5000/server-monitor
echo   Settings: http://localhost:5000/settings
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python video_task_dashboard.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start!
    echo Possible reasons:
    echo 1. Port 5000 is in use
    echo 2. Database connection failed
    echo 3. Config file error
    pause
    exit /b 1
)

pause
