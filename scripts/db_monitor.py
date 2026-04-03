#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库监控模块
"""

from flask import jsonify, render_template_string, request
import mysql.connector

from settings import get_db_monitor_config


DB_MONITOR_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库监控 - 视频任务运维系统</title>
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
        .top-navbar { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); padding: 12px 30px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
        .navbar-left { display: flex; align-items: center; gap: 16px; }
        .navbar-label { color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 500; }
        .navbar-select { padding: 8px 14px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 6px; color: white; font-size: 14px; min-width: 180px; cursor: pointer; transition: all 0.2s; }
        .navbar-select:hover { background: rgba(255,255,255,0.25); }
        .navbar-select option { background: var(--bg-card); color: var(--text-primary); }
        .btn { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: rgba(255,255,255,0.16); color: white; border: 1px solid rgba(255,255,255,0.28); }
        .btn-primary:hover { background: rgba(255,255,255,0.24); }
        .main-content { padding: 24px 30px; flex: 1; }
        .page-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; }
        .page-header h1 { font-size: 24px; margin-bottom: 6px; }
        .page-subtitle { color: var(--text-secondary); font-size: 14px; }
        .status-badges { display: flex; gap: 12px; flex-wrap: wrap; }
        .status-badge { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; min-width: 180px; }
        .status-badge-label { color: var(--text-secondary); font-size: 12px; margin-bottom: 6px; }
        .status-badge-value { font-size: 14px; font-weight: 600; word-break: break-all; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .summary-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }
        .summary-label { color: var(--text-secondary); font-size: 13px; margin-bottom: 10px; }
        .summary-value { font-size: 26px; font-weight: 700; }
        .summary-sub { color: var(--text-secondary); font-size: 12px; margin-top: 8px; }
        .tabs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
        .tab-btn { background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border); border-radius: 10px; padding: 10px 16px; cursor: pointer; font-size: 14px; transition: all 0.2s; }
        .tab-btn:hover { color: var(--text-primary); background: var(--bg-hover); }
        .tab-btn.active { color: white; background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); border-color: transparent; }
        .panel { display: none; background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
        .panel.active { display: block; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid var(--border); gap: 12px; flex-wrap: wrap; }
        .panel-title { font-size: 16px; font-weight: 600; }
        .panel-desc { color: var(--text-secondary); font-size: 13px; }
        .panel-body { padding: 0; }
        .table-wrap { overflow: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 14px; border-bottom: 1px solid rgba(148, 163, 184, 0.12); text-align: left; vertical-align: top; font-size: 13px; }
        th { color: var(--text-secondary); background: rgba(15, 23, 42, 0.4); font-weight: 600; position: sticky; top: 0; z-index: 1; }
        td { color: var(--text-primary); }
        .mono { font-family: 'Consolas', 'Monaco', monospace; white-space: pre-wrap; word-break: break-word; }
        .pill { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .pill.success { background: rgba(5, 150, 105, 0.16); color: #6ee7b7; }
        .pill.warning { background: rgba(217, 119, 6, 0.16); color: #fbbf24; }
        .pill.danger { background: rgba(220, 38, 38, 0.16); color: #fca5a5; }
        .empty-state, .error-state, .loading-state { padding: 48px 24px; text-align: center; color: var(--text-secondary); }
        .error-state { color: #fca5a5; }
        .hint-box { margin-top: 20px; background: rgba(124, 58, 237, 0.12); border: 1px solid rgba(124, 58, 237, 0.25); border-radius: 12px; padding: 16px 18px; color: #ddd6fe; font-size: 13px; line-height: 1.6; }
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
            <a href="/" class="menu-item" data-page="internal"><span class="icon">🎬</span><span class="label">内部译制</span></a>
            <a href="/mps" class="menu-item" data-page="mps"><span class="icon">🐧</span><span class="label">腾讯 MPS</span></a>
            <div class="menu-section" style="margin-top: 20px;">日志管理</div>
            <a href="/algo-comm-log" class="menu-item" data-page="algo-comm-log"><span class="icon">🔬</span><span class="label">算法通讯日志</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs"><span class="icon">📋</span><span class="label">日志监控</span></a>
            <a href="/server-monitor" class="menu-item" data-page="server-monitor"><span class="icon">🖥️</span><span class="label">服务器监控</span></a>
            <a href="/db-monitor" class="menu-item active" data-page="db-monitor"><span class="icon">🗄️</span><span class="label">数据库监控</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings"><span class="icon">⚙️</span><span class="label">系统设置</span></a>
            <a href="/dict-config" class="menu-item" data-page="dict-config"><span class="icon">📚</span><span class="label">字典配置</span></a>
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-status"><span class="status-dot"></span><span>系统运行正常</span></div>
            <div class="last-update">最后更新：<span id="lastUpdate">-</span> | 查询耗时：<span id="queryTime">-</span></div>
        </div>
    </aside>

    <div class="main-wrapper" id="mainWrapper">
        <div class="top-navbar">
            <div class="navbar-left">
                <span class="navbar-label">数据源：</span>
                <select id="globalDataSource" class="navbar-select" onchange="switchDataSource()">
                    <option value="">加载中...</option>
                </select>
                <button class="btn btn-primary" onclick="refreshAll()">🔄 刷新监控</button>
            </div>
        </div>

        <div class="main-content">
            <div class="page-header">
                <div>
                    <h1>🗄️ 数据库监控</h1>
                    <div class="page-subtitle">使用系统设置中的“数据库监控配置”连接目标实例，实时查看慢 SQL、锁等待、活跃会话和表空间。</div>
                </div>
                <div class="status-badges">
                    <div class="status-badge">
                        <div class="status-badge-label">当前实例</div>
                        <div class="status-badge-value" id="targetHost">-</div>
                    </div>
                    <div class="status-badge">
                        <div class="status-badge-label">当前库</div>
                        <div class="status-badge-value" id="targetDatabase">-</div>
                    </div>
                </div>
            </div>

            <div class="summary-grid" id="summaryGrid">
                <div class="summary-card"><div class="summary-label">连接数</div><div class="summary-value">-</div><div class="summary-sub">当前连接</div></div>
                <div class="summary-card"><div class="summary-label">运行线程</div><div class="summary-value">-</div><div class="summary-sub">Threads_running</div></div>
                <div class="summary-card"><div class="summary-label">慢查询累计</div><div class="summary-value">-</div><div class="summary-sub">Slow_queries</div></div>
                <div class="summary-card"><div class="summary-label">锁等待</div><div class="summary-value">-</div><div class="summary-sub">当前等待数</div></div>
                <div class="summary-card"><div class="summary-label">最大连接</div><div class="summary-value">-</div><div class="summary-sub">max_connections</div></div>
                <div class="summary-card"><div class="summary-label">实例版本</div><div class="summary-value" style="font-size:18px;">-</div><div class="summary-sub">MySQL</div></div>
            </div>

            <div class="tabs">
                <button class="tab-btn active" data-tab="slow" onclick="switchTab('slow')">慢 SQL</button>
                <button class="tab-btn" data-tab="locks" onclick="switchTab('locks')">锁等待</button>
                <button class="tab-btn" data-tab="process" onclick="switchTab('process')">活跃会话</button>
                <button class="tab-btn" data-tab="tables" onclick="switchTab('tables')">表空间</button>
            </div>

            <div id="panel-slow" class="panel active">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">慢 SQL 概览</div>
                        <div class="panel-desc">优先读取 performance_schema 的 SQL 摘要，无权限或关闭时回退到当前长耗时会话。</div>
                    </div>
                </div>
                <div class="panel-body" id="slowPanel"></div>
            </div>

            <div id="panel-locks" class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">锁等待 / 锁表信息</div>
                        <div class="panel-desc">兼容 MySQL 8 performance_schema 和旧版本 information_schema.innodb_lock_waits。</div>
                    </div>
                </div>
                <div class="panel-body" id="locksPanel"></div>
            </div>

            <div id="panel-process" class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">活跃会话</div>
                        <div class="panel-desc">默认仅展示非 Sleep 线程，便于快速定位阻塞与慢查询来源。</div>
                    </div>
                </div>
                <div class="panel-body" id="processPanel"></div>
            </div>

            <div id="panel-tables" class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">表空间使用</div>
                        <div class="panel-desc">优先查看当前配置库；若配置库为空或为 information_schema，则展示非系统库的最大表。</div>
                    </div>
                </div>
                <div class="panel-body" id="tablesPanel"></div>
            </div>

            <div class="hint-box">
                若页面显示无数据或权限不足，请前往系统设置检查当前环境的数据库监控配置是否填写了可访问实例的主机、端口、库名、账号和密码，并确认账号具备 SHOW PROCESSLIST、performance_schema 或 information_schema 查询权限。
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

        function escapeHtml(text) {
            return String(text ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function setLoading(id, text = '加载中...') {
            document.getElementById(id).innerHTML = '<div class="loading-state">' + escapeHtml(text) + '</div>';
        }

        function setError(id, text) {
            document.getElementById(id).innerHTML = '<div class="error-state">' + escapeHtml(text) + '</div>';
        }

        function setEmpty(id, text) {
            document.getElementById(id).innerHTML = '<div class="empty-state">' + escapeHtml(text) + '</div>';
        }

        async function fetchJson(url) {
            const res = await fetch(url);
            const data = await res.json();
            if (!data.success) {
                throw new Error(data.error || data.message || '请求失败');
            }
            return data;
        }

        async function getActiveProfile() {
            let activeProfile = localStorage.getItem('activeProfile') || '';
            if (activeProfile) return activeProfile;
            const data = await fetchJson('/api/settings/config');
            activeProfile = data.activeProfile || '';
            if (activeProfile) {
                localStorage.setItem('activeProfile', activeProfile);
            }
            return activeProfile;
        }

        async function initDataSourceSelector() {
            try {
                const data = await fetchJson('/api/settings/valid_profiles');
                const select = document.getElementById('globalDataSource');
                select.innerHTML = '';
                data.profiles.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.key;
                    option.textContent = p.name;
                    if (p.active) option.selected = true;
                    select.appendChild(option);
                });
                localStorage.setItem('activeProfile', data.activeProfile);
            } catch (err) {
                showToast('环境列表加载失败：' + err.message, 'error');
            }
        }

        async function switchDataSource() {
            const select = document.getElementById('globalDataSource');
            const newProfile = select.value;
            const currentProfile = localStorage.getItem('activeProfile') || '';
            if (newProfile === currentProfile) return;
            try {
                const res = await fetch('/api/settings/switch_profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile: newProfile })
                });
                const data = await res.json();
                if (data.success) {
                    localStorage.setItem('activeProfile', newProfile);
                    refreshAll();
                } else {
                    alert('切换失败：' + (data.error || '未知错误'));
                    initDataSourceSelector();
                }
            } catch (err) {
                alert('切换失败：' + err.message);
            }
        }

        function profileQuery(profile) {
            return profile ? ('?profile=' + encodeURIComponent(profile)) : '';
        }

        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
            document.querySelectorAll('.panel').forEach(panel => panel.classList.toggle('active', panel.id === 'panel-' + tab));
        }

        function sqlCell(text) {
            if (!text) return '-';
            return '<div class="mono">' + escapeHtml(text) + '</div>';
        }

        function renderSummary(summary) {
            document.getElementById('targetHost').textContent = summary.targetHost || '-';
            document.getElementById('targetDatabase').textContent = summary.targetDatabase || '-';
            document.getElementById('summaryGrid').innerHTML = [
                ['连接数', summary.threadsConnected, '当前连接'],
                ['运行线程', summary.threadsRunning, 'Threads_running'],
                ['慢查询累计', summary.slowQueries, 'Slow_queries'],
                ['锁等待', summary.lockWaitCount, '当前等待数'],
                ['最大连接', summary.maxConnections, 'max_connections'],
                ['实例版本', summary.version || '-', summary.uptimeLabel || 'MySQL']
            ].map(item => `
                <div class="summary-card">
                    <div class="summary-label">${item[0]}</div>
                    <div class="summary-value" style="${item[0] === '实例版本' ? 'font-size:18px;' : ''}">${escapeHtml(item[1])}</div>
                    <div class="summary-sub">${escapeHtml(item[2])}</div>
                </div>
            `).join('');
        }

        function renderSlowQueries(data) {
            if (!data.rows.length) {
                setEmpty('slowPanel', '当前未发现慢 SQL 指标。');
                return;
            }
            document.getElementById('slowPanel').innerHTML = `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>来源</th>
                                <th>Schema</th>
                                <th>执行次数</th>
                                <th>平均耗时(ms)</th>
                                <th>最大耗时(ms)</th>
                                <th>总耗时(ms)</th>
                                <th>SQL</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.rows.map(row => `
                                <tr>
                                    <td><span class="pill ${row.source === 'performance_schema' ? 'success' : 'warning'}">${escapeHtml(row.source)}</span></td>
                                    <td>${escapeHtml(row.schema_name || '-')}</td>
                                    <td>${escapeHtml(row.exec_count)}</td>
                                    <td>${escapeHtml(row.avg_time_ms)}</td>
                                    <td>${escapeHtml(row.max_time_ms)}</td>
                                    <td>${escapeHtml(row.total_time_ms)}</td>
                                    <td>${sqlCell(row.sample_sql)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function renderLocks(data) {
            if (!data.rows.length) {
                setEmpty('locksPanel', '当前没有锁等待或锁表信息。');
                return;
            }
            document.getElementById('locksPanel').innerHTML = `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>来源</th>
                                <th>等待秒数</th>
                                <th>等待线程</th>
                                <th>阻塞线程</th>
                                <th>表</th>
                                <th>锁模式</th>
                                <th>等待 SQL</th>
                                <th>阻塞 SQL</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.rows.map(row => `
                                <tr>
                                    <td><span class="pill danger">${escapeHtml(row.source)}</span></td>
                                    <td>${escapeHtml(row.wait_seconds)}</td>
                                    <td>${escapeHtml(row.waiting_thread || row.waiting_trx_id || '-')}</td>
                                    <td>${escapeHtml(row.blocking_thread || row.blocking_trx_id || '-')}</td>
                                    <td>${escapeHtml(row.object_name || row.waiting_table || '-')}</td>
                                    <td>${escapeHtml(row.lock_mode || row.waiting_mode || '-')}</td>
                                    <td>${sqlCell(row.waiting_query)}</td>
                                    <td>${sqlCell(row.blocking_query)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function renderProcesses(data) {
            if (!data.rows.length) {
                setEmpty('processPanel', '当前没有活跃会话。');
                return;
            }
            document.getElementById('processPanel').innerHTML = `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>用户</th>
                                <th>主机</th>
                                <th>数据库</th>
                                <th>命令</th>
                                <th>耗时(s)</th>
                                <th>状态</th>
                                <th>SQL</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.rows.map(row => `
                                <tr>
                                    <td>${escapeHtml(row.id)}</td>
                                    <td>${escapeHtml(row.user)}</td>
                                    <td>${escapeHtml(row.host)}</td>
                                    <td>${escapeHtml(row.db || '-')}</td>
                                    <td>${escapeHtml(row.command)}</td>
                                    <td>${escapeHtml(row.time)}</td>
                                    <td>${escapeHtml(row.state || '-')}</td>
                                    <td>${sqlCell(row.info)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function renderTables(data) {
            if (!data.rows.length) {
                setEmpty('tablesPanel', '当前没有可展示的表空间信息。');
                return;
            }
            document.getElementById('tablesPanel').innerHTML = `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Schema</th>
                                <th>表名</th>
                                <th>引擎</th>
                                <th>行数</th>
                                <th>数据(MB)</th>
                                <th>索引(MB)</th>
                                <th>总大小(MB)</th>
                                <th>更新时间</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.rows.map(row => `
                                <tr>
                                    <td>${escapeHtml(row.table_schema)}</td>
                                    <td>${escapeHtml(row.table_name)}</td>
                                    <td>${escapeHtml(row.engine || '-')}</td>
                                    <td>${escapeHtml(row.table_rows)}</td>
                                    <td>${escapeHtml(row.data_mb)}</td>
                                    <td>${escapeHtml(row.index_mb)}</td>
                                    <td>${escapeHtml(row.total_mb)}</td>
                                    <td>${escapeHtml(row.update_time || '-')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        function updateQueryTime(data) {
            if (data.query_time !== undefined) {
                document.getElementById('queryTime').textContent = data.query_time.toFixed(3) + 's';
            }
        }

        async function loadSummary(profile) {
            const data = await fetchJson('/api/db-monitor/summary' + profileQuery(profile));
            renderSummary(data.summary);
            updateQueryTime(data);
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
        }

        async function loadSlowQueries(profile) {
            setLoading('slowPanel');
            try {
                const data = await fetchJson('/api/db-monitor/slow-queries' + profileQuery(profile));
                updateQueryTime(data);
                renderSlowQueries(data);
            } catch (err) {
                setError('slowPanel', err.message);
            }
        }

        async function loadLocks(profile) {
            setLoading('locksPanel');
            try {
                const data = await fetchJson('/api/db-monitor/locks' + profileQuery(profile));
                updateQueryTime(data);
                renderLocks(data);
            } catch (err) {
                setError('locksPanel', err.message);
            }
        }

        async function loadProcesses(profile) {
            setLoading('processPanel');
            try {
                const data = await fetchJson('/api/db-monitor/processlist' + profileQuery(profile));
                updateQueryTime(data);
                renderProcesses(data);
            } catch (err) {
                setError('processPanel', err.message);
            }
        }

        async function loadTables(profile) {
            setLoading('tablesPanel');
            try {
                const data = await fetchJson('/api/db-monitor/table-stats' + profileQuery(profile));
                updateQueryTime(data);
                renderTables(data);
            } catch (err) {
                setError('tablesPanel', err.message);
            }
        }

        async function refreshAll() {
            try {
                const profile = await getActiveProfile();
                await loadSummary(profile);
                await Promise.all([
                    loadSlowQueries(profile),
                    loadLocks(profile),
                    loadProcesses(profile),
                    loadTables(profile)
                ]);
            } catch (err) {
                showToast('数据库监控加载失败：' + err.message, 'error');
                ['slowPanel', 'locksPanel', 'processPanel', 'tablesPanel'].forEach(id => setError(id, err.message));
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
            sidebar.addEventListener('mouseenter', function() {
                if (sidebar.classList.contains('collapsed')) {
                    sidebar.classList.remove('collapsed');
                    mainWrapper.classList.remove('collapsed-margin');
                    toggleIcon.style.transform = 'rotate(0deg)';
                }
            });
            mainWrapper.addEventListener('click', function() {
                if (!sidebar.classList.contains('collapsed')) {
                    sidebar.classList.add('collapsed');
                    mainWrapper.classList.add('collapsed-margin');
                    toggleIcon.style.transform = 'rotate(180deg)';
                    localStorage.setItem('sidebarCollapsed', 'true');
                }
            });
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed-margin');
                toggleIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            });
        }

        document.addEventListener('DOMContentLoaded', async function() {
            setupSidebarToggle();
            await initDataSourceSelector();
            await refreshAll();
        });
    </script>
</body>
</html>
"""


