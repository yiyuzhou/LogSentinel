#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法请求日志模块 - 基于 v_algorithm_request_log 视图
"""

from flask import request, jsonify, render_template_string

ALGO_LOG_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>算法请求日志 - 视频任务运维系统</title>
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
        .navbar-version { font-size: 11px; color: var(--text-secondary); white-space: nowrap; }
        .sidebar-toggle { background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 4px; margin-left: auto; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 6px; transition: background 0.2s, color 0.2s; }
        .sidebar-toggle:hover { background: var(--bg-hover); color: var(--text-primary); }
        .sidebar-menu { flex: 1; padding: 16px 0; overflow-y: auto; overflow-x: hidden; }
        .menu-section { padding: 8px 20px 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-secondary); white-space: nowrap; transition: opacity 0.2s; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 10px 20px; color: var(--text-secondary); text-decoration: none; transition: background 0.15s, color 0.15s; white-space: nowrap; overflow: hidden; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: rgba(37, 99, 235, 0.15); color: var(--primary); border-right: 3px solid var(--primary); }
        .menu-item .icon { font-size: 18px; flex-shrink: 0; width: 24px; text-align: center; }
        .menu-item .label { font-size: 14px; transition: opacity 0.2s; }
        .sidebar-footer { padding: 16px 20px; border-top: 1px solid var(--border); }
        .sidebar-status { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
        .status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; flex-shrink: 0; animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1}50%{opacity:.5} }
        .last-update { font-size: 11px; color: var(--text-secondary); margin-top: 4px; white-space: nowrap; }
        .sidebar.collapsed .menu-section, .sidebar.collapsed .label, .sidebar.collapsed .navbar-version,
        .sidebar.collapsed .sidebar-logo h1, .sidebar.collapsed .last-update, .sidebar.collapsed .sidebar-status span:last-child { opacity: 0; width: 0; overflow: hidden; }
        .main-wrapper { margin-left: var(--sidebar-width); flex: 1; display: flex; flex-direction: column; transition: margin-left 0.3s ease; min-height: 100vh; }
        .main-wrapper.expanded { margin-left: 64px; }
        .top-navbar { background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 10px 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .navbar-left { display: flex; align-items: center; gap: 10px; }
        .navbar-label { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
        .navbar-select { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-primary); padding: 5px 10px; border-radius: 6px; font-size: 13px; cursor: pointer; min-width: 120px; }
        .navbar-select:focus { outline: none; border-color: var(--primary); }
        .main-content { flex: 1; padding: 24px; }
        .page-header { margin-bottom: 20px; }
        .page-header h1 { font-size: 22px; font-weight: 600; }
        .page-header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
        .filter-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; }
        .filter-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
        .filter-group { display: flex; flex-direction: column; gap: 4px; }
        .filter-group label { font-size: 12px; color: var(--text-secondary); }
        .filter-input { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-primary); padding: 6px 10px; border-radius: 6px; font-size: 13px; min-width: 140px; }
        .filter-input:focus { outline: none; border-color: var(--primary); }
        .filter-select { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-primary); padding: 6px 10px; border-radius: 6px; font-size: 13px; min-width: 140px; cursor: pointer; }
        .btn { padding: 7px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: background 0.15s; }
        .btn-primary { background: var(--primary); color: #fff; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: #475569; }
        .table-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
        .table-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--border); }
        .table-header h2 { font-size: 15px; font-weight: 600; }
        .table-info { font-size: 13px; color: var(--text-secondary); }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        thead th { background: rgba(51,65,85,0.5); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }
        tbody tr { border-top: 1px solid var(--border); transition: background 0.12s; }
        tbody tr:hover { background: var(--bg-hover); }
        tbody td { padding: 10px 14px; color: var(--text-primary); vertical-align: middle; }
        .cell-mono { font-family: 'Courier New', monospace; font-size: 12px; color: var(--text-secondary); }
        .cell-url { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: var(--text-secondary); cursor: pointer; }
        .cell-url:hover { color: var(--primary); text-decoration: underline; }
        .badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 12px; font-size: 11px; font-weight: 500; white-space: nowrap; }
        .badge-success { background: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
        .badge-fail { background: rgba(220,38,38,0.15); color: #f87171; border: 1px solid rgba(220,38,38,0.3); }
        .badge-status { background: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
        .duration-fast { color: #34d399; }
        .duration-mid  { color: #fbbf24; }
        .duration-slow { color: #f87171; }
        .pagination { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; border-top: 1px solid var(--border); }
        .page-info { font-size: 13px; color: var(--text-secondary); }
        .page-btns { display: flex; gap: 6px; align-items: center; }
        .page-btn { padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-dark); color: var(--text-primary); cursor: pointer; font-size: 13px; }
        .page-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
        .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .page-btn.active { background: var(--primary); border-color: var(--primary); color: #fff; }
        .loading { display: flex; align-items: center; justify-content: center; padding: 60px; color: var(--text-secondary); gap: 10px; }
        .loading-spinner { width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .empty { text-align: center; padding: 60px; color: var(--text-secondary); font-size: 14px; }
        .error-msg { color: #f87171; font-size: 13px; padding: 4px 0; }
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; align-items: center; justify-content: center; }
        .modal-overlay.show { display: flex; }
        .modal-box { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; max-width: 760px; width: 95%; max-height: 80vh; display: flex; flex-direction: column; }
        .modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
        .modal-head h3 { font-size: 15px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 20px; line-height: 1; }
        .modal-body { padding: 16px 20px; overflow-y: auto; flex: 1; }
        .modal-body pre { background: var(--bg-dark); border-radius: 8px; padding: 14px; font-size: 12px; white-space: pre-wrap; word-break: break-all; color: var(--text-primary); border: 1px solid var(--border); max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
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
            <a href="/" class="menu-item" data-page="internal"><span class="icon">🎬</span><span class="label">内部译制</span></a>
            <a href="/mps" class="menu-item" data-page="mps"><span class="icon">🐧</span><span class="label">腾讯 MPS</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs"><span class="icon">📋</span><span class="label">日志监控</span></a>
            <a href="/server-monitor" class="menu-item" data-page="server-monitor"><span class="icon">🖥️</span><span class="label">服务器监控</span></a>
            <a href="/db-monitor" class="menu-item" data-page="db-monitor"><span class="icon">🗄️</span><span class="label">数据库监控</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings"><span class="icon">⚙️</span><span class="label">系统设置</span></a>
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-status"><span class="status-dot"></span><span>系统运行正常</span></div>
            <div class="last-update">最后更新：<span id="lastUpdate">-</span></div>
        </div>
    </aside>

    <div class="main-wrapper" id="mainWrapper">
        <!-- 环境切换顶部栏 -->
        <div class="top-navbar">
            <div class="navbar-left">
                <span class="navbar-label">当前环境：</span>
                <select class="navbar-select" id="profileSelect" onchange="switchDataSource(this.value)">
                    <option value="">加载中...</option>
                </select>
            </div>
        </div>

        <div class="main-content">
            <div class="page-header">
                <h1>🔬 算法请求日志</h1>
                <p>查看算法模块的 HTTP 请求与响应记录，支持多维度筛选</p>
            </div>

            <!-- 筛选区 -->
            <div class="filter-card">
                <div class="filter-row">
                    <div class="filter-group">
                        <label>Task ID</label>
                        <input type="text" class="filter-input" id="fTaskId" placeholder="输入 Task ID" style="width:130px;">
                    </div>
                    <div class="filter-group">
                        <label>Trace ID</label>
                        <input type="text" class="filter-input" id="fTraceId" placeholder="输入 Trace ID" style="width:200px;">
                    </div>
                    <div class="filter-group">
                        <label>模块名称</label>
                        <select class="filter-select" id="fModule" style="min-width:170px;">
                            <option value="">全部模块</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>结果</label>
                        <select class="filter-select" id="fSuccess" style="min-width:100px;">
                            <option value="">全部</option>
                            <option value="1">成功</option>
                            <option value="0">失败</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>开始时间（起）</label>
                        <input type="datetime-local" class="filter-input" id="fTimeStart" style="width:175px;">
                    </div>
                    <div class="filter-group">
                        <label>开始时间（止）</label>
                        <input type="datetime-local" class="filter-input" id="fTimeEnd" style="width:175px;">
                    </div>
                    <div class="filter-group" style="justify-content: flex-end;">
                        <label style="visibility:hidden;">操作</label>
                        <div style="display:flex;gap:8px;">
                            <button class="btn btn-primary" onclick="doSearch()">🔍 查询</button>
                            <button class="btn btn-secondary" onclick="doReset()">↺ 重置</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 数据表格 -->
            <div class="table-card">
                <div class="table-header">
                    <h2>请求记录</h2>
                    <span class="table-info" id="totalInfo">-</span>
                </div>
                <div id="tableContainer">
                    <div class="loading"><div class="loading-spinner"></div>加载中...</div>
                </div>
                <div class="pagination" id="paginationBar" style="display:none;">
                    <span class="page-info" id="pageInfo">-</span>
                    <div class="page-btns" id="pageBtns"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 详情弹窗 -->
    <div class="modal-overlay" id="detailModal" onclick="closeModal(event)">
        <div class="modal-box">
            <div class="modal-head">
                <h3 id="modalTitle">请求详情</h3>
                <button class="modal-close" onclick="hideModal()">✕</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        // ======== 侧边栏折叠 ========
        const sidebar = document.getElementById('sidebar');
        const mainWrapper = document.getElementById('mainWrapper');
        document.getElementById('sidebarToggle').addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            mainWrapper.classList.toggle('expanded');
            const icon = document.getElementById('toggleIcon');
            if (sidebar.classList.contains('collapsed')) {
                icon.innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>';
                localStorage.setItem('sidebarCollapsed', 'true');
            } else {
                icon.innerHTML = '<polyline points="15 18 9 12 15 6"></polyline>';
                localStorage.setItem('sidebarCollapsed', 'false');
            }
        });
        // 恢复侧边栏状态
        if (localStorage.getItem('sidebarCollapsed') === 'true') {
            sidebar.classList.add('collapsed');
            mainWrapper.classList.add('expanded');
            document.getElementById('toggleIcon').innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>';
        }

        // ======== 环境切换 ========
        async function initDataSourceSelector() {
            try {
                const res = await fetch('/api/settings/valid_profiles');
                const data = await res.json();
                if (!data.success) return;
                const sel = document.getElementById('profileSelect');
                sel.innerHTML = '';
                data.profiles.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.key;
                    opt.textContent = p.name;
                    if (p.active) opt.selected = true;
                    sel.appendChild(opt);
                });
                const saved = localStorage.getItem('activeProfile');
                if (saved && data.profiles.find(p => p.key === saved)) {
                    sel.value = saved;
                }
                // 确保 localStorage 记录当前激活的数据源
                const activeKey = sel.value || data.activeProfile || '';
                if (activeKey) localStorage.setItem('activeProfile', activeKey);
            } catch (e) { console.warn('加载数据源失败', e); }
        }

        function switchDataSource(profileKey) {
            if (!profileKey) return;
            localStorage.setItem('activeProfile', profileKey);
            currentPage = 1;
            loadData();
        }

        async function getActiveProfile() {
            let activeProfile = localStorage.getItem('activeProfile') || '';
            if (activeProfile) return activeProfile;
            // localStorage 为空时从后端获取激活的数据源
            try {
                const res = await fetch('/api/settings/valid_profiles');
                const data = await res.json();
                if (data.success && data.activeProfile) {
                    activeProfile = data.activeProfile;
                    localStorage.setItem('activeProfile', activeProfile);
                }
            } catch (e) {}
            return activeProfile || document.getElementById('profileSelect').value || '';
        }

        // ======== 分页状态 ========
        let currentPage = 1;
        const PAGE_SIZE = 20;
        let totalCount = 0;
        // 行数据缓存（避免 JSON 直接内联到 onclick 导致特殊字符破坏 HTML）
        let _rowCache = {};

        // ======== 主加载函数 ========
        async function loadData() {
            document.getElementById('tableContainer').innerHTML = '<div class="loading"><div class="loading-spinner"></div>加载中...</div>';
            document.getElementById('paginationBar').style.display = 'none';

            const params = await buildParams();
            try {
                const res = await fetch('/api/algo-log/list?' + params);
                const data = await res.json();
                if (!data.success) {
                    document.getElementById('tableContainer').innerHTML = '<div class="empty">❌ 加载失败：' + escHtml(data.error || '未知错误') + '</div>';
                    return;
                }
                totalCount = data.total;
                document.getElementById('totalInfo').textContent = '共 ' + totalCount + ' 条记录';
                renderTable(data.rows);
                renderPagination();
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (e) {
                document.getElementById('tableContainer').innerHTML = '<div class="empty">❌ 请求异常：' + escHtml(e.message) + '</div>';
            }
        }

        async function buildParams() {
            const p = new URLSearchParams();
            const profile = await getActiveProfile();
            if (profile) p.set('profile', profile);
            const taskId = document.getElementById('fTaskId').value.trim();
            const traceId = document.getElementById('fTraceId').value.trim();
            const module = document.getElementById('fModule').value;
            const success = document.getElementById('fSuccess').value;
            const timeStart = document.getElementById('fTimeStart').value;
            const timeEnd = document.getElementById('fTimeEnd').value;
            if (taskId) p.set('task_id', taskId);
            if (traceId) p.set('trace_id', traceId);
            if (module) p.set('module_name', module);
            if (success !== '') p.set('success', success);
            if (timeStart) p.set('begin_time_start', timeStart.replace('T', ' ') + ':00');
            if (timeEnd) p.set('begin_time_end', timeEnd.replace('T', ' ') + ':59');
            p.set('page', currentPage);
            p.set('page_size', PAGE_SIZE);
            return p.toString();
        }

        function renderTable(rows) {
            if (!rows || rows.length === 0) {
                document.getElementById('tableContainer').innerHTML = '<div class="empty">暂无数据</div>';
                return;
            }
            // 清空并重建行缓存
            _rowCache = {};
            rows.forEach(r => { _rowCache[r.id] = r; });

            let html = '<div class="table-wrap"><table><thead><tr>';
            html += '<th>ID</th><th>Task ID</th><th>Series ID</th><th>Trace ID</th>';
            html += '<th>模块名称</th><th>请求 URL</th><th>状态码</th><th>结果</th>';
            html += '<th>失败类型</th><th>耗时(ms)</th><th>开始时间</th><th>结束时间</th><th>操作</th>';
            html += '</tr></thead><tbody>';
            rows.forEach(r => {
                html += '<tr>';
                html += '<td class="cell-mono">' + (r.id || '-') + '</td>';
                html += '<td>' + (r.task_id != null ? r.task_id : '-') + '</td>';
                html += '<td>' + (r.series_id != null ? r.series_id : '-') + '</td>';
                html += '<td class="cell-mono" style="font-size:11px;">' + escHtml(r.trace_id || '-') + '</td>';
                html += '<td>' + escHtml(r.module_name || '-') + '</td>';
                html += '<td><div class="cell-url" data-url="' + escHtml(r.request_url || '') + '" onclick="showUrl(this.dataset.url)">' + escHtml(truncate(r.request_url || '-', 40)) + '</div></td>';
                html += '<td><span class="badge badge-status">' + (r.response_status || '-') + '</span></td>';
                html += '<td>' + formatSuccess(r.success) + '</td>';
                html += '<td>' + escHtml(r.fail_type || '-') + '</td>';
                html += '<td class="' + durationClass(r.duration_ms) + '">' + (r.duration_ms != null ? r.duration_ms.toLocaleString() : '-') + '</td>';
                html += '<td class="cell-mono" style="font-size:11px;">' + escHtml(r.begin_time || '-') + '</td>';
                html += '<td class="cell-mono" style="font-size:11px;">' + escHtml(r.end_time || '-') + '</td>';
                html += '<td><button class="btn btn-secondary" style="padding:3px 9px;font-size:12px;" data-id="' + r.id + '" onclick="showDetailById(this.dataset.id)">详情</button></td>';
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            document.getElementById('tableContainer').innerHTML = html;
        }

        function formatSuccess(val) {
            if (val === 1 || val === true) return '<span class="badge badge-success">✓ 成功</span>';
            if (val === 0 || val === false) return '<span class="badge badge-fail">✗ 失败</span>';
            return '-';
        }

        function durationClass(ms) {
            if (ms == null) return '';
            if (ms < 1000) return 'duration-fast';
            if (ms < 10000) return 'duration-mid';
            return 'duration-slow';
        }

        function renderPagination() {
            const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
            const bar = document.getElementById('paginationBar');
            const info = document.getElementById('pageInfo');
            const btns = document.getElementById('pageBtns');
            info.textContent = '第 ' + currentPage + ' / ' + totalPages + ' 页，共 ' + totalCount + ' 条';
            let html = '';
            html += '<button class="page-btn" onclick="gotoPage(' + (currentPage - 1) + ')"' + (currentPage <= 1 ? ' disabled' : '') + '>上一页</button>';
            // 显示最多 7 个页码按钮
            let start = Math.max(1, currentPage - 3);
            let end = Math.min(totalPages, start + 6);
            if (end - start < 6) start = Math.max(1, end - 6);
            if (start > 1) html += '<button class="page-btn" onclick="gotoPage(1)">1</button>';
            if (start > 2) html += '<span style="color:var(--text-secondary);padding:0 4px;">…</span>';
            for (let i = start; i <= end; i++) {
                html += '<button class="page-btn' + (i === currentPage ? ' active' : '') + '" onclick="gotoPage(' + i + ')">' + i + '</button>';
            }
            if (end < totalPages - 1) html += '<span style="color:var(--text-secondary);padding:0 4px;">…</span>';
            if (end < totalPages) html += '<button class="page-btn" onclick="gotoPage(' + totalPages + ')">' + totalPages + '</button>';
            html += '<button class="page-btn" onclick="gotoPage(' + (currentPage + 1) + ')"' + (currentPage >= totalPages ? ' disabled' : '') + '>下一页</button>';
            btns.innerHTML = html;
            bar.style.display = 'flex';
        }

        function gotoPage(p) {
            const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
            if (p < 1 || p > totalPages) return;
            currentPage = p;
            loadData();
        }

        // ======== 模块下拉初始化 ========
        async function loadModules() {
            try {
                const profile = await getActiveProfile();
                const res = await fetch('/api/algo-log/modules' + (profile ? '?profile=' + encodeURIComponent(profile) : ''));
                const data = await res.json();
                if (!data.success) return;
                const sel = document.getElementById('fModule');
                const cur = sel.value;
                sel.innerHTML = '<option value="">全部模块</option>';
                data.modules.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m;
                    opt.textContent = m;
                    sel.appendChild(opt);
                });
                if (cur) sel.value = cur;
            } catch (e) {}
        }

        // ======== 筛选操作 ========
        function doSearch() {
            currentPage = 1;
            loadData();
        }

        function doReset() {
            document.getElementById('fTaskId').value = '';
            document.getElementById('fTraceId').value = '';
            document.getElementById('fModule').value = '';
            document.getElementById('fSuccess').value = '';
            document.getElementById('fTimeStart').value = '';
            document.getElementById('fTimeEnd').value = '';
            currentPage = 1;
            loadData();
        }

        // ======== 详情弹窗 ========
        function showDetailById(id) {
            const row = _rowCache[Number(id)];
            if (row) showDetail(row);
        }

        function showDetail(row) {
            document.getElementById('modalTitle').textContent = '请求详情 #' + (row.id || '-');
            let html = '';
            const fields = [
                ['ID', row.id], ['Trace ID', row.trace_id], ['Task ID', row.task_id],
                ['Series ID', row.series_id], ['模块名称', row.module_name],
                ['请求 URL', row.request_url], ['请求方法', row.request_method],
                ['响应状态码', row.response_status], ['结果', row.success === 1 ? '成功' : '失败'],
                ['失败类型', row.fail_type], ['错误名称', row.error_name],
                ['错误信息', row.error_message], ['根因信息', row.error_root_cause_message],
                ['耗时(ms)', row.duration_ms], ['开始时间', row.begin_time], ['结束时间', row.end_time],
            ];
            fields.forEach(([k, v]) => {
                if (v != null && v !== '') {
                    html += '<div style="margin-bottom:8px;"><span style="color:var(--text-secondary);font-size:12px;">' + escHtml(k) + '</span>';
                    html += '<div style="margin-top:2px;font-size:13px;">' + escHtml(String(v)) + '</div></div>';
                }
            });
            if (row.request_body) {
                html += '<div style="margin-bottom:8px;"><span style="color:var(--text-secondary);font-size:12px;">请求体</span>';
                html += '<pre>' + escHtml(tryPretty(row.request_body)) + '</pre></div>';
            }
            if (row.response_body) {
                html += '<div style="margin-bottom:8px;"><span style="color:var(--text-secondary);font-size:12px;">响应体</span>';
                html += '<pre>' + escHtml(tryPretty(row.response_body)) + '</pre></div>';
            }
            document.getElementById('modalBody').innerHTML = html;
            document.getElementById('detailModal').classList.add('show');
        }

        function showUrl(url) {
            document.getElementById('modalTitle').textContent = '完整 URL';
            document.getElementById('modalBody').innerHTML = '<pre>' + escHtml(url) + '</pre>';
            document.getElementById('detailModal').classList.add('show');
        }

        function hideModal() { document.getElementById('detailModal').classList.remove('show'); }
        function closeModal(e) { if (e.target === document.getElementById('detailModal')) hideModal(); }

        // ======== 工具函数 ========
        function escHtml(s) {
            return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }
        function escJs(s) { return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
        function truncate(s, n) { return s && s.length > n ? s.substring(0, n) + '…' : s; }
        function tryPretty(s) {
            try { return JSON.stringify(JSON.parse(s), null, 2); } catch(e) { return s; }
        }

        // ======== 初始化 ========
        document.addEventListener('DOMContentLoaded', async () => {
            // 先初始化数据源选择器，确保 localStorage 有值
            await initDataSourceSelector();
            // 然后并行加载模块和数据
            await Promise.all([loadModules(), loadData()]);
        });
    </script>
</body>
</html>
"""


