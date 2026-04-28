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
            },
            "server_monitor_ssh": {
                "hostname": "101.126.91.130",
                "port": 22,
                "username": "ubuntu",
                "password": ""  # 加密存储
            },
            "db_monitor": {
                "host": "101.126.91.130",
                "port": 3306,
                "database": "information_schema",
                "user": "yiyuzhou",
                "password": ""  # 加密存储
            },
            "server_data_source": {
                "host": "101.126.91.130",
                "port": 22,
                "username": "ubuntu",
                "password": ""  # 加密存储
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


def get_db_monitor_config(profile_name=None):
    """获取数据库监控配置（从当前激活的 profile 中获取）"""
    config = load_config()
    actual_profile_name = profile_name or config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(actual_profile_name, config.get("profiles", {}).get("default"))
    
    if not profile:
        return {
            'host': 'localhost',
            'port': 3306,
            'database': 'information_schema',
            'user': 'root',
            'password': ''
        }
    
    # 从 profile 中获取 db_monitor 配置
    db_monitor = profile.get("db_monitor", {})
    
    return {
        'host': db_monitor.get('host', 'localhost'),
        'port': db_monitor.get('port', 3306),
        'database': db_monitor.get('database', 'information_schema'),
        'user': db_monitor.get('user', 'root'),
        'password': decode_password(db_monitor.get('password', ''))
    }


def save_db_monitor_config(db_monitor_config, profile_name=None):
    """保存数据库监控配置到指定的 profile（或当前激活的 profile）"""
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
    
    # 保存 db_monitor 配置到当前 profile
    config["profiles"][profile_name]["db_monitor"] = {
        'host': db_monitor_config.get('host', 'localhost'),
        'port': db_monitor_config.get('port', 3306),
        'database': db_monitor_config.get('database', 'information_schema'),
        'user': db_monitor_config.get('user', 'root'),
        'password': encode_password(db_monitor_config.get('password', ''))
    }
    
    save_config(config)
    return True


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


def get_server_data_source_config(profile_name=None):
    """获取服务器数据源配置（从当前激活的 profile 中获取）"""
    config = load_config()
    actual_profile_name = profile_name or config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(actual_profile_name, config.get("profiles", {}).get("default"))
    
    if not profile:
        return {
            'host': 'localhost',
            'port': 22,
            'username': 'root',
            'password': ''
        }
    
    # 从 profile 中获取 server_data_source 配置
    server_data_source = profile.get("server_data_source", {})
    
    return {
        'host': server_data_source.get('host', 'localhost'),
        'port': server_data_source.get('port', 22),
        'username': server_data_source.get('username', 'root'),
        'password': decode_password(server_data_source.get('password', ''))
    }


def save_server_data_source_config(server_data_source_config, profile_name=None):
    """保存服务器数据源配置到指定的 profile（或当前激活的 profile）"""
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
    
    # 保存 server_data_source 配置到当前 profile
    config["profiles"][profile_name]["server_data_source"] = {
        'host': server_data_source_config.get('host', 'localhost'),
        'port': server_data_source_config.get('port', 22),
        'username': server_data_source_config.get('username', 'root'),
        'password': encode_password(server_data_source_config.get('password', ''))
    }
    
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


def test_db_monitor_connection(db_monitor_config):
    """测试数据库监控连接"""
    try:
        db_config = {
            'host': db_monitor_config.get('host', 'localhost'),
            'port': db_monitor_config.get('port', 3306),
            'database': db_monitor_config.get('database', 'information_schema'),
            'user': db_monitor_config.get('user', 'root'),
            'password': db_monitor_config.get('password', ''),
            'charset': 'utf8mb4',
            'connect_timeout': 5,
            'connection_timeout': 5
        }
        conn = mysql.connector.connect(**db_config)
        
        # 测试是否能访问 information_schema
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return {'success': True, 'message': f'数据库监控连接成功，可访问 {count} 个表'}
    except mysql.connector.errors.ProgrammingError as e:
        return {'success': False, 'message': f'数据库访问错误：{str(e)}'}
    except mysql.connector.errors.OperationalError as e:
        return {'success': False, 'message': f'数据库操作错误：{str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'连接失败：{str(e)}'}


def test_server_data_source_connection(server_data_source_config):
    """测试服务器数据源连接（SSH 连接测试）"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=server_data_source_config.get('host', ''),
            port=server_data_source_config.get('port', 22),
            username=server_data_source_config.get('username', ''),
            password=server_data_source_config.get('password', ''),
            timeout=10
        )
        client.close()
        return {'success': True, 'message': '服务器数据源连接成功'}
    except paramiko.AuthenticationException:
        return {'success': False, 'message': '认证失败：用户名或密码错误'}
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
        
        /* 双栏布局 */
        .settings-layout { display: grid; grid-template-columns: 280px 1fr; gap: 24px; }
        
        /* 左侧配置列表 */
        .config-list-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; height: fit-content; }
        .config-list-card h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
        .config-list { list-style: none; padding: 0; margin: 0; }
        .config-list-item { display: flex; flex-direction: column; gap: 4px; padding: 12px 14px; margin-bottom: 8px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .config-list-item:hover { background: var(--bg-hover); border-color: var(--primary); }
        .config-list-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(29, 78, 216, 0.1) 100%); border-color: var(--primary); }
        .config-list-item-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
        .config-list-item-info { font-size: 12px; color: var(--text-secondary); }
        .config-list-item-actions { display: flex; gap: 6px; margin-top: 8px; }
        .config-list-btn { background: none; border: none; color: var(--text-secondary); font-size: 14px; cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: all 0.2s; }
        .config-list-btn:hover { background: var(--bg-card); color: var(--text-primary); }
        .config-list-btn.delete:hover { color: var(--danger); }
        .add-config-btn { width: 100%; margin-top: 12px; padding: 10px; background: var(--bg-dark); border: 1px dashed var(--border); border-radius: 8px; color: var(--text-secondary); font-size: 14px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .add-config-btn:hover { background: var(--bg-hover); border-color: var(--primary); color: var(--primary); }
        
        /* 右侧配置详情 */
        .config-detail-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
        .config-detail-header { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        .config-detail-header h2 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
        .config-detail-header p { color: var(--text-secondary); font-size: 13px; }
        
        .settings-card { background: var(--bg-dark); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .settings-card h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        
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
            <div class="menu-section" style="margin-top: 20px;">日志管理</div>
            <a href="/algo-comm-log" class="menu-item" data-page="algo-comm-log"><span class="icon">🔬</span><span class="label">算法通讯日志</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统监控</div>
            <a href="/logs" class="menu-item" data-page="logs">
                <span class="icon">📋</span>
                <span class="label">日志监控</span>
            </a>
            <a href="/server-monitor" class="menu-item" data-page="server-monitor">
                <span class="icon">🖥️</span>
                <span class="label">服务器监控</span>
            </a>
            <a href="/db-monitor" class="menu-item" data-page="db-monitor">
                <span class="icon">🗄️</span>
                <span class="label">数据库监控</span>
            </a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item active" data-page="settings">
                <span class="icon">⚙️</span>
                <span class="label">系统设置</span>
            </a>
            <a href="/dict-config" class="menu-item" data-page="dict-config">
                <span class="icon">📚</span>
                <span class="label">字典配置</span>
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
            
            <!-- 双栏布局 -->
            <div class="settings-layout">
                <!-- 左侧配置列表 -->
                <div class="config-list-card">
                    <h2>📁 配置列表</h2>
                    <ul class="config-list" id="configList"></ul>
                    <button class="add-config-btn" onclick="newProfile()">➕ 新建配置</button>
                </div>
                
                <!-- 右侧配置详情 -->
                <div class="config-detail-card">
                    <div class="config-detail-header">
                        <h2>配置详情</h2>
                        <p>当前配置：<span id="currentProfileName">默认配置</span></p>
                    </div>

                    <!-- 隐藏的 profileSelect 用于内部逻辑 -->
                    <select id="profileSelect" style="display:none;">
                        <option value="default">默认配置</option>
                    </select>

                    <!-- 配置操作按钮 -->
                    <div class="profile-selector" style="margin-bottom: 20px;">
                        <div class="profile-actions">
                            <button class="btn btn-primary" onclick="saveSettings()">💾 保存配置</button>
                            <button class="btn btn-secondary" onclick="loadSettings()">🔄 重置</button>
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
                    <input type="text" id="videoPassword" placeholder="请输入数据库密码（明文显示）">
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
            
            <!-- 数据库监控配置 -->
            <div class="settings-card">
                <h2>🗄️ 数据库监控配置</h2>
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
                    <input type="text" id="dbMonitorPassword" placeholder="请输入数据库密码（明文显示）">
                </div>
                <div class="form-actions">
                    <button class="btn btn-success" onclick="testDbMonitorConnection()">🔌 测试连接</button>
                    <span id="dbMonitorStatus" class="connection-status" style="display: none;"></span>
                </div>
            </div>
            
            <!-- 服务器数据源配置 -->
            <div class="settings-card">
                <h2>🖥️ 服务器数据源配置</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>服务器 IP</label>
                        <input type="text" id="serverDataSourceHost" placeholder="例如：101.126.91.130">
                    </div>
                    <div class="form-group">
                        <label>端口</label>
                        <input type="number" id="serverDataSourcePort" placeholder="22" value="22">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>用户名</label>
                        <input type="text" id="serverDataSourceUser" placeholder="例如：ubuntu">
                    </div>
                    <div class="form-group">
                        <label>密码</label>
                        <input type="password" id="serverDataSourcePassword" placeholder="请输入服务器密码">
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-success" onclick="testServerDataSourceConnection()">🔌 测试连接</button>
                    <span id="serverDataSourceStatus" class="connection-status" style="display: none;"></span>
                </div>
            </div>
            
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast 提示 -->
    <div id="toast" class="toast"></div>
    
    <script>
        let currentConfig = null;
        let profiles = {};
        const DB_MONITOR_PLAIN_PASSWORDS_KEY = 'dbMonitorPlainPasswords';
        const VIDEO_PLAIN_PASSWORDS_KEY = 'videoPlainPasswords';

        function _getPlainPasswordMap(key) {
            try {
                const raw = localStorage.getItem(key);
                return raw ? JSON.parse(raw) : {};
            } catch (err) {
                return {};
            }
        }

        function _setPlainPassword(key, profileName, password) {
            const passwordMap = _getPlainPasswordMap(key);
            if (password) {
                passwordMap[profileName] = password;
            } else {
                delete passwordMap[profileName];
            }
            localStorage.setItem(key, JSON.stringify(passwordMap));
        }

        function _getPlainPassword(key, profileName) {
            return _getPlainPasswordMap(key)[profileName] || '';
        }

        function setDbMonitorPlainPassword(profileName, password) { _setPlainPassword(DB_MONITOR_PLAIN_PASSWORDS_KEY, profileName, password); }
        function getDbMonitorPlainPassword(profileName) { return _getPlainPassword(DB_MONITOR_PLAIN_PASSWORDS_KEY, profileName); }

        function setVideoPlainPassword(profileName, password) { _setPlainPassword(VIDEO_PLAIN_PASSWORDS_KEY, profileName, password); }
        function getVideoPlainPassword(profileName) { return _getPlainPassword(VIDEO_PLAIN_PASSWORDS_KEY, profileName); }
        
        // 渲染左侧配置列表
        function renderConfigList() {
            const configList = document.getElementById('configList');
            const profileSelect = document.getElementById('profileSelect');
            const activeProfile = profileSelect ? profileSelect.value : 'default';
            
            if (!configList) {
                console.error('[renderConfigList] 错误：configList 元素不存在');
                return;
            }
            
            configList.innerHTML = '';
            
            if (Object.keys(profiles).length === 0) {
                configList.innerHTML = '<li style="color: var(--text-secondary); font-size: 13px; padding: 12px;">暂无配置</li>';
                return;
            }
            
            Object.keys(profiles).forEach(name => {
                const li = document.createElement('li');
                li.className = 'config-list-item' + (name === activeProfile ? ' active' : '');
                li.onclick = () => {
                    profileSelect.value = name;
                    switchProfile();
                };
                
                const profile = profiles[name];
                const videoHost = profile.video?.host || '未配置';
                
                li.innerHTML = `
                    <div class="config-list-item-name">${profile.name || name}</div>
                    <div class="config-list-item-info">MySQL: ${videoHost}</div>
                    <div class="config-list-item-actions">
                        <button class="config-list-btn" onclick="event.stopPropagation(); editProfile('${name}')" title="重命名">✏️</button>
                        ${name !== 'default' ? `<button class="config-list-btn delete" onclick="event.stopPropagation(); deleteProfileByName('${name}')" title="删除">🗑️</button>` : ''}
                    </div>
                `;
                
                configList.appendChild(li);
            });
            
            console.log('[renderConfigList] 配置列表已渲染，当前激活:', activeProfile);
        }
        
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

                // 渲染左侧配置列表
                renderConfigList();
                
                // 更新详情卡片标题
                const currentProfileNameEl = document.getElementById('currentProfileName');
                if (currentProfileNameEl && profiles[activeProfile]) {
                    currentProfileNameEl.textContent = profiles[activeProfile].name || activeProfile;
                }
                
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
                videoPasswordEl.value = getVideoPlainPassword(profileName);
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
                
                // 填充数据库监控配置
                const dbMonitorConfig = profile.db_monitor || {};
                console.log('[loadProfileData] db_monitor 配置:', dbMonitorConfig);
                
                const dbMonitorHostEl = document.getElementById('dbMonitorHost');
                const dbMonitorPortEl = document.getElementById('dbMonitorPort');
                const dbMonitorDatabaseEl = document.getElementById('dbMonitorDatabase');
                const dbMonitorUserEl = document.getElementById('dbMonitorUser');
                const dbMonitorPasswordEl = document.getElementById('dbMonitorPassword');
                
                if (!dbMonitorHostEl || !dbMonitorPortEl || !dbMonitorDatabaseEl || !dbMonitorUserEl || !dbMonitorPasswordEl) {
                    console.error('[loadProfileData] 错误：数据库监控配置表单元素不存在');
                    return false;
                }
                
                dbMonitorHostEl.value = dbMonitorConfig.host || '';
                dbMonitorPortEl.value = dbMonitorConfig.port || 3306;
                dbMonitorDatabaseEl.value = dbMonitorConfig.database || '';
                dbMonitorUserEl.value = dbMonitorConfig.user || '';
                dbMonitorPasswordEl.value = getDbMonitorPlainPassword(profileName);
                console.log('[loadProfileData] 数据库监控配置已加载:', dbMonitorConfig.host);
                
                // 填充服务器数据源配置
                const serverDataSourceConfig = profile.server_data_source || {};
                console.log('[loadProfileData] server_data_source 配置:', serverDataSourceConfig);
                
                const serverDataSourceHostEl = document.getElementById('serverDataSourceHost');
                const serverDataSourcePortEl = document.getElementById('serverDataSourcePort');
                const serverDataSourceUserEl = document.getElementById('serverDataSourceUser');
                const serverDataSourcePasswordEl = document.getElementById('serverDataSourcePassword');
                
                if (!serverDataSourceHostEl || !serverDataSourcePortEl || !serverDataSourceUserEl || !serverDataSourcePasswordEl) {
                    console.error('[loadProfileData] 错误：服务器数据源配置表单元素不存在');
                    return false;
                }
                
                serverDataSourceHostEl.value = serverDataSourceConfig.host || '';
                serverDataSourcePortEl.value = serverDataSourceConfig.port || 22;
                serverDataSourceUserEl.value = serverDataSourceConfig.username || '';
                serverDataSourcePasswordEl.value = ''; // 密码不回填
                console.log('[loadProfileData] 服务器数据源配置已加载:', serverDataSourceConfig.host);
                
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
                
                // 更新左侧配置列表高亮
                renderConfigList();
                
                // 更新详情卡片标题
                const currentProfileNameEl = document.getElementById('currentProfileName');
                if (currentProfileNameEl) {
                    currentProfileNameEl.textContent = profiles[profileName].name || profileName;
                }
                
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
            
            // 更新下拉框
            const profileSelect = document.getElementById('profileSelect');
            const option = document.createElement('option');
            option.value = profileKey;
            option.textContent = name;
            profileSelect.appendChild(option);
            profileSelect.value = profileKey;
            
            // 重新渲染列表
            renderConfigList();
            
            saveSettings();
        }
        
        // 编辑配置名称（左侧列表按钮）
        function editProfile(profileName) {
            const profile = profiles[profileName];
            if (!profile) return;
            
            const newName = prompt('请输入新配置名称：', profile.name || profileName);
            if (!newName || newName === profile.name) return;
            
            profile.name = newName;
            
            // 更新下拉框中的文本
            const profileSelect = document.getElementById('profileSelect');
            for (let i = 0; i < profileSelect.options.length; i++) {
                if (profileSelect.options[i].value === profileName) {
                    profileSelect.options[i].textContent = newName;
                    break;
                }
            }
            
            renderConfigList();
            showToast('配置名称已更新', 'success');
        }
        
        // 删除配置（左侧列表按钮）
        function deleteProfileByName(profileName) {
            if (profileName === 'default') {
                showToast('不能删除默认配置', 'error');
                return;
            }
            
            const profileDisplayName = profiles[profileName].name || profileName;
            if (confirm(`确定要删除配置 "${profileDisplayName}" 吗？`)) {
                delete profiles[profileName];
                
                // 从下拉框中移除
                const profileSelect = document.getElementById('profileSelect');
                for (let i = 0; i < profileSelect.options.length; i++) {
                    if (profileSelect.options[i].value === profileName) {
                        profileSelect.remove(i);
                        break;
                    }
                }
                
                currentConfig.profiles = profiles;
                currentConfig.activeProfile = 'default';
                profileSelect.value = 'default';
                // 重新渲染列表
                renderConfigList();

                saveSettings();
                showToast(`已删除配置：${profileDisplayName}`, 'success');
            }
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
        
        async function testDbMonitorConnection() {
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
                showStatus('dbMonitorStatus', data.success, data.message);
                showToast(data.success ? '数据库监控连接成功！' : '数据库监控连接失败：' + data.message, data.success ? 'success' : 'error');
            } catch (err) {
                showStatus('dbMonitorStatus', false, '测试失败');
                showToast('测试失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔌 测试连接';
            }
        }
        
        async function testServerDataSourceConnection() {
            const config = {
                host: document.getElementById('serverDataSourceHost').value,
                port: parseInt(document.getElementById('serverDataSourcePort').value) || 22,
                username: document.getElementById('serverDataSourceUser').value,
                password: document.getElementById('serverDataSourcePassword').value
            };
            
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '测试中...';
            
            try {
                const res = await fetch('/api/settings/test_server_data_source', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                showStatus('serverDataSourceStatus', data.success, data.message);
                showToast(data.success ? '服务器数据源连接成功！' : '服务器数据源连接失败：' + data.message, data.success ? 'success' : 'error');
            } catch (err) {
                showStatus('serverDataSourceStatus', false, '测试失败');
                showToast('测试失败：' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔌 测试连接';
            }
        }

        async function saveSettings() {
            // 保持当前的 active_profile 不变
            const activeProfile = currentConfig?.activeProfile || currentConfig?.active_profile || 'default';
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
                setVideoPlainPassword(activeProfile, videoPassword || getVideoPlainPassword(activeProfile));
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
                
                // 保存数据库监控配置到同一个 profile
                const dbMonitorPassword = document.getElementById('dbMonitorPassword').value;
                currentProfile.db_monitor = {
                    host: document.getElementById('dbMonitorHost').value,
                    port: parseInt(document.getElementById('dbMonitorPort').value) || 3306,
                    database: document.getElementById('dbMonitorDatabase').value,
                    user: document.getElementById('dbMonitorUser').value,
                    password: dbMonitorPassword ? btoa(dbMonitorPassword) : (currentProfile.db_monitor?.password || '')
                };
                setDbMonitorPlainPassword(activeProfile, dbMonitorPassword || getDbMonitorPlainPassword(activeProfile));
                
                // 保存服务器数据源配置到同一个 profile
                const serverDataSourcePassword = document.getElementById('serverDataSourcePassword').value;
                currentProfile.server_data_source = {
                    host: document.getElementById('serverDataSourceHost').value,
                    port: parseInt(document.getElementById('serverDataSourcePort').value) || 22,
                    username: document.getElementById('serverDataSourceUser').value,
                    password: serverDataSourcePassword ? btoa(serverDataSourcePassword) : (currentProfile.server_data_source?.password || '')
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
    # 密码验证（写死：5066995）
    ADMIN_PASSWORD = "5066995"

    @app.route('/api/settings/verify_password', methods=['POST'])
    def api_verify_password():
        """验证管理密码"""
        try:
            data = request.json
            password = data.get('password', '')
            if password == ADMIN_PASSWORD:
                # 验证成功，设置 session
                from flask import session
                session['admin_verified'] = True
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': '密码错误'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/check_verified', methods=['GET'])
    def api_check_verified():
        """检查是否已验证"""
        from flask import session
        return jsonify({'verified': session.get('admin_verified', False)})

    def check_admin_session():
        """检查 session 是否已验证"""
        from flask import session
        return session.get('admin_verified', False)

    @app.route('/settings')
    def settings_page():
        from flask import session
        if not check_admin_session():
            # 返回密码输入页面
            return render_template_string(PASSWORD_TEMPLATE)
        return render_template_string(SETTINGS_TEMPLATE)

    # 密码输入模板（内嵌在 settings.py 中）
    PASSWORD_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>验证密码 - 视频任务运维系统</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; background: #0f172a; min-height: 100vh; display: flex; align-items: center; justify-content: center; color: #f1f5f9; }
        .password-box { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); text-align: center; }
        .password-box h2 { margin-bottom: 20px; }
        .password-box input { width: 200px; padding: 12px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #f1f5f9; font-size: 16px; text-align: center; }
        .password-box button { margin-top: 20px; padding: 12px 30px; border-radius: 6px; border: none; background: #2563eb; color: white; font-size: 16px; cursor: pointer; }
        .password-box button:hover { background: #1d4ed8; }
        .error { color: #dc2626; margin-top: 10px; display: none; }
    </style>
</head>
<body>
    <div class="password-box">
        <h2>请输入管理密码</h2>
        <input type="password" id="password" placeholder="请输入密码" onkeydown="if(event.key==='Enter')verify()">
        <br><button onclick="verify()">验证</button>
        <div class="error" id="errorMsg">密码错误，请重试</div>
    </div>
    <script>
        async function verify() {
            const password = document.getElementById('password').value;
            const res = await fetch('/api/settings/verify_password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password})
            });
            const data = await res.json();
            if (data.success) {
                window.location.href = '/settings';
            } else {
                document.getElementById('errorMsg').style.display = 'block';
            }
        }
    </script>
</body>
</html>"""

    # 字典配置模板
    DICT_CONFIG_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>字典配置 - 视频任务运维系统</title>
    <style>
        :root { --primary: #2563eb; --primary-dark: #1d4ed8; --success: #059669; --warning: #d97706; --danger: #dc2626; --info: #7c3aed; --bg-dark: #0f172a; --bg-card: #1e293b; --bg-hover: #334155; --text-primary: #f1f5f9; --text-secondary: #94a3b8; --border: #334155; --sidebar-width: 240px; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: var(--bg-dark); min-height: 100vh; color: var(--text-primary); display: flex; }
        .sidebar { width: var(--sidebar-width); background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-right: 1px solid var(--border); min-height: 100vh; position: fixed; left: 0; top: 0; display: flex; flex-direction: column; }
        .sidebar-logo { padding: 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .sidebar-logo .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, var(--primary) 0%, var(--info) 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .sidebar-logo h1 { color: var(--text-primary); font-size: 18px; font-weight: 600; }
        .navbar-version { font-size: 11px; color: var(--text-secondary); }
        .sidebar-menu { flex: 1; padding: 16px 0; overflow-y: auto; }
        .menu-section { padding: 8px 20px 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); }
        .menu-item { display: flex; align-items: center; gap: 12px; padding: 10px 20px; color: var(--text-secondary); text-decoration: none; transition: background 0.15s; }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
        .menu-item.active { background: rgba(37, 99, 235, 0.15); color: var(--primary); border-right: 3px solid var(--primary); }
        .menu-item .icon { font-size: 18px; width: 24px; text-align: center; }
        .menu-item .label { font-size: 14px; }
        .sidebar-footer { padding: 16px 20px; border-top: 1px solid var(--border); }
        .sidebar-status { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); }
        .status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; }
        .main-wrapper { margin-left: var(--sidebar-width); flex: 1; padding: 24px; }
        .page-header { margin-bottom: 20px; }
        .page-header h1 { font-size: 22px; font-weight: 600; }
        .page-header p { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
        .dict-container { display: flex; gap: 20px; height: calc(100vh - 150px); }
        .dict-panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; display: flex; flex-direction: column; }
        .dict-panel-left { width: 350px; flex-shrink: 0; }
        .dict-panel-right { flex: 1; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--border); }
        .panel-header h2 { font-size: 15px; font-weight: 600; }
        .panel-body { flex: 1; overflow-y: auto; padding: 10px; }
        .dict-item { padding: 10px 14px; border-radius: 6px; cursor: pointer; margin-bottom: 4px; transition: background 0.15s; }
        .dict-item:hover { background: var(--bg-hover); }
        .dict-item.active { background: rgba(37, 99, 235, 0.2); color: var(--primary); }
        .dict-item-name { font-size: 14px; font-weight: 500; }
        .dict-item-meta { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
        .btn { padding: 6px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; }
        .btn-primary { background: var(--primary); color: #fff; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-danger { background: var(--danger); color: #fff; }
        .btn-sm { padding: 4px 10px; font-size: 12px; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        thead th { background: rgba(51,65,85,0.5); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 12px; white-space: nowrap; }
        tbody td { padding: 10px 14px; border-top: 1px solid var(--border); }
        tbody tr:hover { background: var(--bg-hover); }
        .empty { text-align: center; padding: 40px; color: var(--text-secondary); }
        .loading { text-align: center; padding: 40px; color: var(--text-secondary); }
        .form-row { display: flex; gap: 12px; margin-bottom: 12px; }
        .form-group { display: flex; flex-direction: column; gap: 4px; flex: 1; }
        .form-group label { font-size: 12px; color: var(--text-secondary); }
        .form-input { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-primary); padding: 6px 10px; border-radius: 6px; font-size: 13px; }
        .form-input:focus { outline: none; border-color: var(--primary); }
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }
        .modal-overlay.show { display: flex; }
        .modal-box { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; max-width: 500px; width: 95%; }
        .modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
        .modal-head h3 { font-size: 15px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 20px; }
        .modal-body { padding: 20px; }
        .modal-foot { padding: 16px 20px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px; }
        .top-navbar { background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 10px 24px; display: flex; align-items: center; gap: 16px; }
        .navbar-label { font-size: 13px; color: var(--text-secondary); }
        .navbar-select { background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-primary); padding: 5px 10px; border-radius: 6px; font-size: 13px; cursor: pointer; }
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-logo">
            <div class="logo-icon">📊</div>
            <div><h1>运维系统</h1><div class="navbar-version">v1.0.0 by yiyuzhou</div></div>
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
            <a href="/db-monitor" class="menu-item" data-page="db-monitor"><span class="icon">🗄️</span><span class="label">数据库监控</span></a>
            <div class="menu-section" style="margin-top: 20px;">系统</div>
            <a href="/settings" class="menu-item" data-page="settings"><span class="icon">⚙️</span><span class="label">系统设置</span></a>
            <a href="/dict-config" class="menu-item active" data-page="dict-config"><span class="icon">📚</span><span class="label">字典配置</span></a>
        </nav>
        <div class="sidebar-footer">
            <div class="sidebar-status"><span class="status-dot"></span><span>系统运行正常</span></div>
        </div>
    </aside>

    <div class="main-wrapper">
        <div class="top-navbar">
            <span class="navbar-label">当前环境：</span>
            <select class="navbar-select" id="profileSelect" onchange="switchProfile()"><option value="">加载中...</option></select>
        </div>

        <div class="page-header">
            <h1>📚 字典配置</h1>
            <p>管理系统字典类型和字典数据</p>
        </div>

        <div class="dict-container">
            <div class="dict-panel dict-panel-left">
                <div class="panel-header">
                    <h2>字典类型</h2>
                    <button class="btn btn-primary btn-sm" onclick="openTypeModal()">+ 新增</button>
                </div>
                <div style="padding:10px 14px;border-bottom:1px solid var(--border);">
                    <input type="text" class="form-input" id="typeKeyword" placeholder="搜索名称/类型" style="width:100%;" oninput="searchTypes(this.value)">
                </div>
                <div class="panel-body" id="typeList">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            <div class="dict-panel dict-panel-right">
                <div class="panel-header">
                    <h2>字典数据 <span id="currentTypeName" style="font-weight:normal;font-size:13px;color:var(--text-secondary)"></span></h2>
                    <div style="display:flex;gap:8px;">
                        <input type="text" class="form-input" id="dataKeyword" placeholder="搜索标签/值" style="width:140px;" oninput="searchData()">
                        <button class="btn btn-primary btn-sm" id="addDataBtn" onclick="openDataModal()" disabled>+ 新增</button>
                    </div>
                </div>
                <div class="panel-body" id="dataList">
                    <div class="empty">请先选择左侧字典类型</div>
                </div>
                <div id="dataPagination" style="border-top:1px solid var(--border);"></div>
            </div>
        </div>
    </div>

    <!-- 字典类型弹窗 -->
    <div class="modal-overlay" id="typeModal">
        <div class="modal-box">
            <div class="modal-head">
                <h3 id="typeModalTitle">新增字典类型</h3>
                <button class="modal-close" onclick="closeModal('typeModal')">✕</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="typeId">
                <div class="form-group" style="margin-bottom:12px;">
                    <label>名称</label>
                    <input type="text" class="form-input" id="typeName" placeholder="请输入名称">
                </div>
                <div class="form-group" style="margin-bottom:12px;">
                    <label>类型</label>
                    <input type="text" class="form-input" id="typeCode" placeholder="请输入类型编码">
                </div>
                <div class="form-group">
                    <label>状态</label>
                    <select class="form-input" id="typeStatus">
                        <option value="0">启用</option>
                        <option value="1">禁用</option>
                    </select>
                </div>
            </div>
            <div class="modal-foot">
                <button class="btn btn-secondary" onclick="closeModal('typeModal')">取消</button>
                <button class="btn btn-primary" onclick="saveType()">保存</button>
            </div>
        </div>
    </div>

    <!-- 字典数据弹窗 -->
    <div class="modal-overlay" id="dataModal">
        <div class="modal-box">
            <div class="modal-head">
                <h3 id="dataModalTitle">新增字典数据</h3>
                <button class="modal-close" onclick="closeModal('dataModal')">✕</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="dataId">
                <div class="form-group" style="margin-bottom:12px;">
                    <label>标签</label>
                    <input type="text" class="form-input" id="dataLabel" placeholder="请输入标签">
                </div>
                <div class="form-group" style="margin-bottom:12px;">
                    <label>值</label>
                    <input type="text" class="form-input" id="dataValue" placeholder="请输入值">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>排序</label>
                        <input type="number" class="form-input" id="dataSort" value="0">
                    </div>
                    <div class="form-group">
                        <label>状态</label>
                        <select class="form-input" id="dataStatus">
                            <option value="0">启用</option>
                            <option value="1">禁用</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="modal-foot">
                <button class="btn btn-secondary" onclick="closeModal('dataModal')">取消</button>
                <button class="btn btn-primary" onclick="saveData()">保存</button>
            </div>
        </div>
    </div>

    <script>
        let selectedTypeId = null;
        let typeList = [];

        async function init() {
            await loadProfiles();
            loadTypes();
        }

        async function loadProfiles() {
            try {
                const res = await fetch('/api/settings/valid_profiles');
                const data = await res.json();
                if (!data.success) return;
                const sel = document.getElementById('profileSelect');
                sel.innerHTML = '';
                data.profiles.forEach(p => { const opt = document.createElement('option'); opt.value = p.key; opt.textContent = p.name; if (p.active) opt.selected = true; sel.appendChild(opt); });
                const saved = localStorage.getItem('activeProfile');
                if (saved && data.profiles.find(p => p.key === saved)) sel.value = saved;
                if (sel.value) localStorage.setItem('activeProfile', sel.value);
            } catch (e) { console.warn('加载数据源失败', e); }
        }

        function switchProfile() {
            const profile = document.getElementById('profileSelect').value;
            if (profile) localStorage.setItem('activeProfile', profile);
            loadTypes();
        }

        function getProfile() {
            return localStorage.getItem('activeProfile') || '';
        }

        let typeKeyword = '';
        let dataKeyword = '';
        let dataPage = 1;
        let dataTotal = 0;

        async function loadTypes() {
            const profile = getProfile();
            let url = '/api/settings/dict-types';
            if (profile) url += '?profile=' + encodeURIComponent(profile);
            if (typeKeyword) url += (profile ? '&' : '?') + 'keyword=' + encodeURIComponent(typeKeyword);
            try {
                const res = await fetch(url);
                const data = await res.json();
                if (!data.success) { document.getElementById('typeList').innerHTML = '<div class="empty">加载失败: ' + data.error + '</div>'; return; }
                typeList = data.rows || [];
                renderTypeList();
            } catch (e) { document.getElementById('typeList').innerHTML = '<div class="empty">加载失败</div>'; }
        }

        function searchTypes(kw) { typeKeyword = kw; loadTypes(); }
        function searchData() { dataKeyword = document.getElementById('dataKeyword').value; dataPage = 1; loadData(); }

        function renderTypeList() {
            const container = document.getElementById('typeList');
            if (typeList.length === 0) { container.innerHTML = '<div class="empty">暂无数据</div>'; return; }
            let html = '';
            typeList.forEach(t => {
                const active = t.id === selectedTypeId ? 'active' : '';
                const statusBadge = t.status === 0 ? '<span style="color:#10b981;margin-left:8px;">●</span>' : '<span style="color:#6b7280;margin-left:8px;">●</span>';
                html += '<div class="dict-item ' + active + '" onclick="selectType(' + t.id + ')">';
                html += '<div class="dict-item-name">' + escHtml(t.name || t.type) + statusBadge + '</div>';
                html += '<div class="dict-item-meta">' + escHtml(t.type || '') + ' | ' + (t.create_time || '-') + '</div>';
                html += '<div style="margin-top:8px;display:flex;gap:6px;">';
                html += '<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();editType(' + t.id + ')">编辑</button>';
                html += '<button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteType(' + t.id + ')">删除</button>';
                html += '</div></div>';
            });
            container.innerHTML = html;
        }

        function editType(id) { openTypeModal(id); }

        async function selectType(id) {
            selectedTypeId = id;
            renderTypeList();
            document.getElementById('addDataBtn').disabled = false;
            const t = typeList.find(x => x.id === id);
            document.getElementById('currentTypeName').textContent = t ? '- ' + escHtml(t.name || t.type) : '';
            loadData();
        }

        async function loadData() {
            if (!selectedTypeId) return;
            const profile = getProfile();
            let url = '/api/settings/dict-data?type_id=' + selectedTypeId + '&page=' + dataPage + '&page_size=20';
            if (profile) url += '&profile=' + encodeURIComponent(profile);
            if (dataKeyword) url += '&keyword=' + encodeURIComponent(dataKeyword);
            try {
                const res = await fetch(url);
                const data = await res.json();
                if (!data.success) { document.getElementById('dataList').innerHTML = '<div class="empty">加载失败</div>'; return; }
                dataTotal = data.total || 0;
                renderData(data.rows || []);
                renderDataPagination();
            } catch (e) { document.getElementById('dataList').innerHTML = '<div class="empty">加载失败</div>'; }
        }

        function renderDataPagination() {
            const totalPages = Math.ceil(dataTotal / 20);
            let html = '<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-top:1px solid var(--border);">';
            html += '<span style="font-size:13px;color:var(--text-secondary);">共 ' + dataTotal + ' 条</span>';
            html += '<div style="display:flex;gap:6px;">';
            html += '<button class="btn btn-secondary btn-sm" onclick="dataPage=1;loadData()" ' + (dataPage <= 1 ? 'disabled' : '') + '>首页</button>';
            html += '<button class="btn btn-secondary btn-sm" onclick="dataPage--;loadData()" ' + (dataPage <= 1 ? 'disabled' : '') + '>上一页</button>';
            html += '<span style="padding:4px 10px;font-size:13px;">' + dataPage + '/' + totalPages + '</span>';
            html += '<button class="btn btn-secondary btn-sm" onclick="dataPage++;loadData()" ' + (dataPage >= totalPages ? 'disabled' : '') + '>下一页</button>';
            html += '<button class="btn btn-secondary btn-sm" onclick="dataPage=totalPages;loadData()" ' + (dataPage >= totalPages ? 'disabled' : '') + '>末页</button>';
            html += '</div></div>';
            document.getElementById('dataPagination').innerHTML = html;
        }

        function renderData(rows) {
            const container = document.getElementById('dataList');
            if (rows.length === 0) {
                container.innerHTML = '<div class="empty">暂无数据</div>';
                return;
            }
            let html = '<div class="table-wrap"><table><thead><tr><th>标签</th><th>值</th><th>排序</th><th>状态</th><th>操作</th></tr></thead><tbody>';
            rows.forEach(d => {
                const statusBadge = d.status === 0 ? '<span style="color:#10b981">启用</span>' : '<span style="color:#6b7280">禁用</span>';
                html += '<tr>';
                html += '<td>' + escHtml(d.label || '') + '</td>';
                html += '<td>' + escHtml(d.value || '') + '</td>';
                html += '<td>' + (d.sort || 0) + '</td>';
                html += '<td>' + statusBadge + '</td>';
                html += '<td><button class="btn btn-secondary btn-sm" onclick="editData(' + d.id + ')">编辑</button> <button class="btn btn-danger btn-sm" onclick="deleteData(' + d.id + ')">删除</button></td>';
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }

        function openTypeModal(id) {
            document.getElementById('typeModal').classList.add('show');
            document.getElementById('typeModalTitle').textContent = id ? '编辑字典类型' : '新增字典类型';
            document.getElementById('typeId').value = id || '';
            if (id) {
                const t = typeList.find(x => x.id === id);
                if (t) {
                    document.getElementById('typeName').value = t.name || '';
                    document.getElementById('typeCode').value = t.type || '';
                    document.getElementById('typeStatus').value = t.status || 1;
                }
            } else {
                document.getElementById('typeName').value = '';
                document.getElementById('typeCode').value = '';
                document.getElementById('typeStatus').value = 1;
            }
        }

        async function saveType() {
            const id = document.getElementById('typeId').value;
            const name = document.getElementById('typeName').value;
            const type = document.getElementById('typeCode').value;
            const status = document.getElementById('typeStatus').value;
            if (!name) { alert('请输入名称'); return; }
            if (!type) { alert('请输入类型'); return; }

            const profile = getProfile();
            const res = await fetch('/api/settings/dict-type', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id || null, name, type, status: parseInt(status), profile})
            });
            const data = await res.json();
            if (data.success) {
                closeModal('typeModal');
                loadTypes();
            } else {
                alert('保存失败: ' + data.error);
            }
        }

        async function deleteType(id) {
            if (!confirm('确定要删除此字典类型吗？')) return;
            const profile = getProfile();
            const res = await fetch('/api/settings/dict-type', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, profile})
            });
            const data = await res.json();
            if (data.success) {
                if (selectedTypeId === id) selectedTypeId = null;
                loadTypes();
            } else {
                alert('删除失败: ' + data.error);
            }
        }

        function openDataModal(id) {
            document.getElementById('dataModal').classList.add('show');
            document.getElementById('dataModalTitle').textContent = id ? '编辑字典数据' : '新增字典数据';
            document.getElementById('dataId').value = id || '';
            if (id) {
                // 获取当前数据
                const profile = getProfile();
                fetch('/api/settings/dict-data?type_id=' + selectedTypeId + (profile ? '&profile=' + encodeURIComponent(profile) : ''))
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            const d = (data.rows || []).find(x => x.id === id);
                            if (d) {
                                document.getElementById('dataLabel').value = d.label || '';
                                document.getElementById('dataValue').value = d.value || '';
                                document.getElementById('dataSort').value = d.sort || 0;
                                document.getElementById('dataStatus').value = d.status || 1;
                            }
                        }
                    });
            } else {
                document.getElementById('dataLabel').value = '';
                document.getElementById('dataValue').value = '';
                document.getElementById('dataSort').value = 0;
                document.getElementById('dataStatus').value = 0;
            }
        }

        async function saveData() {
            const id = document.getElementById('dataId').value;
            const label = document.getElementById('dataLabel').value;
            const value = document.getElementById('dataValue').value;
            const sort = document.getElementById('dataSort').value;
            const status = document.getElementById('dataStatus').value;
            const currentType = typeList.find(x => x.id === selectedTypeId);
            const dict_type = currentType ? currentType.type : '';
            if (!label) { alert('请输入标签'); return; }
            if (!value) { alert('请输入值'); return; }

            const profile = getProfile();
            const res = await fetch('/api/settings/dict-data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id || null, type_id: selectedTypeId, dict_type, label, value, sort: parseInt(sort), status: parseInt(status), profile})
            });
            const data = await res.json();
            if (data.success) {
                closeModal('dataModal');
                loadData();
            } else {
                alert('保存失败: ' + data.error);
            }
        }

        async function deleteData(id) {
            if (!confirm('确定要删除此字典数据吗？')) return;
            const profile = getProfile();
            const res = await fetch('/api/settings/dict-data', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, profile})
            });
            const data = await res.json();
            if (data.success) {
                loadData();
            } else {
                alert('删除失败: ' + data.error);
            }
        }

        function editData(id) { openDataModal(id); }

        function closeModal(id) { document.getElementById(id).classList.remove('show'); }
        function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

        init();
    </script>