def _normalize_db_monitor_config(profile_name=None):
    config = get_db_monitor_config(profile_name)
    if not config.get('host') or not config.get('user'):
        raise ValueError('当前环境缺少数据库监控配置，请到系统设置补全数据库监控配置')
    return {
        'host': config.get('host'),
        'port': int(config.get('port') or 3306),
        'database': config.get('database') or 'information_schema',
        'user': config.get('user'),
        'password': config.get('password') or '',
        'charset': 'utf8mb4',
        'connection_timeout': 8
    }


def _get_connection(profile_name=None):
    return mysql.connector.connect(**_normalize_db_monitor_config(profile_name))


def _fetch_status_map(cursor, names):
    placeholders = ', '.join(['%s'] * len(names))
    cursor.execute(f"SHOW GLOBAL STATUS WHERE Variable_name IN ({placeholders})", tuple(names))
    return {row['Variable_name']: row['Value'] for row in cursor.fetchall()}


def _fetch_variable_map(cursor, names):
    placeholders = ', '.join(['%s'] * len(names))
    cursor.execute(f"SHOW GLOBAL VARIABLES WHERE Variable_name IN ({placeholders})", tuple(names))
    return {row['Variable_name']: row['Value'] for row in cursor.fetchall()}


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_summary(profile_name=None):
    with _get_connection(profile_name) as conn:
        cursor = conn.cursor(dictionary=True)
        status = _fetch_status_map(cursor, ['Threads_connected', 'Threads_running', 'Slow_queries', 'Uptime'])
        variables = _fetch_variable_map(cursor, ['max_connections', 'version'])

        lock_wait_count = 0
        try:
            cursor.execute("SELECT COUNT(*) AS cnt FROM performance_schema.data_lock_waits")
            lock_wait_count = _to_int(cursor.fetchone().get('cnt'))
        except Exception:
            try:
                cursor.execute("SELECT COUNT(*) AS cnt FROM information_schema.innodb_lock_waits")
                lock_wait_count = _to_int(cursor.fetchone().get('cnt'))
            except Exception:
                lock_wait_count = 0

        cfg = _normalize_db_monitor_config(profile_name)
        return {
            'targetHost': f"{cfg['host']}:{cfg['port']}",
            'targetDatabase': cfg['database'],
            'threadsConnected': _to_int(status.get('Threads_connected')),
            'threadsRunning': _to_int(status.get('Threads_running')),
            'slowQueries': _to_int(status.get('Slow_queries')),
            'lockWaitCount': lock_wait_count,
            'maxConnections': _to_int(variables.get('max_connections')),
            'version': variables.get('version', '-'),
            'uptimeLabel': f"运行 {_to_int(status.get('Uptime'))} 秒"
        }


