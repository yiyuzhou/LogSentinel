@echo off
title Video Task Sentinel - Start

echo ========================================
echo     Video Task Sentinel v1.0.0
echo ========================================
echo.

:: Check Python
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

:: Change to scripts directory
cd /d %~dp0scripts
if errorlevel 1 (
    echo [ERROR] Cannot access scripts directory
    pause
    exit /b 1
)

:: Check dependencies
echo Checking dependencies...
python -c "import flask" >nul 2>&1 && echo [OK] flask || (echo [INSTALL] flask & pip install flask -q)
python -c "import flask_cors" >nul 2>&1 && echo [OK] flask-cors || (echo [INSTALL] flask-cors & pip install flask-cors -q)
python -c "import mysql.connector" >nul 2>&1 && echo [OK] mysql-connector-python || (echo [INSTALL] mysql-connector-python & pip install mysql-connector-python -q)
python -c "import paramiko" >nul 2>&1 && echo [OK] paramiko || (echo [INSTALL] paramiko & pip install paramiko -q)
python -c "import psutil" >nul 2>&1 && echo [OK] psutil || (echo [INSTALL] psutil & pip install psutil -q)

echo.
echo ========================================
echo     Starting server...
echo ========================================
echo.
echo Access URLs:
echo   http://localhost:5000/
echo   http://localhost:5000/mps
echo   http://localhost:5000/logs
echo   http://localhost:5000/server-monitor
echo   http://localhost:5000/settings
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

:: Start the server
python video_task_dashboard.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo [ERROR] Server failed to start
    echo ========================================
    pause
    exit /b 1
)

pause
