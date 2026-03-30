# 数据源配置模块使用说明

## 功能概述

本模块为视频任务运维系统提供数据库配置管理功能，支持：

- ✅ 配置内部译制和腾讯 MPS 两套 MySQL 数据源
- ✅ Base64 密码加密存储
- ✅ 多套配置保存和切换
- ✅ 表单验证和测试连接功能
- ✅ 主程序启动时自动加载配置

## 文件结构

```
workspace/
├── config/
│   └── database.json          # 数据库配置文件（自动创建）
└── scripts/
    ├── settings.py            # 设置模块（新增）
    ├── video_task_dashboard.py # 主程序（已修改）
    ├── mps_module.py          # MPS 模块（已修改）
    └── log_viewer.py          # 日志模块（已修改）
```

## 访问设置页面

1. 启动主程序：
   ```bash
   cd D:\.openclaw\agents\weather-bot\workspace\scripts
   python video_task_dashboard.py
   ```

2. 浏览器访问：
   ```
   http://localhost:5000/settings
   ```

3. 或从任意页面的侧边栏菜单点击 **⚙️ 系统设置**

## 配置项说明

### 内部译制数据源

| 字段 | 说明 | 示例 |
|------|------|------|
| MySQL 主机 | 数据库服务器 IP | `101.126.91.130` |
| 端口 | MySQL 端口 | `4005` |
| 数据库名 | 数据库名称 | `videoai` |
| 用户名 | 数据库用户 | `yiyuzhou` |
| 密码 | 数据库密码（加密存储） | `******` |

### 腾讯 MPS 数据源

| 字段 | 说明 | 示例 |
|------|------|------|
| MySQL 主机 | 数据库服务器 IP | `101.126.91.130` |
| 端口 | MySQL 端口 | `4005` |
| 数据库名 | 数据库名称 | `videoai` |
| 用户名 | 数据库用户 | `yiyuzhou` |
| 密码 | 数据库密码（加密存储） | `******` |

## 使用流程

### 1. 配置数据源

1. 进入 **系统设置** 页面
2. 填写内部译制数据源信息
3. 点击 **🔌 测试连接** 验证配置
4. 填写腾讯 MPS 数据源信息
5. 点击 **🔌 测试连接** 验证配置
6. 点击 **💾 保存配置** 保存设置

### 2. 多配置管理

- **新建配置**：点击"➕ 新建配置"，输入配置名称
- **切换配置**：从下拉菜单选择要使用的配置
- **删除配置**：选择配置后点击"🗑️ 删除配置"（默认配置不可删除）

### 3. 配置文件位置

配置文件保存在：
```
D:\.openclaw\agents\weather-bot\workspace\config\database.json
```

## 配置文件格式

```json
{
  "active_profile": "default",
  "profiles": {
    "default": {
      "name": "默认配置",
      "internal": {
        "host": "101.126.91.130",
        "port": 4005,
        "database": "videoai",
        "user": "yiyuzhou",
        "password": "eWl5dXpob3U1MDY2OTk1"
      },
      "mps": {
        "host": "101.126.91.130",
        "port": 4005,
        "database": "videoai",
        "user": "yiyuzhou",
        "password": "eWl5dXpob3U1MDY2OTk1"
      }
    }
  }
}
```

## API 接口

### 获取配置
```
GET /api/settings/config
```

### 保存配置
```
POST /api/settings/save
Content-Type: application/json

{
  "active_profile": "default",
  "profiles": {...}
}
```

### 测试内部数据库连接
```
POST /api/settings/test_internal
Content-Type: application/json

{
  "host": "101.126.91.130",
  "port": 4005,
  "database": "videoai",
  "user": "yiyuzhou",
  "password": "******"
}
```

### 测试 MPS 数据库连接
```
POST /api/settings/test_mps
Content-Type: application/json

{
  "host": "101.126.91.130",
  "port": 4005,
  "database": "videoai",
  "user": "yiyuzhou",
  "password": "******"
}
```

## 代码集成

### 在主程序中使用配置

```python
from settings import get_internal_db_config, get_mps_db_config

# 获取内部数据库配置
internal_config = get_internal_db_config()
# 获取 MPS 数据库配置
mps_config = get_mps_db_config()

# 使用配置连接数据库
import mysql.connector
conn = mysql.connector.connect(**internal_config)
```

### 初始化配置

主程序启动时会自动调用：
```python
from settings import init_db_config
init_db_config()  # 加载配置文件
```

## 安全说明

- ✅ 密码使用 Base64 编码存储
- ✅ 配置文件仅保存在本地
- ⚠️ 建议在生产环境中使用更强的加密方式
- ⚠️ 请确保配置文件权限设置正确

## 故障排查

### 问题：无法保存配置

**解决方案**：
1. 检查 `config/` 目录是否存在
2. 检查是否有写入权限
3. 查看控制台错误日志

### 问题：测试连接失败

**解决方案**：
1. 检查数据库主机和端口是否正确
2. 检查网络连接
3. 检查数据库用户权限
4. 查看详细错误信息

### 问题：配置未生效

**解决方案**：
1. 确认已点击"💾 保存配置"
2. 重启主程序
3. 检查 `database.json` 文件内容
4. 确认 `active_profile` 指向正确的配置

## 更新日志

### v1.0.0 (2026-03-30)
- ✨ 新增系统设置页面
- ✨ 支持内部译制和腾讯 MPS 数据源配置
- ✨ 支持多配置管理和切换
- ✨ Base64 密码加密
- ✨ 测试连接功能
- ✨ 自动加载配置文件