def _build_processlist(profile_name=None):
    with _get_connection(profile_name) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW FULL PROCESSLIST")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            if row.get('Command') == 'Sleep':
                continue
            result.append({
                'id': row.get('Id'),
                'user': row.get('User'),
                'host': row.get('Host'),
                'db': row.get('db'),
                'command': row.get('Command'),
                'time': row.get('Time', 0),
                'state': row.get('State'),
                'info': row.get('Info')
            })
        result.sort(key=lambda item: _to_int(item.get('time')), reverse=True)
        return result[:50]


def _build_slow_queries(profile_name=None):
    cfg = _normalize_db_monitor_config(profile_name)
    target_db = cfg['database']
    with _get_connection(profile_name) as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT
                    COALESCE(SCHEMA_NAME, '') AS schema_name,
                    COUNT_STAR AS exec_count,
                    ROUND(AVG_TIMER_WAIT / 1000000000, 2) AS avg_time_ms,
                    ROUND(MAX_TIMER_WAIT / 1000000000, 2) AS max_time_ms,
                    ROUND(SUM_TIMER_WAIT / 1000000000, 2) AS total_time_ms,
                    DIGEST_TEXT AS sample_sql
                FROM performance_schema.events_statements_summary_by_digest
                WHERE DIGEST_TEXT IS NOT NULL
                  AND (%s = '' OR SCHEMA_NAME = %s OR (%s = 'information_schema' AND SCHEMA_NAME IS NOT NULL))
                ORDER BY AVG_TIMER_WAIT DESC
                LIMIT 20
            """
            cursor.execute(sql, (target_db, target_db, target_db))
            rows = cursor.fetchall()
            if rows:
                return [
                    {
                        'source': 'performance_schema',
                        'schema_name': row.get('schema_name'),
                        'exec_count': _to_int(row.get('exec_count')),
                        'avg_time_ms': _to_float(row.get('avg_time_ms')),
                        'max_time_ms': _to_float(row.get('max_time_ms')),
                        'total_time_ms': _to_float(row.get('total_time_ms')),
                        'sample_sql': row.get('sample_sql')
                    }
                    for row in rows
                ]
        except Exception:
            pass

        cursor.execute("SHOW FULL PROCESSLIST")
        rows = cursor.fetchall()
        slow_rows = []
        for row in rows:
            if row.get('Command') == 'Sleep' or not row.get('Info'):
                continue
            if _to_int(row.get('Time')) < 2:
                continue
            if target_db and target_db != 'information_schema' and row.get('db') not in (None, target_db):
                continue
            slow_rows.append({
                'source': 'processlist',
                'schema_name': row.get('db'),
                'exec_count': 1,
                'avg_time_ms': _to_int(row.get('Time')) * 1000,
                'max_time_ms': _to_int(row.get('Time')) * 1000,
                'total_time_ms': _to_int(row.get('Time')) * 1000,
                'sample_sql': row.get('Info')
            })
        slow_rows.sort(key=lambda item: item['avg_time_ms'], reverse=True)
        return slow_rows[:20]


def _build_locks(profile_name=None):
    with _get_connection(profile_name) as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT
                    COALESCE(r.THREAD_ID, r.PROCESSLIST_ID) AS waiting_thread,
                    COALESCE(b.THREAD_ID, b.PROCESSLIST_ID) AS blocking_thread,
                    req.OBJECT_SCHEMA AS object_schema,
                    req.OBJECT_NAME AS object_name,
                    req.LOCK_MODE AS lock_mode,
                    LEFT(r.PROCESSLIST_INFO, 500) AS waiting_query,
                    LEFT(b.PROCESSLIST_INFO, 500) AS blocking_query,
                    COALESCE(r.PROCESSLIST_TIME, 0) AS wait_seconds
                FROM performance_schema.data_lock_waits w
                JOIN performance_schema.data_locks req
                    ON w.REQUESTING_ENGINE_LOCK_ID = req.ENGINE_LOCK_ID
                JOIN performance_schema.data_locks blk
                    ON w.BLOCKING_ENGINE_LOCK_ID = blk.ENGINE_LOCK_ID
                LEFT JOIN performance_schema.threads r
                    ON req.THREAD_ID = r.THREAD_ID
                LEFT JOIN performance_schema.threads b
                    ON blk.THREAD_ID = b.THREAD_ID
                ORDER BY wait_seconds DESC
            """)
            rows = cursor.fetchall()
            if rows:
                return [{'source': 'performance_schema', **row} for row in rows]
        except Exception:
            pass

        try:
            cursor.execute("""
                SELECT
                    r.trx_mysql_thread_id AS waiting_thread,
                    b.trx_mysql_thread_id AS blocking_thread,
                    rl.lock_table AS waiting_table,
                    rl.lock_mode AS waiting_mode,
                    LEFT(r.trx_query, 500) AS waiting_query,
                    LEFT(b.trx_query, 500) AS blocking_query,
                    TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) AS wait_seconds,
                    r.trx_id AS waiting_trx_id,
                    b.trx_id AS blocking_trx_id
                FROM information_schema.innodb_lock_waits w
                JOIN information_schema.innodb_trx r
                    ON w.requesting_trx_id = r.trx_id
                JOIN information_schema.innodb_trx b
                    ON w.blocking_trx_id = b.trx_id
                LEFT JOIN information_schema.innodb_locks rl
                    ON w.requested_lock_id = rl.lock_id
                ORDER BY wait_seconds DESC
            """)
            rows = cursor.fetchall()
            return [{'source': 'innodb_lock_waits', **row} for row in rows]
        except Exception:
            return []


