#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置模块 - 数据源配置管理
"""

import json
import os
import base64
from flask import render_template_string, jsonify, request
import mysql.connector
import paramiko

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'database.json')

# 默认配置
DEFAULT_CONFIG = {
    "active_profile": "default",
    "profiles": {
        "default": {
            "name": "默认配置",
            "video": {
                "host": "101.126.91.130",
                "port": 4005,
                "database": "videoai",
                "user": "yiyuzhou",
                "password": ""  # 加密存储
            },
            "ssh_config": {
                "hostname": "101.126.91.130",
                "port": 22,
                "username": "ubuntu",
                "password": "",  # 加密存储
                "log_dir": "/home/ubuntu/workspace/logs/translator"
            }
        }
    }
}


def encode_password(password):
    """Base64 加密密码"""
    if not password:
        return ""
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')


def decode_password(encoded):
    """Base64 解密密码"""
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
    except Exception:
        return encoded  # 如果解密失败，返回原值（可能是未加密的）


def load_config():
    """加载配置文件（支持旧配置自动迁移）"""
    if not os.path.exists(CONFIG_FILE):
        # 创建默认配置
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保结构完整
        if "profiles" not in config:
            config["profiles"] = DEFAULT_CONFIG["profiles"]
        if "active_profile" not in config:
            config["active_profile"] = "default"
        
        # 向后兼容迁移：如果存在全局 ssh_config，迁移到每个 profile
        global_ssh = config.get("ssh_config", {})
        if global_ssh and global_ssh.get("hostname"):
            print("[配置迁移] 检测到旧版全局 ssh_config，正在迁移到各 profile...")
            for profile_name, profile in config["profiles"].items():
                if "ssh_config" not in profile or not profile["ssh_config"].get("hostname"):
                    profile["ssh_config"] = {
                        "hostname": global_ssh.get("hostname", ""),
                        "port": global_ssh.get("port", 22),
                        "username": global_ssh.get("username", ""),
                        "password": global_ssh.get("password", ""),
                        "log_dir": global_ssh.get("log_dir", "")
                    }
            # 迁移完成后保存
            save_config(config)
            print("[配置迁移] 迁移完成，全局 ssh_config 已保留用于兼容")
        
        return config
    except Exception as e:
        print(f"Load config error: {e}")
        return DEFAULT_CONFIG


def save_config(config):
    """保存配置文件"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return True


def merge_profile_config(existing_config, incoming_config):
    """合并配置，避免前端空密码覆盖已有密码"""
    existing_profiles = existing_config.get("profiles", {}) if existing_config else {}
    incoming_profiles = incoming_config.get("profiles", {}) if incoming_config else {}
    merged_profiles = {}

    for profile_name, incoming_profile in incoming_profiles.items():
        existing_profile = existing_profiles.get(profile_name, {})
        merged_profile = dict(existing_profile)
        merged_profile.update(incoming_profile or {})

        existing_video = existing_profile.get("video", {})
        incoming_video = (incoming_profile or {}).get("video", {})
        merged_video = dict(existing_video)
        merged_video.update(incoming_video)
        if not incoming_video.get("password"):
            merged_video["password"] = existing_video.get("password", "")
        merged_profile["video"] = merged_video

        existing_ssh = existing_profile.get("ssh_config", {})
        incoming_ssh = (incoming_profile or {}).get("ssh_config", {})
        merged_ssh = dict(existing_ssh)
        merged_ssh.update(incoming_ssh)
        if not incoming_ssh.get("password"):
            merged_ssh["password"] = existing_ssh.get("password", "")
        merged_profile["ssh_config"] = merged_ssh

        merged_profiles[profile_name] = merged_profile

    temp_config = {"profiles": merged_profiles}
    for profile_name, profile in merged_profiles.items():
        video = profile.get("video", {})
        if video.get("host") and not video.get("password"):
            recovered_password = _find_matching_video_password(temp_config, profile_name, video)
            if recovered_password:
                profile["video"]["password"] = recovered_password

    merged_config = {
        "active_profile": incoming_config.get("active_profile") or existing_config.get("active_profile", "default"),
        "profiles": merged_profiles
    }

    if "ssh_config" in existing_config:
        merged_config["ssh_config"] = existing_config["ssh_config"]

    return merged_config


