#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器监控模块 - Web API 服务
实时监控服务器关键指标：CPU、内存、硬盘、网络流量、系统信息

使用方式：
1. 作为独立模块运行：python server_monitor.py
2. 集成到 video_task_dashboard.py：from server_monitor import register_server_monitor_routes
"""

from flask import jsonify
import psutil
import time
import os
import sys
from datetime import datetime
from collections import deque
import threading

# 历史数据存储（最近 10 分钟，每 3 秒一次，约 200 个点）
MAX_HISTORY_POINTS = 200
history_data = {
    'cpu': deque(maxlen=MAX_HISTORY_POINTS),
    'memory': deque(maxlen=MAX_HISTORY_POINTS),
    'network': deque(maxlen=MAX_HISTORY_POINTS),
    'timestamps': deque(maxlen=MAX_HISTORY_POINTS)
}

# 后台数据收集线程
data_collection_running = False
data_collection_thread = None

def collect_data():
    """后台收集数据"""
    global data_collection_running
    while data_collection_running:
        try:
            timestamp = datetime.now().isoformat()
            
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用
            mem = psutil.virtual_memory()
            
            # 网络流量
            net = psutil.net_io_counters()
            
            # 存储历史数据
            history_data['cpu'].append(cpu_percent)
            history_data['memory'].append(mem.percent)
            history_data['network'].append({
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv
            })
            history_data['timestamps'].append(timestamp)
            
            time.sleep(3)  # 每 3 秒收集一次
        except Exception as e:
            print(f"Data collection error: {e}")
            time.sleep(3)

def start_data_collection():
    """启动后台数据收集"""
    global data_collection_running, data_collection_thread
    if not data_collection_running:
        data_collection_running = True
        data_collection_thread = threading.Thread(target=collect_data, daemon=True)
        data_collection_thread.start()
        print("Server monitor data collection started")

def get_system_info():
    """获取系统信息"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            'os_name': psutil.system_description(),
            'os_platform': psutil.platform(),
            'hostname': psutil.hostname(),
            'cpu_model': psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A',
            'cpu_cores': psutil.cpu_count(logical=True),
            'cpu_cores_physical': psutil.cpu_count(logical=False),
            'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0]
        }
    except Exception as e:
        print(f"Get system info error: {e}")
        return None

def get_cpu_info():
    """获取 CPU 信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_freq = psutil.cpu_freq()
        per_cpu_percent = psutil.cpu_percent(percpu=True)
        
        return {
            'usage_percent': cpu_percent,
            'frequency_current': cpu_freq.current if cpu_freq else 0,
            'frequency_max': cpu_freq.max if cpu_freq else 0,
            'cores_logical': psutil.cpu_count(logical=True),
            'cores_physical': psutil.cpu_count(logical=False),
            'per_cpu_usage': per_cpu_percent
        }
    except Exception as e:
        print(f"Get CPU info error: {e}")
        return None

def get_memory_info():
    """获取内存信息"""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }
    except Exception as e:
        print(f"Get memory info error: {e}")
        return None

def get_disk_info():
    """获取硬盘信息"""
    try:
        partitions = psutil.disk_partitions()
        disk_usage = []
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        
        return disk_usage
    except Exception as e:
        print(f"Get disk info error: {e}")
        return []

def get_network_info():
    """获取网络信息"""
    try:
        net = psutil.net_io_counters()
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        interfaces = {}
        for iface, addrs in net_if_addrs.items():
            stats = net_if_stats.get(iface)
            interfaces[iface] = {
                'is_up': stats.isup if stats else False,
                'speed': stats.speed if stats else 0,
                'addresses': [
                    {
                        'family': addr.family.name,
                        'address': addr.address,
                        'netmask': addr.netmask
                    }
                    for addr in addrs
                    if addr.family.name in ['AF_INET', 'AF_INET6']
                ]
            }
        
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv,
            'errin': net.errin,
            'errout': net.errout,
            'dropin': net.dropin,
            'dropout': net.dropout,
            'interfaces': interfaces
        }
    except Exception as e:
        print(f"Get network info error: {e}")
        return None

def format_bytes(bytes_value):
    """格式化字节数为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