def _build_table_stats(profile_name=None):
    cfg = _normalize_db_monitor_config(profile_name)
    target_db = cfg['database']
    with _get_connection(profile_name) as conn:
        cursor = conn.cursor(dictionary=True)
        if target_db and target_db not in ('information_schema', 'mysql', 'performance_schema', 'sys'):
            cursor.execute("""
                SELECT
                    TABLE_SCHEMA AS table_schema,
                    TABLE_NAME AS table_name,
                    ENGINE AS engine,
                    COALESCE(TABLE_ROWS, 0) AS table_rows,
                    ROUND(COALESCE(DATA_LENGTH, 0) / 1024 / 1024, 2) AS data_mb,
                    ROUND(COALESCE(INDEX_LENGTH, 0) / 1024 / 1024, 2) AS index_mb,
                    ROUND((COALESCE(DATA_LENGTH, 0) + COALESCE(INDEX_LENGTH, 0)) / 1024 / 1024, 2) AS total_mb,
                    COALESCE(DATE_FORMAT(UPDATE_TIME, '%%Y-%%m-%%d %%H:%%i:%%s'), '') AS update_time
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY (COALESCE(DATA_LENGTH, 0) + COALESCE(INDEX_LENGTH, 0)) DESC
                LIMIT 30
            """, (target_db,))
        else:
            cursor.execute("""
                SELECT
                    TABLE_SCHEMA AS table_schema,
                    TABLE_NAME AS table_name,
                    ENGINE AS engine,
                    COALESCE(TABLE_ROWS, 0) AS table_rows,
                    ROUND(COALESCE(DATA_LENGTH, 0) / 1024 / 1024, 2) AS data_mb,
                    ROUND(COALESCE(INDEX_LENGTH, 0) / 1024 / 1024, 2) AS index_mb,
                    ROUND((COALESCE(DATA_LENGTH, 0) + COALESCE(INDEX_LENGTH, 0)) / 1024 / 1024, 2) AS total_mb,
                    COALESCE(DATE_FORMAT(UPDATE_TIME, '%%Y-%%m-%%d %%H:%%i:%%s'), '') AS update_time
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                ORDER BY (COALESCE(DATA_LENGTH, 0) + COALESCE(INDEX_LENGTH, 0)) DESC
                LIMIT 30
            """)
        return cursor.fetchall()


