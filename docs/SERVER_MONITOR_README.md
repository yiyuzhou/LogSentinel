# 服务器监控模块文档

## 📋 功能概述

服务器监控模块提供了对服务器关键指标的实时图形化监控，包括：

1. **CPU 使用率**
   - 实时使用率百分比
   - 逻辑核心数/物理核心数
   - CPU 频率
   - 每核心使用率
   - 最近 10 分钟使用率趋势图

2. **内存使用**
   - 总内存/已用内存/可用内存
   - 使用率百分比
   - 虚拟内存（Swap）使用情况
   - 最近 10 分钟内存使用趋势图

3. **硬盘使用**
   - 各分区使用情况
   - 总容量/已用/可用空间
   - 使用率饼图
   - 文件系统类型
   - 可视化进度条

4. **网络流量**
   - 上传/下载速度（实时）
   - 累计流量统计
   - 网络接口详情（IP 地址、链路速度）
   - 最近 10 分钟流量趋势图

5. **系统信息**
   - 操作系统版本
   - 运行时间（Uptime）
   - 主机名
   - CPU 型号

## 🎨 页面布局

```
┌─────────────────────────────────────────────────┐
│ 🖥️ 服务器监控                                   │
├─────────────────────────────────────────────────┤
│ [CPU 卡片] [内存卡片] [硬盘卡片] [网络卡片]     │
├─────────────────────────────────────────────────┤
│ [CPU 趋势图]           [内存趋势图]             │
├─────────────────────────────────────────────────┤
│ [硬盘分区饼图]         [网络流量图]             │
├─────────────────────────────────────────────────┤
│ [系统信息]                                      │
├─────────────────────────────────────────────────┤
│ [硬盘分区详情表格]                              │
├─────────────────────────────────────────────────┤
│ [网络接口详情]                                  │
└─────────────────────────────────────────────────┘
```

## 🔧 技术实现

### 后端（Python）

- **库依赖**: `psutil`, `flask`, `flask-cors`
- **数据收集**: 后台线程每 3 秒收集一次系统指标
- **历史数据**: 内存中存储最近 200 个数据点（约 10 分钟）
- **API 接口**:
  - `GET /server-monitor` - 监控页面
  - `GET /api/server/metrics` - 获取所有监控指标
  - `GET /api/server/history` - 获取历史数据

### 前端

- **图表库**: Chart.js
- **刷新频率**: 每 3 秒自动刷新
- **特性**:
  - 响应式布局
  - 实时趋势图
  - 自动/手动刷新切换
  - 倒计时显示

## 📁 修改文件

### 新建文件

- `D:\.openclaw\agents\weather-bot\workspace\scripts\server_monitor.py`
  - 服务器监控模块主文件
  - 包含数据收集、API 接口、前端页面

### 修改文件

- `D:\.openclaw\agents\weather-bot\workspace\scripts\video_task_dashboard.py`
  - 导入 `register_server_monitor_routes` 和 `start_data_collection`
  - 注册服务器监控路由
  - 启动后台数据收集线程
  - 更新侧边栏菜单（添加"服务器监控"入口）

## 🚀 使用方法

### 方式 1：集成到主仪表板

服务器监控模块已自动集成到 `video_task_dashboard.py` 中。

启动主仪表板后，访问：
```
http://localhost:5000/server-monitor
```

### 方式 2：独立运行

```bash
cd D:\.openclaw\agents\weather-bot\workspace\scripts
python server_monitor.py
```

访问：
```
http://localhost:5001/server-monitor
```

## 📊 API 接口

### GET /api/server/metrics

获取所有监控指标和历史数据。

**响应示例**:
```json
{
  "success": true,
  "cpu": {
    "usage_percent": 25.3,
    "frequency_current": 2400,
    "frequency_max": 3200,
    "cores_logical": 8,
    "cores_physical": 4,
    "per_cpu_usage": [20.5, 30.2, 25.1, 28.7, ...]
  },
  "memory": {
    "total": 17179869184,
    "available": 8589934592,
    "used": 8589934592,
    "percent": 50.0,
    "swap_total": 4294967296,
    "swap_used": 1073741824,
    "swap_percent": 25.0
  },
  "disk": [
    {
      "device": "C:",
      "mountpoint": "C:\\",
      "fstype": "NTFS",
      "total": 500000000000,
      "used": 250000000000,
      "free": 250000000000,
      "percent": 50.0
    }
  ],
  "network": {
    "bytes_sent": 1073741824,
    "bytes_recv": 2147483648,
    "interfaces": {...}
  },
  "system_info": {
    "os_name": "Windows 10",
    "hostname": "DESKTOP-XXXX",
    "uptime_formatted": "3 days 04:25:30",
    "cpu_model": "Intel Core i7"
  },
  "history_cpu": [25.3, 26.1, 24.8, ...],
  "history_memory": [50.0, 50.5, 49.8, ...],
  "history_network": [...],
  "history_timestamps": [...]
}
```

### GET /api/server/history

仅获取历史数据（用于趋势图）。

## 🔍 侧边栏菜单

服务器监控入口已添加到所有页面的侧边栏菜单中：

```
系统监控
├── 📋 日志监控
└── 🖥️ 服务器监控 ⭐ 新增
```

## 📝 注意事项

1. **权限**: 某些系统信息可能需要管理员权限才能获取
2. **性能**: 数据收集线程每 3 秒运行一次，对系统性能影响极小
3. **内存**: 历史数据存储在内存中，最多保存 200 个数据点
4. **浏览器**: 需要支持 Chart.js（现代浏览器）

## 🛠️ 依赖安装

```bash
pip install psutil flask flask-cors
```

## 📅 更新日期

2026-03-30

## 👨‍💻 开发者

视频任务运维系统 - 服务器监控模块
