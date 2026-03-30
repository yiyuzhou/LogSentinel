#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志监控模块 - 实时监控和排查日志问题
"""

from flask import render_template_string, jsonify, request
import paramiko
import os
import sys
from datetime import datetime

# 从 settings 模块加载 SSH 配置
from settings import get_ssh_config

# 全局 SSH 配置（启动时加载，可通过 reload 更新）
SSH_CONFIG = get_ssh_config()
LOG_DIR = SSH_CONFIG.get('log_dir', '/home/ubuntu/workspace/logs/translator')


def reload_ssh_config(profile=None):
    """重新加载 SSH 配置
    
    Args:
        profile: 指定配置档名称，如果为 None 则使用当前激活的配置
    """
    global SSH_CONFIG, LOG_DIR
    from settings import load_config, decode_password
    
    config = load_config()
    
    # 如果指定了 profile，使用该 profile 的配置
    if profile:
        profile_data = config.get('profiles', {}).get(profile)
        if profile_data:
            ssh_config = profile_data.get('ssh_config', {})
            if ssh_config.get('hostname'):
                SSH_CONFIG = {
                    'hostname': ssh_config.get('hostname', ''),
                    'port': ssh_config.get('port', 22),
                    'username': ssh_config.get('username', ''),
                    'password': decode_password(ssh_config.get('password', '')),
                    'log_dir': ssh_config.get('log_dir', '')
                }
                LOG_DIR = SSH_CONFIG.get('log_dir', '/home/ubuntu/workspace/logs/translator')
                return
    
    # 使用默认逻辑（当前激活的 profile）
    SSH_CONFIG = get_ssh_config()
    LOG_DIR = SSH_CONFIG.get('log_dir', '/home/ubuntu/workspace/logs/translator')

def get_ssh_client():
    """获取 SSH 连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=SSH_CONFIG.get('hostname', ''),
        port=SSH_CONFIG.get('port', 22),
        username=SSH_CONFIG.get('username', ''),
        password=SSH_CONFIG.get('password', ''),
        timeout=10
    )
    return client