</body>
</html>"""

    @app.route('/dict-config')
    def dict_config_page():
        if not check_admin_session():
            return render_template_string(PASSWORD_TEMPLATE)
        return render_template_string(DICT_CONFIG_TEMPLATE)

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
                
                # 获取 db_monitor 配置
                db_monitor_config = profile.get('db_monitor', {})
                
                # 获取 server_data_source 配置
                server_data_source = profile.get('server_data_source', {})
                
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
                    },
                    'db_monitor': {
                        'host': db_monitor_config.get('host', ''),
                        'port': db_monitor_config.get('port', 3306),
                        'database': db_monitor_config.get('database', ''),
                        'user': db_monitor_config.get('user', ''),
                        'password': ''  # 密码不返回
                    },
                    'server_data_source': {
                        'host': server_data_source.get('host', ''),
                        'port': server_data_source.get('port', 22),
                        'username': server_data_source.get('username', ''),
                        'password': ''  # 密码不返回
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

    @app.route('/api/settings/valid_profiles')
    def api_get_valid_profiles():
        """获取数据源列表（返回系统设置中所有已配置的环境）"""
        try:
            config = load_config()
            valid_profiles = []
            active_profile = config.get('active_profile', 'default')

            for name, profile in config.get('profiles', {}).items():
                valid_profiles.append({
                    'key': name,
                    'name': profile.get('name', name),
                    'active': name == active_profile
                })

            return jsonify({
                'success': True,
                'profiles': valid_profiles,
                'activeProfile': active_profile
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

    @app.route('/api/settings/switch_profile', methods=['POST'])
    def api_switch_profile():
        """切换当前激活的数据源"""
        try:
            data = request.json
            new_profile = data.get('profile', 'default')

            config = load_config()

            # 检查目标 profile 是否存在且有效
            profile = config.get('profiles', {}).get(new_profile)
            if not profile:
                return jsonify({'success': False, 'error': '数据源不存在'}), 400

            video = profile.get('video', {})
            if not (video.get('host') and video.get('database') and video.get('user')):
                return jsonify({'success': False, 'error': '数据源配置不完整'}), 400

            # 切换数据源
            config['active_profile'] = new_profile
            save_config(config)

            return jsonify({
                'success': True,
                'activeProfile': new_profile,
                'profileName': profile.get('name', new_profile)
            })
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
    
    @app.route('/api/settings/test_db_monitor', methods=['POST'])
    def api_test_db_monitor():
        """测试数据库监控连接"""
        try:
            data = request.json
            db_monitor_config = {
                'host': data.get('host', 'localhost'),
                'port': data.get('port', 3306),
                'database': data.get('database', 'information_schema'),
                'user': data.get('user', 'root'),
                'password': data.get('password', '')
            }
            result = test_db_monitor_connection(db_monitor_config)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/settings/test_server_data_source', methods=['POST'])
    def api_test_server_data_source():
        """测试服务器数据源连接"""
        try:
            data = request.json
            server_data_source_config = {
                'host': data.get('host', 'localhost'),
                'port': data.get('port', 22),
                'username': data.get('username', 'root'),
                'password': data.get('password', '')
            }
            result = test_server_data_source_connection(server_data_source_config)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ========== 字典配置 API ==========
    def _get_db_config_for_dict(profile_name=None):
        """获取字典配置的数据库连接参数"""
        config = get_video_db_config_for_profile(profile_name)
        if not config:
            # 使用默认配置
            return {
                'host': '101.126.91.130',
                'port': 4005,
                'database': 'videoai',
                'user': 'yiyuzhou',
                'password': 'yiyuzhou5066995',
                'charset': 'utf8mb4',
                'connect_timeout': 5
            }
        return {
            'host': config.get('host'),
            'port': config.get('port', 3306),
            'database': config.get('database', 'videoai'),
            'user': config.get('user'),
            'password': config.get('password', ''),
            'charset': 'utf8mb4',
            'connect_timeout': 5
        }

    def _query_dict_db(sql, params=None, profile_name=None):
        """执行字典配置的数据库查询"""
        db_config = _get_db_config_for_dict(profile_name)
        conn = mysql.connector.connect(**db_config)
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            cursor.close()
            return rows
        finally:
            conn.close()

    @app.route('/api/settings/dict-types')
    def api_dict_types():
        """获取字典类型列表"""
        try:
            profile = request.args.get('profile')
            keyword = request.args.get('keyword', '').strip()

            sql = "SELECT id, name, type, status, create_time FROM videoai.system_dict_type WHERE deleted = 0"
            params = []
            if keyword:
                sql += " AND (name LIKE %s OR type LIKE %s)"
                params = ['%' + keyword + '%', '%' + keyword + '%']
            sql += " ORDER BY id DESC"

            rows = _query_dict_db(sql, tuple(params) if params else None, profile_name=profile)
            return jsonify({'success': True, 'rows': rows})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/dict-data')
    def api_dict_data():
        """获取字典数据列表（支持搜索和分页）"""
        try:
            profile = request.args.get('profile')
            type_id = request.args.get('type_id')
            keyword = request.args.get('keyword', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(1, int(request.args.get('page_size', 20))))

            if not type_id:
                return jsonify({'success': False, 'error': '缺少 type_id 参数'}), 400

            # 条件
            where_clauses = ["deleted = 0", "type_id = %s"]
            params = [type_id]
            if keyword:
                where_clauses.append("(label LIKE %s OR value LIKE %s)")
                params.extend(['%' + keyword + '%', '%' + keyword + '%'])

            where_sql = " AND ".join(where_clauses)

            # 总数
            count_sql = f"SELECT COUNT(*) as cnt FROM videoai.system_dict_data WHERE {where_sql}"
            count_rows = _query_dict_db(count_sql, tuple(params), profile_name=profile)
            total = count_rows[0]['cnt'] if count_rows else 0

            # 数据
            offset = (page - 1) * page_size
            data_sql = f"SELECT id, label, value, status, dict_type, sort FROM videoai.system_dict_data WHERE {where_sql} ORDER BY sort ASC LIMIT {page_size} OFFSET {offset}"
            rows = _query_dict_db(data_sql, tuple(params), profile_name=profile)

            return jsonify({'success': True, 'rows': rows, 'total': total, 'page': page, 'page_size': page_size})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/dict-type', methods=['POST'])
    def api_save_dict_type():
        """新增/编辑字典类型"""
        try:
            data = request.json
            profile = data.get('profile')
            dict_id = data.get('id')
            name = data.get('name')
            dict_type = data.get('type')
            status = data.get('status', 1)

            db_config = _get_db_config_for_dict(profile)
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            try:
                if dict_id:
                    sql = "UPDATE videoai.system_dict_type SET name=%s, type=%s, status=%s, update_time=NOW(), version=version+1 WHERE id=%s"
                    cursor.execute(sql, (name, dict_type, status, dict_id))
                else:
                    sql = "INSERT INTO videoai.system_dict_type (name, type, status, deleted, create_time, update_time, version) VALUES (%s, %s, %s, 0, NOW(), NOW(), 1)"
                    cursor.execute(sql, (name, dict_type, status))
                conn.commit()
                return jsonify({'success': True})
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/dict-type', methods=['DELETE'])
    def api_delete_dict_type():
        """删除字典类型"""
        try:
            data = request.json
            profile = data.get('profile')
            dict_id = data.get('id')

            db_config = _get_db_config_for_dict(profile)
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            try:
                # 软删除
                cursor.execute("UPDATE videoai.system_dict_type SET deleted=1 WHERE id=%s", (dict_id,))
                # 同时删除关联的字典数据
                cursor.execute("UPDATE videoai.system_dict_data SET deleted=1 WHERE type_id=%s", (dict_id,))
                conn.commit()
                return jsonify({'success': True})
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/dict-data', methods=['POST'])
    def api_save_dict_data():
        """新增/编辑字典数据"""
        try:
            data = request.json
            profile = data.get('profile')
            dict_id = data.get('id')
            type_id = data.get('type_id')
            dict_type = data.get('dict_type')
            label = data.get('label')
            value = data.get('value')
            status = data.get('status', 0)
            sort = data.get('sort', 0)

            db_config = _get_db_config_for_dict(profile)
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            try:
                if dict_id:
                    sql = "UPDATE videoai.system_dict_data SET type_id=%s, dict_type=%s, label=%s, value=%s, status=%s, sort=%s, update_time=NOW(), version=version+1 WHERE id=%s"
                    cursor.execute(sql, (type_id, dict_type, label, value, status, sort, dict_id))
                else:
                    sql = "INSERT INTO videoai.system_dict_data (type_id, dict_type, label, value, status, sort, deleted, create_time, update_time, version) VALUES (%s, %s, %s, %s, %s, %s, 0, NOW(), NOW(), 1)"
                    cursor.execute(sql, (type_id, dict_type, label, value, status, sort))
                conn.commit()
                return jsonify({'success': True})
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/settings/dict-data', methods=['DELETE'])
    def api_delete_dict_data():
        """删除字典数据"""
        try:
            data = request.json
            profile = data.get('profile')
            dict_id = data.get('id')

            db_config = _get_db_config_for_dict(profile)
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE videoai.system_dict_data SET deleted=1 WHERE id=%s", (dict_id,))
                conn.commit()
                return jsonify({'success': True})
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


# 初始化时自动加载配置
def init_db_config():
    """初始化数据库配置（在主程序启动时调用）"""
    config = load_config()
    print(f"Database config loaded: active_profile={config.get('active_profile', 'default')}")
    return config
