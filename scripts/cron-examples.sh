#!/bin/bash
# Memory-Like-A-Tree Cron 配置示例
#
# 将以下内容添加到 crontab -e

# ============================================
# 记忆树自动化任务
# ============================================

# 每 2 小时扫描索引（增量）
0 */2 * * * cd /path/to/memory-like-a-tree && python3 core/indexer.py --watch >> /tmp/mlat-indexer.log 2>&1

# 每天凌晨 2 点执行衰减
0 2 * * * cd /path/to/memory-like-a-tree && python3 core/decayer.py --run >> /tmp/mlat-decayer.log 2>&1

# 每天凌晨 3 点执行清理
0 3 * * * cd /path/to/memory-like-a-tree && python3 core/cleaner.py --auto-cleanup >> /tmp/mlat-cleaner.log 2>&1

# 每 2 小时同步到 Obsidian（可选，需要配置 obsidian_vault）
# 0 */2 * * * cd /path/to/memory-like-a-tree && python3 core/sync_workspace_to_obsidian.py --quiet >> /tmp/mlat-sync.log 2>&1

# ============================================
# 使用说明
# ============================================
#
# 1. 将 /path/to/memory-like-a-tree 替换为实际路径
# 2. 确保 python3 在 PATH 中
# 3. 可选：调整日志路径
# 4. 运行 crontab -e 添加任务
#
# 验证 cron 是否生效：
#   crontab -l
#
# 查看日志：
#   tail -f /tmp/mlat-*.log
