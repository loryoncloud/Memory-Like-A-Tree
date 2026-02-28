# Memory-Like-A-Tree 配置参考

## 配置文件位置

按优先级搜索：
1. `./memory-like-a-tree.json`
2. `./config.json`
3. `~/.memory-like-a-tree/config.json`
4. 环境变量 `MLAT_CONFIG` 指定的路径

---

## 完整配置示例

```json
{
  "version": "1.0.0",
  "name": "my-memory-tree",
  
  "paths": {
    "base_dir": "~/.memory-like-a-tree",
    "data_dir": "~/.memory-like-a-tree/data",
    "archive_dir": "~/.memory-like-a-tree/data/archive",
    "obsidian_vault": null
  },
  
  "agents": [
    {
      "name": "default",
      "workspace": "~/.memory-like-a-tree/workspace",
      "memory_file": "MEMORY.md",
      "memory_dir": "memory"
    }
  ],
  
  "confidence": {
    "initial": 0.7,
    "min": 0.05,
    "max": 1.0,
    "search_boost": 0.03,
    "use_boost": 0.08,
    "confirm_value": 0.95
  },
  
  "decay": {
    "grace_period_days": 60,
    "rates": {
      "P0": 0.0,
      "P1": 0.004,
      "P2": 0.008
    }
  },
  
  "cleanup": {
    "archive_threshold": 0.3,
    "auto_cleanup_threshold": 0.05,
    "review_threshold": 0.1
  },
  
  "sync": {
    "enabled": false,
    "interval_hours": 2
  }
}
```

---

## 配置项说明

### paths - 路径配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_dir` | string | `~/.memory-like-a-tree` | 基础目录 |
| `data_dir` | string | `{base_dir}/data` | 数据目录（存放 confidence-db.json）|
| `archive_dir` | string | `{data_dir}/archive` | 归档目录 |
| `obsidian_vault` | string\|null | `null` | Obsidian Vault 路径（可选）|

### agents - Agent 配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | 必填 | Agent 名称 |
| `workspace` | string | 必填 | workspace 路径 |
| `memory_file` | string | `MEMORY.md` | 长期记忆文件名 |
| `memory_dir` | string | `memory` | 中期记忆目录名 |

### confidence - 置信度配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `initial` | float | `0.7` | 新记忆的初始置信度 |
| `min` | float | `0.05` | 最低置信度 |
| `max` | float | `1.0` | 最高置信度 |
| `search_boost` | float | `0.03` | 被搜索时提升量 |
| `use_boost` | float | `0.08` | 被使用时提升量 |
| `confirm_value` | float | `0.95` | 人工确认后的值 |

### decay - 衰减配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `grace_period_days` | int | `60` | 宽限期（天），期间不衰减 |
| `rates.P0` | float | `0.0` | P0 每日衰减率（永不衰减）|
| `rates.P1` | float | `0.004` | P1 每日衰减率 |
| `rates.P2` | float | `0.008` | P2 每日衰减率 |

### cleanup - 清理配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `archive_threshold` | float | `0.3` | 归档阈值 |
| `auto_cleanup_threshold` | float | `0.05` | 自动清理阈值 |
| `review_threshold` | float | `0.1` | 人工审核阈值 |

### sync - 同步配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `false` | 是否启用 Obsidian 同步 |
| `interval_hours` | int | `2` | 同步间隔（小时）|

---

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `MLAT_CONFIG` | 配置文件路径 | `/path/to/config.json` |
| `MLAT_BASE_DIR` | 基础目录（覆盖配置）| `~/.my-memory-tree` |
| `MLAT_DATA_DIR` | 数据目录（覆盖配置）| `~/.my-memory-tree/data` |
| `MLAT_OBSIDIAN_VAULT` | Obsidian Vault 路径 | `~/Documents/Obsidian` |
| `MLAT_GRACE_PERIOD` | 宽限期天数 | `90` |

---

## 多 Agent 配置示例

```json
{
  "agents": [
    {
      "name": "main",
      "workspace": "~/.my-app/workspace"
    },
    {
      "name": "dev",
      "workspace": "~/.my-app/workspace-dev"
    },
    {
      "name": "researcher",
      "workspace": "~/.my-app/workspace-researcher"
    }
  ]
}
```

---

## 衰减计算公式

```
归档时间 = 宽限期 + (初始置信度 - 归档阈值) / 每日衰减率

P2 示例：
归档时间 = 60 + (0.7 - 0.3) / 0.008 = 60 + 50 = 110 天 ≈ 3.7 个月

P1 示例：
归档时间 = 60 + (0.7 - 0.3) / 0.004 = 60 + 100 = 160 天 ≈ 5.3 个月
```

---

*配置一次，自动运行。* 🌳
