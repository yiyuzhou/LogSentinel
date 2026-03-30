#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频任务统计报表 - Web API 服务 (带搜索、详情、分页功能)
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import os
import sys
import json
import math
from mps_module import MPS_LIST_TEMPLATE, MPS_DETAIL_TEMPLATE
from log_viewer import LOG_VIEWER_TEMPLATE, list_log_files, get_log_content, get_new_log_lines, get_log_stats, download_log_file, validate_log_file
from settings import create_settings_routes, init_db_config, get_video_db_config
from server_monitor import register_server_monitor_routes, start_data_collection

app = Flask(__name__)
CORS(app)

# Favicon 路由 - 避免浏览器请求 404 错误
@app.route('/favicon.ico')
def favicon():
    # 返回 204 No Content，避免 404 错误
    return '', 204

# 创建设置路由（在其他路由之前注册）
create_settings_routes(app)

# 初始化数据库配置
init_db_config()

# 从配置文件加载数据库配置
# 注意：不再使用全局缓存，每次请求都从配置文件读取，确保配置同步
_DB_CONFIG_CACHE = None
_CONFIG_CACHE_TIMESTAMP = 0

def get_db_config(profile=None, use_cache=True):
    """获取数据库配置（从配置文件加载）
    
    Args:
        profile: 指定配置档名称，如果为 None 则使用当前激活的配置
        use_cache: 是否使用缓存（默认 True）
    """
    global _DB_CONFIG_CACHE, _CONFIG_CACHE_TIMESTAMP
    
    # 如果指定了 profile，从该配置读取（不使用缓存）
    if profile:
        from settings import get_video_db_config_for_profile
        db_config = get_video_db_config_for_profile(profile)
        if db_config:
            print(f"[get_db_config] 返回 profile '{profile}' 配置：host={db_config['host']}, user={db_config['user']}, password={'***' if db_config['password'] else '(empty)'}")
            return db_config

        print(f"[get_db_config] 警告：找不到 profile '{profile}'，使用当前激活的配置")
        profile = None
    
    # 使用默认逻辑（当前激活的 profile）
    # 检查缓存是否有效（5 秒过期）
    import time
    current_time = time.time()
    if use_cache and _DB_CONFIG_CACHE and (current_time - _CONFIG_CACHE_TIMESTAMP) < 5:
        print(f"[get_db_config] 使用缓存的配置：host={_DB_CONFIG_CACHE.get('host')}, user={_DB_CONFIG_CACHE.get('user')}")
        return _DB_CONFIG_CACHE
    
    # 从配置文件重新加载
    config = get_video_db_config()
    if config:
        print(f"[get_db_config] 从配置文件加载配置：host={config.get('host')}, user={config.get('user')}, password={'***' if config.get('password') else '(empty)'}")
        _DB_CONFIG_CACHE = config
        _CONFIG_CACHE_TIMESTAMP = current_time
        return config
    else:
        # 默认配置（向后兼容）
        print(f"[get_db_config] 警告：get_video_db_config() 返回 None，使用硬编码默认配置")
        _DB_CONFIG_CACHE = {
            'host': '101.126.91.130',
            'port': 4005,
            'database': 'videoai',
            'user': 'yiyuzhou',
            'password': 'yiyuzhou5066995',
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'connection_timeout': 5
        }
        _CONFIG_CACHE_TIMESTAMP = current_time
        return _DB_CONFIG_CACHE

def get_db_connection(profile=None):
    """获取数据库连接
    
    Args:
        profile: 可选的 profile 名称，如果指定则使用该 profile 的配置
    """
    try:
        # 如果指定了 profile，不使用缓存，确保使用最新的配置
        config = get_db_config(profile, use_cache=(profile is None))
        print(f"[get_db_connection] 使用配置：host={config.get('host')}, user={config.get('user')}, password={'***' if config.get('password') else '(empty)'}")
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as e:
        error_msg = f"DB connection error: {e.errno} ({e.sqlstate}): {e.msg}"
        print(error_msg, file=sys.stderr)
        raise
    except Exception as e:
        print(f"DB connection error: {e}", file=sys.stderr)
        raise

def format_rfc_time(time_value):
    """将时间值转换为 yyyy-MM-dd HH:mm:ss 格式"""
    if not time_value:
        return None
    # 如果已经是 datetime 对象，直接格式化
    if isinstance(time_value, datetime):
        return time_value.strftime("%Y-%m-%d %H:%M:%S")
    # 如果是字符串，尝试解析 RFC 格式
    if isinstance(time_value, str):
        try:
            input_format = "%a, %d %b %Y %H:%M:%S GMT"
            dt = datetime.strptime(time_value, input_format)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return time_value[:19] if len(time_value) >= 19 else time_value
    return str(time_value)[:19]

def query_db(sql, params=None, profile=None):
    """执行数据库查询
    
    Args:
        sql: SQL 语句
        params: SQL 参数
        profile: 可选的 profile 名称，如果指定则使用该 profile 的配置
    """
    conn = get_db_connection(profile)
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()

