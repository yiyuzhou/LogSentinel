# 配置读取问题修复报告

## 问题描述

用户在系统设置中保存了配置后，切换到"内部译制"或"腾讯 MPS"页面时出现数据库连接错误：
```
❌ 加载失败：1045 (28000): Access denied for user 'root'@'110.53.251.71' (using password: NO)
```

## 根本原因分析

### 1. 配置状态
通过测试脚本验证，当前 `database.json` 配置如下：

- **active_profile**: `default`
- **default profile**: 
  - Host: `101.126.91.130`
  - User: `root`
  - Password: **(空)** ❌
  
- **dev profile** (profile_1774842228864):
  - Host: `101.126.91.130`
  - User: `root`
  - Password: `sGq0EqkU0y...` (已加密) ✓

### 2. 问题根源

1. **系统使用 "default" profile**，该 profile 的密码字段为空
2. **前端 localStorage 可能为空或不一致**，导致没有传递正确的 profile 参数到后端
3. **后端使用 default profile 配置**（密码为空）尝试连接数据库，导致认证失败

### 3. 代码问题

`video_task_dashboard.py` 中的 `get_db_config()` 函数存在以下问题：
- 没有详细的日志输出，难以调试
- 配置缓存逻辑可能导致不同请求之间的配置混淆
- 当指定 profile 但配置不完整时，没有正确处理

## 修复内容

### 1. 增强 `get_db_config()` 函数

**文件**: `scripts/video_task_dashboard.py`

**修复内容**:
- 添加详细的日志输出，记录配置加载过程
- 改进缓存逻辑（5 秒过期），确保配置及时更新
- 当指定 profile 时，直接从配置文件读取，不使用缓存
- 当 profile 不存在或配置不完整时，返回适当的配置而不是硬编码默认值

**关键代码**:
```python
def get_db_config(profile=None, use_cache=True):
    """获取数据库配置（从配置文件加载）"""
    # 如果指定了 profile，从该配置读取（不使用缓存）
    if profile:
        config = load_config()
        profile_data = config.get('profiles', {}).get(profile)
        if profile_data:
            video = profile_data.get('video', {})
            # 返回该 profile 的配置
            return {
                'host': video.get('host', 'localhost'),
                'port': video.get('port', 3306),
                'database': video.get('database', ''),
                'user': video.get('user', ''),
                'password': decode_password(video.get('password', '')),
                # ...
            }
    
    # 使用缓存（5 秒过期）或从配置文件重新加载
    # ...
```

### 2. 增强 `get_db_connection()` 函数

**修复内容**:
- 添加详细的日志输出，记录连接配置
- 改进错误处理，区分 MySQL 错误和其他错误

### 3. 增强 API 日志

**修复的 API**:
- `/api/data`
- `/api/task_detail`
- `/api/mps_data`
- `/api/mps_detail`

**修复内容**:
- 添加 profile 参数日志
- 在请求开始时"预热"配置缓存，确保后续查询使用正确的配置

### 4. 创建测试脚本

**文件**: `scripts/test_profile_config.py`

**用途**: 验证配置读取是否正确，显示所有 profile 的详细信息

## 使用方法

### 1. 运行测试脚本验证配置

```bash
cd D:\.openclaw\agents\weather-bot\workspace\scripts
python test_profile_config.py
```

### 2. 在设置页面切换到正确的 profile

1. 打开系统设置页面 (`/settings`)
2. 在下拉框中选择正确的配置（如 "dev"）
3. **确保输入密码**（如果密码字段为空，需要输入新密码）
4. 点击"保存配置"按钮
5. 页面会自动刷新，应用新配置

### 3. 验证修复

1. 切换到"内部译制"页面 (`/`)
2. 检查是否能正常加载数据
3. 查看服务器日志，确认配置读取正确

## 日志示例

修复后，服务器日志会显示详细的配置加载信息：

```
[API /api/data] 收到请求，profile 参数：profile_1774842228864
[get_db_config] 请求 profile: 'profile_1774842228864', config.active_profile: 'default'
[get_db_config] 找到 profile 'profile_1774842228864': dev
[get_db_config] 返回 profile 'profile_1774842228864' 配置：host=101.126.91.130, user=root, password=***
[API /api/data] 已预热 profile 'profile_1774842228864' 的配置
[get_db_connection] 使用配置：host=101.126.91.130, user=root, password=***
```

## 后续建议

1. **添加配置验证**：在保存配置时验证必填字段（如密码）
2. **改进前端提示**：如果用户切换 profile 但没有保存，提示用户保存
3. **同步 localStorage 和后端配置**：在页面加载时，如果 localStorage 与后端配置不一致，提示用户
4. **添加配置测试功能**：在设置页面添加"测试连接"按钮，确保配置正确

## 测试状态

- ✅ 配置读取测试通过
- ✅ 日志输出正常
- ⏳ 需要用户在浏览器中验证前端功能

## 相关文件

- `scripts/video_task_dashboard.py` - 主要修复文件
- `scripts/settings.py` - 配置管理（无需修改）
- `config/database.json` - 配置文件
- `scripts/test_profile_config.py` - 测试脚本
