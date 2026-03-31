#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库监控模块
"""

from flask import render_template_string, jsonify, request
from settings import get_db_monitor_config, save_db_monitor_config, test_db_monitor_connection

DB_MONITOR_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库监控 - 短剧运维系统</title>
    <style>
        :root {
            --primary: #2563eb; --primary-dark: #1d4ed8; --success: #059669; --warning: #d97706;
            --danger: #dc2626; --info: #7c3aed; --bg-dark: #0f172a; --bg-card: #1e293b;
            --bg-hover: #334155; --text-primary: #f1f5f9; --text-secondary: #94a3b8;
            --border: #334155; --sidebar-width: 240px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: var(--bg-dark); min-height: 100vh; color: var(--text-primary); display: flex; }
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
        .sidebar-footer { padding: 16px; border-top: 1px solid var(--border); background: var(--bg-dark); transition: opacity 0.2s; }
        .sidebar.collapsed .sidebar-footer { opacity: 0; }
        .sidebar-status { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 12px; white-space: nowrap; }
        .status-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .last-update { color: var(--text-secondary); font-size: 11px; margin-top: 8px; white-space: nowrap; }
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; transition: margin-left 0.3s ease; }
        .sidebar.collapsed ~ .main-wrapper, .main-wrapper.collapsed-margin { margin-left: 64px; }
        .main-content { padding: 24px 30px; flex: 1; }
        .settings-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
        .settings-card h2 { font-size: 18px; font-weight: 600; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; color: var(--text-secondary); font-size: 13px; margin-bottom: 6px; font-weight: 500; }
        .form-group input { width: 100%; padding: 10px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text-primary); font-size: 14px; transition: all 0.2s; }
        .form-group input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .btn-success { background: linear-gradient(135deg, var(--success) 0%, #047857 100%); color: white; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        .connection-status { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; font-size: 13px; margin-left: 12px; }
        .connection-status.success { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .connection-status.error { background: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); }
        .toast { position: fixed; top: 20px; right: 20px; padding: 16px 24px; border-radius: 8px; color: white; font-weight: 500; z-index: 9999; transform: translateX(400px); transition: transform 0.3s ease; }
        .toast.show { transform: translateX(0); }
        .toast-success { background: var(--success); }
        .toast-error { background: var(--danger); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo"><div class="logo-icon">📊</div><div><h1>运维系统</h1><div class="navbar-version">v1.0.0 by yiyuzhou</div></div>
            <button class="sidebar-toggle" id="sidebarToggle" title="收起/展开菜单">
                <svg id="toggleIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
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
            <a href="/db-monitor" class="menu-item active" data-page="db-monitor">
                <span class="icon">🗄️</span>
                <span class="label">数据库监控</span>
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
    
    <div class="main-wrapper" id="mainWrapper">
        <div class="main-content">
            <h1 style="margin-bottom: 24px; font-size: 24px;">🗄️ 数据库监控配置</h1>
            
            <div class="settings-card">
                <h2>📊 数据库监控连接配置</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>MySQL 主机</label>
                        <input type="text" id="dbMonitorHost" placeholder="例如：101.126.91.130">
                    </div>
                    <div class="form-group">
                        <label>端口</label>
                        <input type="number" id="dbMonitorPort" placeholder="3306" value="3306">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>数据库名</label>
                        <input type="text" id="dbMonitorDatabase" placeholder="例如：information_schema">
                    </div>
                    <div class="form-group">
                        <label>用户名</label>
                        <input type="text" id="dbMonitorUser" placeholder="例如：root">
                    </div>
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" id="dbMonitorPassword" placeholder="请输入数据库密码">
                </div>
                <div style="margin-top: 24px;">
                    <button class="btn btn-success" onclick="testConnection()">🔌 测试连接</button>
                    <button class="btn btn-primary" onclick="saveConfig()" style="margin-left: 12px;">💾 保存配置</button>
                    <span id="dbMonitorStatus" class="connection-status" style="display: none;"></span>
                </div>
            </div>
        </div>
    </div>
    
    <div id="toast" class="toast"></div>
    
    <script>
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast toast-' + type + ' show';
            setTimeout(() => { toast.classList.remove('show'); }, 3000);
        }
        
        function showStatus(success, message) {
            const el = document.getElementById('dbMonitorStatus');
            el.style.display = 'inline-flex';
            el.className = 'connection-status ' + (success ? 'success' : 'error');
            el.textContent = message;
        }
        
        async function loadConfig() {
            try {
                const res = await fetch('/api/settings/config');
                const data = await res.json();
                if (data.success) {
                    const activeProfile = data.activeProfile || 'default';
                    const profile = data.profiles[activeProfile] || {};
                    const dbMonitor = profile.db_monitor || {};
                    
                    document.getElementById('dbMonitorHost').value = dbMonitor.host || '';
                    document.getElementById('dbMonitorPort').value = dbMonitor.port || 3306;
                    document.getElementById('dbMonitorDatabase').value = dbMonitor.database || '';
                    document.getElementById('dbMonitorUser').value = dbMonitor.user || '';
                    document.getElementById('dbMonitorPassword').value = '';
                    
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
                }
            } catch (err) {
                console.error('Load config error:', err);
                showToast('加载配置失败：' + err.message, 'error');
            }
        }
        
        async function testConnection() {
            const config = {
                host: document.getElementById('dbMonitorHost').value,
                port: parseInt(document.getElementById('dbMonitorPort').value) || 3306,
                database: document.getElementById('dbMonitorDatabase').value,
                user: document.getElementById('dbMonitorUser').value,
                password: document.getElementById('dbMonitorPassword').value
            };
            
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '测试中...';
            
            try {
                const res = await fetch('/api/settings/test_db_monitor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                showStatus(data.success, data.message);
                showToast(data.success ? '连接成功！' : '连接失败：' + data.message, data.success ? 'success' : 'error');
            } catch (err) {
                showStatus(false, '测试失败');
                showToast('测试失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔌 测试连接';
            }
        }
        
        async function saveConfig() {
            try {
                const res = await fetch('/api/settings/config');
                const data = await res.json();
                const activeProfile = data.activeProfile || 'default';
                
                const config = {
                    activeProfile: activeProfile,
                    active_profile: activeProfile,
                    profiles: data.profiles || {}
                };
                
                const currentProfile = config.profiles[activeProfile] || {};
                currentProfile.db_monitor = {
                    host: document.getElementById('dbMonitorHost').value,
                    port: parseInt(document.getElementById('dbMonitorPort').value) || 3306,
                    database: document.getElementById('dbMonitorDatabase').value,
                    user: document.getElementById('dbMonitorUser').value,
                    password: document.getElementById('dbMonitorPassword').value ? btoa(document.getElementById('dbMonitorPassword').value) : (currentProfile.db_monitor?.password || '')
                };
                config.profiles[activeProfile] = currentProfile;
                
                const saveRes = await fetch('/api/settings/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const saveData = await saveRes.json();
                if (saveData.success) {
                    showToast('配置保存成功！', 'success');
                    setTimeout(() => { window.location.reload(); }, 1000);
                } else {
                    showToast('保存失败：' + saveData.error, 'error');
                }
            } catch (err) {
                showToast('保存失败：' + err.message, 'error');
            }
        }
        
        function setupSidebarToggle() {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('sidebarToggle');
            const mainWrapper = document.getElementById('mainWrapper');
            const toggleIcon = document.getElementById('toggleIcon');
            
            const savedState = localStorage.getItem('sidebarCollapsed');
            if (savedState === 'true') {
                sidebar.classList.add('collapsed');
                mainWrapper.classList.add('collapsed-margin');
                toggleIcon.style.transform = 'rotate(180deg)';
            }
            
            // 鼠标悬停展开（仅当sidebar已折叠时）
            sidebar.addEventListener('mouseenter', function() {
                if (sidebar.classList.contains('collapsed')) {
                    sidebar.classList.remove('collapsed');
                    mainWrapper.classList.remove('collapsed-margin');
                    toggleIcon.style.transform = 'rotate(0deg)';
                }
            });

            // 点击主内容区域折叠sidebar（仅当sidebar展开时）
            mainWrapper.addEventListener('click', function() {
                if (!sidebar.classList.contains('collapsed')) {
                    sidebar.classList.add('collapsed');
                    mainWrapper.classList.add('collapsed-margin');
                    toggleIcon.style.transform = 'rotate(180deg)';
                    localStorage.setItem('sidebarCollapsed', 'true');
                }
            });

            // 点击切换按钮
            toggle.addEventListener('click', function(e) {
                e.stopPropagation(); // 阻止事件冒泡到mainWrapper
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed-margin');
                toggleIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            loadConfig();
            setupSidebarToggle();
        });
    </script>
</body>
</html>
"""

def register_db_monitor_routes(app):
    """注册数据库监控路由"""
    
    @app.route('/db-monitor')
    def db_monitor_page():
        """数据库监控页面"""
        return render_template_string(DB_MONITOR_TEMPLATE)
