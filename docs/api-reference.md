# Memory-Like-A-Tree API 参考

## 核心模块 (core/)

### config.py - 配置管理

```python
from core.config import get_config

config = get_config()

# 属性
config.base_dir      # Path: 基础目录
config.data_dir      # Path: 数据目录
config.archive_dir   # Path: 归档目录
config.obsidian_vault # Path|None: Obsidian Vault 路径
config.agents        # list: Agent 配置列表
config.confidence    # dict: 置信度配置
config.decay         # dict: 衰减配置
config.cleanup       # dict: 清理配置
config.sync          # dict: 同步配置

# 方法
config.get(key, default=None)      # 获取配置值
config.get_agent(name)             # 获取指定 Agent 配置
config.get_agent_workspace(name)   # 获取 Agent workspace 路径
config.to_dict()                   # 导出配置为字典
config.save(path=None)             # 保存配置到文件
Config.reload()                    # 重新加载配置
```

### db.py - 数据库操作

```python
from core.db import (
    load_db, save_db, get_memory, set_memory,
    get_all_memories, get_stats, content_hash
)

# 加载/保存数据库
db = load_db()                     # 加载数据库
save_db(db)                        # 保存数据库

# 记忆操作
memory = get_memory(memory_id)     # 获取单条记忆
set_memory(memory_id, data)        # 设置单条记忆
memories = get_all_memories()      # 获取所有记忆

# 统计
stats = get_stats()                # 获取统计信息

# 工具
hash = content_hash(content)       # 计算内容哈希
```

### indexer.py - 记忆索引

```bash
# 命令行
python3 indexer.py --scan-all          # 扫描所有 workspace
python3 indexer.py --watch             # 增量扫描
python3 indexer.py --rebuild-indexes   # 重建索引
python3 indexer.py --report            # 生成报告
python3 indexer.py --stats             # 显示统计
```

```python
# Python API
from core.indexer import (
    scan_workspace, scan_all_workspaces,
    parse_memory_section, rebuild_index
)

result = scan_all_workspaces()     # 扫描所有 workspace
result = scan_workspace(path)      # 扫描单个 workspace
sections = parse_memory_section(content)  # 解析 MEMORY.md
```

### decayer.py - 置信度衰减

```bash
# 命令行
python3 decayer.py --run           # 执行衰减
python3 decayer.py --dry-run       # 预览衰减
```

```python
# Python API
from core.decayer import run_decay, preview_decay

result = run_decay()               # 执行衰减
result = preview_decay()           # 预览衰减
```

### cleaner.py - 记忆清理

```bash
# 命令行
python3 cleaner.py --auto-cleanup  # 自动清理
python3 cleaner.py --report        # 生成报告
python3 cleaner.py --archive-all   # 归档所有低置信度记忆
```

```python
# Python API
from core.cleaner import (
    get_cleanup_candidates, archive_memory,
    auto_cleanup, generate_report
)

candidates = get_cleanup_candidates()  # 获取清理候选
result = archive_memory(memory_id)     # 归档单条记忆
result = auto_cleanup()                # 自动清理
report = generate_report()             # 生成报告
```

### knowledge_flow.py - 知识搜索

```bash
# 命令行
python3 knowledge_flow.py search "关键词" --scope team
python3 knowledge_flow.py search "关键词" --scope self --agent default
python3 knowledge_flow.py recommend --agent default --task "任务描述"
python3 knowledge_flow.py graph --output graph.json
```

```python
# Python API
from core.knowledge_flow import (
    search_memories, recommend_memories,
    boost_confidence, build_knowledge_graph
)

results = search_memories(query, scope="team")  # 搜索
results = recommend_memories(agent, task)       # 推荐
boost_confidence(memory_id, amount=0.05)        # 提升置信度
graph = build_knowledge_graph()                 # 构建知识图谱
```

### memory_tree.py - 可视化

```bash
# 命令行
python3 memory_tree.py visualize   # 可视化树状态
python3 memory_tree.py status      # 查看状态
python3 memory_tree.py search "关键词"  # 搜索
python3 memory_tree.py archive --agent default  # 归档
```

```python
# Python API
from core.memory_tree import (
    get_tree_status, visualize_tree,
    archive_agent_memories, extract_essence
)

status = get_tree_status()         # 获取树状态
output = visualize_tree()          # 生成可视化输出
result = archive_agent_memories(agent)  # 归档 Agent 记忆
essence = extract_essence(memory)  # 提取精华
```

---

## Issue 管理器 (issue-manager/)

### manager.py

```bash
# 命令行
python3 manager.py create --title "标题" --priority P1 --labels bug
python3 manager.py list --status open
python3 manager.py show 1
python3 manager.py assign 1 default
python3 manager.py close 1 --learnings "学到了什么"
python3 manager.py close 1 --skip-learnings
python3 manager.py sync
python3 manager.py stats
```

### sync_progress.py

```bash
# 命令行
python3 sync_progress.py update 1 --progress "进度描述" --agent default
python3 sync_progress.py view --issue 1
```

### deliverable.py

```bash
# 命令行
python3 deliverable.py add 1 --file /path/to/file.md
python3 deliverable.py list --issue 1
```

---

## 沉淀系统 (sediment/)

### sediment.py

```bash
# 命令行
python3 sediment.py --agent default --content "内容" --type knowledge
python3 sediment.py --agent default --issue 1 --summary "总结"
python3 sediment.py --sync-all
```

```python
# Python API
from sediment.sediment import (
    sediment_knowledge, sediment_issue,
    sync_all_systems
)

result = sediment_knowledge(agent, content, type)  # 沉淀知识
result = sediment_issue(agent, issue_id, summary)  # 沉淀 Issue
result = sync_all_systems()                        # 同步所有系统
```

---

## 数据结构

### 记忆 (Memory)

```json
{
  "id": "agent:title",
  "agent": "default",
  "title": "知识标题",
  "priority": "P2",
  "ttl": "30d",
  "confidence": 0.7,
  "source": "manual",
  "content_hash": "abc123",
  "content_preview": "内容预览...",
  "file": "/path/to/MEMORY.md",
  "line_start": 10,
  "created_at": "2026-02-28T12:00:00",
  "updated_at": "2026-02-28T12:00:00",
  "last_accessed": "2026-02-28T12:00:00",
  "access_count": 5
}
```

### 数据库 (confidence-db.json)

```json
{
  "version": "1.0.0",
  "memories": {
    "agent:title": { ... }
  },
  "last_updated": "2026-02-28T12:00:00"
}
```

---

*让知识像树一样生长。* 🌳
