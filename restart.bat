@echo off
title Video Task System - Restart

echo.
echo ========================================
echo     Video Task System - Restart
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Stopping existing service...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000.*LISTENING"') do (
    echo       Stopping PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
ping 127.0.0.1 -n 3 >nul
echo       [OK] Stopped
echo.

echo [2/3] Checking environment...
where python >nul 2>&1
if errorlevel 1 (
    echo       [ERROR] Python not found
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo       [OK] %%i
echo.

echo [3/3] Starting service...
if not exist "scripts\video_task_dashboard.py" (
    echo       [ERROR] scripts\video_task_dashboard.py not found
    echo       Current dir: %CD%
    echo.
    pause
    exit /b 1
)
cd scripts
start "video_task_dashboard" /min python video_task_dashboard.py
cd ..

echo       Waiting for startup...
ping 127.0.0.1 -n 4 >nul

echo.
echo       Checking port 5000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000.*LISTENING"') do (
    set NEWPID=%%a
)

if defined NEWPID (
    echo.
    echo ========================================
    echo     Restart Success!
    echo ========================================
    echo.
    echo   PID: %NEWPID%
    echo   URL: http://localhost:5000
    echo   Settings: http://localhost:5000/settings
    echo.
    echo   Closing this window will NOT stop the service
    echo ========================================
) else (
    echo.
    echo ========================================
    echo     [WARN] Could not confirm service started
    echo ========================================
    echo.
    echo   Please check: http://localhost:5000
    echo ========================================
)

echo.
pause