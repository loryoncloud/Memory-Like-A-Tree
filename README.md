# 🌳 Memory-Like-A-Tree

> AI Agent 记忆管理系统 - 让知识像树一样生长

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 这是什么？

Memory-Like-A-Tree 是一个为 AI Agent 设计的记忆管理系统。

**核心理念**：Agent 正常工作，树自动生长。

就像真正的树：
- 🌱 新知识像种子一样萌芽
- 🌿 常用的知识茁壮成长
- 🍂 不用的知识自然凋零
- 🪨 落叶化作养分，滋养新的生长

---

## 📐 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           🌳 Memory-Like-A-Tree                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              Agent 工作                                     │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         workspace                                    │   │
│  │                        （唯一源）                                    │   │
│  │                                                                      │   │
│  │   ┌────────────┐ ┌────────────┐ ┌────────────┐                      │   │
│  │   │ MEMORY.md  │ │  memory/   │ │  memory/   │                      │   │
│  │   │  (长期)    │ │ 2026-02.md │ │ 2026-03.md │                      │   │
│  │   └────────────┘ └────────────┘ └────────────┘                      │   │
│  │                                                                      │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                           │
│              ┌──────────────────┼──────────────────┐                       │
│              │                  │                  │                       │
│              ▼                  ▼                  ▼                       │
│       ┌───────────┐      ┌───────────┐      ┌───────────┐                 │
│       │  indexer  │      │  search   │      │  sediment │                 │
│       │  (索引)   │      │  (搜索)   │      │  (沉淀)   │                 │
│       └─────┬─────┘      └─────┬─────┘      └─────┬─────┘                 │
│             │                  │                  │                       │
│             ▼                  │                  │                       │
│       ┌───────────┐            │                  │                       │
│       │confidence │◄───────────┴──────────────────┘                       │
│       │   -db     │                                                        │
│       │  (索引)   │                                                        │
│       └─────┬─────┘                                                        │
│             │                                                              │
│             │ 置信度追踪                                                   │
│             │                                                              │
│       ┌─────┴─────────────────────────────────────┐                       │
│       │                                           │                       │
│       ▼                                           ▼                       │
│  ┌─────────┐                                ┌─────────┐                   │
│  │ decayer │ ──→ 置信度衰减 ──→ 🍂 黄叶 ──→ │ cleaner │                   │
│  │(每天2点)│                                │(每天3点)│                   │
│  └─────────┘                                └────┬────┘                   │
│                                                  │                        │
│                                                  ▼                        │
│                                           ┌───────────┐                   │
│                                           │  archive  │                   │
│                                           │ + 精华提取│                   │
│                                           └───────────┘                   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 生命周期流程

```
创建知识 ──→ 🌱 萌芽 (0.7)
                │
                │ 被使用 → 置信度 ↑
                ▼
            🌿 绿叶 (>=0.8) ←──────────────────────┐
                │                                   │
                │ 长期不使用                        │ 被搜索/使用
                ▼                                   │
            🍂 黄叶 (0.5-0.8) ─────────────────────→│
                │                                   │
                │ 继续不使用                        │
                ▼                                   │
            🍁 枯叶 (0.3-0.5)                       │
                │                                   │
                │ 置信度 < 0.3                      │
                ▼                                   │
            🪨 土壤 ──→ 提取精华 ──→ 可被新知识引用 ┘
```

---

## 🚀 5 分钟快速开始

### 第一步：下载项目

```bash
git clone https://github.com/your-org/memory-like-a-tree.git
cd memory-like-a-tree
```

### 第二步：创建你的第一棵树

```bash
# 创建 workspace 目录
mkdir -p ~/.memory-like-a-tree/workspace/memory

# 创建你的第一个 MEMORY.md
cat > ~/.memory-like-a-tree/workspace/MEMORY.md << 'EOF'
# 我的记忆

## [P0] 核心原则
<!-- TTL: never -->

这里记录永不过期的重要知识。
比如：我的核心价值观、重要的人生经验。

## [P1] 重要知识
<!-- TTL: 90d -->

这里记录重要但可能会过时的知识。
比如：项目架构、技术方案。

## [P2] 日常笔记
<!-- TTL: 30d -->

这里记录日常学习笔记。
比如：今天学到的东西、临时想法。
EOF

echo "✅ workspace 创建完成！"
```

### 第三步：扫描并索引

```bash
cd memory-like-a-tree/core
python3 indexer.py --scan-all
```

你会看到：
```
🔍 开始扫描所有 workspace...

📁 扫描 workspace...
  + 新增: 核心原则 (置信度: 1.0)
  + 新增: 重要知识 (置信度: 0.8)
  + 新增: 日常笔记 (置信度: 0.6)
  共 3 条记忆

✅ 扫描完成: 共 3 条记忆
```

### 第四步：查看你的树

```bash
python3 memory_tree.py visualize
```

输出：
```
🌳 记忆树 (Memory Tree)
│
├── 📊 健康度: 66.7%
├── 🍃 总叶子: 3
│   ├── 🌿 绿叶: 2
│   ├── 🍂 黄叶: 1
│   ├── 🍁 枯叶: 0
│   └── 🪨 土壤: 0
│
└── default: 3 叶
    ├── 🌿 2 🍂 1 🍁 0 🪨 0
```

**恭喜！你的第一棵记忆树已经种下了！** 🎉

---

## 📖 日常使用指南

### 场景一：记录新知识

