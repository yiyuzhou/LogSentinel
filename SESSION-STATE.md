记录时间：2026-03-31 09:38:00（本文件用于 WAL 协议）

状态变更：
- [completed] 已重启服务并确认修复：`系统`分组内不再包含“服务器监控”（仅在`系统监控`下保留）
- [in_progress] 用户反馈菜单仍存在：继续排查并修复仍把“服务器监控”显示在“系统”分组下的页面/模板（重点检查 `/settings`）
- [in_progress] 发现 `video_task_dashboard.py` / `log_viewer.py` 仍残留“系统分组内无href的服务器监控 span + 多余 </a>”，将继续清理并重启

