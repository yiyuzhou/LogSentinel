# 配置管理切换功能修复报告

## 问题描述
用户反馈系统设置页面中的"配置管理"下拉框无法切换配置，选择某个配置后没有反应。

## 检查结果

### ✅ 已验证正确的部分
1. **HTML 结构正确**：`<select id="profileSelect" onchange="switchProfile()">` 事件绑定正确
2. **API 数据结构正确**：`/api/settings/config` 返回的数据包含 `profiles`、`activeProfile` 等字段
3. **配置文件结构正确**：`database.json` 中有 `default` 和 `profile_*` 两个配置

### ❌ 发现的问题
1. **缺少错误处理**：`switchProfile()` 和 `loadProfileData()` 函数在失败时静默失败，没有任何提示
2. **缺少调试日志**：无法通过控制台查看配置加载过程
3. **配置切换后未保存**：切换配置后只更新了前端状态，没有保存到服务器（刷新后会丢失）

## 修复内容

### 1. 增强 `switchProfile()` 函数
**修复前**：
```javascript
function switchProfile() {
    const profileName = document.getElementById('profileSelect').value;
    currentConfig.activeProfile = profileName;
    loadProfileData(profileName);
    showToast('已切换到配置：' + profileName, 'success');
}
```

**修复后**：
```javascript
function switchProfile() {
    const profileName = document.getElementById('profileSelect').value;
    console.log('[switchProfile] 切换配置:', profileName);
    console.log('[switchProfile] 可用 profiles:', Object.keys(profiles));
    
    // 检查 profile 是否存在
    if (!profiles[profileName]) {
        console.error('[switchProfile] 错误：找不到配置', profileName);
        showToast('切换失败：找不到配置 "' + profileName + '"', 'error');
        return;
    }
    
    currentConfig.activeProfile = profileName;
    
    // 加载当前 profile 的数据
    const loaded = loadProfileData(profileName);
    if (loaded) {
        showToast('已切换到配置：' + profileName + '（视频任务数据源 + 日志监控配置）', 'success');
    } else {
        console.error('[switchProfile] loadProfileData 返回 false');
        showToast('切换失败：无法加载配置数据', 'error');
    }
}
```

**改进**：
- ✅ 添加配置存在性检查
- ✅ 添加控制台日志便于调试
- ✅ 根据 `loadProfileData()` 返回值显示不同提示

### 2. 增强 `loadProfileData()` 函数
**修复前**：
```javascript
function loadProfileData(profileName) {
    const profile = profiles[profileName] || profiles['default'];
    if (!profile) return;  // 静默失败
    
    // 填充表单...
}
```

**修复后**：
```javascript
function loadProfileData(profileName) {
    console.log('[loadProfileData] 加载配置:', profileName);
    const profile = profiles[profileName] || profiles['default'];
    
    if (!profile) {
        console.error('[loadProfileData] 错误：找不到配置', profileName, 'profiles:', profiles);
        showToast('加载配置失败：找不到配置 "' + profileName + '"', 'error');
        return false;
    }
    
    try {
        // 填充表单...
        console.log('[loadProfileData] video 配置已加载:', video.host);
        console.log('[loadProfileData] SSH 配置已加载:', sshConfig.hostname);
        return true;
    } catch (err) {
        console.error('[loadProfileData] 加载配置出错:', err);
        showToast('加载配置出错：' + err.message, 'error');
        return false;
    }
}
```

**改进**：
- ✅ 添加返回值（true/false）表示加载是否成功
- ✅ 添加详细的控制台日志
- ✅ 添加 try-catch 错误处理
- ✅ 失败时显示明确的错误提示

### 3. 增强 `loadSettings()` 函数
**修复后添加的日志**：
```javascript
async function loadSettings() {
    try {
        console.log('[loadSettings] 开始加载配置...');
        const res = await fetch('/api/settings/config');
        const data = await res.json();
        
        console.log('[loadSettings] API 返回:', data);
        console.log('[loadSettings] profiles 已加载:', Object.keys(profiles));
        console.log('[loadSettings] activeProfile:', data.activeProfile);
        
        // ...
        
        const loaded = loadProfileData(data.activeProfile || 'default');
        console.log('[loadSettings] 配置加载结果:', loaded ? '成功' : '失败');
    } catch (err) {
        console.error('[loadSettings] 加载配置错误:', err);
        showToast('加载配置失败：' + err.message, 'error');
    }
}
```

**改进**：
- ✅ 添加完整的加载流程日志
- ✅ 显示 API 返回数据便于调试
- ✅ 显示配置加载结果

## 验证步骤

### 1. 重启 Flask 应用
```bash
# 停止当前运行的服务
# 重新启动
python scripts/video_task_dashboard.py
```

### 2. 打开浏览器开发者工具
1. 访问 `http://localhost:5000/settings`
2. 按 F12 打开开发者工具
3. 切换到 Console 标签

### 3. 验证配置加载
查看控制台输出，应该看到类似：
```
[loadSettings] 开始加载配置...
[loadSettings] API 返回：{success: true, config: {...}, profiles: {...}, activeProfile: "default"}
[loadSettings] profiles 已加载：["default", "profile_1774842228864"]
[loadSettings] activeProfile: default
[loadProfileData] 加载配置：default
[loadProfileData] video 配置已加载：101.126.91.130
[loadProfileData] SSH 配置已加载：101.126.91.130
[loadSettings] 配置加载结果：成功
```

### 4. 验证配置切换
1. 在"配置管理"下拉框中选择另一个配置（如 "dev"）
2. 查看控制台输出：
```
[switchProfile] 切换配置：profile_1774842228864
[switchProfile] 可用 profiles：["default", "profile_1774842228864"]
[loadProfileData] 加载配置：profile_1774842228864
[loadProfileData] video 配置已加载：localhost
[loadProfileData] SSH 配置已加载：
```
3. 页面右上角应显示成功提示："已切换到配置：dev（视频任务数据源 + 日志监控配置）"
4. 表单中的"视频任务数据源"字段应更新为 dev 配置的值

### 5. 验证错误处理
如果选择不存在的配置（可通过修改 HTML 测试），应看到：
```
[switchProfile] 切换配置：non_existent
[switchProfile] 可用 profiles：["default", "profile_1774842228864"]
[switchProfile] 错误：找不到配置 non_existent
```
页面应显示错误提示："切换失败：找不到配置 "non_existent""

## 后续建议

### 1. 保存切换状态（可选增强）
目前切换配置后只更新前端状态，如需持久化，可在 `switchProfile()` 中添加保存逻辑：
```javascript
async function switchProfile() {
    // ... 现有代码 ...
    
    // 可选：保存到服务器
    try {
        await fetch('/api/settings/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                active_profile: profileName,
                profiles: currentConfig.profiles
            })
        });
    } catch (err) {
        console.error('保存配置失败:', err);
    }
}
```

### 2. 添加配置验证
在 `loadProfileData()` 中添加配置完整性验证：
```javascript
if (!profile.video || !profile.video.host) {
    console.warn('[loadProfileData] 警告：配置缺少 video.host');
}
```

## 修复文件
- `D:\.openclaw\agents\weather-bot\workspace\scripts\settings.py`

## 修复时间
2026-03-30
