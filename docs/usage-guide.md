# Memory-Like-A-Tree 使用指南

## 快速开始

### 1. 单 Agent 场景

最简单的使用方式，适合个人使用。

```bash
# 1. 克隆项目
git clone https://github.com/your-org/memory-like-a-tree.git
cd memory-like-a-tree

# 2. 复制配置
cp examples/single-agent.json memory-like-a-tree.json

# 3. 创建 workspace
mkdir -p ~/.memory-like-a-tree/workspace/memory

# 4. 创建 MEMORY.md
cat > ~/.memory-like-a-tree/workspace/MEMORY.md << 'EOF'
# 我的记忆

## [P0] 核心原则
<!-- TTL: never -->

这里记录永不过期的重要知识。

## [P1] 重要知识
<!-- TTL: 90d -->

这里记录重要但可能会过时的知识。

## [P2] 普通笔记
<!-- TTL: 30d -->

这里记录日常笔记。
EOF

# 5. 扫描索引
python3 core/indexer.py --scan-all

# 6. 查看树状态
python3 core/memory_tree.py visualize
```

### 2. 多 Agent 场景

适合 AI Agent 团队协作。

```bash
# 1. 复制多 Agent 配置
cp examples/multi-agent.json memory-like-a-tree.json

# 2. 编辑配置，添加你的 Agent
vim memory-like-a-tree.json

# 3. 为每个 Agent 创建 workspace
for agent in main dev researcher writer; do
  mkdir -p ~/.my-app/workspace-$agent/memory
  touch ~/.my-app/workspace-$agent/MEMORY.md
done

# 4. 扫描所有 workspace
python3 core/indexer.py --scan-all
```

---

## 日常使用

### 搜索知识

```bash
# 搜索所有 Agent 的知识
python3 core/knowledge_flow.py search "关键词" --scope team

# 只搜索自己的知识
python3 core/knowledge_flow.py search "关键词" --scope self --agent default
```

### 沉淀知识

**方式一：直接编辑 MEMORY.md**

```markdown
## [P2] 今天学到的
<!-- TTL: 30d -->

学到了 XXX...
```

**方式二：使用沉淀脚本**

```bash
python3 sediment/sediment.py --agent default --content "学到的内容" --type knowledge
```

### 关闭 Issue

```bash
# 必须填写 learnings
python3 issue-manager/manager.py close 1 --learnings "学到了什么"

# 如果实在没什么可写的（不推荐）
python3 issue-manager/manager.py close 1 --skip-learnings
```

---

## 自动化配置

### 设置 Cron

```bash
# 编辑 crontab
crontab -e

# 添加以下内容（修改路径）
0 */2 * * * cd ~/memory-like-a-tree && python3 core/indexer.py --watch
0 2 * * * cd ~/memory-like-a-tree && python3 core/decayer.py --run
0 3 * * * cd ~/memory-like-a-tree && python3 core/cleaner.py --auto-cleanup
```

### 验证自动化

```bash
# 查看 cron 任务
crontab -l

# 手动测试
python3 core/indexer.py --watch
python3 core/decayer.py --dry-run
python3 core/cleaner.py --report
```

---

## MEMORY.md 格式

```markdown
# 标题（可选）

## [P0] 核心知识标题
<!-- TTL: never -->

内容...

## [P1] 重要知识标题
<!-- TTL: 90d -->

内容...

## [P2] 普通知识标题
<!-- TTL: 30d -->

内容...
```

### 优先级说明

| 优先级 | 说明 | 衰减速度 |
|--------|------|----------|
| P0 | 核心知识，永不过期 | 不衰减 |
| P1 | 重要知识，90 天开始衰减 | -0.004/天 |
| P2 | 普通知识，30 天开始衰减 | -0.008/天 |

### TTL 说明

| TTL | 说明 |
|-----|------|
| never | 永不过期 |
| 90d | 90 天后开始衰减 |
| 30d | 30 天后开始衰减 |

---

## 常见问题

### Q: 置信度怎么提升？

| 事件 | 提升量 |
|------|--------|
| 被搜索命中 | +0.03 |
| 被引用使用 | +0.08 |
| 人工确认 | 设为 0.95 |

### Q: 知识什么时候会被归档？

当置信度低于 0.3 时，会被自动归档。

计算公式：
- P2：60 天宽限期 + 50 天衰减 ≈ 3.7 个月
- P1：60 天宽限期 + 100 天衰减 ≈ 5.3 个月

### Q: 归档后的知识还能找到吗？

可以。归档的知识会保存在 `archive/` 目录，精华会被提取。

### Q: 怎么让知识「复活」？

搜索或使用这条知识，置信度就会提升。如果置信度提升到 0.3 以上，就不会被归档。

---

## 最佳实践

1. **定期更新 MEMORY.md** - 把重要的经验记录下来
2. **用搜索代替直接读文件** - 搜索会提升置信度
3. **关闭 Issue 时认真填 learnings** - 这是沉淀知识的好机会
4. **P0 要慎用** - 只有真正核心的知识才标 P0
5. **让自动化运行** - 设置好 Cron，不用手动操作

---

*Agent 正常工作，树自动生长。* 🌳
