# 日志文件下载功能实现文档

## 功能概述
在日志监控页面中添加了日志文件下载功能，用户可以下载当前查看的日志文件。

## 修改文件

### 1. `scripts/log_viewer.py`

#### 新增后端函数

**`download_log_file(filename, lines='all')`**
- 功能：通过 SSH 下载日志文件内容
- 参数：
  - `filename`: 日志文件名
  - `lines`: 下载行数选项 (`all`, `1000`, `5000`)
- 返回：包含文件内容、大小、行数的字典

**`validate_log_file(filename)`**
- 功能：验证日志文件名，防止路径遍历攻击
- 验证规则：
  - 只允许字母、数字、下划线、连字符
  - 必须以 `.log` 结尾
  - 不能包含路径分隔符 (`/`, `\`, `..`)

#### 前端修改

**新增 CSS 样式**
```css
.download-group { 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  background: var(--bg-dark); 
  padding: 6px 12px; 
  border-radius: 6px; 
  border: 1px solid var(--border); 
}

.download-select { 
  padding: 6px 10px; 
  background: var(--bg-card); 
  border: 1px solid var(--border); 
  border-radius: 4px; 
  color: var(--text-primary); 
  font-size: 12px; 
  cursor: pointer; 
}
```

**新增 HTML 元素**
```html
<div class="download-group">
  <select id="downloadLines" class="download-select">
    <option value="all">全部</option>
    <option value="5000">最近 5000 行</option>
    <option value="1000">最近 1000 行</option>
  </select>
  <button class="btn btn-success" onclick="downloadLog()">📥 下载日志</button>
</div>
```

**新增 JavaScript 函数**

`downloadLog()`:
- 检查是否已选择文件
- 获取文件统计信息（大小、行数）
- 大文件警告（>100MB 时提示）
- 显示预计下载时间
- 触发浏览器下载
- 错误处理和状态提示

`formatTime(seconds)`:
- 格式化下载时间显示

---

### 2. `scripts/video_task_dashboard.py`

#### 新增导入
```python
from log_viewer import (
    LOG_VIEWER_TEMPLATE, 
    list_log_files, 
    get_log_content, 
    get_new_log_lines, 
    get_log_stats, 
    download_log_file,      # 新增
    validate_log_file       # 新增
)
```

#### 新增 API 端点

**`/api/logs/download`**
- 方法：GET
- 参数：
  - `file`: 日志文件名（必需）
  - `lines`: 下载行数选项 (`all`, `1000`, `5000`)，默认 `all`
- 返回：文件流（下载）
- 安全验证：
  - 防止路径遍历攻击
  - 文件名格式验证
  - 只允许日志目录内的文件

**响应头**
```
Content-Disposition: attachment; filename="<filename>_<lines>_<timestamp>.log"
X-File-Size: <文件大小>
X-Download-Lines: <选择的行数>
X-Actual-Lines: <实际行数>
```

---

## 功能特性

### ✅ 已实现功能

1. **下载按钮**
   - 位置：日志内容区域上方
   - 样式：绿色成功按钮（btn-success）
   - 图标：📥

2. **行数选择**
   - 下拉框选项：
     - 全部
     - 最近 5000 行
     - 最近 1000 行
   - 默认：全部

3. **大文件处理**
   - 100MB 以上文件显示警告
   - 用户确认后继续下载
   - 分块传输（8KB/chunk），避免内存溢出

4. **文件信息展示**
   - 显示文件大小
   - 显示选择的行数
   - 显示预计下载时间（基于 1MB/s 估算）

5. **安全保护**
   - 文件名验证（正则表达式）
   - 路径遍历防护
   - 只允许 `.log` 文件
   - 不允许路径分隔符

6. **用户体验**
   - 下载按钮状态反馈（准备中...）
   - 状态栏显示下载进度
   - 错误提示
   - 下载完成后恢复按钮状态

---

## 技术实现

### 后端流式传输
```python
def generate():
    chunk_size = 8192  # 8KB per chunk
    content = result['content']
    for i in range(0, len(content), chunk_size):
        yield content[i:i+chunk_size].encode('utf-8')
        time.sleep(0.001)  # 避免阻塞
```

### 前端下载触发
```javascript
const link = document.createElement('a');
link.href = downloadUrl;
link.download = '';
document.body.appendChild(link);
link.click();
document.body.removeChild(link);
```

---

## 测试建议

1. **基本功能测试**
   - 选择不同日志文件下载
   - 测试不同行数选项
   - 验证下载文件内容完整性

2. **大文件测试**
   - 测试 >100MB 文件的下载
   - 验证警告提示
   - 测试内存使用情况

3. **安全测试**
   - 尝试路径遍历攻击（`../../../etc/passwd`）
   - 尝试非法文件名
   - 验证只允许访问日志目录

4. **错误处理测试**
   - 文件不存在
   - 网络中断
   - SSH 连接失败

---

## 使用示例

1. 访问日志监控页面：`http://localhost:5000/logs`
2. 从左侧选择日志文件
3. 在顶部选择下载行数（全部/最近 5000 行/最近 1000 行）
4. 点击 "📥 下载日志" 按钮
5. 浏览器自动开始下载

---

## 注意事项

1. **性能考虑**
   - 大文件下载时建议使用 "最近 1000 行" 或 "最近 5000 行" 选项
   - 下载过程中保持页面打开
   - 避免同时发起多个下载请求

2. **安全考虑**
   - 确保 SSH 凭证安全
   - 日志目录权限设置正确
   - 定期清理旧日志文件

3. **浏览器兼容性**
   - 支持现代浏览器（Chrome, Firefox, Edge, Safari）
   - 下载行为可能受浏览器设置影响

---

## 完成日期
2026-03-30