def _find_matching_video_password(config, current_profile_name, video_config):
    """当当前 profile 缺少密码时，尝试从相同数据源的其他 profile 复用密码"""
    if not video_config:
        return ""

    for profile_name, profile in config.get("profiles", {}).items():
        if profile_name == current_profile_name:
            continue

        candidate = profile.get("video", {})
        if not candidate.get("password"):
            continue

        same_source = (
            candidate.get("host") == video_config.get("host") and
            candidate.get("port", 3306) == video_config.get("port", 3306) and
            candidate.get("database") == video_config.get("database") and
            candidate.get("user") == video_config.get("user")
        )
        if same_source:
            print(f"[配置恢复] profile '{current_profile_name}' 缺少 video 密码，复用 '{profile_name}' 的同源密码")
            return candidate.get("password", "")

    return ""


def get_video_db_config_for_profile(profile_name=None):
    """获取指定 profile 的视频任务数据库配置（内部译制和腾讯 MPS 共用）"""
    config = load_config()
    actual_profile_name = profile_name or config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(actual_profile_name, config.get("profiles", {}).get("default"))

    if not profile:
        return None

    # 优先使用新的 video 配置
    video = profile.get("video", {})
    if video and video.get("host"):
        encoded_password = video.get("password", "")
        if not encoded_password:
            encoded_password = _find_matching_video_password(config, actual_profile_name, video)
        return {
            'host': video.get('host', 'localhost'),
            'port': video.get('port', 3306),
            'database': video.get('database', ''),
            'user': video.get('user', ''),
            'password': decode_password(encoded_password),
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'connection_timeout': 5
        }

    # 向后兼容：如果旧配置存在，自动迁移提示
    internal = profile.get("internal", {})
    if internal and internal.get("host"):
        print("[配置迁移提示] 检测到旧版 internal 配置，已自动使用。建议更新为统一的 video 配置。")
        return {
            'host': internal.get('host', 'localhost'),
            'port': internal.get('port', 3306),
            'database': internal.get('database', ''),
            'user': internal.get('user', ''),
            'password': decode_password(internal.get('password', '')),
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'connection_timeout': 5
        }

    # 最后尝试 mps 配置（向后兼容）
    mps = profile.get("mps", {})
    if mps and mps.get("host"):
        print("[配置迁移提示] 检测到旧版 mps 配置，已自动使用。建议更新为统一的 video 配置。")
        return {
            'host': mps.get('host', 'localhost'),
            'port': mps.get('port', 3306),
            'database': mps.get('database', ''),
            'user': mps.get('user', ''),
            'password': decode_password(mps.get('password', '')),
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'connection_timeout': 5
        }

    return None


def get_active_config():
    """获取当前激活的配置"""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(profile_name, config.get("profiles", {}).get("default"))
    return profile


def get_video_db_config():
    """获取视频任务数据库配置（内部译制和腾讯 MPS 共用）"""
    return get_video_db_config_for_profile()


def get_internal_db_config():
    """获取内部译制数据库配置（已废弃，使用 get_video_db_config 代替）"""
    print("[警告] get_internal_db_config 已废弃，请使用 get_video_db_config")
    return get_video_db_config()


def get_mps_db_config():
    """获取腾讯 MPS 数据库配置（已废弃，使用 get_video_db_config 代替）"""
    print("[警告] get_mps_db_config 已废弃，请使用 get_video_db_config")
    return get_video_db_config()


def get_ssh_config():
    """获取 SSH 配置（从当前激活的 profile 中获取）"""
    config = load_config()
    profile_name = config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(profile_name, config.get("profiles", {}).get("default"))
    
    if not profile:
        return {
            'hostname': '',
            'port': 22,
            'username': '',
            'password': '',
            'log_dir': ''
        }
    
    # 从 profile 中获取 ssh_config
    ssh_config = profile.get("ssh_config", {})
    
    # 向后兼容：如果 profile 中没有 ssh_config，尝试从全局获取
    if not ssh_config.get("hostname"):
        global_ssh = config.get("ssh_config", {})
        if global_ssh.get("hostname"):
            print("[配置迁移提示] 检测到旧版全局 ssh_config 配置，已自动使用。建议更新为 profile 内的 ssh_config。")
            ssh_config = global_ssh
    
    return {
        'hostname': ssh_config.get('hostname', ''),
        'port': ssh_config.get('port', 22),
        'username': ssh_config.get('username', ''),
        'password': decode_password(ssh_config.get('password', '')),
        'log_dir': ssh_config.get('log_dir', '')
    }


