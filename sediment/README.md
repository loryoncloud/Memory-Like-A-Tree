# 统一沉淀系统

让沉淀成为自动化习惯，而不是手动提醒。

## 功能

1. **更新 MEMORY.md** - 自动添加到 Agent 的记忆文件
2. **触发索引** - 自动更新 memory-confidence 数据库
3. **同步 Obsidian** - 自动同步到知识库
4. **建立关联** - 自动建立知识之间的链接

## 快速使用

### 沉淀知识

```bash
cd ~/.openclaw/shared/sediment

# 沉淀一条知识
python3 sediment.py --agent dev --content "学到的知识内容" --type knowledge

# 沉淀经验教训
python3 sediment.py --agent dev --content "踩坑经验" --type lesson

# 沉淀任务总结（关联 Issue）
python3 sediment.py --agent dev --issue 24 --content "任务总结" --type summary
```

### 同步所有系统

```bash
# 一键同步所有系统
python3 sediment.py --sync-all
```

### 检查状态

```bash
# 检查所有 Agent 的沉淀状态
python3 sediment.py --status

# 检查单个 Agent
python3 sediment.py --status --agent dev
```

## 内容类型

| 类型 | 说明 | 优先级 |
|------|------|--------|
| `knowledge` | 技术知识 | P2 |
| `lesson` | 经验教训 | P1 |
| `rule` | 规则/规范 | P1 |
| `tool` | 工具/技巧 | P2 |
| `decision` | 决策记录 | P2 |
| `summary` | 任务总结 | P2 |

## 数据流

```
沉淀内容
   │
   ▼
┌─────────────────┐
│  sediment.py    │
└────────┬────────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
MEMORY  索引  Obsidian
  .md   更新   同步
```

## 与 Issue 系统集成

关闭 Issue 时自动沉淀：

```bash
# 1. 沉淀任务总结
python3 sediment.py --agent dev --issue 24 --content "任务总结" --type summary

# 2. 关闭 Issue
cd ~/.openclaw/shared/async-issue-manager/scripts
python3 manager.py close 24
```

## Cron 配置

每日自动同步（建议添加到 cron）：

```bash
# 每天 06:00 同步所有系统
0 6 * * * cd ~/.openclaw/shared/sediment && python3 sediment.py --sync-all >> /tmp/sediment.log 2>&1
```
