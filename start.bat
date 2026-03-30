@echo off
chcp 65001 >nul
title 视频任务运维系统 - 启动脚本

echo ========================================
echo     视频任务运维系统
echo     Video Task Sentinel v1.0.0
echo ========================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [✓] Python 已安装
python --version
echo.

:: 进入脚本目录
cd /d %~dp0scripts

:: 检查依赖是否完整
echo [检查] 正在检查依赖...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 Flask...
    pip install flask -q
)

python -c "import flask_cors" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 Flask-CORS...
    pip install flask-cors -q
)

python -c "import mysql.connector" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 MySQL Connector...
    pip install mysql-connector-python -q
)

python -c "import paramiko" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 Paramiko...
    pip install paramiko -q
)

python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 Psutil...
    pip install psutil -q
)

echo [✓] 依赖检查完成
echo.

:: 检查配置文件
cd ..
if not exist "config\database.json" (
    echo [警告] 未找到配置文件，正在创建...
    if exist "config\database.json.example" (
        copy "config\database.json.example" "config\database.json"
        echo.
        echo [提示] 请编辑 config\database.json 配置数据库信息
        echo 按任意键继续启动（使用默认配置可能会报错）...
        pause
    ) else (
        echo [错误] 未找到配置模板文件
        pause
        exit /b 1
    )
)

cd scripts

echo ========================================
echo     正在启动服务...
echo ========================================
echo.
echo 访问地址:
echo   首页（内部译制）: http://localhost:5000/
echo   腾讯 MPS:        http://localhost:5000/mps
echo   日志监控：http://localhost:5000/logs
echo   服务器监控：http://localhost:5000/server-monitor
echo   系统设置：http://localhost:5000/settings
echo.
echo 按 Ctrl+C 可停止服务
echo ========================================
echo.

:: 启动服务
python video_task_dashboard.py

pause
