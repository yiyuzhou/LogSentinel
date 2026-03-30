@echo off
chcp 65001 >nul
title 视频任务运维系统 - 停止脚本

echo ========================================
echo     视频任务运维系统 - 停止服务
echo ========================================
echo.

:: 查找 Python 进程
echo [查找] 正在查找运行的服务进程...

for /f "tokens=2" %%i in ('tasklist /FI "WINDOWTITLE eq video_task_dashboard*" /NH 2^>nul') do (
    set PID=%%i
    goto :found
)

:: 尝试通过命令行查找
for /f "tokens=2" %%i in ('wmic process where "CommandLine like '%%video_task_dashboard.py%%'" get ProcessId 2^>nul ^| findstr [0-9]') do (
    set PID=%%i
    goto :found
)

echo [提示] 未找到运行的服务进程
echo.
pause
exit /b 0

:found
echo [找到] 发现服务进程，PID: %PID%
echo.
echo [警告] 即将停止服务...
echo.

:: 停止进程
taskkill /F /PID %PID% >nul 2>&1

if errorlevel 1 (
    echo [失败] 停止服务失败，请手动关闭
    echo.
    pause
    exit /b 1
) else (
    echo [✓] 服务已停止
    echo.
    echo 按任意键退出...
    pause
    exit /b 0
)
