# 日志监控搜索功能改进

## 修改时间
2026-03-30

## 修改文件
- `scripts/log_viewer.py` - 日志查看器前端模板和后端函数
- `scripts/video_task_dashboard.py` - 添加新的 API 路由

## 新增功能

### 1. 搜索关键字高亮显示 🔍
- 所有匹配的日志行使用醒目的黄色背景高亮（`rgba(234, 179, 8, 0.3)`）
- 左侧添加黄色边框标识（3px solid #fbbf24）
- 悬停时背景加深，提升交互反馈

### 2. 鼠标悬停显示上下文 🖱️
- 悬停到匹配行时，右侧显示上下文提示框
- 显示前后各 5 行日志内容
- 目标行使用黄色高亮显示
- 提示框采用悬浮设计，不遮挡主视图

### 3. 点击跳转完整上下文 👆
- 点击匹配行后，视图跳转到该关键字位置
- 显示前后各 10 行完整日志
- 自动滚动到目标行并居中显示
- 目标行高亮 2 秒后恢复

### 4. 匹配计数器 📊
- 显示总匹配数："找到 15 处匹配"
- 显示当前位置："当前第 3 处"
- 实时更新，搜索后立即显示

### 5. 导航按钮 ⬅️➡️
- "上一个匹配"按钮：跳转到上一个匹配行
- "下一个匹配"按钮：跳转到下一个匹配行
- 到达边界时按钮自动禁用
- 支持键盘 Enter 键快速搜索

## 技术实现

### 后端改动

#### 1. `get_log_content()` 函数增强
```python
# 搜索时返回完整日志和匹配信息
if search:
    return {
        'match_lines': [...],      # 匹配的行
        'match_indices': [...],    # 匹配行索引（0-based）
        'all_lines': [...],        # 完整日志行
        'total_matches': int       # 匹配总数
    }
```

#### 2. 新增 `get_log_context()` 函数
```python
def get_log_context(filename, line_index, context_lines=10):
    """获取指定行周围的上下文日志"""
    # 返回指定行前后各 N 行的内容
    return {
        'lines': [...],           # 上下文行
        'start_line': int,        # 起始行号
        'end_line': int,          # 结束行号
        'highlight_index': int    # 高亮行在数组中的索引
    }
```

#### 3. 新增 API 路由 `/api/logs/context`
```python
@app.route('/api/logs/context')
def api_logs_context():
    """获取指定行周围的上下文日志"""
    # 参数：file, line_index, context_lines
```

### 前端改动

#### 1. CSS 样式新增
```css
.log-line.match-highlight { 
    background: rgba(234, 179, 8, 0.3); 
    border-left: 3px solid #fbbf24; 
}
.log-line.current-match { 
    background: rgba(234, 179, 8, 0.5); 
}
.context-tooltip { 
    /* 悬浮提示框样式 */
}
.search-nav { 
    /* 搜索导航控件样式 */
}
```

#### 2. JavaScript 新增功能
- `updateMatchCounter()` - 更新匹配计数器
- `scrollToMatch(index)` - 滚动到指定匹配
- `navigateToNextMatch()` - 下一个匹配
- `navigateToPrevMatch()` - 上一个匹配
- `showContextTooltip(event, lineIndex)` - 显示上下文提示
- `hideContextTooltip()` - 隐藏提示
- `onLineClick(lineIndex)` - 处理行点击

#### 3. 搜索流程优化
```javascript
// 搜索时保留完整日志上下文
allLogLines = data.all_lines || [];
matchIndices = data.match_indices || [];

// 渲染所有行，高亮匹配
allLogLines.forEach((line, idx) => {
    const isMatch = matchIndices.includes(idx);
    html += renderLogLine(line, isMatch, idx);
});
```

## 用户体验提升

| 功能 | 改进前 | 改进后 |
|------|--------|--------|
| 搜索结果显示 | 仅显示匹配行 | 显示全部日志，高亮匹配行 |
| 上下文查看 | 无 | 悬停显示±5 行，点击显示±10 行 |
| 导航 | 无 | 上一个/下一个按钮 |
| 位置感知 | 无 | 匹配计数器（第 X/共 Y） |
| 视觉反馈 | 无高亮 | 黄色背景 + 边框高亮 |

## 使用说明

### 搜索日志
1. 在搜索框输入关键字
2. 按 Enter 或点击"搜索"按钮
3. 所有匹配行自动高亮显示

### 查看上下文
- **快速预览**：鼠标悬停到匹配行，右侧显示±5 行上下文
- **详细查看**：点击匹配行，视图切换到±10 行完整上下文

### 导航匹配
- 使用"上一个"/"下一个"按钮在匹配间跳转
- 当前匹配行会短暂高亮显示（2 秒）
- 计数器实时更新位置

## 注意事项

1. **性能优化**：搜索时加载完整日志文件，大文件可能需要几秒
2. **内存管理**：搜索模式下保留完整日志在内存中
3. **实时模式**：搜索时自动暂停实时刷新，清除搜索后恢复
4. **安全过滤**：所有 API 调用包含路径遍历保护

## 测试建议

1. 测试小文件（<1000 行）搜索性能
2. 测试大文件（>10000 行）搜索性能
3. 测试无匹配、单匹配、多匹配场景
4. 测试导航按钮边界情况（第一个/最后一个）
5. 测试悬停提示的显示/隐藏流畅性