def register_algo_request_log_routes(app, query_db):
    """注册算法请求日志相关路由"""

    @app.route('/algo-log')
    def algo_log_page():
        return render_template_string(ALGO_LOG_TEMPLATE)

    @app.route('/api/algo-log/modules')
    def api_algo_log_modules():
        """获取模块名称列表（用于下拉筛选）"""
        try:
            profile = request.args.get('profile')
            rows = query_db(
                "SELECT DISTINCT module_name FROM v_algorithm_request_log "
                "WHERE module_name IS NOT NULL AND module_name != '' ORDER BY module_name",
                profile=profile
            )
            modules = [r['module_name'] for r in rows]
            return jsonify({'success': True, 'modules': modules})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/algo-log/list')
    def api_algo_log_list():
        """分页查询算法请求日志"""
        try:
            profile = request.args.get('profile')
            task_id = request.args.get('task_id', '').strip()
            trace_id = request.args.get('trace_id', '').strip()
            module_name = request.args.get('module_name', '').strip()
            success = request.args.get('success', '')
            begin_time_start = request.args.get('begin_time_start', '').strip()
            begin_time_end = request.args.get('begin_time_end', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(1, int(request.args.get('page_size', 20))))

            where_clauses = ['deleted = 0']
            params = []

            if task_id:
                where_clauses.append('task_id = %s')
                params.append(int(task_id))
            if trace_id:
                where_clauses.append('trace_id LIKE %s')
                params.append('%' + trace_id + '%')
            if module_name:
                where_clauses.append('module_name = %s')
                params.append(module_name)
            if success != '':
                where_clauses.append('success = %s')
                params.append(int(success))
            if begin_time_start:
                where_clauses.append('begin_time >= %s')
                params.append(begin_time_start)
            if begin_time_end:
                where_clauses.append('begin_time <= %s')
                params.append(begin_time_end)

            where_sql = ' AND '.join(where_clauses)
            offset = (page - 1) * page_size

            # 查总数
            count_rows = query_db(
                f"SELECT COUNT(*) AS cnt FROM v_algorithm_request_log WHERE {where_sql}",
                tuple(params), profile=profile
            )
            total = count_rows[0]['cnt'] if count_rows else 0

            # 查数据（不返回大字段 request_body/response_body，详情页单独展示）
            data_rows = query_db(
                f"""SELECT id, trace_id, task_id, series_id, module_name, module_path,
                           request_url, request_method, response_status,
                           success, fail_type, error_name, error_message, error_root_cause_message,
                           begin_time, end_time, duration_ms, request_body, response_body
                    FROM v_algorithm_request_log
                    WHERE {where_sql}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s""",
                tuple(params) + (page_size, offset), profile=profile
            )

            # 格式化时间
            from datetime import datetime
            def fmt(v):
                if v is None:
                    return None
                if isinstance(v, datetime):
                    return v.strftime('%Y-%m-%d %H:%M:%S')
                return str(v)

            result = []
            for r in data_rows:
                result.append({
                    'id': r['id'],
                    'trace_id': r['trace_id'],
                    'task_id': r['task_id'],
                    'series_id': r['series_id'],
                    'module_name': r['module_name'],
                    'module_path': r['module_path'],
                    'request_url': r['request_url'],
                    'request_method': r['request_method'],
                    'response_status': r['response_status'],
                    'success': r['success'],
                    'fail_type': r['fail_type'],
                    'error_name': r['error_name'],
                    'error_message': r['error_message'],
                    'error_root_cause_message': r['error_root_cause_message'],
                    'begin_time': fmt(r['begin_time']),
                    'end_time': fmt(r['end_time']),
                    'duration_ms': r['duration_ms'],
                    'request_body': r['request_body'],
                    'response_body': r['response_body'],
                })

            return jsonify({'success': True, 'total': total, 'rows': result})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
