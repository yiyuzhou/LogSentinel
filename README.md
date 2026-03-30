# 视频任务运维系统

基于 Flask 的视频任务运维监控系统，提供任务管理、日志监控、服务器监控等功能。

## 🚀 功能特性

### 任务管理
- **内部译制** - 视频任务列表、搜索筛选、分页展示
- **腾讯 MPS** - MPS 任务管理、提取方式颜色区分

### 系统监控
- **日志监控** - 实时日志查看、搜索高亮、文件下载、SSH 远程日志
- **服务器监控** - CPU/内存/硬盘/网络图形化实时监控

### 系统设置
- **多配置管理** - 支持多套环境配置切换
- **数据源配置** - MySQL 数据库配置
- **SSH 配置** - 远程日志服务器配置

---

## 📦 安装部署

### 1. 环境要求
- Python 3.8+
- MySQL 数据库
- 网络连接（用于 SSH 远程日志）

### 2. 安装依赖
```bash
pip install flask flask-cors mysql-connector-python paramiko psutil
```

### 3. 配置文件
编辑 `config/database.json`：
```json
{
  "profiles": {
    "default": {
      "name": "默认配置",
      "video": {
        "host": "your-mysql-host",
        "port": 3306,
        "database": "videoai",
        "user": "your-username",
        "password": "your-encrypted-password"
      },
      "ssh_config": {
        "hostname": "your-ssh-host",
        "port": 22,
        "username": "your-ssh-username",
        "password": "your-ssh-password",
        "log_dir": "/path/to/logs"
      }
    }
  },
  "active_profile": "default"
}
```

### 4. 启动服务
```bash
cd scripts
python video_task_dashboard.py
```

### 5. 访问系统
打开浏览器访问：http://localhost:5000

---

## 📊 页面说明

| 页面 | URL | 功能 |
|------|-----|------|
| 首页（内部译制） | `/` | 任务列表、搜索筛选 |
| 腾讯 MPS | `/mps` | MPS 任务管理 |
| 日志监控 | `/logs` | 实时日志查看、下载 |
| 服务器监控 | `/server-monitor` | 系统资源监控 |
| 系统设置 | `/settings` | 配置管理 |

---

## 🔧 技术栈

**后端：**
- Python 3.8+
- Flask（Web 框架）
- Flask-CORS（跨域支持）
- MySQL Connector（数据库连接）
- Paramiko（SSH 远程连接）
- Psutil（系统监控）

**前端：**
- HTML5 + CSS3
- 原生 JavaScript
- Chart.js（图表库）

---

## 📁 项目结构

```
video-task-system/
├── scripts/
│   ├── video_task_dashboard.py    # 主程序
│   ├── mps_module.py              # 腾讯 MPS 模块
│   ├── log_viewer.py              # 日志监控模块
│   ├── server_monitor.py          # 服务器监控模块
│   ├── settings.py                # 系统设置模块
│   ├── test_profile_config.py     # 配置测试脚本
│   └── test_profile_routing.py    # 路由测试脚本
├── config/
│   ├── database.json              # 数据库配置
│   └── README.md                  # 配置说明
├── docs/
│   ├── SERVER_MONITOR_README.md   # 服务器监控说明
│   ├── config-fix-report.md       # 配置修复报告
│   └── ...                        # 其他文档
└── memory/
    └── *.md                       # 记忆文件
```

---

## 🎯 使用指南

### 配置管理
1. 访问 `/settings` 页面
2. 在"配置管理"下拉框选择或新建配置
3. 填写 MySQL 和 SSH 配置信息
4. 点击"保存配置"
5. 切换配置后刷新页面生效

### 日志监控
1. 访问 `/logs` 页面
2. 左侧选择日志文件
3. 右侧实时查看日志内容
4. 支持搜索关键词高亮
5. 支持下载日志文件

### 服务器监控
1. 访问 `/server-monitor` 页面
2. 实时查看 CPU、内存、硬盘、网络使用情况
3. 数据每 3 秒自动刷新

---

## ⚠️ 注意事项

1. **密码加密** - 配置文件中的密码使用 Base64 加密存储
2. **配置切换** - 切换配置后需要刷新页面才能生效
3. **SSH 连接** - 确保 SSH 服务器可访问，日志目录存在
4. **数据库连接** - 确保 MySQL 服务正常运行

---

## 📝 更新日志

### v1.0.0 (2026-03-30)
- ✅ 日志监控模块（实时监控、搜索高亮、文件下载）
- ✅ 服务器监控模块（CPU/内存/硬盘/网络）
- ✅ 系统设置模块（多配置管理、数据源切换）
- ✅ 腾讯 MPS 模块（任务列表、详情页）
- ✅ 配置持久化和跨页面同步
- ✅ 侧边栏折叠功能
- ✅ 版本号显示

---

## 👨‍💻 开发者

**yiyuzhou**

## 📄 License

MIT License

---

## 🔗 相关链接

- GitHub: https://github.com/yiyuzhou/video-task-system
- 问题反馈：https://github.com/yiyuzhou/video-task-system/issues
