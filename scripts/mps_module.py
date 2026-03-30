#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯 MPS 模块 - 列表页和详情页
"""

from flask import render_template_string

# 腾讯 MPS 列表页 HTML
MPS_LIST_TEMPLATE = """
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
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); border-color: var(--primary); }
        .stat-card h3 { color: var(--text-secondary); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; font-weight: 500; }
        .stat-card .number { font-size: 32px; font-weight: 700; color: var(--text-primary); }
        .stat-card.total .number { color: var(--primary); }
        .stat-card.success .number { color: var(--success); }
        .stat-card.failed .number { color: var(--danger); }
        .stat-card.today .number { color: var(--info); }
        .toolbar { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
        .toolbar-left { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .toolbar-right { display: flex; align-items: center; gap: 12px; }
        .toolbar-title { font-size: 16px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
        .search-form { display: flex; flex-wrap: wrap; gap: 12px; flex: 1; }
        .search-input, .search-select { padding: 10px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text-primary); font-size: 13px; transition: all 0.2s; }
        .search-input:focus, .search-select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .btn { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .table-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px; overflow: hidden; }
        .table-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 16px 20px; font-size: 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
        .table-count { background: rgba(37, 99, 235, 0.2); color: var(--primary); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: rgba(37, 99, 235, 0.1); font-weight: 600; color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }
        tr:hover { background: var(--bg-hover); }
        tr:last-child td { border-bottom: none; }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .status-success { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .status-failed { background: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); }
        .status-processing { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .status-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
        .type-badge { display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; background: rgba(124, 58, 237, 0.15); color: #a78bfa; border: 1px solid rgba(124, 58, 237, 0.3); }
        .type-badge-audio { background: rgba(37, 99, 235, 0.15); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.3); }
        .type-badge-vision { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .detail-btn { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s; }
        .detail-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .pagination { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 16px 20px; background: var(--bg-dark); border-top: 1px solid var(--border); }
        .pagination button { padding: 8px 14px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
        .pagination button:hover:not(:disabled) { background: var(--primary); border-color: var(--primary); }
        .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
        .pagination button.active { background: var(--primary); border-color: var(--primary); }
        .pagination .page-info { color: var(--text-secondary); font-size: 13px; }
        .no-data { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .no-data-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .error-msg { background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #f87171; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; backdrop-filter: blur(4px); }
        .modal.show { display: flex; justify-content: center; align-items: center; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; width: 90%; max-width: 900px; max-height: 85vh; overflow: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.5); }
        .modal-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); position: sticky; top: 0; }
        .modal-header h3 { font-size: 16px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .modal-close:hover { background: var(--bg-hover); color: var(--text-primary); }
        .modal-body { padding: 24px; }
        .json-viewer { background: #0d1117; color: #c9d1d9; padding: 20px; border-radius: 10px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; max-height: 600px; overflow-y: auto; border: 1px solid var(--border); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo"><div class="logo-icon">📊</div><div><h1>运维系统</h1><div class="navbar-version">v1.0.0 by yiyuzhou</div></div><button class="sidebar-toggle" id="sidebarToggle" title="收起/展开菜单">
                <svg id="toggleIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
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
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs"><span class="icon">📋</span><span class="label">日志监控</span></a><div class="menu-section" style="margin-top: 20px;">系统</div><a href="/settings" class="menu-item" data-page="settings"><span class="icon">⚙️</span><span class="label">系统设置</span></a></nav>
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
            <div id="statsContent"></div>
            <div class="toolbar">
                <div class="toolbar-left">
                    <div class="toolbar-title">🔍 搜索筛选</div>
                    <div class="search-form">
                        <input type="text" id="searchTaskId" class="search-input" placeholder="搜索任务 ID">
                        <input type="text" id="searchEpisode" class="search-input" placeholder="搜索剧集名">
                        <select id="searchType" class="search-select">
                            <option value="">全部提取方式</option>
                            <option value="vision">画面识别</option>
                            <option value="audio">音频识别</option>
                        </select>
                        <select id="searchCosStatus" class="search-select">
                            <option value="">全部 COS 状态</option>
                            <option value="success">成功</option>
                            <option value="failed">失败</option>
                            <option value="processing">处理中</option>
                        </select>
                    </div>
                </div>
                <div class="toolbar-right">
                    <button class="btn btn-secondary" onclick="clearSearch()">清空</button>
                    <button class="btn btn-primary" onclick="applySearch()">搜索</button>
                    <button class="btn btn-primary" onclick="loadData()" id="refreshBtn">🔄 刷新</button>
                </div>
            </div>
            <div id="content"></div>
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
        const PAGE_SIZE = 10;
        let allData = [];
        let filteredData = [];
        let currentPage = 1;
        
        function formatCosStatus(status) {
            if (!status) return '<span class="status-badge status-processing">处理中</span>';
            const s = status.toUpperCase();
            if (s === 'SUCCESS' || s === 'COMPLETED' || s === 'FINISH' || s === 'FINISHED') return '<span class="status-badge status-success">成功</span>';
            if (s === 'FAILED' || s === 'ERROR' || s === 'FAIL') return '<span class="status-badge status-failed">失败</span>';
            if (s === 'PROCESSING' || s === 'RUNNING' || s === 'PENDING') return '<span class="status-badge status-processing">处理中</span>';
            return '<span class="status-badge status-processing">' + status + '</span>';
        }
        function formatExtractType(type) {
            if (type === 'audio') {
                return '<span class="type-badge type-badge-audio">🎵 音频识别</span>';
            } else if (type === 'vision') {
                return '<span class="type-badge type-badge-vision">👁️ 画面识别</span>';
            }
            return '<span class="type-badge">' + type + '</span>';
        }
        function formatTime(timeStr) {
            if (!timeStr) return '-';
            try {
                if (timeStr.includes('T')) return timeStr.replace('T', ' ').substring(0, 19);
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
                return timeStr.substring(0, 19);
            } catch(e) { return timeStr; }
        }
        function truncate(str, len) { if (!str) return '-'; return str.length > len ? str.substring(0, len) + '...' : str; }
        
        function matchesFilter(row, taskId, episode, type, cosStatus) {
            if (taskId && row.task_id != taskId) return false;
            if (episode && (!row.episode_name || !row.episode_name.toLowerCase().includes(episode.toLowerCase()))) return false;
            if (type && row.subtitle_extract_type != type) return false;
            if (cosStatus) {
                const s = (row.cos_status || '').toLowerCase();
                if (cosStatus === 'success' && !s.includes('success') && !s.includes('completed')) return false;
                if (cosStatus === 'failed' && !s.includes('failed') && !s.includes('error')) return false;
                if (cosStatus === 'processing' && (s.includes('success') || s.includes('failed') || s.includes('error'))) return false;
            }
            return true;
        }
        
        function clearSearch() {
            document.getElementById('searchTaskId').value = '';
            document.getElementById('searchEpisode').value = '';
            document.getElementById('searchType').value = '';
            document.getElementById('searchCosStatus').value = '';
            filteredData = [...allData];
            currentPage = 1;
            renderTable();
        }
        
        function renderPagination() {
            const total = filteredData.length;
            const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
            if (totalPages <= 1) return '';
            let html = '<div class="pagination">';
            html += '<button ' + (currentPage <= 1 ? 'disabled' : '') + ' onclick="changePage(' + (currentPage - 1) + ')">← 上一页</button>';
            html += '<span class="page-info">第 ' + currentPage + ' / ' + totalPages + ' 页 (共 ' + total + ' 条)</span>';
            html += '<button ' + (currentPage >= totalPages ? 'disabled' : '') + ' onclick="changePage(' + (currentPage + 1) + ')">下一页 →</button>';
            html += '</div>';
            return html;
        }
        
        function changePage(page) { currentPage = page; renderTable(); }
        
        function renderTable() {
            const total = filteredData.length;
            const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
            const start = (currentPage - 1) * PAGE_SIZE;
            const pageData = filteredData.slice(start, start + PAGE_SIZE);
            
            if (pageData.length === 0) {
                document.getElementById('content').innerHTML = '<div class="table-section"><div class="table-header">📋 任务列表<span class="table-count">0</span></div><div class="no-data"><div class="no-data-icon">📭</div>暂无数据</div></div>';
                return;
            }
            
            const columns = [
                { title: '任务 ID', field: 'task_id' },
                { title: '剧集名', field: 'episode_name', format: v => truncate(v, 30) },
                { title: '提取方式', field: 'subtitle_extract_type', format: formatExtractType },
                { title: 'COS 状态', field: 'cos_status', format: formatCosStatus },
                { title: '创建时间', field: 'create_time', format: formatTime },
                { title: '操作', field: 'task_id', format: v => '<a href="/mps_detail?id=' + v + '" class="detail-btn" target="_blank">📄 查看详情</a>' }
            ];
            
            let html = '<div class="table-section">';
            html += '<div class="table-header">📋 任务列表<span class="table-count">' + pageData.length + ' / ' + total + '</span></div>';
            html += '<div class="table-container"><table><thead><tr>';
            columns.forEach(col => html += '<th>' + col.title + '</th>');
            html += '</tr></thead><tbody>';
            pageData.forEach(row => {
                html += '<tr>';
                columns.forEach(col => {
                    let v = row[col.field];
                    if (col.format) v = col.format(v, row);
                    html += '<td>' + v + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            html += renderPagination();
            html += '</div>';
            document.getElementById('content').innerHTML = html;
        }
        
        function applySearch() {
            const taskId = document.getElementById('searchTaskId').value.trim();
            const episode = document.getElementById('searchEpisode').value.trim();
            const type = document.getElementById('searchType').value;
            const cosStatus = document.getElementById('searchCosStatus').value;
            filteredData = allData.filter(row => matchesFilter(row, taskId, episode, type, cosStatus));
            currentPage = 1;
            renderTable();
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
                const res = await fetch('/api/mps_data?t=' + Date.now() + profileParam);
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Unknown error');
                allData = data.data || [];
                filteredData = [...allData];
                
                const stats = data.stats || {};
                let statsHtml = '<div class="stats-grid">';
                statsHtml += '<div class="stat-card total"><h3>📈 总任务数</h3><div class="number">' + (stats.total || 0) + '</div></div>';
                statsHtml += '<div class="stat-card success"><h3>✅ 成功</h3><div class="number">' + (stats.success || 0) + '</div></div>';
                statsHtml += '<div class="stat-card failed"><h3>❌ 失败</h3><div class="number">' + (stats.failed || 0) + '</div></div>';
                statsHtml += '<div class="stat-card today"><h3>📅 今日新增</h3><div class="number">' + (stats.today || 0) + '</div></div></div>';
                document.getElementById('statsContent').innerHTML = statsHtml;
                
                renderTable();
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
            } catch (err) {
                console.error('Load data error:', err);
                document.getElementById('content').innerHTML = '<div class="error-msg">❌ 加载失败：' + err.message + '</div>';
            } finally { btn.disabled = false; btn.textContent = '🔄 刷新'; }
        }
        
        function viewJson(title, jsonData) {
            if (!jsonData) { document.getElementById('jsonContent').textContent = '无数据'; }
            else if (typeof jsonData === 'string') {
                try { document.getElementById('jsonContent').textContent = JSON.stringify(JSON.parse(jsonData), null, 2); }
                catch(e) { document.getElementById('jsonContent').textContent = jsonData; }
            } else { document.getElementById('jsonContent').textContent = JSON.stringify(jsonData, null, 2); }
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('jsonModal').classList.add('show');
        }
        
        function closeModal() { document.getElementById('jsonModal').classList.remove('show'); }
        document.getElementById('jsonModal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });
        
        // 侧边栏切换
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
            
            toggle.addEventListener('click', function() {
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed-margin');
                toggleIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() { loadData(); setupSidebarToggle(); });
    </script>
</body>
</html>
"""

# 腾讯 MPS 详情页 HTML
MPS_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPS 任务详情</title>
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
        .top-bar { background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 12px 30px; display: flex; justify-content: space-between; align-items: center; }
        .back-btn { background: var(--bg-hover); color: var(--text-primary); text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; border: 1px solid var(--border); transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .back-btn:hover { background: var(--border); }
        .main-content { max-width: 1600px; margin: 0 auto; padding: 24px 30px; flex: 1; }
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
        .view-btn { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.2s; }
        .view-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .no-data { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .no-data-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .error-msg { background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #f87171; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        .loading { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .spinner { border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; width: 48px; height: 48px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; backdrop-filter: blur(4px); }
        .modal.show { display: flex; justify-content: center; align-items: center; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; width: 90%; max-width: 900px; max-height: 85vh; overflow: auto; box-shadow: 0 25px 50px rgba(0,0,0,0.5); }
        .modal-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: var(--text-primary); padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); position: sticky; top: 0; }
        .modal-header h3 { font-size: 16px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .modal-close:hover { background: var(--bg-hover); color: var(--text-primary); }
        .modal-body { padding: 24px; }
        .json-viewer { background: #0d1117; color: #c9d1d9; padding: 20px; border-radius: 10px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; max-height: 600px; overflow-y: auto; border: 1px solid var(--border); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-logo"><div class="logo-icon">📊</div><div><h1>运维系统</h1><div class="navbar-version">v1.0.0 by yiyuzhou</div></div><button class="sidebar-toggle" id="sidebarToggle" title="收起/展开菜单">
                <svg id="toggleIcon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
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
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs"><span class="icon">📋</span><span class="label">日志监控</span></a><div class="menu-section" style="margin-top: 20px;">系统</div><a href="/settings" class="menu-item" data-page="settings"><span class="icon">⚙️</span><span class="label">系统设置</span></a></nav>
        <div class="sidebar-footer">
            <div class="sidebar-status">
                <span class="status-dot"></span>
                <span>系统运行正常</span>
            </div>
            <div class="last-update">最后更新：<span id="lastUpdate">-</span></div>
        </div>
    </aside>
    <div class="main-wrapper" id="mainWrapper">
        <div class="top-bar">
            <a href="/mps" class="back-btn">← 返回列表</a>
        </div>
        <div class="main-content">
            <div id="content">
                <div class="loading"><div class="spinner"></div><p>加载中...</p></div>
            </div>
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
        function formatTime(timeStr) {
            if (!timeStr) return '-';
            try {
                if (timeStr.includes('T')) return timeStr.replace('T', ' ').substring(0, 19);
                return timeStr.substring(0, 19);
            } catch(e) { return timeStr; }
        }
        function formatStatus(status) {
            if (!status || status === 0 || status === '0') return '<span class="status-badge status-success">成功</span>';
            return '<span class="status-badge status-error">失败</span>';
        }
        function formatDuration(ms) {
            if (!ms && ms !== 0) return '-';
            return (ms / 1000).toFixed(2) + 's';
        }
        function truncate(str, len) { if (!str) return '-'; return str.length > len ? str.substring(0, len) + '...' : str; }
        
        function viewJson(title, jsonData) {
            if (!jsonData) { document.getElementById('jsonContent').textContent = '无数据'; }
            else if (typeof jsonData === 'string') {
                try { document.getElementById('jsonContent').textContent = JSON.stringify(JSON.parse(jsonData), null, 2); }
                catch(e) { document.getElementById('jsonContent').textContent = jsonData; }
            } else { document.getElementById('jsonContent').textContent = JSON.stringify(jsonData, null, 2); }
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('jsonModal').classList.add('show');
        }
        
        function closeModal() { document.getElementById('jsonModal').classList.remove('show'); }
        document.getElementById('jsonModal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });
        
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

        async function loadDetail() {
            const urlParams = new URLSearchParams(window.location.search);
            const taskId = urlParams.get('id');
            if (!taskId) { document.getElementById('content').innerHTML = '<div class="error-msg">❌ 缺少任务 ID 参数</div>'; return; }
            
            try {
                const activeProfile = await getActiveProfile();
                const profileParam = activeProfile ? '&profile=' + encodeURIComponent(activeProfile) : '';
                const res = await fetch('/api/mps_detail?id=' + taskId + profileParam);
                const data = await res.json();
                if (!data.success) throw new Error(data.error || '加载失败');
                
                const task = data.task;
                const logs = data.logs || [];
                
                let html = '<div class="task-info"><h2>📌 任务基本信息</h2><div class="info-grid">';
                html += '<div class="info-item"><label>任务 ID</label><div class="value">' + task.task_id + '</div></div>';
                html += '<div class="info-item"><label>剧集名</label><div class="value">' + (task.episode_name || '-') + '</div></div>';
                html += '<div class="info-item"><label>提取方式</label><div class="value">' + (task.subtitle_extract_type === 'vision' ? '画面识别' : task.subtitle_extract_type === 'audio' ? '音频识别' : task.subtitle_extract_type || '-') + '</div></div>';
                html += '<div class="info-item"><label>COS 状态</label><div class="value">' + (task.cos_status || '-') + '</div></div>';
                html += '<div class="info-item"><label>创建时间</label><div class="value">' + formatTime(task.create_time) + '</div></div>';
                html += '</div></div>';
                
                html += '<div class="table-section"><div class="table-header">🔗 请求日志 <span style="font-weight:normal;font-size:13px;opacity:0.8">(' + logs.length + ')</span></div>';
                if (logs.length === 0) { html += '<div class="no-data"><div class="no-data-icon">📭</div>暂无请求日志</div>'; }
                else {
                    html += '<div class="table-container"><table><thead><tr>';
                    html += '<th>模块</th><th>请求 URL</th><th>失败类型</th><th>开始时间</th><th>结束时间</th><th>耗时</th><th>操作</th>';
                    html += '</tr></thead><tbody>';
                    logs.forEach((log, idx) => {
                        html += '<tr>';
                        html += '<td>' + (log.module_name || '-') + '</td>';
                        html += '<td>' + truncate(log.request_url || '-', 40) + '</td>';
                        html += '<td>' + (log.fail_type || '-') + '</td>';
                        html += '<td>' + formatTime(log.begin_time) + '</td>';
                        html += '<td>' + formatTime(log.end_time) + '</td>';
                        html += '<td>' + formatDuration(log.duration_ms) + '</td>';
                        html += '<td>';
                        html += '<button class="view-btn" onclick="viewReq(' + idx + ')">请求</button> ';
                        html += '<button class="view-btn" onclick="viewRes(' + idx + ')">响应</button>';
                        html += '</td>';
                        html += '</tr>';
                    });
                    html += '</tbody></table></div>';
                }
                html += '</div>';
                
                // 绑定查看请求/响应的函数
                window.viewReq = function(idx) {
                    const log = logs[idx];
                    viewJson('请求 Body', log.request_body);
                };
                window.viewRes = function(idx) {
                    const log = logs[idx];
                    viewJson('响应 Body', log.response_body);
                };
                
                document.getElementById('content').innerHTML = html;
                document.title = 'MPS 任务详情 - ' + (task.episode_name || task.task_id);
            } catch (err) {
                console.error('Load detail error:', err);
                document.getElementById('content').innerHTML = '<div class="error-msg">❌ 加载失败：' + err.message + '</div>';
            }
        }
        
        // 侧边栏切换
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
            
            toggle.addEventListener('click', function() {
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed-margin');
                toggleIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() { loadDetail(); setupSidebarToggle(); });
    </script>
</body>
</html>
"""