**方法 A：直接编辑 MEMORY.md（推荐）**

```bash
vim ~/.memory-like-a-tree/workspace/MEMORY.md
```

添加新的知识块：
```markdown
## [P2] 今天学到的 Git 技巧
<!-- TTL: 30d -->

- `git stash` 可以暂存当前修改
- `git cherry-pick` 可以选择性合并提交
```

**方法 B：使用沉淀脚本**

```bash
cd sediment
python3 sediment.py --agent default --content "Git stash 可以暂存修改" --type knowledge
```

### 场景二：搜索知识

```bash
cd core
python3 knowledge_flow.py search "Git" --scope team
```

输出：
```
🔍 搜索结果: 1 条

  [default] 今天学到的 Git 技巧 (置信度: 0.6, 分数: 11.4)
    - git stash 可以暂存当前修改...
```

**小贴士**：每次搜索都会自动提升被找到的知识的置信度！

### 场景三：查看树的健康状况

```bash
python3 memory_tree.py visualize
```

### 场景四：手动触发衰减（通常自动运行）

```bash
# 先预览
python3 decayer.py --dry-run

# 确认后执行
python3 decayer.py --run
```

### 场景五：查看清理报告

```bash
python3 cleaner.py --report
```

---

## ⚙️ 设置自动化

让树自动生长，你只需要设置一次 Cron：

```bash
crontab -e
```

添加以下内容（记得修改路径）：

```bash
# 每 2 小时扫描索引
0 */2 * * * cd ~/memory-like-a-tree/core && python3 indexer.py --watch

# 每天凌晨 2 点执行衰减
0 2 * * * cd ~/memory-like-a-tree/core && python3 decayer.py --run

# 每天凌晨 3 点执行清理
0 3 * * * cd ~/memory-like-a-tree/core && python3 cleaner.py --auto-cleanup
```

设置完成后，树会自动：
- 定期索引你的新知识
- 衰减长期不用的知识
- 归档低置信度的知识并提取精华

---

## 🎯 MEMORY.md 写作指南

### 格式模板

```markdown
## [优先级] 标题
<!-- TTL: 过期时间 -->

内容...
```

### 优先级选择

| 优先级 | 适用场景 | 衰减速度 |
|--------|----------|----------|
| **P0** | 核心价值观、重要原则、永久有效的知识 | 永不衰减 |
| **P1** | 项目架构、技术方案、重要经验 | 慢（约 5 个月归档）|
| **P2** | 日常笔记、临时想法、学习记录 | 快（约 4 个月归档）|

### 示例

```markdown
## [P0] 代码审查原则
<!-- TTL: never -->

1. 先看整体设计，再看细节实现
2. 关注边界条件和错误处理
3. 提出建设性意见，不只是批评

## [P1] 项目 X 的技术架构
<!-- TTL: 90d -->

- 前端：React + TypeScript
- 后端：Python FastAPI
- 数据库：PostgreSQL

## [P2] 今天学到的
<!-- TTL: 30d -->

Python 的 `functools.lru_cache` 可以缓存函数结果，提升性能。
```

---

## ❓ 常见问题

### Q: 置信度是怎么计算的？

| 事件 | 置信度变化 |
|------|------------|
| 创建新知识 | 设为 0.7（萌芽）|
| 被搜索命中 | +0.03 |
| 被引用使用 | +0.08 |
| 人工确认重要 | 设为 0.95 |
| 每天未访问 (P2) | -0.008 |
| 每天未访问 (P1) | -0.004 |
| P0 | 永不衰减 |

### Q: 知识什么时候会被归档？

当置信度低于 0.3 时会被归档。

- **P2**：约 60 + 50 = 110 天（3.7 个月）
- **P1**：约 60 + 100 = 160 天（5.3 个月）
- **P0**：永不归档

### Q: 归档后的知识还能找到吗？

可以！归档的知识保存在 `archive/` 目录，精华会被提取保留。

### Q: 怎么让知识「复活」？

搜索或使用这条知识，置信度就会提升。多次使用后，黄叶会变回绿叶。

### Q: 支持多个 Agent 吗？

支持！参考 `examples/multi-agent.json` 配置多个 Agent 的 workspace。

### Q: 可以同步到 Obsidian 吗？

可以！在配置文件中设置 `obsidian_vault` 路径，然后运行：
```bash
python3 sync_workspace_to_obsidian.py
```

---

## 📁 项目结构

```
memory-like-a-tree/
├── core/                    # 🌳 记忆树核心
│   ├── config.py           # 配置管理
│   ├── db.py               # 数据库操作
│   ├── indexer.py          # 记忆索引
│   ├── decayer.py          # 置信度衰减
│   ├── cleaner.py          # 记忆清理
│   ├── knowledge_flow.py   # 跨 Agent 搜索
│   ├── memory_tree.py      # 可视化
│   └── sync_workspace_to_obsidian.py
│
├── issue-manager/          # 📋 Issue 管理（可选）
├── sediment/               # 💧 沉淀系统
├── examples/               # 📝 配置示例
├── docs/                   # 📚 详细文档
└── scripts/                # 🔧 自动化脚本
```

---

## 📚 更多文档

- [使用指南](docs/usage-guide.md) - 详细使用教程
- [配置参考](docs/config-reference.md) - 完整配置说明
- [API 参考](docs/api-reference.md) - 开发者文档

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

## 📄 License

MIT License

---

**让知识像树一样生长。** 🌳

*Agent 正常工作，树自动生长。*