def save_ssh_config(ssh_config, profile_name=None):
    """保存 SSH 配置到指定的 profile（或当前激活的 profile）"""
    config = load_config()
    
    # 如果没有指定 profile，使用当前激活的 profile
    if profile_name is None:
        profile_name = config.get("active_profile", "default")
    
    # 确保 profiles 存在
    if "profiles" not in config:
        config["profiles"] = {}
    
    # 确保当前 profile 存在
    if profile_name not in config["profiles"]:
        config["profiles"][profile_name] = {"name": profile_name, "video": {}}
    
    # 保存 ssh_config 到当前 profile
    config["profiles"][profile_name]["ssh_config"] = {
        'hostname': ssh_config.get('hostname', ''),
        'port': ssh_config.get('port', 22),
        'username': ssh_config.get('username', ''),
        'password': encode_password(ssh_config.get('password', '')),
        'log_dir': ssh_config.get('log_dir', '')
    }
    
    # 向后兼容：同时保留全局 ssh_config（如果存在）
    # 新代码不再使用全局 ssh_config，但保留以兼容旧版本
    
    save_config(config)
    return True


def test_db_connection(db_config):
    """测试数据库连接"""
    try:
        conn = mysql.connector.connect(**db_config)
        conn.close()
        return {'success': True, 'message': '连接成功'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def test_ssh_connection(ssh_config):
    """测试 SSH 连接"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ssh_config.get('hostname', ''),
            port=ssh_config.get('port', 22),
            username=ssh_config.get('username', ''),
            password=ssh_config.get('password', ''),
            timeout=10
        )
        
        # 测试日志目录是否存在
        log_dir = ssh_config.get('log_dir', '')
        if log_dir:
            stdin, stdout, stderr = client.exec_command(f"test -d '{log_dir}' && echo 'exists' || echo 'not_exists'")
            dir_check = stdout.read().decode('utf-8').strip()
            if dir_check != 'exists':
                client.close()
                return {'success': False, 'message': f'日志目录不存在：{log_dir}'}
        
        client.close()
        return {'success': True, 'message': 'SSH 连接成功，日志目录可访问'}
    except paramiko.AuthenticationException:
        return {'success': False, 'message': 'SSH 认证失败：用户名或密码错误'}
    except paramiko.SSHException as e:
        return {'success': False, 'message': f'SSH 连接错误：{str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'连接失败：{str(e)}'}


# 设置页面 HTML 模板
SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统设置 - 视频任务运维系统</title>
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
        
        /* 主内容区 */
        .main-wrapper { flex: 1; margin-left: var(--sidebar-width); min-height: 100vh; display: flex; flex-direction: column; transition: margin-left 0.3s ease; }
        .sidebar.collapsed ~ .main-wrapper, .main-wrapper.collapsed-margin { margin-left: 64px; }
        .main-content { padding: 24px 30px; flex: 1; max-width: 1200px; }
        
        /* 设置页面样式 */
        .settings-header { margin-bottom: 24px; }
        .settings-header h1 { font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 12px; }
        .settings-header p { color: var(--text-secondary); margin-top: 8px; }
        
        .settings-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
        .settings-card h2 { font-size: 18px; font-weight: 600; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
        
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; color: var(--text-secondary); font-size: 13px; margin-bottom: 6px; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 10px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text-primary); font-size: 14px; transition: all 0.2s; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .form-group input::placeholder { color: var(--text-secondary); }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        
        .form-actions { display: flex; gap: 12px; margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border); }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .btn-success { background: linear-gradient(135deg, var(--success) 0%, #047857 100%); color: white; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        
        .profile-selector { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
        .profile-selector label { color: var(--text-secondary); font-size: 13px; }
        .profile-selector select { padding: 8px 14px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; color: var(--text-primary); font-size: 14px; min-width: 200px; }
        .profile-actions { display: flex; gap: 8px; }
        
        .toast { position: fixed; top: 20px; right: 20px; padding: 16px 24px; border-radius: 8px; color: white; font-weight: 500; z-index: 9999; transform: translateX(400px); transition: transform 0.3s ease; }
        .toast.show { transform: translateX(0); }
        .toast-success { background: var(--success); }
        .toast-error { background: var(--danger); }
        .toast-info { background: var(--info); }
        
        .connection-status { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; font-size: 13px; margin-left: 12px; }
        .connection-status.success { background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.3); }
        .connection-status.error { background: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); }
        .connection-status::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
        
        .section-divider { height: 1px; background: var(--border); margin: 24px 0; }
        
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    </style>
</head>
<body>
    <!-- 左侧菜单栏 -->
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
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item active" data-page="settings">
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
            <div class="settings-header">
                <h1>⚙️ 系统设置</h1>
                <p>配置数据库连接和数据源</p>
            </div>
            
            <!-- 配置管理 -->
            <div class="settings-card">
                <h2>📁 配置管理</h2>
                <div class="profile-selector">
                    <label>当前配置：</label>
                    <select id="profileSelect" onchange="switchProfile()">
                        <option value="default">默认配置</option>
                    </select>
                    <div class="profile-actions">
                        <button class="btn btn-secondary" onclick="newProfile()">➕ 新建配置</button>
                        <button class="btn btn-secondary" onclick="deleteProfile()" id="deleteProfileBtn" disabled>🗑️ 删除配置</button>
                    </div>
                </div>
            </div>
            
            <!-- 视频任务数据源（内部译制 & 腾讯 MPS 共用） -->
            <div class="settings-card">
                <h2>🎬 视频任务数据源 <span style="font-size:12px;color:var(--text-secondary);font-weight:normal;margin-left:10px;">（内部译制 & 腾讯 MPS 共用）</span></h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>MySQL 主机</label>
                        <input type="text" id="videoHost" placeholder="例如：101.126.91.130">
                    </div>
                    <div class="form-group">
                        <label>端口</label>
                        <input type="number" id="videoPort" placeholder="3306" value="3306">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>数据库名</label>
                        <input type="text" id="videoDatabase" placeholder="例如：videoai">
                    </div>
                    <div class="form-group">
                        <label>用户名</label>
                        <input type="text" id="videoUser" placeholder="例如：root">
                    </div>
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" id="videoPassword" placeholder="请输入数据库密码">
                </div>
                <div class="form-actions">
                    <button class="btn btn-success" onclick="testVideoConnection()">🔌 测试连接</button>
                    <span id="videoStatus" class="connection-status" style="display: none;"></span>
                </div>
            </div>
            
            <!-- 日志监控配置 -->
            <div class="settings-card">
                <h2>📋 日志监控配置</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>SSH 服务器 IP</label>
                        <input type="text" id="sshHost" placeholder="例如：101.126.91.130">
                    </div>
                    <div class="form-group">
                        <label>SSH 端口</label>
                        <input type="number" id="sshPort" placeholder="22" value="22">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>SSH 用户名</label>
                        <input type="text" id="sshUser" placeholder="例如：ubuntu">
                    </div>
                    <div class="form-group">
                        <label>SSH 密码</label>
                        <input type="password" id="sshPassword" placeholder="请输入 SSH 密码">
                    </div>
                </div>
                <div class="form-group">
                    <label>日志文件路径</label>
                    <input type="text" id="sshLogDir" placeholder="例如：/home/ubuntu/workspace/logs/translator">
                </div>
                <div class="form-actions">
                    <button class="btn btn-success" onclick="testSSHConnection()">🔌 测试连接</button>
                    <span id="sshStatus" class="connection-status" style="display: none;"></span>
                </div>
            </div>
            
            <!-- 保存按钮 -->
            <div class="settings-card">
                <div class="form-actions" style="border-top: none; padding-top: 0; margin-top: 0;">
                    <button class="btn btn-primary" onclick="saveSettings()">💾 保存配置</button>
                    <button class="btn btn-secondary" onclick="loadSettings()">🔄 重置</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast 提示 -->
    <div id="toast" class="toast"></div>
    
    <script>
        let currentConfig = null;
        let profiles = {};
        
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast toast-' + type + ' show';
            setTimeout(() => { toast.classList.remove('show'); }, 3000);
        }
        
        function showStatus(elementId, success, message) {
            const el = document.getElementById(elementId);
            el.style.display = 'inline-flex';
            el.className = 'connection-status ' + (success ? 'success' : 'error');
            el.textContent = message;
        }
        
        async function loadSettings() {
            try {
                console.log('[loadSettings] 开始加载配置...');
                const res = await fetch('/api/settings/config');
                const data = await res.json();
                
                console.log('[loadSettings] API 返回:', JSON.stringify(data, null, 2));
                
                if (!data.success) {
                    console.error('[loadSettings] API 返回错误:', data.error);
                    throw new Error(data.error);
                }
                
                currentConfig = data.config;
                profiles = data.profiles || {};
                
                console.log('[loadSettings] profiles 已加载:', Object.keys(profiles));
                console.log('[loadSettings] activeProfile:', data.activeProfile);
                
                // 更新配置选择器
                const profileSelect = document.getElementById('profileSelect');
                const previousValue = profileSelect.value;
                profileSelect.innerHTML = '';
                
                if (Object.keys(profiles).length === 0) {
                    console.error('[loadSettings] 错误：profiles 为空!');
                    showToast('配置列表为空，请检查后端配置', 'error');
                    return;
                }
                
                Object.keys(profiles).forEach(name => {
                    const option = document.createElement('option');
                    option.value = name;
                    option.textContent = profiles[name].name || name;
                    profileSelect.appendChild(option);
                    console.log('[loadSettings] 添加选项:', name, '->', profiles[name].name);
                });
                
                // 设置选中值
                const activeProfile = data.activeProfile || 'default';
                console.log('[loadSettings] 设置选中值:', activeProfile);
                profileSelect.value = activeProfile;
                
                // 验证选中值是否成功设置
                if (profileSelect.value !== activeProfile) {
                    console.error('[loadSettings] 警告：选中值设置失败，期望:', activeProfile, '实际:', profileSelect.value);
                }
                
                document.getElementById('deleteProfileBtn').disabled = Object.keys(profiles).length <= 1;
                
                // 填充表单 - 同时加载 video 和 ssh_config
                const loaded = loadProfileData(activeProfile);
                console.log('[loadSettings] 配置加载结果:', loaded ? '成功' : '失败');
                
                if (!loaded) {
                    console.error('[loadSettings] loadProfileData 失败，但继续执行');
                }
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');
            } catch (err) {
                console.error('[loadSettings] 加载配置错误:', err);
                showToast('加载配置失败：' + err.message, 'error');
            }
        }
        
        // 加载指定 profile 的数据到表单，返回是否成功
        function loadProfileData(profileName) {
            console.log('[loadProfileData] 开始加载配置:', profileName);
            console.log('[loadProfileData] 当前 profiles 对象:', Object.keys(profiles));
            
            const profile = profiles[profileName];
            
            if (!profile) {
                console.error('[loadProfileData] 错误：找不到配置 "' + profileName + '"');
                console.error('[loadProfileData] 可用配置:', Object.keys(profiles));
                showToast('加载配置失败：找不到配置 "' + profileName + '"', 'error');
                return false;
            }
            
            console.log('[loadProfileData] 找到配置:', profile.name);
            console.log('[loadProfileData] 配置结构:', JSON.stringify({
                hasVideo: !!profile.video,
                hasSshConfig: !!profile.ssh_config
            }, null, 2));
            
            try {
                // 填充视频任务数据源配置
                const video = profile.video || {};
                console.log('[loadProfileData] video 配置:', video);
                
                const videoHostEl = document.getElementById('videoHost');
                const videoPortEl = document.getElementById('videoPort');
                const videoDatabaseEl = document.getElementById('videoDatabase');
                const videoUserEl = document.getElementById('videoUser');
                const videoPasswordEl = document.getElementById('videoPassword');
                
                if (!videoHostEl || !videoPortEl || !videoDatabaseEl || !videoUserEl || !videoPasswordEl) {
                    console.error('[loadProfileData] 错误：视频配置表单元素不存在');
                    return false;
                }
                
                videoHostEl.value = video.host || '';
                videoPortEl.value = video.port || 3306;
                videoDatabaseEl.value = video.database || '';
                videoUserEl.value = video.user || '';
                videoPasswordEl.value = ''; // 密码不回填
                console.log('[loadProfileData] video 配置已加载:', video.host);
                
                // 填充 SSH 配置（从 profile 中获取）
                const sshConfig = profile.ssh_config || {};
                console.log('[loadProfileData] ssh_config 配置:', sshConfig);
                
                const sshHostEl = document.getElementById('sshHost');
                const sshPortEl = document.getElementById('sshPort');
                const sshUserEl = document.getElementById('sshUser');
                const sshPasswordEl = document.getElementById('sshPassword');
                const sshLogDirEl = document.getElementById('sshLogDir');
                
                if (!sshHostEl || !sshPortEl || !sshUserEl || !sshPasswordEl || !sshLogDirEl) {
                    console.error('[loadProfileData] 错误：SSH 配置表单元素不存在');
                    return false;
                }
                
                sshHostEl.value = sshConfig.hostname || '';
                sshPortEl.value = sshConfig.port || 22;
                sshUserEl.value = sshConfig.username || '';
                sshPasswordEl.value = ''; // 密码不回填
                sshLogDirEl.value = sshConfig.log_dir || '';
                console.log('[loadProfileData] SSH 配置已加载:', sshConfig.hostname);
                
                console.log('[loadProfileData] 配置加载完成');
                return true;
            } catch (err) {
                console.error('[loadProfileData] 加载配置出错:', err);
                showToast('加载配置出错：' + err.message, 'error');
                return false;
            }
        }
        
        function switchProfile() {
            const profileSelect = document.getElementById('profileSelect');
            const profileName = profileSelect.value;
            
            console.log('[switchProfile] ========== 开始切换配置 ==========');
            console.log('[switchProfile] 选中的配置:', profileName);
            console.log('[switchProfile] 可用 profiles:', Object.keys(profiles));
            console.log('[switchProfile] profiles[profileName] 存在:', !!profiles[profileName]);
            
            // 检查 profile 是否存在
            if (!profiles[profileName]) {
                console.error('[switchProfile] 错误：找不到配置', profileName);
                console.error('[switchProfile] 可用配置列表:', Object.keys(profiles));
                showToast('切换失败：找不到配置 "' + profileName + '"', 'error');
                // 重置下拉框到默认值
                profileSelect.value = 'default';
                return;
            }
            
            // 更新当前激活的配置
            currentConfig.activeProfile = profileName;
            console.log('[switchProfile] currentConfig.activeProfile 已更新:', currentConfig.activeProfile);
            
            // 加载当前 profile 的数据
            console.log('[switchProfile] 调用 loadProfileData...');
            const loaded = loadProfileData(profileName);
            console.log('[switchProfile] loadProfileData 返回:', loaded);
            
            if (loaded) {
                console.log('[switchProfile] 切换成功');
                
                // 将 activeProfile 存入 localStorage
                localStorage.setItem('activeProfile', profileName);
                
                showToast('已切换到配置：' + (profiles[profileName].name || profileName) + '，点击保存后生效', 'success');
            } else {
                console.error('[switchProfile] loadProfileData 返回 false');
                showToast('切换失败：无法加载配置数据', 'error');
                // 重置下拉框到之前的值
                profileSelect.value = currentConfig.activeProfile || 'default';
            }
            
            console.log('[switchProfile] ========== 切换完成 ==========');
        }
        
        function newProfile() {
            const name = prompt('请输入新配置名称：');
            if (!name) return;
            
            const profileKey = 'profile_' + Date.now();
            profiles[profileKey] = {
                name: name,
                video: {
                    host: 'localhost',
                    port: 3306,
                    database: '',
                    user: 'root',
                    password: ''
                },
                ssh_config: {
                    hostname: '',
                    port: 22,
                    username: '',
                    password: '',
                    log_dir: ''
                }
            };
            
            currentConfig.profiles = profiles;
            currentConfig.activeProfile = profileKey;
            saveSettings();
        }
        
        function deleteProfile() {
            const profileName = document.getElementById('profileSelect').value;
            if (profileName === 'default') {
                showToast('不能删除默认配置', 'error');
                return;
            }
            
            const profileDisplayName = profiles[profileName].name || profileName;
            if (confirm(`确定要删除配置 "${profileDisplayName}" 吗？\n\n这将同时删除该配置下的：\n- 视频任务数据源配置\n- 日志监控配置`)) {
                delete profiles[profileName];
                currentConfig.profiles = profiles;
                currentConfig.activeProfile = 'default';
                saveSettings();
                showToast(`已删除配置：${profileDisplayName}`, 'success');
            }
        }
        
        async function testVideoConnection() {
            const config = {
                host: document.getElementById('videoHost').value,
                port: parseInt(document.getElementById('videoPort').value) || 3306,
                database: document.getElementById('videoDatabase').value,
                user: document.getElementById('videoUser').value,
                password: document.getElementById('videoPassword').value
            };
            
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '测试中...';
            
            try {
                const res = await fetch('/api/settings/test_video', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                showStatus('videoStatus', data.success, data.message);
                showToast(data.success ? '连接成功！' : '连接失败：' + data.message, data.success ? 'success' : 'error');
            } catch (err) {
                showStatus('videoStatus', false, '测试失败');
                showToast('测试失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔌 测试连接';
            }
        }
        
        async function testSSHConnection() {
            const config = {
                hostname: document.getElementById('sshHost').value,
                port: parseInt(document.getElementById('sshPort').value) || 22,
                username: document.getElementById('sshUser').value,
                password: document.getElementById('sshPassword').value,
                log_dir: document.getElementById('sshLogDir').value
            };
            
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '测试中...';
            
            try {
                const res = await fetch('/api/settings/test_ssh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                showStatus('sshStatus', data.success, data.message);
                showToast(data.success ? 'SSH 连接成功！' : 'SSH 连接失败：' + data.message, data.success ? 'success' : 'error');
            } catch (err) {
                showStatus('sshStatus', false, '测试失败');
                showToast('测试失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔌 测试连接';
            }
        }
        
        async function saveSettings() {
            const activeProfile = document.getElementById('profileSelect').value;
            const config = {
                activeProfile: activeProfile,
                active_profile: activeProfile,
                profiles: {}
            };
            
            // 收集所有配置
            Object.keys(profiles).forEach(name => {
                config.profiles[name] = { ...profiles[name] }; // 浅拷贝
            });
            
            // 更新当前编辑的配置 - 同时保存 video 和 ssh_config 到当前 profile
            const currentProfile = config.profiles[activeProfile];
            if (currentProfile) {
                // 保存视频任务数据源配置
                const videoPassword = document.getElementById('videoPassword').value;
                currentProfile.video = {
                    host: document.getElementById('videoHost').value,
                    port: parseInt(document.getElementById('videoPort').value) || 3306,
                    database: document.getElementById('videoDatabase').value,
                    user: document.getElementById('videoUser').value,
                    password: videoPassword ? btoa(videoPassword) : (currentProfile.video?.password || '')
                };
                
                // 保存日志监控配置（SSH 配置）到同一个 profile
                const sshPassword = document.getElementById('sshPassword').value;
                currentProfile.ssh_config = {
                    hostname: document.getElementById('sshHost').value,
                    port: parseInt(document.getElementById('sshPort').value) || 22,
                    username: document.getElementById('sshUser').value,
                    password: sshPassword ? btoa(sshPassword) : (currentProfile.ssh_config?.password || ''),
                    log_dir: document.getElementById('sshLogDir').value
                };
            }
            
            try {
                const res = await fetch('/api/settings/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (data.success) {
                    const savedActiveProfile = data.activeProfile || activeProfile;
                    const profileName = profiles[savedActiveProfile]?.name || savedActiveProfile;
                    currentConfig.activeProfile = savedActiveProfile;
                    document.getElementById('profileSelect').value = savedActiveProfile;
                    
                    // 将 activeProfile 存入 localStorage，其他页面会自动读取
                    localStorage.setItem('activeProfile', savedActiveProfile);
                    
                    showToast(`配置保存成功！已切换到：${profileName}，页面将自动刷新以应用新配置`, 'success');
                    
                    // 1 秒后自动刷新页面，使配置生效
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast('保存失败：' + data.error, 'error');
                }
            } catch (err) {
                showToast('保存失败：' + err.message, 'error');
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
        
        document.addEventListener('DOMContentLoaded', function() {
            loadSettings();
            setupSidebarToggle();
        });
    </script>
</body>
</html>
"""


# Flask 路由
def create_settings_routes(app):
    """创建设置路由"""
    
    @app.route('/settings')
    def settings_page():
        return render_template_string(SETTINGS_TEMPLATE)
    
    @app.route('/api/settings/config')
    def api_get_config():
        """获取配置"""
        try:
            config = load_config()
            # 解密密码用于显示（实际不显示，只返回配置结构）
            profiles = {}
            for name, profile in config.get('profiles', {}).items():
                # 优先使用 video 配置，向后兼容 internal/mps
                video_config = profile.get('video', {})
                if not video_config.get('host'):
                    # 向后兼容：如果没有 video 配置，尝试使用 internal 或 mps
                    video_config = profile.get('internal', profile.get('mps', {}))
                
                # 获取 ssh_config（从 profile 中）
                ssh_config = profile.get('ssh_config', {})
                
                # 向后兼容：如果 profile 中没有 ssh_config，尝试从全局获取
                if not ssh_config.get('hostname'):
                    global_ssh = config.get('ssh_config', {})
                    if global_ssh.get('hostname'):
                        ssh_config = global_ssh
                
                profiles[name] = {
                    'name': profile.get('name', name),
                    'video': {
                        'host': video_config.get('host', ''),
                        'port': video_config.get('port', 3306),
                        'database': video_config.get('database', ''),
                        'user': video_config.get('user', ''),
                        'password': ''  # 密码不返回
                    },
                    'ssh_config': {
                        'hostname': ssh_config.get('hostname', ''),
                        'port': ssh_config.get('port', 22),
                        'username': ssh_config.get('username', ''),
                        'password': '',  # 密码不返回
                        'log_dir': ssh_config.get('log_dir', '')
                    }
                }
            
            return jsonify({
                'success': True,
                'config': config,
                'profiles': profiles,
                'activeProfile': config.get('active_profile', 'default')
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/settings/save', methods=['POST'])
    def api_save_config():
        """保存配置"""
        try:
            data = request.json
            active_profile = data.get('active_profile') or data.get('activeProfile') or 'default'
            incoming_config = {
                'active_profile': active_profile,
                'profiles': data.get('profiles', {})
            }
            existing_config = load_config()
            config = merge_profile_config(existing_config, incoming_config)

            if active_profile not in config.get('profiles', {}):
                config['active_profile'] = existing_config.get('active_profile', 'default')

            save_config(config)
            print(f"[配置保存] 已保存到配置档：{config.get('active_profile', 'default')}")
            return jsonify({'success': True, 'activeProfile': config.get('active_profile', 'default')})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/settings/test_video', methods=['POST'])
    def api_test_video():
        """测试视频任务数据库连接"""
        try:
            data = request.json
            db_config = {
                'host': data.get('host', 'localhost'),
                'port': data.get('port', 3306),
                'database': data.get('database', ''),
                'user': data.get('user', ''),
                'password': data.get('password', ''),
                'charset': 'utf8mb4',
                'connect_timeout': 5,
                'connection_timeout': 5
            }
            result = test_db_connection(db_config)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/settings/test_ssh', methods=['POST'])
    def api_test_ssh():
        """测试 SSH 连接"""
        try:
            data = request.json
            ssh_config = {
                'hostname': data.get('hostname', ''),
                'port': data.get('port', 22),
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'log_dir': data.get('log_dir', '')
            }
            result = test_ssh_connection(ssh_config)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


# 初始化时自动加载配置
def init_db_config():
    """初始化数据库配置（在主程序启动时调用）"""
    config = load_config()
    print(f"Database config loaded: active_profile={config.get('active_profile', 'default')}")
    return config