def list_log_files():
    """列出日志文件"""
    try:
        client = get_ssh_client()
        sftp = client.open_sftp()
        files = []
        try:
            for entry in sftp.listdir_attr(LOG_DIR):
                if entry.filename.endswith('.log'):
                    files.append({
                        'name': entry.filename,
                        'size': entry.st_size,
                        'mtime': datetime.fromtimestamp(entry.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
        except FileNotFoundError:
            pass
        sftp.close()
        client.close()
        
        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x['mtime'], reverse=True)
        return files
    except Exception as e:
        print(f"List logs error: {e}", file=sys.stderr)
        return []

def get_log_content(filename, lines=500, search=None):
    """获取日志内容"""
    try:
        client = get_ssh_client()
        
        # 构建命令
        filepath = f"{LOG_DIR}/{filename}"
        if search:
            # 搜索时返回所有匹配行及行号
            cmd = f"grep -n '{search}' '{filepath}'"
            stdin, stdout, stderr = client.exec_command(cmd)
            content = stdout.read().decode('utf-8', errors='replace')
            
            # 获取完整日志文件用于上下文
            cmd_all = f"cat '{filepath}'"
            stdin_all, stdout_all, stderr_all = client.exec_command(cmd_all)
            all_content = stdout_all.read().decode('utf-8', errors='replace')
            all_lines = all_content.split('\n')
            
            # 解析匹配行
            match_lines = []
            match_indices = []  # 匹配行在完整日志中的索引（0-based）
            for line in content.strip().split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        try:
                            line_num = int(parts[0])
                            match_lines.append({'line_num': line_num, 'content': parts[1]})
                            match_indices.append(line_num - 1)  # 转为 0-based 索引
                        except ValueError:
                            pass
            
            client.close()
            return {
                'success': True,
                'content': content,
                'lines': len(match_lines),
                'match_lines': match_lines,
                'match_indices': match_indices,
                'all_lines': all_lines,
                'total_matches': len(match_lines)
            }
        else:
            cmd = f"tail -n {lines} '{filepath}'"
            stdin, stdout, stderr = client.exec_command(cmd)
            content = stdout.read().decode('utf-8', errors='replace')
            
            client.close()
            return {'success': True, 'content': content, 'lines': len(content.split('\n'))}
    except Exception as e:
        print(f"Get log error: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e)}

def tail_log(filename, lines=100):
    """实时查看日志（最新 N 行）"""
    return get_log_content(filename, lines)

def get_log_lines_count(filename):
    """获取日志文件总行数"""
    try:
        client = get_ssh_client()
        filepath = f"{LOG_DIR}/{filename}"
        cmd = f"wc -l '{filepath}'"
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        client.close()
        if output:
            return int(output.split()[0])
        return 0
    except Exception as e:
        print(f"Get line count error: {e}", file=sys.stderr)
        return 0

def get_new_log_lines(filename, start_line, lines=100):
    """获取新增的日志行（从 start_line 开始）"""
    try:
        client = get_ssh_client()
        filepath = f"{LOG_DIR}/{filename}"
        cmd = f"tail -n +{start_line + 1} '{filepath}' | tail -n {lines}"
        stdin, stdout, stderr = client.exec_command(cmd)
        content = stdout.read().decode('utf-8', errors='replace')
        client.close()
        return {'success': True, 'content': content, 'lines': len(content.split('\n'))}
    except Exception as e:
        print(f"Get new log error: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e)}

def get_log_stats(filename):
    """获取日志文件统计信息（总行数、文件大小等）"""
    try:
        client = get_ssh_client()
        filepath = f"{LOG_DIR}/{filename}"
        # 获取总行数
        cmd_lines = f"wc -l '{filepath}'"
        stdin, stdout, stderr = client.exec_command(cmd_lines)
        lines_output = stdout.read().decode('utf-8', errors='replace').strip()
        total_lines = int(lines_output.split()[0]) if lines_output else 0
        
        # 获取文件大小
        cmd_size = f"stat -c %s '{filepath}'"
        stdin, stdout, stderr = client.exec_command(cmd_size)
        size_output = stdout.read().decode('utf-8', errors='replace').strip()
        file_size = int(size_output) if size_output else 0
        
        # 获取最后修改时间
        cmd_mtime = f"stat -c %Y '{filepath}'"
        stdin, stdout, stderr = client.exec_command(cmd_mtime)
        mtime_output = stdout.read().decode('utf-8', errors='replace').strip()
        mtime = datetime.fromtimestamp(int(mtime_output)).strftime('%Y-%m-%d %H:%M:%S') if mtime_output else '-'
        
        client.close()
        return {'success': True, 'total_lines': total_lines, 'file_size': file_size, 'mtime': mtime}
    except Exception as e:
        print(f"Get log stats error: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e), 'total_lines': 0, 'file_size': 0, 'mtime': '-'}

def get_log_context(filename, line_index, context_lines=10):
    """获取指定行周围的上下文日志"""
    try:
        client = get_ssh_client()
        filepath = f"{LOG_DIR}/{filename}"
        
        # 计算起始行和结束行
        start_line = max(1, line_index - context_lines + 1)
        end_line = line_index + context_lines + 1
        
        cmd = f"sed -n '{start_line},{end_line}p' '{filepath}'"
        stdin, stdout, stderr = client.exec_command(cmd)
        content = stdout.read().decode('utf-8', errors='replace')
        
        client.close()
        lines = content.split('\n')
        return {
            'success': True,
            'lines': lines,
            'start_line': start_line,
            'end_line': end_line,
            'total_lines': len(lines),
            'highlight_index': context_lines  # 在返回的行数组中，高亮行的索引
        }
    except Exception as e:
        print(f"Get log context error: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e)}

def download_log_file(filename, lines='all'):
    """下载日志文件（支持部分下载）"""
    try:
        client = get_ssh_client()
        filepath = f"{LOG_DIR}/{filename}"
        
        # 验证文件是否存在
        sftp = client.open_sftp()
        try:
            file_attr = sftp.stat(filepath)
            file_size = file_attr.st_size
        except FileNotFoundError:
            sftp.close()
            client.close()
            return {'success': False, 'error': '文件不存在', 'file_size': 0}
        sftp.close()
        
        # 构建下载命令
        if lines == 'all':
            cmd = f"cat '{filepath}'"
        elif lines == '1000':
            cmd = f"tail -n 1000 '{filepath}'"
        elif lines == '5000':
            cmd = f"tail -n 5000 '{filepath}'"
        else:
            cmd = f"cat '{filepath}'"
        
        # 执行命令获取内容
        stdin, stdout, stderr = client.exec_command(cmd)
        content = stdout.read().decode('utf-8', errors='replace')
        error_output = stderr.read().decode('utf-8', errors='replace')
        
        client.close()
        
        if error_output and not content:
            return {'success': False, 'error': error_output, 'file_size': file_size}
        
        return {
            'success': True,
            'content': content,
            'file_size': file_size,
            'lines': len(content.split('\n')),
            'download_lines': lines
        }
    except Exception as e:
        print(f"Download log error: {e}", file=sys.stderr)
        return {'success': False, 'error': str(e), 'file_size': 0}

def validate_log_file(filename):
    """验证日志文件路径，防止路径遍历攻击"""
    # 只允许字母、数字、下划线、连字符和 .log 后缀
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+\.log$', filename):
        return False
    # 确保不包含路径分隔符
    if '/' in filename or '\\' in filename or '..' in filename:
        return False
    return True

# 日志监控页面 HTML
LOG_VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日志监控 - 视频任务运维系统</title>
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
        
        /* 日志监控布局 */
        .log-container { display: grid; grid-template-columns: 300px 1fr; gap: 20px; height: calc(100vh - 120px); }
        .log-sidebar { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
        .log-sidebar-header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); }
        .log-sidebar-header h2 { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .log-file-list { flex: 1; overflow-y: auto; padding: 8px; }
        .log-file-item { padding: 12px 16px; border-radius: 8px; cursor: pointer; transition: all 0.2s; margin-bottom: 4px; border: 1px solid transparent; position: relative; }
        .log-file-item:hover { background: var(--bg-hover); border-color: var(--border); }
        .log-file-item.active { background: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(29, 78, 216, 0.1) 100%); border-color: var(--primary); }
        .log-file-name { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; word-break: break-all; padding-right: 40px; }
        .log-file-meta { font-size: 11px; color: var(--text-secondary); display: flex; justify-content: space-between; }
        .log-file-size { color: var(--info); }
        
        /* 文件下载按钮 */
        .file-download-btn { 
            position: absolute; 
            right: 10px; 
            top: 50%; 
            transform: translateY(-50%);
            background: var(--bg-hover); 
            border: 1px solid var(--border); 
            border-radius: 4px; 
            color: var(--text-primary); 
            cursor: pointer; 
            font-size: 14px; 
            padding: 4px 8px;
            opacity: 0;
            transition: all 0.2s;
            display: none;
            z-index: 10;
        }
        .log-file-item:hover .file-download-btn { opacity: 1; display: block; }
        .file-download-btn:hover { background: var(--primary); border-color: var(--primary); }
        
        /* 下载行数选择菜单 */
        .file-download-menu {
            position: absolute;
            right: 45px;
            top: 50%;
            transform: translateY(-50%);
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px;
            display: none;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .file-download-menu.show { display: block; }
        .file-download-menu-item {
            padding: 6px 12px;
            cursor: pointer;
            font-size: 12px;
            border-radius: 4px;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .file-download-menu-item:hover { background: var(--bg-hover); }
        
        .log-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
        .log-content-header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
        .log-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .log-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .download-group { display: flex; align-items: center; gap: 8px; background: var(--bg-dark); padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); }
        .download-select { padding: 6px 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); font-size: 12px; cursor: pointer; }
        .download-select:focus { outline: none; border-color: var(--primary); }
        .search-box { display: flex; align-items: center; gap: 8px; }
        .search-input { padding: 8px 12px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary); font-size: 13px; width: 200px; }
        .search-input:focus { outline: none; border-color: var(--primary); }
        .btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
        .btn-secondary { background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .btn-success { background: linear-gradient(135deg, var(--success) 0%, #047857 100%); color: white; }
        .btn-warning { background: linear-gradient(135deg, var(--warning) 0%, #b45309 100%); color: white; }
        
        .realtime-toggle { display: flex; align-items: center; gap: 8px; background: var(--bg-dark); padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); }
        .realtime-toggle label { font-size: 13px; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; gap: 6px; }
        .realtime-toggle input[type="checkbox"] { accent-color: var(--success); }
        .realtime-active { border-color: var(--success); background: rgba(5, 150, 105, 0.1); }
        .realtime-indicator { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 1s infinite; display: none; }
        .realtime-active .realtime-indicator { display: inline-block; }
        
        .log-viewer { flex: 1; overflow-y: auto; padding: 16px; background: #0d1117; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; }
        .log-line { padding: 2px 0; white-space: pre-wrap; word-break: break-word; cursor: pointer; position: relative; }
        .log-line:hover { background: rgba(37, 99, 235, 0.1); }
        .log-line.match-highlight { background: rgba(234, 179, 8, 0.3); border-left: 3px solid #fbbf24; }
        .log-line.match-highlight:hover { background: rgba(234, 179, 8, 0.5); }
        .log-line.current-match { background: rgba(234, 179, 8, 0.5); border-left: 3px solid #f59e0b; }
        .log-line.ERROR, .log-line.error { color: #f87171; }
        .log-line.WARN, .log-line.WARNING, .log-line.warn, .log-line.warning { color: #fbbf24; }
        .log-line.INFO, .log-line.info { color: #34d399; }
        .log-line.DEBUG, .log-line.debug { color: #60a5fa; }
        .log-timestamp { color: var(--text-secondary); margin-right: 12px; }
        .log-level { font-weight: 600; margin-right: 12px; padding: 2px 8px; border-radius: 4px; }
        .log-level.ERROR { background: rgba(220, 38, 38, 0.2); }
        .log-level.WARN, .log-level.WARNING { background: rgba(217, 119, 6, 0.2); }
        .log-level.INFO { background: rgba(5, 150, 105, 0.2); }
        .log-level.DEBUG { background: rgba(59, 130, 246, 0.2); }
        
        /* 搜索导航控件 */
        .search-nav { display: flex; align-items: center; gap: 8px; background: var(--bg-dark); padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); margin-left: 8px; }
        .search-nav-count { font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
        .search-nav-btn { padding: 4px 10px; background: var(--bg-hover); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); cursor: pointer; font-size: 12px; transition: all 0.2s; }
        .search-nav-btn:hover:not(:disabled) { background: var(--primary); border-color: var(--primary); }
        .search-nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* 上下文提示框 */
        .context-tooltip { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; font-size: 11px; color: var(--text-secondary); z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: none; max-width: 400px; pointer-events: none; }
        .log-line:hover .context-tooltip { display: block; }
        .context-tooltip-title { font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
        .context-tooltip-content { font-family: 'Consolas', monospace; font-size: 10px; line-height: 1.4; max-height: 150px; overflow: hidden; opacity: 0.8; }
        
        .log-loading { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); }
        .spinner { border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; width: 48px; height: 48px; animation: spin 1s linear infinite; margin-right: 16px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .auto-refresh-control { display: flex; align-items: center; gap: 8px; background: var(--bg-dark); padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); }
        .auto-refresh-control label { font-size: 13px; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; gap: 6px; }
        .auto-refresh-control input[type="checkbox"] { accent-color: var(--primary); }
        
        .no-file-selected { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); font-size: 16px; }
        .no-file-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        
        .auto-refresh-control { display: none; } /* 已废弃，使用 realtime-toggle */
        
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
            <a href="/logs" class="menu-item active" data-page="logs">
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
    
    <div class="main-wrapper" id="mainWrapper">
        <div class="main-content">
            <div class="log-container">
                <div class="log-sidebar">
                    <div class="log-sidebar-header">
                        <h2>📁 日志文件</h2>
                    </div>
                    <div class="log-file-list" id="logFileList">
                        <div class="log-loading"><div class="spinner"></div>加载中...</div>
                    </div>
                </div>
                
                <div class="log-content">
                    <div class="log-content-header">
                        <div class="log-title" id="logTitle">📄 请选择日志文件</div>
                        <div class="log-controls">
                            <div class="download-group">
                                <select id="downloadLines" class="download-select" title="选择下载行数">
                                    <option value="all">全部</option>
                                    <option value="5000">最近 5000 行</option>
                                    <option value="1000">最近 1000 行</option>
                                </select>
                                <button class="btn btn-success" onclick="downloadLog()" title="下载日志文件">📥 下载日志</button>
                            </div>
                            <div class="search-box">
                                <input type="text" id="searchInput" class="search-input" placeholder="搜索关键词...">
                                <button class="btn btn-primary" onclick="applySearch()">🔍 搜索</button>
                            </div>
                            <div class="search-nav" id="searchNav" style="display: none;">
                                <button class="search-nav-btn" id="prevMatchBtn" onclick="navigateToPrevMatch()" title="上一个匹配">◀ 上一个</button>
                                <span class="search-nav-count" id="matchCounter">找到 0 处匹配</span>
                                <button class="search-nav-btn" id="nextMatchBtn" onclick="navigateToNextMatch()" title="下一个匹配">下一个 ▶</button>
                            </div>
                            <button class="btn btn-secondary" onclick="loadCurrentLog()">🔄 刷新</button>
                            <div class="realtime-toggle" id="realtimeToggle">
                                <span class="realtime-indicator"></span>
                                <label><input type="checkbox" id="realtimeMode" checked> ⚡ 实时模式 (3s)</label>
                            </div>
                        </div>
                    </div>
                    <div style="padding: 8px 20px; background: var(--bg-dark); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center;">
                        <span id="logStats">等待选择文件...</span>
                        <span id="lastUpdateTime">最后更新：-</span>
                    </div>
                    <div class="log-viewer" id="logViewer">
                        <div class="no-file-selected">
                            <div style="text-align: center;">
                                <div class="no-file-icon">📭</div>
                                <p>请从左侧选择日志文件</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentFile = null;
        let autoRefreshTimer = null;
        let searchKeyword = '';
        let realtimeMode = true; // 默认开启实时模式
        let lastLineCount = 0; // 记录上次加载的行数，用于增量更新
        let totalLines = 0; // 文件总行数
        
        // 搜索匹配相关
        let matchIndices = []; // 所有匹配行的索引（0-based）
        let currentMatchIndex = -1; // 当前选中的匹配索引
        let allLogLines = []; // 完整日志行（搜索时使用）
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1024 / 1024).toFixed(1) + ' MB';
        }
        
        function formatTime(seconds) {
            if (seconds < 60) return seconds.toFixed(1) + ' 秒';
            if (seconds < 3600) return (seconds / 60).toFixed(1) + ' 分钟';
            return (seconds / 3600).toFixed(1) + ' 小时';
        }
        
        // 切换下载菜单显示/隐藏
        function toggleDownloadMenu(event, filename) {
            event.stopPropagation(); // 阻止触发 selectFile
            const menuId = 'downloadMenu-' + filename.replace(/[^a-zA-Z0-9_-]/g, '_');
            const menu = document.getElementById(menuId);
            
            // 关闭其他菜单
            document.querySelectorAll('.file-download-menu').forEach(m => {
                if (m.id !== menuId) m.classList.remove('show');
            });
            
            menu.classList.toggle('show');
        }
        
        // 从列表直接下载文件
        async function downloadFileFromList(event, filename, lines) {
            event.stopPropagation(); // 阻止触发 selectFile
            
            // 关闭菜单
            const menuId = 'downloadMenu-' + filename.replace(/[^a-zA-Z0-9_-]/g, '_');
            const menu = document.getElementById(menuId);
            if (menu) menu.classList.remove('show');
            
            const originalFile = currentFile;
            currentFile = filename; // 临时设置当前文件
            
            try {
                // 首先获取文件信息
                const statsRes = await fetch('/api/logs/stats?file=' + encodeURIComponent(filename));
                const statsData = await statsRes.json();
                
                if (!statsData.success) {
                    throw new Error(statsData.error || '获取文件信息失败');
                }
                
                const fileSize = statsData.file_size || 0;
                const totalLines = statsData.total_lines || 0;
                
                // 大文件警告
                if (fileSize > 100 * 1024 * 1024) { // 100MB
                    const confirmMsg = `⚠️ 警告：文件较大 (${formatSize(fileSize)})\\n\\n下载可能需要较长时间，确定继续下载吗？`;
                    if (!confirm(confirmMsg)) {
                        currentFile = originalFile;
                        return;
                    }
                }
                
                // 计算预计下载时间（假设 1MB/s）
                const estimatedTime = fileSize / (1024 * 1024); // 秒
                const linesText = lines === 'all' ? '全部' : lines;
                
                // 构建下载 URL
                const downloadUrl = `/api/logs/download?file=${encodeURIComponent(filename)}&lines=${lines}`;
                
                // 创建临时链接触发下载
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                console.log(`✅ 已开始下载：${filename} (${linesText} 行)`);
                
            } catch (err) {
                console.error('Download error:', err);
                alert('❌ 下载失败：' + err.message);
            } finally {
                currentFile = originalFile; // 恢复原文件
            }
        }
        
        // 点击页面其他地方关闭下载菜单
        document.addEventListener('click', function() {
            document.querySelectorAll('.file-download-menu').forEach(m => m.classList.remove('show'));
        });
        
        async function downloadLog() {
            if (!currentFile) {
                alert('请先选择日志文件');
                return;
            }
            
            const linesSelect = document.getElementById('downloadLines');
            const lines = linesSelect.value;
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            // 禁用按钮，显示加载状态
            btn.disabled = true;
            btn.innerHTML = '⏳ 准备中...';
            
            try {
                // 首先获取文件信息
                const statsRes = await fetch('/api/logs/stats?file=' + encodeURIComponent(currentFile));
                const statsData = await statsRes.json();
                
                if (!statsData.success) {
                    throw new Error(statsData.error || '获取文件信息失败');
                }
                
                const fileSize = statsData.file_size || 0;
                const totalLines = statsData.total_lines || 0;
                
                // 大文件警告
                if (fileSize > 100 * 1024 * 1024) { // 100MB
                    const confirmMsg = `⚠️ 警告：文件较大 (${formatSize(fileSize)})\n\n下载可能需要较长时间，确定继续下载吗？`;
                    if (!confirm(confirmMsg)) {
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                        return;
                    }
                }
                
                // 计算预计下载时间（假设 1MB/s）
                const estimatedTime = fileSize / (1024 * 1024); // 秒
                const linesText = lines === 'all' ? '全部' : lines;
                updateLogStatus(`准备下载：${linesText} 行，文件大小 ${formatSize(fileSize)}，预计 ${formatTime(estimatedTime)}`);
                
                // 构建下载 URL
                const downloadUrl = `/api/logs/download?file=${encodeURIComponent(currentFile)}&lines=${lines}`;
                
                // 创建临时链接触发下载
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                updateLogStatus(`✅ 已开始下载：${linesText} 行`);
                
            } catch (err) {
                console.error('Download error:', err);
                alert('❌ 下载失败：' + err.message);
                updateLogStatus('下载失败：' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
        
        function updateLastUpdateTime() {
            const now = new Date();
            document.getElementById('lastUpdateTime').textContent = '最后更新：' + now.toLocaleString('zh-CN');
        }
        
        function updateLogStatus(message) {
            const logStatsEl = document.getElementById('logStats');
            if (logStatsEl) logStatsEl.textContent = message;
        }
        
        async function loadFileList() {
            try {
                // 从 localStorage 读取当前激活的 profile
                const activeProfile = localStorage.getItem('activeProfile') || '';
                const profileParam = activeProfile ? '?profile=' + encodeURIComponent(activeProfile) : '';
                const res = await fetch('/api/logs/list' + profileParam);
                const data = await res.json();
                if (!data.success) throw new Error(data.error);
                
                const files = data.files || [];
                const listEl = document.getElementById('logFileList');
                
                if (files.length === 0) {
                    listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">暂无日志文件</div>';
                    return;
                }
                
                let html = '';
                files.forEach(file => {
                    const isActive = currentFile === file.name ? 'active' : '';
                    html += '<div class="log-file-item ' + isActive + '" onclick="selectFile(\\'' + file.name + '\\')">';
                    html += '<div class="log-file-name">📄 ' + file.name + '</div>';
                    html += '<div class="log-file-meta">';
                    html += '<span>🕐 ' + file.mtime + '</span>';
                    html += '<span class="log-file-size">📦 ' + formatSize(file.size) + '</span>';
                    html += '</div>';
                    // 下载按钮和菜单
                    html += '<div class="file-download-menu" id="downloadMenu-' + file.name.replace(/[^a-zA-Z0-9_-]/g, '_') + '">';
                    html += '<div class="file-download-menu-item" onclick="downloadFileFromList(event, \\'' + file.name + '\\', \\'all\\')">📥 下载全部</div>';
                    html += '<div class="file-download-menu-item" onclick="downloadFileFromList(event, \\'' + file.name + '\\', \\'5000\\')">📥 最近 5000 行</div>';
                    html += '<div class="file-download-menu-item" onclick="downloadFileFromList(event, \\'' + file.name + '\\', \\'1000\\')">📥 最近 1000 行</div>';
                    html += '</div>';
                    html += '<button class="file-download-btn" onclick="toggleDownloadMenu(event, \\'' + file.name + '\\')" title="下载日志">📥</button>';
                    html += '</div>';
                });
                listEl.innerHTML = html;
            } catch (err) {
                console.error('Load file list error:', err);
                document.getElementById('logFileList').innerHTML = '<div style="padding: 20px; color: var(--danger);">❌ 加载失败：' + err.message + '</div>';
            }
        }
        
        async function selectFile(filename) {
            currentFile = filename;
            lastLineCount = 0; // 重置行数计数
            totalLines = 0;
            document.getElementById('logTitle').textContent = '📄 ' + filename;
            loadFileList(); // 更新高亮
            
            // 选中文件后自动开启实时模式
            const realtimeCheckbox = document.getElementById('realtimeMode');
            if (!realtimeCheckbox.checked) {
                realtimeCheckbox.checked = true;
                toggleRealtimeMode(true);
            }
            
            // 加载文件统计信息
            await loadLogStats(filename);
            
            loadCurrentLog(true); // 全量加载
        }
        
        async function loadLogStats(filename) {
            try {
                // 从 localStorage 读取当前激活的 profile
                const activeProfile = localStorage.getItem('activeProfile') || '';
                const profileParam = activeProfile ? '&profile=' + encodeURIComponent(activeProfile) : '';
                const res = await fetch('/api/logs/stats?file=' + encodeURIComponent(filename) + profileParam);
                const data = await res.json();
                if (data.success) {
                    const statsText = `总行数：${data.total_lines.toLocaleString()} | 文件大小：${formatSize(data.file_size)} | 最后修改：${data.mtime}`;
                    updateLogStatus(statsText);
                }
            } catch (err) {
                console.error('Load stats error:', err);
            }
        }
        
        async function loadCurrentLog(fullLoad = false) {
            if (!currentFile) return;
            
            const viewer = document.getElementById('logViewer');
            
            // 如果不是全量加载且是实时模式，使用增量加载
            if (!fullLoad && realtimeMode && lastLineCount > 0 && !searchKeyword) {
                await loadNewLogLines();
                return;
            }
            
            // 全量加载模式
            if (!fullLoad) {
                viewer.innerHTML = '<div class="log-loading"><div class="spinner"></div>加载中...</div>';
            }
            
            try {
                // 从 localStorage 读取当前激活的 profile
                const activeProfile = localStorage.getItem('activeProfile') || '';
                const profileParam = activeProfile ? '&profile=' + encodeURIComponent(activeProfile) : '';
                const url = '/api/logs/content?file=' + encodeURIComponent(currentFile) + '&lines=500' + (searchKeyword ? '&search=' + encodeURIComponent(searchKeyword) : '') + profileParam;
                const res = await fetch(url);
                const data = await res.json();
                if (!data.success) throw new Error(data.error);
                
                let html = '';
                
                if (searchKeyword && data.match_lines) {
                    // 搜索模式：显示所有匹配行，带高亮
                    matchIndices = data.match_indices || [];
                    allLogLines = data.all_lines || [];
                    currentMatchIndex = -1;
                    
                    // 更新匹配计数器
                    updateMatchCounter();
                    
                    // 渲染所有日志行，高亮匹配的行
                    allLogLines.forEach((line, idx) => {
                        if (!line.trim()) return;
                        const isMatch = matchIndices.includes(idx);
                        const renderedLine = renderLogLine(line, isMatch, idx);
                        html += renderedLine;
                    });
                    
                    lastLineCount = allLogLines.length;
                    updateLogStatus(`找到 ${matchIndices.length} 处匹配`);
                } else {
                    // 普通模式
                    const content = data.content || '';
                    const lines = content.split('\\n');
                    lastLineCount = lines.length;
                    matchIndices = [];
                    currentMatchIndex = -1;
                    updateMatchCounter();
                    
                    lines.forEach(line => {
                        if (!line.trim()) return;
                        const renderedLine = renderLogLine(line, false, -1);
                        html += renderedLine;
                    });
                }
                
                viewer.innerHTML = html || '<div style="color: var(--text-secondary); padding: 20px;">日志内容为空</div>';
                
                // 如果有匹配，滚动到第一个匹配
                if (searchKeyword && matchIndices.length > 0) {
                    currentMatchIndex = 0;
                    setTimeout(() => {
                        scrollToMatch(0);
                    }, 100);
                } else {
                    // 自动滚动到最新
                    viewer.scrollTop = viewer.scrollHeight;
                }
                
                updateLastUpdateTime();
            } catch (err) {
                console.error('Load log error:', err);
                if (!fullLoad) {
                    viewer.innerHTML = '<div style="padding: 20px; color: var(--danger);">❌ 加载失败：' + err.message + '</div>';
                }
                updateLogStatus('加载失败：' + err.message);
            }
        }
        
        async function loadNewLogLines() {
            if (!currentFile || !realtimeMode) return;
            
            try {
                // 从 localStorage 读取当前激活的 profile
                const activeProfile = localStorage.getItem('activeProfile') || '';
                const profileParam = activeProfile ? '&profile=' + encodeURIComponent(activeProfile) : '';
                const url = '/api/logs/new?file=' + encodeURIComponent(currentFile) + '&start_line=' + lastLineCount + '&lines=100' + profileParam;
                const res = await fetch(url);
                const data = await res.json();
                if (!data.success) throw new Error(data.error);
                
                const content = data.content || '';
                const lines = content.split('\\n');
                const newLinesCount = lines.filter(l => l.trim()).length;
                
                if (newLinesCount > 0) {
                    const viewer = document.getElementById('logViewer');
                    let html = '';
                    lines.forEach(line => {
                        if (!line.trim()) return;
                        const renderedLine = renderLogLine(line);
                        html += renderedLine;
                    });
                    
                    // 追加新日志
                    viewer.insertAdjacentHTML('beforeend', html);
                    lastLineCount += newLinesCount;
                    
                    // 自动滚动到最新
                    viewer.scrollTop = viewer.scrollHeight;
                    
                    updateLastUpdateTime();
                    updateLogStatus(`新增 ${newLinesCount} 行，共 ${lastLineCount} 行`);
                } else {
                    updateLogStatus(`实时监控中... 共 ${lastLineCount} 行`);
                }
            } catch (err) {
                console.error('Load new log error:', err);
                updateLogStatus('获取新日志失败');
            }
        }
        
        function renderLogLine(line, isMatch = false, lineIndex = -1) {
            if (!line.trim()) return '';
            const levelMatch = line.match(/\\b(ERROR|WARN|WARNING|INFO|DEBUG)\\b/i);
            const level = levelMatch ? levelMatch[1].toUpperCase() : '';
            const timeMatch = line.match(/\\d{4}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}:\\d{2}/);
            const timestamp = timeMatch ? timeMatch[0] : '';
            
            let displayLine = line;
            if (timestamp) {
                displayLine = displayLine.replace(timestamp, '');
            }
            if (level) {
                displayLine = displayLine.replace(new RegExp('\\\\b' + level + '\\\\b', 'i'), '');
            }
            
            let classes = ['log-line', level];
            if (isMatch) {
                classes.push('match-highlight');
            }
            
            let html = '<div class="' + classes.join(' ') + '" data-line-index="' + lineIndex + '" onclick="onLineClick(' + lineIndex + ')" onmouseenter="showContextTooltip(event, ' + lineIndex + ')" onmouseleave="hideContextTooltip()">';
            if (timestamp) html += '<span class="log-timestamp">' + timestamp + '</span>';
            if (level) html += '<span class="log-level ' + level + '">' + level + '</span>';
            html += '<span>' + escapeHtml(displayLine) + '</span>';
            
            // 如果是匹配行，添加上下文提示
            if (isMatch && searchKeyword) {
                html += '<div class="context-tooltip" id="tooltip-' + lineIndex + '">';
                html += '<div class="context-tooltip-title">📋 悬停查看上下文（前后 5 行）</div>';
                html += '<div class="context-tooltip-content">点击查看详情...</div>';
                html += '</div>';
            }
            
            html += '</div>';
            return html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function applySearch() {
            searchKeyword = document.getElementById('searchInput').value.trim();
            if (searchKeyword) {
                document.getElementById('searchNav').style.display = 'flex';
            } else {
                document.getElementById('searchNav').style.display = 'none';
            }
            loadCurrentLog();
        }
        
        function updateMatchCounter() {
            const counterEl = document.getElementById('matchCounter');
            const navEl = document.getElementById('searchNav');
            const prevBtn = document.getElementById('prevMatchBtn');
            const nextBtn = document.getElementById('nextMatchBtn');
            
            if (matchIndices.length === 0) {
                counterEl.textContent = '找到 0 处匹配';
                prevBtn.disabled = true;
                nextBtn.disabled = true;
                navEl.style.display = searchKeyword ? 'flex' : 'none';
            } else {
                counterEl.textContent = `找到 ${matchIndices.length} 处匹配，当前第 ${currentMatchIndex + 1} 处`;
                prevBtn.disabled = currentMatchIndex <= 0;
                nextBtn.disabled = currentMatchIndex >= matchIndices.length - 1;
                navEl.style.display = 'flex';
            }
        }
        
        function scrollToMatch(index) {
            if (index < 0 || index >= matchIndices.length) return;
            
            const lineIndex = matchIndices[index];
            const lineEl = document.querySelector(`.log-line[data-line-index="${lineIndex}"]`);
            if (lineEl) {
                lineEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // 高亮当前匹配
                document.querySelectorAll('.log-line.current-match').forEach(el => el.classList.remove('current-match'));
                lineEl.classList.add('current-match');
                lineEl.style.background = 'rgba(234, 179, 8, 0.6)';
                setTimeout(() => {
                    lineEl.style.background = '';
                }, 2000);
            }
        }
        
        function navigateToNextMatch() {
            if (currentMatchIndex < matchIndices.length - 1) {
                currentMatchIndex++;
                updateMatchCounter();
                scrollToMatch(currentMatchIndex);
            }
        }
        
        function navigateToPrevMatch() {
            if (currentMatchIndex > 0) {
                currentMatchIndex--;
                updateMatchCounter();
                scrollToMatch(currentMatchIndex);
            }
        }
        
        let contextTooltipTimer = null;
        
        async function showContextTooltip(event, lineIndex) {
            if (!matchIndices.includes(lineIndex)) return;
            
            const tooltipEl = document.getElementById(`tooltip-${lineIndex}`);
            if (!tooltipEl) return;
            
            // 显示加载中
            tooltipEl.querySelector('.context-tooltip-content').innerHTML = '<span style="color: var(--primary);">加载中...</span>';
            tooltipEl.style.display = 'block';
            
            try {
                const url = `/api/logs/context?file=${encodeURIComponent(currentFile)}&line_index=${lineIndex}&context_lines=5`;
                const res = await fetch(url);
                const data = await res.json();
                
                if (data.success) {
                    let contextHtml = '';
                    data.lines.forEach((line, idx) => {
                        const isTargetLine = idx === data.highlight_index;
                        const lineClass = isTargetLine ? 'style="color: #fbbf24; font-weight: 600;"' : '';
                        contextHtml += `<div ${lineClass}>${escapeHtml(line || '')}</div>`;
                    });
                    
                    tooltipEl.querySelector('.context-tooltip-content').innerHTML = contextHtml;
                } else {
                    tooltipEl.querySelector('.context-tooltip-content').innerHTML = '<span style="color: var(--danger);">加载失败</span>';
                }
            } catch (err) {
                console.error('Load context error:', err);
                tooltipEl.querySelector('.context-tooltip-content').innerHTML = '<span style="color: var(--danger);">加载失败</span>';
            }
        }
        
        function hideContextTooltip() {
            document.querySelectorAll('.context-tooltip').forEach(el => el.style.display = 'none');
        }
        
        async function onLineClick(lineIndex) {
            if (!matchIndices.includes(lineIndex)) return;
            
            // 点击后跳转到该位置并显示前后各 10 行
            currentMatchIndex = matchIndices.indexOf(lineIndex);
            updateMatchCounter();
            
            try {
                const url = `/api/logs/context?file=${encodeURIComponent(currentFile)}&line_index=${lineIndex}&context_lines=10`;
                const res = await fetch(url);
                const data = await res.json();
                
                if (data.success) {
                    const viewer = document.getElementById('logViewer');
                    let html = '';
                    
                    data.lines.forEach((line, idx) => {
                        const isTargetLine = idx === data.highlight_index;
                        const renderedLine = renderLogLine(line, isTargetLine, data.start_line - 1 + idx);
                        html += renderedLine;
                    });
                    
                    viewer.innerHTML = html;
                    
                    // 滚动到目标行
                    setTimeout(() => {
                        const targetEl = document.querySelector(`.log-line[data-line-index="${lineIndex}"]`);
                        if (targetEl) {
                            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            targetEl.style.background = 'rgba(234, 179, 8, 0.6)';
                            setTimeout(() => {
                                targetEl.style.background = '';
                            }, 2000);
                        }
                    }, 100);
                    
                    updateLogStatus(`显示第 ${lineIndex + 1} 行（共 ${data.total_lines} 行）`);
                }
            } catch (err) {
                console.error('Load context on click error:', err);
            }
        }
        
        function toggleRealtimeMode(enabled) {
            const toggle = document.getElementById('realtimeToggle');
            if (enabled) {
                realtimeMode = true;
                toggle.classList.add('realtime-active');
                if (autoRefreshTimer) clearInterval(autoRefreshTimer);
                autoRefreshTimer = setInterval(() => {
                    if (currentFile) loadCurrentLog(false);
                }, 3000);
                updateLogStatus('实时模式已开启');
            } else {
                realtimeMode = false;
                toggle.classList.remove('realtime-active');
                if (autoRefreshTimer) {
                    clearInterval(autoRefreshTimer);
                    autoRefreshTimer = null;
                }
                updateLogStatus('实时模式已关闭');
            }
        }
        
        function setupRealtimeMode() {
            const checkbox = document.getElementById('realtimeMode');
            checkbox.addEventListener('change', function() {
                toggleRealtimeMode(this.checked);
            });
        }
        
        function setupSearchInput() {
            const searchInput = document.getElementById('searchInput');
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    applySearch();
                }
            });
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
            // 初始化实时模式状态
            const realtimeCheckbox = document.getElementById('realtimeMode');
            if (realtimeCheckbox && realtimeMode) {
                document.getElementById('realtimeToggle').classList.add('realtime-active');
            }
            
            loadFileList();
            setupRealtimeMode();
            setupSearchInput();
            setupSidebarToggle();
        });
    </script>
</body>
</html>
"""