# 服务器监控页面 HTML
SERVER_MONITOR_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>服务器监控 - 视频任务运维系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        .navbar-version { font-size: 11px; color: var(--text-secondary); margin-top: 4px; white-space: nowrap; transition: opacity 0.2s; }
        .sidebar-menu { flex: 1; padding: 16px 12px; }
        .menu-section { color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 12px; margin-bottom: 8px; margin-top: 8px; }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; color: var(--text-secondary); text-decoration: none; transition: all 0.2s; margin-bottom: 4px; cursor: pointer; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(29, 78, 216, 0.1) 100%); color: var(--primary); border: 1px solid rgba(37, 99, 235, 0.3); }
        .menu-item .icon { font-size: 18px; width: 24px; text-align: center; }
        .menu-item .label { flex: 1; font-size: 14px; font-weight: 500; }
        .menu-badge { background: var(--danger); color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; }
        .main-content { padding: 24px 30px; flex: 1; }
        .page-header { margin-bottom: 24px; }
        .page-header h1 { font-size: 24px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 12px; }
        .last-update { color: var(--text-secondary); font-size: 13px; margin-top: 8px; display: flex; align-items: center; gap: 8px; }
        .update-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); border-color: var(--primary); }
        .stat-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .stat-card-title { color: var(--text-secondary); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }
        .stat-card-icon { font-size: 28px; }
        .stat-card-value { font-size: 32px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
        .stat-card-detail { color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
        .stat-card.cpu .stat-card-value { color: #3b82f6; }
        .stat-card.memory .stat-card-value { color: #8b5cf6; }
        .stat-card.disk .stat-card-value { color: #059669; }
        .stat-card.network .stat-card-value { color: #d97706; }
        .charts-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 24px; }
        .chart-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .chart-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
        .chart-container { position: relative; height: 250px; }
        .info-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; }
        .info-header { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .info-item { background: var(--bg-dark); padding: 16px; border-radius: 10px; border: 1px solid var(--border); }
        .info-item-label { color: var(--text-secondary); font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .info-item-value { color: var(--text-primary); font-size: 15px; font-weight: 600; }
        .disk-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        .disk-table th, .disk-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        .disk-table th { background: rgba(37, 99, 235, 0.1); font-weight: 600; color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        .disk-table tr:hover { background: var(--bg-hover); }
        .progress-bar { background: var(--bg-dark); border-radius: 10px; height: 8px; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 10px; transition: width 0.3s; }
        .progress-fill.low { background: var(--success); }
        .progress-fill.medium { background: var(--warning); }
        .progress-fill.high { background: var(--danger); }
        .network-interface { background: var(--bg-dark); padding: 16px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 12px; }
        .network-interface-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .network-interface-name { font-weight: 600; color: var(--text-primary); }
        .network-interface-status { font-size: 12px; padding: 4px 10px; border-radius: 10px; }
        .network-interface-status.up { background: rgba(5, 150, 105, 0.15); color: var(--success); }
        .network-interface-status.down { background: rgba(220, 38, 38, 0.15); color: var(--danger); }
        .network-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .network-stat { font-size: 13px; color: var(--text-secondary); }
        .network-stat-value { color: var(--text-primary); font-weight: 600; margin-top: 4px; }
        .auto-refresh { display: flex; align-items: center; gap: 10px; background: var(--bg-dark); padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border); }
        .auto-refresh label { color: var(--text-secondary); font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 8px; }
        .auto-refresh input[type="checkbox"] { accent-color: var(--primary); }
        .error-msg { background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); color: #f87171; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
        @media (max-width: 1200px) { .charts-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-logo"><div class="logo-icon">📊</div><div><h1>运维系统</h1><div class="navbar-version">v1.0.0 by yiyuzhou</div></div>
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
            <a href="/server-monitor" class="menu-item active" data-page="server-monitor">
                <span class="icon">🖥️</span>
                <span class="label">服务器监控</span>
            </a>
            <a href="/db-monitor" class="menu-item" data-page="db-monitor">
                <span class="icon">🗄️</span>
                <span class="label">数据库监控</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings">
                <span class="icon">⚙️</span>
                <span class="label">系统设置</span>
            </a>
        </nav>
    </aside>
    <div class="main-wrapper">
        <div class="main-content">
            <div class="page-header">
                <h1>🖥️ 服务器监控</h1>
                <div class="last-update">
                    <span class="update-dot"></span>
                    最后更新：<span id="lastUpdate">-</span>
                    <div class="auto-refresh" style="margin-left: 16px;">
                        <label><input type="checkbox" id="autoRefresh" checked>自动刷新</label>
                        <span id="countdown" style="margin-left: 8px; color: var(--text-secondary); font-size: 13px;">3s</span>
                    </div>
                </div>
            </div>
            <div class="stats-grid">
                <div class="stat-card cpu">
                    <div class="stat-card-header">
                        <span class="stat-card-title">CPU 使用率</span>
                        <span class="stat-card-icon">🔵</span>
                    </div>
                    <div class="stat-card-value" id="cpuValue">-</div>
                    <div class="stat-card-detail">
                        <div>核心数：<span id="cpuCores">-</span></div>
                        <div>频率：<span id="cpuFreq">-</span> MHz</div>
                    </div>
                </div>
                <div class="stat-card memory">
                    <div class="stat-card-header">
                        <span class="stat-card-title">内存使用</span>
                        <span class="stat-card-icon">🟣</span>
                    </div>
                    <div class="stat-card-value" id="memoryValue">-</div>
                    <div class="stat-card-detail">
                        <div>总计：<span id="memoryTotal">-</span></div>
                        <div>可用：<span id="memoryAvailable">-</span></div>
                    </div>
                </div>
                <div class="stat-card disk">
                    <div class="stat-card-header">
                        <span class="stat-card-title">硬盘使用</span>
                        <span class="stat-card-icon">🟢</span>
                    </div>
                    <div class="stat-card-value" id="diskValue">-</div>
                    <div class="stat-card-detail">
                        <div>分区数：<span id="diskPartitions">-</span></div>
                        <div>系统盘：<span id="systemDisk">-</span></div>
                    </div>
                </div>
                <div class="stat-card network">
                    <div class="stat-card-header">
                        <span class="stat-card-title">网络流量</span>
                        <span class="stat-card-icon">🟡</span>
                    </div>
                    <div class="stat-card-value" id="networkValue">-</div>
                    <div class="stat-card-detail">
                        <div>上传：<span id="networkSent">-</span></div>
                        <div>下载：<span id="networkRecv">-</span></div>
                    </div>
                </div>
            </div>
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">📈 CPU 使用率趋势（最近 10 分钟）</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="cpuChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">📊 内存使用率趋势（最近 10 分钟）</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="memoryChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">🥧 硬盘分区使用率</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="diskChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-header">
                        <span class="chart-title">📡 网络流量趋势（最近 10 分钟）</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="networkChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-header">💻 系统信息</div>
                <div class="info-grid" id="systemInfo">
                    <div class="info-item">
                        <div class="info-item-label">操作系统</div>
                        <div class="info-item-value" id="osName">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">主机名</div>
                        <div class="info-item-value" id="hostname">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">运行时间</div>
                        <div class="info-item-value" id="uptime">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">CPU 型号</div>
                        <div class="info-item-value" id="cpuModel">-</div>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-header">💾 硬盘分区详情</div>
                <div id="diskDetails"></div>
            </div>
            <div class="info-section">
                <div class="info-header">🌐 网络接口详情</div>
                <div id="networkDetails"></div>
            </div>
        </div>
    </div>
    <script>
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = '#334155';
        let cpuChart, memoryChart, diskChart, networkChart;
        let autoRefreshTimer = null;
        let countdownTimer = null;
        let countdownSeconds = 3;
        let lastNetworkData = null;
        function initCharts() {
            const cpuCtx = document.getElementById('cpuChart').getContext('2d');
            cpuChart = new Chart(cpuCtx, {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'CPU 使用率 (%)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.4, pointRadius: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: true, grid: { display: false } }, y: { display: true, min: 0, max: 100, grid: { color: '#334155' } } }, animation: { duration: 0 } }
            });
            const memCtx = document.getElementById('memoryChart').getContext('2d');
            memoryChart = new Chart(memCtx, {
                type: 'line',
                data: { labels: [], datasets: [{ label: '内存使用率 (%)', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', fill: true, tension: 0.4, pointRadius: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: true, grid: { display: false } }, y: { display: true, min: 0, max: 100, grid: { color: '#334155' } } }, animation: { duration: 0 } }
            });
            const diskCtx = document.getElementById('diskChart').getContext('2d');
            diskChart = new Chart(diskCtx, {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], backgroundColor: ['#059669', '#d97706', '#dc2626', '#3b82f6', '#8b5cf6'], borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
            });
            const netCtx = document.getElementById('networkChart').getContext('2d');
            networkChart = new Chart(netCtx, {
                type: 'line',
                data: { labels: [], datasets: [
                    { label: '上传 (KB/s)', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                    { label: '下载 (KB/s)', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.4, pointRadius: 0 }
                ] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true } }, scales: { x: { display: true, grid: { display: false } }, y: { display: true, grid: { color: '#334155' } } }, animation: { duration: 0 } }
            });
        }
        function formatBytes(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let i = 0;
            while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
            return bytes.toFixed(2) + ' ' + units[i];
        }
        function updateCharts(data) {
            const timestamps = data.history_timestamps || [];
            const cpuHistory = data.history_cpu || [];
            const memoryHistory = data.history_memory || [];
            const networkHistory = data.history_network || [];
            const labels = timestamps.map(ts => { try { const d = new Date(ts); return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0') + ':' + d.getSeconds().toString().padStart(2, '0'); } catch(e) { return ts; } });
            cpuChart.data.labels = labels; cpuChart.data.datasets[0].data = cpuHistory; cpuChart.update();
            memoryChart.data.labels = labels; memoryChart.data.datasets[0].data = memoryHistory; memoryChart.update();
            const diskUsage = data.disk || [];
            if (diskUsage.length > 0) { diskChart.data.labels = diskUsage.map(d => d.mountpoint); diskChart.data.datasets[0].data = diskUsage.map(d => d.percent); diskChart.update(); }
            if (networkHistory.length > 0 && lastNetworkData) {
                const uploadSpeeds = []; const downloadSpeeds = [];
                for (let i = 1; i < networkHistory.length; i++) {
                    const prev = networkHistory[i - 1]; const curr = networkHistory[i];
                    const uploadSpeed = (curr.bytes_sent - prev.bytes_sent) / 3 / 1024;
                    const downloadSpeed = (curr.bytes_recv - prev.bytes_recv) / 3 / 1024;
                    uploadSpeeds.push(uploadSpeed); downloadSpeeds.push(downloadSpeed);
                }
                networkChart.data.labels = labels.slice(1);
                networkChart.data.datasets[0].data = uploadSpeeds;
                networkChart.data.datasets[1].data = downloadSpeeds;
                networkChart.update();
            }
        }
        function updateUI(data) {
            if (data.cpu) {
                document.getElementById('cpuValue').textContent = data.cpu.usage_percent.toFixed(1) + '%';
                document.getElementById('cpuCores').textContent = data.cpu.cores_logical;
                document.getElementById('cpuFreq').textContent = data.cpu.frequency_current.toFixed(0);
            }
            if (data.memory) {
                document.getElementById('memoryValue').textContent = data.memory.percent.toFixed(1) + '%';
                document.getElementById('memoryTotal').textContent = formatBytes(data.memory.total);
                document.getElementById('memoryAvailable').textContent = formatBytes(data.memory.available);
            }
            if (data.disk && data.disk.length > 0) {
                const totalPercent = data.disk.reduce((sum, d) => sum + d.percent, 0) / data.disk.length;
                document.getElementById('diskValue').textContent = totalPercent.toFixed(1) + '%';
                document.getElementById('diskPartitions').textContent = data.disk.length;
                document.getElementById('systemDisk').textContent = formatBytes(data.disk[0].used) + ' / ' + formatBytes(data.disk[0].total);
            }
            if (data.network) {
                document.getElementById('networkValue').textContent = formatBytes(data.network.bytes_sent) + ' ↑ / ' + formatBytes(data.network.bytes_recv) + ' ↓';
                document.getElementById('networkSent').textContent = formatBytes(data.network.bytes_sent);
                document.getElementById('networkRecv').textContent = formatBytes(data.network.bytes_recv);
            }
            if (data.system_info) {
                document.getElementById('osName').textContent = data.system_info.os_name || '-';
                document.getElementById('hostname').textContent = data.system_info.hostname || '-';
                document.getElementById('uptime').textContent = data.system_info.uptime_formatted || '-';
                document.getElementById('cpuModel').textContent = data.system_info.cpu_model || '-';
            }
            if (data.disk && data.disk.length > 0) {
                let diskHtml = '<table class="disk-table"><thead><tr><th>分区</th><th>挂载点</th><th>文件系统</th><th>总容量</th><th>已用</th><th>可用</th><th>使用率</th></tr></thead><tbody>';
                data.disk.forEach(d => {
                    const progressClass = d.percent < 70 ? 'low' : (d.percent < 90 ? 'medium' : 'high');
                    diskHtml += '<tr><td>' + (d.device || '-') + '</td><td>' + (d.mountpoint || '-') + '</td><td>' + (d.fstype || '-') + '</td><td>' + formatBytes(d.total) + '</td><td>' + formatBytes(d.used) + '</td><td>' + formatBytes(d.free) + '</td><td><div style="display:flex;align-items:center;gap:8px"><div class="progress-bar" style="width:100px"><div class="progress-fill ' + progressClass + '" style="width:' + d.percent + '%"></div></div><span>' + d.percent.toFixed(1) + '%</span></div></td></tr>';
                });
                diskHtml += '</tbody></table>';
                document.getElementById('diskDetails').innerHTML = diskHtml;
            }
            if (data.network && data.network.interfaces) {
                let netHtml = '';
                for (const [name, iface] of Object.entries(data.network.interfaces)) {
                    const statusClass = iface.is_up ? 'up' : 'down';
                    const statusText = iface.is_up ? '运行中' : '已断开';
                    netHtml += '<div class="network-interface"><div class="network-interface-header"><span class="network-interface-name">' + name + '</span><span class="network-interface-status ' + statusClass + '">' + statusText + '</span></div><div class="network-stats">';
                    if (iface.speed > 0) { netHtml += '<div class="network-stat"><div>链路速度</div><div class="network-stat-value">' + (iface.speed / 1000).toFixed(0) + ' Mbps</div></div>'; }
                    if (iface.addresses && iface.addresses.length > 0) {
                        const ipAddr = iface.addresses.find(a => a.family === 'AF_INET');
                        if (ipAddr) { netHtml += '<div class="network-stat"><div>IP 地址</div><div class="network-stat-value">' + ipAddr.address + '</div></div>'; }
                    }
                    netHtml += '</div></div>';
                }
                document.getElementById('networkDetails').innerHTML = netHtml || '<div style="color:var(--text-secondary);text-align:center;padding:20px">暂无网络接口信息</div>';
            }
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
        }
        async function loadData() {
            try {
                const res = await fetch('/api/server/metrics?t=' + Date.now());
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Unknown error');
                updateUI(data);
                updateCharts(data);
                lastNetworkData = data.network;
                if (document.getElementById('autoRefresh').checked) { countdownSeconds = 3; }
            } catch (err) { console.error('Load data error:', err); }
        }
        function setupAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            const countdownEl = document.getElementById('countdown');
            function updateCountdown() { countdownEl.textContent = countdownSeconds + 's'; countdownEl.style.color = countdownSeconds <= 1 ? 'var(--warning)' : 'var(--text-secondary)'; }
            function startCountdown() { countdownSeconds = 3; updateCountdown(); if (countdownTimer) clearInterval(countdownTimer); countdownTimer = setInterval(() => { countdownSeconds--; if (countdownSeconds <= 0) countdownSeconds = 3; updateCountdown(); }, 1000); }
            function start() { if (autoRefreshTimer) clearInterval(autoRefreshTimer); autoRefreshTimer = setInterval(() => { loadData(); countdownSeconds = 3; updateCountdown(); }, 3000); startCountdown(); }
            function stop() { if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; } if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; } countdownEl.textContent = '--'; }
            checkbox.addEventListener('change', function() { if (this.checked) start(); else stop(); });
            start();
        }
        document.addEventListener('DOMContentLoaded', function() { initCharts(); loadData(); setupAutoRefresh(); });
    </script>
</body>
</html>
"""

def register_server_monitor_routes(app):
    """注册服务器监控路由到 Flask 应用"""
    
    @app.route('/server-monitor')
    def server_monitor_page():
        """服务器监控页面"""
        from flask import render_template_string
        return render_template_string(SERVER_MONITOR_TEMPLATE)
    
    @app.route('/api/server/metrics')
    def server_metrics_api():
        """获取所有监控指标"""
        from flask import jsonify
        try:
            cpu_info = get_cpu_info()
            memory_info = get_memory_info()
            disk_info = get_disk_info()
            network_info = get_network_info()
            system_info = get_system_info()
            
            with threading.Lock():
                history_cpu = list(history_data['cpu'])
                history_memory = list(history_data['memory'])
                history_network = list(history_data['network'])
                history_timestamps = list(history_data['timestamps'])
            
            return jsonify({
                'success': True,
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'system_info': system_info,
                'history_cpu': history_cpu,
                'history_memory': history_memory,
                'history_network': history_network,
                'history_timestamps': history_timestamps,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"API /api/server/metrics error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/server/history')
    def server_history_api():
        """获取历史数据"""
        from flask import jsonify
        try:
            with threading.Lock():
                history_cpu = list(history_data['cpu'])
                history_memory = list(history_data['memory'])
                history_network = list(history_data['network'])
                history_timestamps = list(history_data['timestamps'])
            
            return jsonify({
                'success': True,
                'cpu': history_cpu,
                'memory': history_memory,
                'network': history_network,
                'timestamps': history_timestamps
            })
        except Exception as e:
            print(f"API /api/server/history error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

# 独立运行时启动
if __name__ == '__main__':
    from flask import Flask
    from flask_cors import CORS
    
    monitor_app = Flask(__name__)
    CORS(monitor_app)
    
    # 注册路由
    register_server_monitor_routes(monitor_app)
    
    # 启动数据收集
    start_data_collection()
    
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting server monitor: http://localhost:{port}/server-monitor", file=sys.stderr)
    sys.stdout.flush()
    monitor_app.run(host='0.0.0.0', port=port, debug=False)
