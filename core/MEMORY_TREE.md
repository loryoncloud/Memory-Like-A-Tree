# 🌳 记忆树系统

> 这不是一个新系统，而是用「树」的语义框架来描述现有架构。

---

## 一、树的结构

```
🌳 记忆树
│
├── 🪵 主树干 = Obsidian Vault
│   └── ~/.openclaw/shared/obsidian-vault/
│
├── 🌿 分支 = 各 Agent 的 workspace
│   ├── workspace/          (main)
│   ├── workspace-dev/      (dev)
│   ├── workspace-hunter/   (hunter)
│   └── ...                 (其他 Agent)
│
├── 🍃 叶子 = 记忆
│   ├── MEMORY.md           (长期记忆)
│   └── memory/*.md         (中期记忆)
│
├── 💧 养分系统 = 置信度
│   └── memory-confidence/confidence-db.json
│
└── 🪨 土壤 = 归档区
    └── memory-archive/
```

---

## 二、组件映射

| 树的概念 | 现有组件 | 位置 |
|----------|----------|------|
| **主树干** | Obsidian Vault | `~/.openclaw/shared/obsidian-vault/` |
| **分支** | workspace-{agent}/ | `~/.openclaw/workspace-*/` |
| **叶子** | MEMORY.md + memory/*.md | 各 workspace |
| **养分** | 置信度系统 | `~/.openclaw/shared/memory-confidence/` |
| **土壤** | 归档区 | `~/.openclaw/shared/memory-archive/` |
| **养分输入** | sediment.py | `~/.openclaw/shared/sediment/` |
| **养分流动** | knowledge_flow.py | `~/.openclaw/shared/memory-confidence/` |
| **落叶入土** | cleaner.py | `~/.openclaw/shared/memory-confidence/` |

---

## 三、叶子的生命周期

叶子（记忆）的状态由**置信度**决定：

| 状态 | 置信度 | 说明 |
|------|--------|------|
| 🌱 萌芽 | 0.7 (初始) | 刚创建的记忆 |
| 🌿 绿叶 | ≥ 0.8 | 活跃使用的记忆 |
| 🍂 黄叶 | 0.5 - 0.8 | 开始衰减 |
| 🍁 枯叶 | 0.3 - 0.5 | 准备归档 |
| 🪨 土壤 | < 0.3 | 已归档 |

### 置信度变化

| 事件 | 变化 | 执行者 |
|------|------|--------|
| 创建记忆 | = 0.7 | sediment.py |
| 被搜索命中 | += 0.05 | knowledge_flow.py |
| 被引用/使用 | += 0.1 | memory_tree_api.py |
| 被 bro 确认 | = 0.95 | 手动 |
| 每天未访问 | -= 0.015 | decayer.py |
| 归档 | = 0 | cleaner.py |

---

## 四、养分循环

```
创建记忆 (sediment.py)
    │
    ▼
🌱 萌芽 → 🌿 绿叶 → 🍂 黄叶 → 🍁 枯叶
    │                              │
    │ 被访问 → 置信度 ↑            │ 不访问 → 置信度 ↓
    │                              │
    │                              ▼
    │                         归档 (cleaner.py)
    │                              │
    │                              ▼
    │                         🪨 土壤 (memory-archive/)
    │                              │
    │                              ▼ 提取精华
    │                         Obsidian 精华库
    │                              │
    └──────────────────────────────┘
                    ↑ 新记忆可以引用旧精华
```

---

## 五、自动化任务

| 任务 | 频率 | 组件 | 功能 |
|------|------|------|------|
| 索引更新 | 每 2 小时 | indexer.py | 扫描新记忆 |
| 置信度衰减 | 每天 02:00 | decayer.py | 衰减未访问记忆 |
| 归档清理 | 每天 03:00 | cleaner.py | 归档低置信度记忆 |

---

## 六、使用方式

### 添加记忆（养分输入）

```bash
cd ~/.openclaw/shared/sediment
python3 sediment.py --agent dev --content "学到的内容" --type knowledge
```

### 搜索记忆（养分流动）

```bash
cd ~/.openclaw/shared/memory-confidence
python3 knowledge_flow.py search "关键词" --scope team
```

### 查看树状态

```bash
cd ~/.openclaw/shared/memory-confidence
python3 memory_tree.py visualize
```

### 获取推荐

```bash
python3 knowledge_flow.py recommend --agent dev --task "当前任务"
```

---

## 七、核心原则

1. **统一入口** - 通过 sediment.py 添加，通过 knowledge_flow.py 搜索
2. **自动生命周期** - decayer/cleaner 自动管理置信度
3. **养分循环** - 归档记忆的精华回流到 Obsidian
4. **分支隔离** - 每个 Agent 的 workspace 独立

---

*这不是新系统，是现有架构的语义框架。*