# 列表页 HTML（带分页）
LIST_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频任务运维系统</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --success: #059669;
            --warning: #d97706;
            --danger: #dc2626;
            --info: #7c3aed;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border: #334155;
            --sidebar-width: 240px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: var(--bg-dark); min-height: 100vh; padding: 0; color: var(--text-primary); display: flex; }
        
        /* 左侧菜单栏 */
        .sidebar { width: var(--sidebar-width); background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-right: 1px solid var(--border); min-height: 100vh; position: fixed; left: 0; top: 0; display: flex; flex-direction: column; transition: width 0.3s ease; overflow: hidden; z-index: 100; }
        .sidebar.collapsed { width: 64px; }
        .sidebar-logo { padding: 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .sidebar-logo .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, var(--primary) 0%, var(--info) 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
        .sidebar-logo h1 { color: var(--text-primary); font-size: 18px; font-weight: 600; white-space: nowrap; transition: opacity 0.2s; }
        .sidebar.collapsed .sidebar-logo h1 { opacity: 0; pointer-events: none; }
        .navbar-version { font-size: 11px; color: var(--text-secondary); margin-top: 4px; white-space: nowrap; transition: opacity 0.2s; }
        .sidebar.collapsed .navbar-version { opacity: 0; }
        .sidebar-toggle { background: var(--bg-hover); border: 1px solid var(--border); color: var(--text-secondary); width: 28px; height: 28px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; flex-shrink: 0; }
        .sidebar-toggle:hover { background: var(--primary); color: white; border-color: var(--primary); }
        .sidebar-menu { flex: 1; padding: 16px 12px; overflow-y: auto; }
        .menu-section { color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px; margin-top: 8px; white-space: nowrap; transition: opacity 0.2s; }
        .sidebar.collapsed .menu-section { opacity: 0; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; color: var(--text-secondary); text-decoration: none; transition: all 0.2s; margin-bottom: 4px; cursor: pointer; white-space: nowrap; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(29, 78, 216, 0.1) 100%); color: var(--primary); border: 1px solid rgba(37, 99, 235, 0.3); }
        .menu-item .icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
        .menu-item .label { flex: 1; font-size: 14px; font-weight: 500; transition: opacity 0.2s; }
        .sidebar.collapsed .menu-item .label { opacity: 0; pointer-events: none; }
        .menu-item .menu-badge { background: var(--danger); color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; transition: opacity 0.2s; }
        .sidebar.collapsed .menu-badge { opacity: 0; }
        
        /* 侧边栏底部状态 */
        .sidebar-footer { padding: 16px; border-top: 1px solid var(--border); background: var(--bg-dark); transition: opacity 0.2s; }
        .sidebar.collapsed .sidebar-footer { opacity: 0; }
        .sidebar-status { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 12px; white-space: nowrap; }
        .status-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .last-update { color: var(--text-secondary); font-size: 11px; margin-top: 8px; white-space: nowrap; }
        
        /* 主内容区 */
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; transition: margin-left 0.3s ease; }
        .sidebar.collapsed ~ .main-wrapper, .main-wrapper.collapsed-margin { margin-left: 64px; }
        .main-content { padding: 24px 30px; flex: 1; }
        
        /* 统计卡片 */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); border-color: var(--primary); }
        .stat-card h3 { color: var(--text-secondary); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; font-weight: 500; }
        .stat-card .number { font-size: 32px; font-weight: 700; color: var(--text-primary); }
        .stat-card.total .number { color: var(--primary); }
        .stat-card.waiting .number { color: var(--warning); }
        .stat-card.processing .number { color: #3b82f6; }
        .stat-card.completed .number { color: var(--success); }
        .stat-card.failed .number { color: var(--danger); }
        .stat-card.today .number { color: var(--info); }
        
        /* 操作栏 */
        .toolbar { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
        .toolbar-left { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .toolbar-right { display: flex; align-items: center; gap: 12px; }
        .toolbar-title { font-size: 16px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
        
        /* 搜索表单 */
        .search-form { display: flex; flex-wrap: wrap; gap: 12px; flex: 1; }
        .search-form .search-input, .search-form .search-select { flex: 1; min-width: 160px; }
        .search-input, .search-select { padding: 10px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text-primary); font-size: 13px; transition: all 0.2s; }
        .search-input:focus, .search-select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .search-input::placeholder { color: var(--text-secondary); }
        .search-select option { background: var(--bg-card); color: var(--text-primary); }
        
        /* 按钮 */
        .btn { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        
        /* 表格区域 */
        .table-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px; overflow: hidden; }
        .table-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 16px 20px; font-size: 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
        .table-count { background: rgba(37, 99, 235, 0.2); color: var(--primary); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: rgba(37, 99, 235, 0.1); font-weight: 600; color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }
        tr:hover { background: var(--bg-hover); }
        tr:last-child td { border-bottom: none; }
        
        /* 状态徽章 */
        .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .status-waiting { background: rgba(217, 119, 6, 0.15); color: #fbbf24; border: 1px solid rgba(217, 119, 6, 0.3); }
        .status-processing { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .status-completed { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .status-failed { background: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); }
        .status-queuing { background: rgba(124, 58, 237, 0.15); color: #a78bfa; border: 1px solid rgba(124, 58, 237, 0.3); }
        .status-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
        
        /* 类型徽章 */
        .type-badge { display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; background: rgba(37, 99, 235, 0.15); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.3); }
        
        /* 操作按钮 */
        .detail-btn { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s; }
        .detail-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        
        /* 分页 */
        .pagination { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 16px 20px; background: var(--bg-dark); border-top: 1px solid var(--border); }
        .pagination button { padding: 8px 14px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
        .pagination button:hover:not(:disabled) { background: var(--primary); border-color: var(--primary); }
        .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
        .pagination button.active { background: var(--primary); border-color: var(--primary); }
        .pagination .page-info { color: var(--text-secondary); font-size: 13px; }
        
        /* 自动刷新 */
        .auto-refresh { display: flex; align-items: center; gap: 10px; background: var(--bg-dark); padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border); }
        .auto-refresh label { color: var(--text-secondary); font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 8px; }
        .auto-refresh input[type="checkbox"] { accent-color: var(--primary); }
        
        /* 无数据 */
        .no-data { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .no-data-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        
        /* 错误消息 */
        .error-msg { background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #f87171; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        
        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; backdrop-filter: blur(4px); }
        .modal.show { display: flex; justify-content: center; align-items: center; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; width: 90%; max-width: 900px; max-height: 85vh; overflow: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.5); }
        .modal-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); position: sticky; top: 0; }
        .modal-header h3 { font-size: 16px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .modal-close:hover { background: var(--bg-hover); color: var(--text-primary); }
        .modal-body { padding: 24px; }
        .json-viewer { background: #0d1117; color: #c9d1d9; padding: 20px; border-radius: 10px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; max-height: 600px; overflow-y: auto; border: 1px solid var(--border); }
        
        /* 滚动条 */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <!-- 左侧菜单栏 -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo">
            <div class="logo-icon">📊</div>
            <div>
                <h1>运维系统</h1>
                <div class="navbar-version">v1.0.0 by yiyuzhou</div>
            </div>
            <button class="sidebar-toggle" id="sidebarToggle" title="收起/展开菜单">
                <svg id="toggleIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
        </div>
        <nav class="sidebar-menu">
            <div class="menu-section">任务管理</div>
            <a href="/" class="menu-item active" data-page="internal">
                <span class="icon">🎬</span>
                <span class="label">内部译制</span>
            </a>
            <a href="/mps" class="menu-item" data-page="mps">
                <span class="icon">🐧</span>
                <span class="label">腾讯 MPS</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs">
                <span class="icon">📋</span>
                <span class="label">日志监控</span>
            </a>
            <a href="/server-monitor" class="menu-item" data-page="server-monitor">
                <span class="icon">🖥️</span>
                <span class="label">服务器监控</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings">
                <span class="icon">⚙️</span>
                <span class="label">系统设置</span>
            </a>
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-status">
                <span class="status-dot"></span>
                <span>系统运行正常</span>
            </div>
            <div class="last-update">最后更新：<span id="lastUpdate">-</span></div>
        </div>
    </aside>
    
    <!-- 主内容区 -->
    <div class="main-wrapper" id="mainWrapper">
        <div class="main-content">
            <div id="statsContent"></div>
            
            <div class="toolbar">
                <div class="toolbar-left">
                    <div class="toolbar-title">🔍 搜索筛选</div>
                    <div class="search-form">
                        <input type="text" id="searchTaskId" class="search-input" placeholder="搜索 Task ID">
                        <input type="text" id="searchName" class="search-input" placeholder="搜索剧名">
                        <select id="searchType" class="search-select">
                            <option value="">全部类型</option>
                            <option value="RENDER">多语言版本</option>
                            <option value="SOURCE">原剧版</option>
                        </select>
                        <select id="searchStatus" class="search-select">
                            <option value="">全部状态</option>
                            <option value="0">等待</option>
                            <option value="1">处理中</option>
                            <option value="2">完成</option>
                            <option value="3">失败</option>
                            <option value="4">排队</option>
                        </select>
                    </div>
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-secondary" onclick="clearSearch()">清空</button>
                    <button class="btn btn-primary" onclick="applySearch()">搜索</button>
                    <div class="auto-refresh">
                        <label><input type="checkbox" id="autoRefresh" checked>自动刷新</label>
                        <span id="countdown" style="margin-left: 8px; color: var(--text-secondary); font-size: 13px;">30s</span>
                    </div>
                    <button class="btn btn-primary" onclick="loadData()" id="refreshBtn">🔄 刷新</button>
                </div>
            </div>
            
            <div id="content"></div>
        </div>
    </div>

    <!-- JSON 查看 Modal -->
    <div id="jsonModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">JSON 详情</h3>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                <div id="jsonContent" class="json-viewer"></div>
            </div>
        </div>
    </div>

    <script>
        const PAGE_SIZE = 10;
        let allData = { processing: [], completed: [] };
        let filteredData = { processing: [], completed: [] };
        let currentPage = { processing: 1, completed: 1, all: 1 };
        let autoRefreshTimer = null;
        let countdownTimer = null;
        let countdownSeconds = 30;
        
        function formatStatus(status) {
            const map = { 0: { text: '等待', class: 'status-waiting' }, 1: { text: '处理中', class: 'status-processing' }, 2: { text: '完成', class: 'status-completed' }, 3: { text: '失败', class: 'status-failed' }, 4: { text: '排队', class: 'status-queuing' } };
            const s = map[status] || { text: '未知', class: '' };
            return '<span class="status-badge ' + s.class + '">' + s.text + '</span>';
        }
        function formatType(type) {
            const map = { 'RENDER': '多语言版本', 'SOURCE': '原剧版' };
            return '<span class="type-badge">' + (map[type] || type) + '</span>';
        }
        function formatTime(timeStr) {
            if (!timeStr) return '-';
            try {
                // ISO 格式：2026-03-29T22:43:00 → 2026-03-29 22:43:00
                if (timeStr.includes('T')) {
                    return timeStr.replace('T', ' ').substring(0, 19);
                }
                // RFC 格式：Sun, 29 Mar 2026 22:43:00 GMT → 2026-03-29 22:43:00
                if (timeStr.includes(',') && timeStr.includes('GMT')) {
                    const parts = timeStr.split(',');
                    if (parts.length >= 2) {
                        const dateTime = parts[1].trim();
                        const words = dateTime.split(' ');
                        if (words.length >= 4) {
                            const day = words[0];
                            const monthStr = words[1];
                            const year = words[2];
                            const time = words[3];
                            const months = { 'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06', 'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12' };
                            const month = months[monthStr] || '01';
                            return year + '-' + month + '-' + day + ' ' + time.substring(0, 8);
                        }
                    }
                }
                // 标准格式直接返回
                return timeStr.substring(0, 19);
            } catch(e) {
                return timeStr;
            }
        }
        function truncate(str, len) { if (!str) return '-'; return str.length > len ? str.substring(0, len) + '...' : str; }
        
        function matchesFilter(row, taskId, name, type, status) {
            if (taskId && row.id != taskId) return false;
            if (name && (!row.name || !row.name.toLowerCase().includes(name.toLowerCase()))) return false;
            if (type && row.task_type != type) return false;
            if (status && row.status != parseInt(status)) return false;
            return true;
        }
        
        function clearSearch() {
            document.getElementById('searchTaskId').value = '';
            document.getElementById('searchName').value = '';
            document.getElementById('searchType').value = '';
            document.getElementById('searchStatus').value = '';
            filteredData = { ...allData };
            currentPage = { processing: 1, completed: 1, all: 1 };
            renderTables();
        }
        
        function renderPagination(data, listType) {
            const total = data.length;
            const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
            const current = currentPage[listType];
            
            if (totalPages <= 1) return '';
            
            let html = '<div class="pagination">';
            html += '<button ' + (current <= 1 ? 'disabled' : '') + ' onclick="changePage(\\'' + listType + '\\', ' + (current - 1) + ')">← 上一页</button>';
            html += '<span class="page-info">第 ' + current + ' / ' + totalPages + ' 页 (共 ' + total + ' 条)</span>';
            html += '<button ' + (current >= totalPages ? 'disabled' : '') + ' onclick="changePage(\\'' + listType + '\\', ' + (current + 1) + ')">下一页 →</button>';
            html += '</div>';
            return html;
        }
        
        function changePage(listType, page) {
            currentPage[listType] = page;
            renderTables();
        }
        
        function renderTable(title, data, columns, listType) {
            const total = data.length;
            const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
            const current = currentPage[listType];
            const start = (current - 1) * PAGE_SIZE;
            const pageData = data.slice(start, start + PAGE_SIZE);
            
            if (pageData.length === 0) {
                return '<div class="table-section"><div class="table-header">' + title + '<span class="table-count">0</span></div><div class="no-data"><div class="no-data-icon">📭</div>暂无数据</div></div>';
            }
            
            let html = '<div class="table-section">';
            html += '<div class="table-header">' + title + '<span class="table-count">' + pageData.length + ' / ' + total + '</span></div>';
            html += '<div class="table-container"><table><thead><tr>';
            columns.forEach(col => html += '<th>' + col.title + '</th>');
            html += '</tr></thead><tbody>';
            pageData.forEach(row => { html += '<tr>'; columns.forEach(col => { let v = row[col.field]; if (col.format) v = col.format(v, row); html += '<td>' + v + '</td>'; }); html += '</tr>'; });
            html += '</tbody></table></div>';
            html += renderPagination(data, listType);
            html += '</div>';
            return html;
        }
        
        function viewJson(title, jsonData) {
            if (!jsonData) { document.getElementById('jsonContent').textContent = '无数据'; }
            else if (typeof jsonData === 'string') {
                try {
                    const obj = JSON.parse(jsonData);
                    document.getElementById('jsonContent').textContent = JSON.stringify(obj, null, 2);
                } catch(e) {
                    document.getElementById('jsonContent').textContent = jsonData;
                }
            } else {
                document.getElementById('jsonContent').textContent = JSON.stringify(jsonData, null, 2);
            }
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('jsonModal').classList.add('show');
        }
        
        function closeModal() {
            document.getElementById('jsonModal').classList.remove('show');
        }
        
        document.getElementById('jsonModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });
        
        function renderTables() {
            let html = '';
            const allColumns = [
                { title: 'taskId', field: 'id' },
                { title: '剧名', field: 'name', format: v => truncate(v, 25) },
                { title: '类型', field: 'task_type', format: formatType },
                { title: '推理状态', field: 'status', format: formatStatus },
                { title: '创建时间', field: 'create_time', format: formatTime },
                { title: '操作', field: 'id', format: (v, row) => '<a href="/task_detail?id=' + v + '" class="detail-btn" target="_blank">📄 查看详情</a>' }
            ];
            // 合并所有任务并按创建时间倒序
            const allTasks = [...filteredData.processing, ...filteredData.completed].sort((a, b) => {
                if (!a.create_time) return 1;
                if (!b.create_time) return -1;
                return new Date(b.create_time) - new Date(a.create_time);
            });
            html += renderTable('📋 全部任务', allTasks, allColumns, 'all');
            
            document.getElementById('content').innerHTML = html;
        }
        
        function applySearch() {
            const taskId = document.getElementById('searchTaskId').value.trim();
            const name = document.getElementById('searchName').value.trim();
            const type = document.getElementById('searchType').value;
            const status = document.getElementById('searchStatus').value;
            filteredData.processing = allData.processing.filter(row => matchesFilter(row, taskId, name, type, status));
            filteredData.completed = allData.completed.filter(row => matchesFilter(row, taskId, name, type, status));
            currentPage = { processing: 1, completed: 1, all: 1 };
            renderTables();
        }

        async function getActiveProfile() {
            let activeProfile = localStorage.getItem('activeProfile') || '';
            if (activeProfile) return activeProfile;

            try {
                const res = await fetch('/api/settings/config');
                const data = await res.json();
                activeProfile = data.activeProfile || '';
                if (activeProfile) {
                    localStorage.setItem('activeProfile', activeProfile);
                }
            } catch (err) {
                console.warn('Load active profile error:', err);
            }

            return activeProfile;
        }
        
        async function loadData() {
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true; btn.textContent = '加载中...';
            try {
                const activeProfile = await getActiveProfile();
                const profileParam = activeProfile ? '&profile=' + encodeURIComponent(activeProfile) : '';
                const res = await fetch('/api/data?t=' + Date.now() + profileParam);
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Unknown error');
                allData = { stats: data.stats, processing: data.processing || [], completed: data.completed || [] };
                
                // 渲染统计卡片
                const stats = data.stats || {};
                let statsHtml = '<div class="stats-grid">';
                statsHtml += '<div class="stat-card total"><h3>📈 总任务数</h3><div class="number">' + (stats.total || 0) + '</div></div>';
                statsHtml += '<div class="stat-card waiting"><h3>⏳ 等待</h3><div class="number">' + (stats.waiting || 0) + '</div></div>';
                statsHtml += '<div class="stat-card processing"><h3>🔄 处理中</h3><div class="number">' + (stats.processing || 0) + '</div></div>';
                statsHtml += '<div class="stat-card completed"><h3>✅ 完成</h3><div class="number">' + (stats.completed || 0) + '</div></div>';
                statsHtml += '<div class="stat-card failed"><h3>❌ 失败</h3><div class="number">' + (stats.failed || 0) + '</div></div>';
                statsHtml += '<div class="stat-card today"><h3>📅 今日新增</h3><div class="number">' + (stats.today_total || 0) + '</div></div></div>';
                document.getElementById('statsContent').innerHTML = statsHtml;
                
                applySearch();
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
                
                // 重置倒计时
                if (document.getElementById('autoRefresh').checked) {
                    countdownSeconds = 30;
                }
            } catch (err) {
                console.error('Load data error:', err);
                document.getElementById('content').innerHTML = '<div class="error-msg">❌ 加载失败：' + err.message + '</div>';
            } finally { btn.disabled = false; btn.textContent = '🔄 刷新'; }
        }
        
        function setupAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            const countdownEl = document.getElementById('countdown');
            
            function updateCountdown() {
                countdownEl.textContent = countdownSeconds + 's';
                if (countdownSeconds <= 5) {
                    countdownEl.style.color = 'var(--warning)';
                } else {
                    countdownEl.style.color = 'var(--text-secondary)';
                }
            }
            
            function startCountdown() {
                countdownSeconds = 30;
                updateCountdown();
                if (countdownTimer) clearInterval(countdownTimer);
                countdownTimer = setInterval(() => {
                    countdownSeconds--;
                    if (countdownSeconds <= 0) {
                        countdownSeconds = 30;
                    }
                    updateCountdown();
                }, 1000);
            }
            
            function start() {
                if (autoRefreshTimer) clearInterval(autoRefreshTimer);
                autoRefreshTimer = setInterval(() => {
                    loadData();
                    countdownSeconds = 30;
                    updateCountdown();
                }, 30000);
                startCountdown();
            }
            
            function stop() {
                if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
                if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
                countdownEl.textContent = '--';
            }
            
            checkbox.addEventListener('change', function() {
                if (this.checked) start();
                else stop();
            });
            
            start();
        }
        
        // 侧边栏切换
        function setupSidebarToggle() {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('sidebarToggle');
            const mainWrapper = document.getElementById('mainWrapper');
            const toggleIcon = document.getElementById('toggleIcon');
            
            // 从 localStorage 读取状态
            const savedState = localStorage.getItem('sidebarCollapsed');
            if (savedState === 'true') {
                sidebar.classList.add('collapsed');
                mainWrapper.classList.add('collapsed-margin');
                toggleIcon.style.transform = 'rotate(180deg)';
            }
            
            // 鼠标悬停展开
            let hoverTimeout = null;
            sidebar.addEventListener('mouseenter', function() {
                if (sidebar.classList.contains('collapsed')) {
                    sidebar.classList.remove('collapsed');
                    mainWrapper.classList.remove('collapsed-margin');
                    toggleIcon.style.transform = 'rotate(0deg)';
                }
            });
            
            sidebar.addEventListener('mouseleave', function() {
                if (savedState === 'true') {
                    hoverTimeout = setTimeout(function() {
                        sidebar.classList.add('collapsed');
                        mainWrapper.classList.add('collapsed-margin');
                        toggleIcon.style.transform = 'rotate(180deg)';
                    }, 200);
                }
            });
            
            // 点击切换
            toggle.addEventListener('click', function() {
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed-margin');
                toggleIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() { console.log('formatTime loaded'); loadData(); setupAutoRefresh(); setupSidebarToggle(); });
    </script>
</body>
</html>
"""

# 腾讯 MPS 页面 HTML
MPS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>腾讯 MPS - 视频任务运维系统</title>
    <style>
        :root {
            --primary: #2563eb; --primary-dark: #1d4ed8; --success: #059669; --warning: #d97706;
            --danger: #dc2626; --info: #7c3aed; --bg-dark: #0f172a; --bg-card: #1e293b;
            --bg-hover: #334155; --text-primary: #f1f5f9; --text-secondary: #94a3b8;
            --border: #334155; --sidebar-width: 240px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: var(--bg-dark); min-height: 100vh; color: var(--text-primary); display: flex; }
        .sidebar { width: var(--sidebar-width); background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-right: 1px solid var(--border); min-height: 100vh; position: fixed; left: 0; top: 0; display: flex; flex-direction: column; }
        .sidebar-logo { padding: 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .sidebar-logo .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, var(--primary) 0%, var(--info) 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .sidebar-logo h1 { color: var(--text-primary); font-size: 18px; font-weight: 600; }
        .sidebar-menu { flex: 1; padding: 16px 12px; }
        .menu-section { color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px; margin-top: 8px; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; color: var(--text-secondary); text-decoration: none; transition: all 0.2s; margin-bottom: 4px; cursor: pointer; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(29, 78, 216, 0.1) 100%); color: var(--primary); border: 1px solid rgba(37, 99, 235, 0.3); }
        .menu-item .icon { font-size: 18px; width: 24px; text-align: center; }
        .menu-item .label { flex: 1; font-size: 14px; font-weight: 500; }
        .menu-badge { background: var(--danger); color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; }
        .main-content { padding: 24px 30px; flex: 1; display: flex; align-items: center; justify-content: center; }
        .coming-soon { text-align: center; padding: 60px 20px; }
        .coming-soon-icon { font-size: 96px; margin-bottom: 24px; opacity: 0.5; }
        .coming-soon h1 { color: var(--text-primary); font-size: 28px; margin-bottom: 16px; }
        .coming-soon p { color: var(--text-secondary); font-size: 16px; max-width: 400px; margin: 0 auto; }
        .badge { display: inline-block; background: var(--warning); color: white; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-top: 24px; }
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-logo">
            <div class="logo-icon">📊</div>
            <h1>运维系统</h1>
        </div>
        <nav class="sidebar-menu">
            <div class="menu-section">任务管理</div>
            <a href="/" class="menu-item" data-page="internal">
                <span class="icon">🎬</span>
                <span class="label">内部译制</span>
            </a>
            <a href="/mps" class="menu-item active" data-page="mps">
                <span class="icon">🐧</span>
                <span class="label">腾讯 MPS</span>
                <span class="menu-badge">开发中</span>
            </a>
        </nav>
    </aside>
    <div class="main-wrapper">
        <div class="main-content">
            <div class="coming-soon">
                <div class="coming-soon-icon">🚧</div>
                <h1>腾讯 MPS 页面开发中</h1>
                <p>该模块正在紧锣密鼓地开发中，敬请期待！</p>
                <span class="badge">Coming Soon</span>
            </div>
        </div>
    </div>
</body>
</html>
"""

# 详情页 HTML
DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务详情 - Task #{{ task_id }}</title>
    <style>
        :root {
            --primary: #2563eb; --primary-dark: #1d4ed8; --success: #059669; --warning: #d97706;
            --danger: #dc2626; --info: #7c3aed; --bg-dark: #0f172a; --bg-card: #1e293b;
            --bg-hover: #334155; --text-primary: #f1f5f9; --text-secondary: #94a3b8;
            --border: #334155; --sidebar-width: 240px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: var(--bg-dark); min-height: 100vh; color: var(--text-primary); display: flex; }
        
        /* 左侧菜单栏 */
        .sidebar { width: var(--sidebar-width); background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-right: 1px solid var(--border); min-height: 100vh; position: fixed; left: 0; top: 0; display: flex; flex-direction: column; }
        .sidebar-logo { padding: 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .sidebar-logo .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, var(--primary) 0%, var(--info) 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .sidebar-logo h1 { color: var(--text-primary); font-size: 18px; font-weight: 600; }
        .sidebar-menu { flex: 1; padding: 16px 12px; }
        .menu-section { color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px; margin-top: 8px; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; color: var(--text-secondary); text-decoration: none; transition: all 0.2s; margin-bottom: 4px; cursor: pointer; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(29, 78, 216, 0.1) 100%); color: var(--primary); border: 1px solid rgba(37, 99, 235, 0.3); }
        .menu-item .icon { font-size: 18px; width: 24px; text-align: center; }
        .menu-item .label { flex: 1; font-size: 14px; font-weight: 500; }
        .menu-badge { background: var(--danger); color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; }
        .main-content { max-width: 1600px; margin: 0 auto; padding: 24px 30px; flex: 1; }
        .top-bar { background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 12px 30px; display: flex; justify-content: space-between; align-items: center; }
        .back-btn { background: var(--bg-hover); color: var(--text-primary); text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; border: 1px solid var(--border); transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .back-btn:hover { background: var(--border); }
        .task-info { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
        .task-info h2 { color: var(--text-primary); font-size: 18px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
        .info-item { background: var(--bg-dark); padding: 16px; border-radius: 10px; border: 1px solid var(--border); }
        .info-item label { color: var(--text-secondary); font-size: 12px; display: block; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .info-item .value { color: var(--text-primary); font-size: 16px; font-weight: 600; word-break: break-all; }
        .table-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 24px; }
        .table-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 16px 20px; font-size: 15px; font-weight: 600; border-bottom: 1px solid var(--border); }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
        th { background: rgba(37, 99, 235, 0.1); font-weight: 600; color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        tr:hover { background: var(--bg-hover); }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .status-success { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .status-error { background: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); }
        .status-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; backdrop-filter: blur(4px); }
        .modal.show { display: flex; justify-content: center; align-items: center; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; width: 90%; max-width: 900px; max-height: 85vh; overflow: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.5); }
        .modal-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); position: sticky; top: 0; }
        .modal-header h3 { font-size: 16px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .modal-close:hover { background: var(--bg-hover); color: var(--text-primary); }
        .modal-body { padding: 24px; }
        .json-viewer { background: #0d1117; color: #c9d1d9; padding: 20px; border-radius: 10px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; max-height: 600px; overflow-y: auto; border: 1px solid var(--border); }
        .view-btn { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.2s; }
        .view-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .no-data { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .no-data-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .error-msg { background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #f87171; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        .loading { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .spinner { border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; width: 48px; height: 48px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <!-- 左侧菜单栏 -->
    <aside class="sidebar">
        <div class="sidebar-logo">
            <div class="logo-icon">📊</div>
            <h1>运维系统</h1>
        </div>
        <nav class="sidebar-menu">
            <div class="menu-section">任务管理</div>
            <a href="/" class="menu-item" data-page="internal">
                <span class="icon">🎬</span>
                <span class="label">内部译制</span>
            </a>
            <a href="/mps" class="menu-item" data-page="mps">
                <span class="icon">🐧</span>
                <span class="label">腾讯 MPS</span>
                <span class="menu-badge">开发中</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs">
                <span class="icon">📋</span>
                <span class="label">日志监控</span>
            </a>
            <a href="/server-monitor" class="menu-item" data-page="server-monitor">
                <span class="icon">🖥️</span>
                <span class="label">服务器监控</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings">
                <span class="icon">⚙️</span>
                <span class="label">系统设置</span>
            </a>
        </nav>
    </aside>
    
    <!-- 主内容区 -->
    <div class="main-wrapper">
        <div class="top-bar">
            <a href="/" class="back-btn">← 返回列表</a>
        </div>
        <div class="main-content">
            <div id="content">
                <div class="loading"><div class="spinner"></div><p>加载中...</p></div>
            </div>
        </div>
    </div>

    <div id="jsonModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">JSON 详情</h3>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body">
                <div id="jsonContent" class="json-viewer"></div>
            </div>
        </div>
    </div>

    <script>
        function formatTime(timeStr) {
            if (!timeStr) return '-';
            try {
                // ISO 格式：2026-03-29T22:43:00 → 2026-03-29 22:43:00
                if (timeStr.includes('T')) {
                    return timeStr.replace('T', ' ').substring(0, 19);
                }
                // RFC 格式：Sun, 29 Mar 2026 22:43:00 GMT → 2026-03-29 22:43:00
                if (timeStr.includes(',') && timeStr.includes('GMT')) {
                    const parts = timeStr.split(',');
                    if (parts.length >= 2) {
                        const dateTime = parts[1].trim();
                        const words = dateTime.split(' ');
                        if (words.length >= 4) {
                            const day = words[0];
                            const monthStr = words[1];
                            const year = words[2];
                            const time = words[3];
                            const months = { 'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06', 'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12' };
                            const month = months[monthStr] || '01';
                            return year + '-' + month + '-' + day + ' ' + time.substring(0, 8);
                        }
                    }
                }
                // 标准格式直接返回
                return timeStr.substring(0, 19);
            } catch(e) {
                return timeStr;
            }
        }
        function formatStatus(status, failType, endTime) {
            if (status == 200 || status == '200') return '<span class="status-badge status-success">成功</span>';
            // 如果状态不是 200，但没有结束时间，说明是进行中
            const hasEndTime = endTime && endTime !== '' && endTime !== null && endTime !== undefined && endTime !== '-' && endTime !== 'None';
            if (!hasEndTime) {
                return '<span class="status-badge status-processing">处理中</span>';
            }
            return '<span class="status-badge status-error">失败</span>';
        }
        function truncate(str, len) { if (!str) return '-'; return str.length > len ? str.substring(0, len) + '...' : str; }
        
        function viewJson(title, jsonData) {
            if (!jsonData) { document.getElementById('jsonContent').textContent = '无数据'; }
            else if (typeof jsonData === 'string') {
                try { const obj = JSON.parse(jsonData); document.getElementById('jsonContent').textContent = JSON.stringify(obj, null, 2); }
                catch(e) { document.getElementById('jsonContent').textContent = jsonData; }
            } else { document.getElementById('jsonContent').textContent = JSON.stringify(jsonData, null, 2); }
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('jsonModal').classList.add('show');
        }
        
        function closeModal() { document.getElementById('jsonModal').classList.remove('show'); }
        document.getElementById('jsonModal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });
        
        async function loadDetail() {
            const urlParams = new URLSearchParams(window.location.search);
            const taskId = urlParams.get('id');
            if (!taskId) { document.getElementById('content').innerHTML = '<div class="error-msg">❌ 缺少任务 ID 参数</div>'; return; }
            
            try {
                const res = await fetch('/api/task_detail?id=' + taskId);
                const data = await res.json();
                if (!data.success) throw new Error(data.error || '加载失败');
                
                const task = data.task;
                const logs = data.logs || [];
                
                let html = '<div class="task-info"><h2>📌 任务基本信息</h2><div class="info-grid">';
                html += '<div class="info-item"><label>Task ID</label><div class="value">' + task.id + '</div></div>';
                html += '<div class="info-item"><label>剧名</label><div class="value">' + (task.name || '-') + '</div></div>';
                html += '<div class="info-item"><label>类型</label><div class="value">' + (task.task_type || '-') + '</div></div>';
                html += '<div class="info-item"><label>状态</label><div class="value">' + (task.status_text || '-') + '</div></div>';
                html += '<div class="info-item"><label>Series ID</label><div class="value">' + (task.series_id || '-') + '</div></div>';
                html += '<div class="info-item"><label>创建时间</label><div class="value">' + formatTime(task.create_time) + '</div></div>';
                html += '</div></div>';
                
                html += '<div class="table-section"><div class="table-header">🔗 请求日志 <span style="font-weight:normal;font-size:13px;opacity:0.8">(' + logs.length + ')</span></div>';
                if (logs.length === 0) { html += '<div class="no-data"><div class="no-data-icon">📭</div>暂无请求日志</div>'; }
                else {
                    html += '<div class="table-container"><table><thead><tr>';
                    html += '<th>Trace ID</th><th>模块</th><th>请求 URL</th><th>状态</th><th>失败类型</th><th>开始时间</th><th>结束时间</th><th>耗时 (s)</th><th>操作</th>';
                    html += '</tr></thead><tbody>';
                    logs.forEach((log, idx) => {
                        const duration = log.begin_time && log.end_time ? ((new Date(log.end_time) - new Date(log.begin_time)) / 1000).toFixed(2) : '-';
                        const reqBodyStr = log.request_body ? JSON.stringify(log.request_body) : 'null';
                        const resBodyStr = log.response_body ? JSON.stringify(log.response_body) : 'null';
                        html += '<tr>';
                        html += '<td>' + (log.trace_id || '-') + '</td>';
                        html += '<td>' + (log.module_name || '-') + '</td>';
                        html += '<td>' + truncate(log.request_url || '-', 40) + '</td>';
                        html += '<td>' + formatStatus(log.response_status) + '</td>';
                        html += '<td>' + (log.fail_type || '-') + '</td>';
                        html += '<td>' + formatTime(log.begin_time) + '</td>';
                        html += '<td>' + formatTime(log.end_time) + '</td>';
                        html += '<td>' + duration + '</td>';
                        html += '<td>';
                        html += '<button class="view-btn" onclick="viewReq(' + idx + ')">请求</button> ';
                        html += '<button class="view-btn" onclick="viewRes(' + idx + ')">响应</button>';
                        html += '</td></tr>';
                    });
                    html += '</tbody></table></div>';
                }
                html += '</div>';
                document.getElementById('content').innerHTML = html;
                
                // 绑定查看请求/响应的函数
                window.viewReq = function(idx) {
                    const log = logs[idx];
                    const data = log.request_body;
                    viewJson('请求 Body', data);
                };
                window.viewRes = function(idx) {
                    const log = logs[idx];
                    const data = log.response_body;
                    viewJson('响应 Body', data);
                };
                
                document.title = '任务详情 - Task #' + taskId;
            } catch (err) {
                console.error('Load detail error:', err);
                document.getElementById('content').innerHTML = '<div class="error-msg">❌ 加载失败：' + err.message + '</div>';
            }
        }
        document.addEventListener('DOMContentLoaded', loadDetail);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(LIST_TEMPLATE)

@app.route('/mps')
def mps():
    return render_template_string(MPS_LIST_TEMPLATE)

@app.route('/mps_detail')
def mps_detail():
    task_id = request.args.get('id')
    if not task_id:
        return render_template_string(MPS_DETAIL_TEMPLATE.replace('<div id="content">', '<div id="content"><div class="error-msg">❌ 缺少任务 ID 参数</div>'))
    return render_template_string(MPS_DETAIL_TEMPLATE)

@app.route('/task_detail')
def task_detail():
    task_id = request.args.get('id')
    if not task_id:
        return render_template_string(DETAIL_TEMPLATE.replace('<div id="content">', '<div id="content"><div class="error-msg">❌ 缺少任务 ID 参数</div>'))
    return render_template_string(DETAIL_TEMPLATE, task_id=task_id)

@app.route('/api/data')
def get_data():
    start = datetime.now()
    try:
        # 支持 ?profile=xxx 参数
        profile = request.args.get('profile')
        print(f"[API /api/data] 收到请求，profile 参数：{profile if profile else '(none)'}")
        
        stats_sql = """SELECT COUNT(*) as total,
            SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as waiting,
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 3 THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 4 THEN 1 ELSE 0 END) as queuing
        FROM v_episode_task WHERE deleted = 0"""
        stats = query_db(stats_sql, profile=profile)[0]
        
        today_sql = "SELECT COUNT(*) as today_total FROM v_episode_task WHERE deleted = 0 AND DATE(create_time) = CURDATE()"
        today = query_db(today_sql, profile=profile)[0]
        stats['today_total'] = today['today_total'] or 0
        
        processing_sql = """SELECT id, name, task_type, status, create_time 
        FROM v_episode_task WHERE deleted = 0 AND status != 2 ORDER BY create_time DESC LIMIT 500"""
        processing = query_db(processing_sql, profile=profile)
        # Python 格式化时间
        for task in processing:
            if task.get('create_time'):
                task['create_time'] = format_rfc_time(task['create_time'])
        
        completed_sql = """SELECT id, name, task_type, status, create_time 
        FROM v_episode_task WHERE deleted = 0 AND status = 2 ORDER BY create_time DESC LIMIT 200"""
        completed = query_db(completed_sql, profile=profile)
        # Python 格式化时间
        for task in completed:
            if task.get('create_time'):
                task['create_time'] = format_rfc_time(task['create_time'])
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"API /api/data response in {elapsed:.2f}s", file=sys.stderr)
        
        return jsonify({'success': True, 'stats': stats, 'processing': processing, 'completed': completed, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        print(f"API /api/data error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task_detail')
def get_task_detail():
    task_id = request.args.get('id')
    if not task_id:
        return jsonify({'success': False, 'error': 'Missing task ID'})
    
    try:
        # 支持 ?profile=xxx 参数
        profile = request.args.get('profile')
        print(f"[API /api/task_detail] task_id={task_id}, profile 参数：{profile if profile else '(none)'}")
        
        task_sql = "SELECT id, name, task_type, status, series_id, create_time FROM v_episode_task WHERE id = %s AND deleted = 0"
        task = query_db(task_sql, (task_id,), profile=profile)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task[0]
        status_map = {0: '等待', 1: '处理中', 2: '完成', 3: '失败', 4: '排队'}
        task['status_text'] = status_map.get(task['status'], '未知')
        # Python 格式化任务创建时间
        if task.get('create_time'):
            task['create_time'] = format_rfc_time(task['create_time'])
        
        # 请求日志（时间正序）
        log_sql = """SELECT trace_id, task_id, series_id, module_name, module_path, request_url, 
               request_body, response_body, response_status, fail_type, begin_time, end_time 
        FROM v_algorithm_request_log WHERE task_id = %s ORDER BY begin_time ASC LIMIT 100"""
        logs = query_db(log_sql, (task_id,), profile=profile)
        
        # 处理 JSON 字段和时间格式化
        for log in logs:
            if log['request_body']:
                try: log['request_body'] = json.loads(log['request_body']) if isinstance(log['request_body'], str) else log['request_body']
                except: pass
            if log['response_body']:
                try: log['response_body'] = json.loads(log['response_body']) if isinstance(log['response_body'], str) else log['response_body']
                except: pass
            # Python 格式化日志时间
            if log.get('begin_time'):
                log['begin_time'] = format_rfc_time(log['begin_time'])
            if log.get('end_time'):
                log['end_time'] = format_rfc_time(log['end_time'])
        
        print(f"API /api/task_detail task={task_id} logs={len(logs)}", file=sys.stderr)
        
        return jsonify({'success': True, 'task': task, 'logs': logs, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        print(f"API /api/task_detail error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============== 腾讯 MPS API ==============

@app.route('/api/mps_data')
def get_mps_data():
    start = datetime.now()
    try:
        # 支持 ?profile=xxx 参数
        profile = request.args.get('profile')
        print(f"[API /api/mps_data] 收到请求，profile 参数：{profile if profile else '(none)'}")
        
        # 统计数据
        stats_sql = """SELECT COUNT(*) as total,
            SUM(CASE WHEN UPPER(cos_status) IN ('SUCCESS', 'COMPLETED', 'FINISH', 'FINISHED') THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN UPPER(cos_status) IN ('FAILED', 'ERROR', 'FAIL') THEN 1 ELSE 0 END) as failed
        FROM videoai.v_fast_translate_series_item WHERE deleted = 0"""
        stats_result = query_db(stats_sql, profile=profile)
        stats = stats_result[0] if stats_result else {}
        
        # 今日新增
        today_sql = "SELECT COUNT(*) as today FROM videoai.v_fast_translate_series_item WHERE deleted = 0 AND DATE(create_time) = CURDATE()"
        today = query_db(today_sql, profile=profile)[0]
        stats['today'] = today['today'] or 0
        
        # 任务列表
        data_sql = """SELECT id as task_id, episode_name, subtitle_extract_type, cos_status, create_time 
        FROM videoai.v_fast_translate_series_item WHERE deleted = 0 ORDER BY create_time DESC LIMIT 500"""
        data = query_db(data_sql, profile=profile)
        
        # 格式化时间
        for item in data:
            if item.get('create_time'):
                item['create_time'] = format_rfc_time(item['create_time'])
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"API /api/mps_data response in {elapsed:.2f}s, total={stats.get('total', 0)}", file=sys.stderr)
        
        return jsonify({'success': True, 'data': data, 'stats': stats, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        print(f"API /api/mps_data error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mps_detail')
def get_mps_detail():
    task_id = request.args.get('id')
    if not task_id:
        return jsonify({'success': False, 'error': 'Missing task ID'})
    
    try:
        # 支持 ?profile=xxx 参数
        profile = request.args.get('profile')
        print(f"[API /api/mps_detail] task_id={task_id}, profile 参数：{profile if profile else '(none)'}")
        
        # 任务详情
        task_sql = """SELECT id as task_id, episode_name, subtitle_extract_type, cos_status, create_time 
        FROM videoai.v_fast_translate_series_item WHERE id = %s AND deleted = 0"""
        task = query_db(task_sql, (task_id,), profile=profile)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        task = task[0]
        
        # 请求日志
        log_sql = """SELECT id, mps_task_id, episode_name, module_name, request_url, request_body, response_body, 
               fail_type, begin_time, end_time, duration_ms 
        FROM videoai.v_fast_translate_mps_request_log 
        WHERE deleted = 0 AND fast_translate_series_item_id = %s 
        ORDER BY begin_time ASC LIMIT 100"""
        logs = query_db(log_sql, (task_id,), profile=profile)
        
        # 格式化时间
        for log in logs:
            if log.get('begin_time'):
                log['begin_time'] = format_rfc_time(log['begin_time'])
            if log.get('end_time'):
                log['end_time'] = format_rfc_time(log['end_time'])
        
        print(f"API /api/mps_detail task={task_id} logs={len(logs)}", file=sys.stderr)
        
        return jsonify({'success': True, 'task': task, 'logs': logs, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        print(f"API /api/mps_detail error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============== 日志监控 API ==============

@app.route('/logs')
def log_viewer():
    return render_template_string(LOG_VIEWER_TEMPLATE)

# 注册服务器监控路由
register_server_monitor_routes(app)

# 启动后台数据收集
start_data_collection()

@app.route('/api/logs/list')
def api_logs_list():
    """获取日志文件列表"""
    # 支持 ?profile=xxx 参数
    profile = request.args.get('profile')
    if profile:
        from log_viewer import reload_ssh_config
        reload_ssh_config(profile)
    files = list_log_files()
    return jsonify({'success': True, 'files': files})

@app.route('/api/logs/content')
def api_logs_content():
    """获取日志文件内容"""
    # 支持 ?profile=xxx 参数
    profile = request.args.get('profile')
    if profile:
        from log_viewer import reload_ssh_config
        reload_ssh_config(profile)
    
    filename = request.args.get('file', '')
    lines = request.args.get('lines', '500')
    search = request.args.get('search', '')
    
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'})
    
    # 安全过滤：防止路径遍历攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    result = get_log_content(filename, int(lines), search if search else None)
    return jsonify(result)

@app.route('/api/logs/new')
def api_logs_new():
    """获取新增的日志行（增量更新）"""
    filename = request.args.get('file', '')
    start_line = request.args.get('start_line', '0')
    lines = request.args.get('lines', '100')
    
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'})
    
    # 安全过滤：防止路径遍历攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    try:
        start_line_int = int(start_line)
        lines_int = int(lines)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid line numbers'}), 400
    
    result = get_new_log_lines(filename, start_line_int, lines_int)
    return jsonify(result)

@app.route('/api/logs/stats')
def api_logs_stats():
    """获取日志文件统计信息"""
    filename = request.args.get('file', '')
    
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'})
    
    # 安全过滤：防止路径遍历攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    result = get_log_stats(filename)
    return jsonify(result)

@app.route('/api/logs/context')
def api_logs_context():
    """获取指定行周围的上下文日志"""
    filename = request.args.get('file', '')
    line_index = request.args.get('line_index', '0')
    context_lines = request.args.get('context_lines', '10')
    
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'})
    
    # 安全过滤：防止路径遍历攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    try:
        line_index_int = int(line_index)
        context_lines_int = int(context_lines)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid line numbers'}), 400
    
    result = get_log_context(filename, line_index_int, context_lines_int)
    return jsonify(result)

@app.route('/api/logs/download')
def api_logs_download():
    """下载日志文件（支持选择行数）"""
    from flask import Response
    import time
    
    filename = request.args.get('file', '')
    lines = request.args.get('lines', 'all')
    
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename'})
    
    # 安全过滤：防止路径遍历攻击
    if '..' in filename or filename.startswith('/') or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    # 验证文件名格式
    if not validate_log_file(filename):
        return jsonify({'success': False, 'error': 'Invalid filename format'}), 400
    
    # 验证 lines 参数
    if lines not in ['all', '1000', '5000']:
        lines = 'all'
    
    result = download_log_file(filename, lines)
    
    if not result['success']:
        return jsonify(result), 400
    
    # 生成下载文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    download_filename = f"{filename.replace('.log', '')}_{lines}_{timestamp}.log"
    
    # 创建流式响应
    def generate():
        # 分块传输，每块 8KB
        chunk_size = 8192
        content = result['content']
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size].encode('utf-8')
            time.sleep(0.001)  # 避免阻塞
    
    response = Response(
        generate(),
        mimetype='text/plain; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{download_filename}"',
            'X-File-Size': str(result['file_size']),
            'X-Download-Lines': lines,
            'X-Actual-Lines': str(result['lines'])
        }
    )
    
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server: http://localhost:{port}", file=sys.stderr)
    print(f"Dashboard: http://localhost:{port}/", file=sys.stderr)
    print(f"Settings: http://localhost:{port}/settings", file=sys.stderr)
    sys.stdout.flush()
    app.run(host='0.0.0.0', port=port, debug=False)