def register_db_monitor_routes(app):
    """注册数据库监控路由"""

    @app.route('/db-monitor')
    def db_monitor_page():
        return render_template_string(DB_MONITOR_TEMPLATE)

    @app.route('/api/db-monitor/summary')
    def api_db_monitor_summary():
        try:
            profile = request.args.get('profile')
            from datetime import datetime
            query_start = datetime.now()
            result = _build_summary(profile)
            query_time = (datetime.now() - query_start).total_seconds()
            return jsonify({'success': True, 'summary': result, 'query_time': query_time})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/db-monitor/processlist')
    def api_db_monitor_processlist():
        try:
            profile = request.args.get('profile')
            from datetime import datetime
            query_start = datetime.now()
            result = _build_processlist(profile)
            query_time = (datetime.now() - query_start).total_seconds()
            return jsonify({'success': True, 'rows': result, 'query_time': query_time})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/db-monitor/slow-queries')
    def api_db_monitor_slow_queries():
        try:
            profile = request.args.get('profile')
            from datetime import datetime
            query_start = datetime.now()
            result = _build_slow_queries(profile)
            query_time = (datetime.now() - query_start).total_seconds()
            return jsonify({'success': True, 'rows': result, 'query_time': query_time})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/db-monitor/locks')
    def api_db_monitor_locks():
        try:
            profile = request.args.get('profile')
            from datetime import datetime
            query_start = datetime.now()
            result = _build_locks(profile)
            query_time = (datetime.now() - query_start).total_seconds()
            return jsonify({'success': True, 'rows': result, 'query_time': query_time})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/db-monitor/table-stats')
    def api_db_monitor_table_stats():
        try:
            profile = request.args.get('profile')
            from datetime import datetime
            query_start = datetime.now()
            result = _build_table_stats(profile)
            query_time = (datetime.now() - query_start).total_seconds()
            return jsonify({'success': True, 'rows': result, 'query_time': query_time})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
