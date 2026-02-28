#!/usr/bin/env python3
"""
🌳 Memory-Like-A-Tree 记忆树系统

统一语义框架，让知识像树一样生长、流动、循环。

架构：
- 主树干 = Obsidian Vault（共有知识库，可选）
- 分支 = 各 Agent 的 workspace
- 叶子 = 知识/记忆（置信度决定生命周期）
- 土壤 = 归档区（养分循环）

用法：
    python3 memory_tree.py status                    # 查看树的状态
    python3 memory_tree.py search "关键词"           # 搜索知识
    python3 memory_tree.py archive --agent dev       # 归档低置信度记忆
    python3 memory_tree.py extract --memory-id xxx   # 提取精华
    python3 memory_tree.py flow                      # 养分回流
    python3 memory_tree.py visualize                 # 可视化
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

# 尝试导入配置
try:
    from config import get_config
    _config = get_config()
    BASE_DIR = _config.base_dir
    DATA_DIR = _config.data_dir
    ARCHIVE_DIR = _config.archive_dir
    OBSIDIAN_VAULT_DIR = _config.obsidian_vault
    ESSENCE_DIR = OBSIDIAN_VAULT_DIR / "03-精华库" if OBSIDIAN_VAULT_DIR else None
    
    # 从配置构建 WORKSPACES
    WORKSPACES = {}
    for agent in _config.agents:
        WORKSPACES[agent["name"]] = Path(agent["workspace"])
except:
    # 回退到默认路径
    BASE_DIR = Path.home() / ".memory-like-a-tree"
    DATA_DIR = BASE_DIR / "data"
    ARCHIVE_DIR = DATA_DIR / "archive"
    OBSIDIAN_VAULT_DIR = None
    ESSENCE_DIR = None
    WORKSPACES = {
        "default": BASE_DIR / "workspace"
    }

# 置信度阈值
CONFIDENCE_THRESHOLDS = {
    "green": 0.8,    # 🌿 绿叶茂盛
    "yellow": 0.5,   # 🍂 叶子变黄
    "withered": 0.3, # 🍁 枯萎落叶
    "soil": 0.0,     # 🪨 落入土壤
}

# 叶子状态 emoji
LEAF_STATUS = {
    "green": "🌿",
    "yellow": "🍂",
    "withered": "🍁",
    "soil": "🪨",
}


def load_memory_db() -> Dict[str, Any]:
    """加载 memory-confidence 数据库"""
    db_path = DATA_DIR / "confidence-db.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"memories": {}}


def save_memory_db(db: Dict[str, Any]):
    """保存 memory-confidence 数据库"""
    db_path = DATA_DIR / "confidence-db.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_leaf_status(confidence: float) -> str:
    """根据置信度获取叶子状态"""
    if confidence >= CONFIDENCE_THRESHOLDS["green"]:
        return "green"
    elif confidence >= CONFIDENCE_THRESHOLDS["yellow"]:
        return "yellow"
    elif confidence >= CONFIDENCE_THRESHOLDS["withered"]:
        return "withered"
    else:
        return "soil"


def get_tree_status() -> Dict[str, Any]:
    """
    获取记忆树状态
    
    Returns:
        树的状态统计
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    # 统计各分支（Agent）的叶子状态
    branches = defaultdict(lambda: {"green": 0, "yellow": 0, "withered": 0, "soil": 0, "total": 0})
    
    for mem_id, mem in memories.items():
        agent = mem.get("agent", "unknown")
        confidence = mem.get("confidence", 0.5)
        status = get_leaf_status(confidence)
        
        branches[agent][status] += 1
        branches[agent]["total"] += 1
    
    # 计算整体健康度
    total_leaves = len(memories)
    green_leaves = sum(b["green"] for b in branches.values())
    health = round(green_leaves / total_leaves * 100, 1) if total_leaves > 0 else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_leaves": total_leaves,
        "health_percent": health,
        "branches": dict(branches),
        "summary": {
            "green": sum(b["green"] for b in branches.values()),
            "yellow": sum(b["yellow"] for b in branches.values()),
            "withered": sum(b["withered"] for b in branches.values()),
            "soil": sum(b["soil"] for b in branches.values()),
        }
    }


def extract_essence(memory: Dict[str, Any]) -> Dict[str, Any]:
    """
    从记忆中提取精华
    
    Args:
        memory: 记忆数据
    
    Returns:
        精华数据
    """
    content = memory.get("content_preview", "")
    title = memory.get("title", "")
    
    # 提取关键信息
    essence = {
        "original_id": memory.get("id"),
        "original_agent": memory.get("agent"),
        "title": title,
        "extracted_at": datetime.now().isoformat(),
        "keywords": [],
        "summary": "",
        "lessons": [],
    }
    
    # 提取关键词
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)
    english_words = re.findall(r'[a-zA-Z]{4,}', content)
    essence["keywords"] = list(set(chinese_words[:5] + [w.lower() for w in english_words[:5]]))
    
    # 提取经验教训（查找特定模式）
    lesson_patterns = [
        r'经验[：:](.*?)(?:\n|$)',
        r'教训[：:](.*?)(?:\n|$)',
        r'注意[：:](.*?)(?:\n|$)',
        r'重要[：:](.*?)(?:\n|$)',
    ]
    for pattern in lesson_patterns:
        matches = re.findall(pattern, content)
        essence["lessons"].extend(matches)
    
    # 生成摘要（取前 100 字）
    clean_content = re.sub(r'[#\-*`]', '', content)
    essence["summary"] = clean_content[:100].strip() + "..." if len(clean_content) > 100 else clean_content.strip()
    
    return essence


def archive_memory(memory_id: str, extract: bool = True) -> Dict[str, Any]:
    """
    归档记忆（移入土壤）
    
    Args:
        memory_id: 记忆 ID
        extract: 是否提取精华
    
    Returns:
        归档结果
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    if memory_id not in memories:
        return {"status": "error", "message": f"记忆 {memory_id} 不存在"}
    
    memory = memories[memory_id]
    
    # 确保归档目录存在
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 提取精华
    essence = None
    if extract:
        essence = extract_essence(memory)
    
    # 保存到归档
    archive_data = {
        "archived_at": datetime.now().isoformat(),
        "original_memory": memory,
        "essence": essence,
    }
    
    archive_file = ARCHIVE_DIR / f"{memory_id.replace(':', '_').replace('/', '_')}.json"
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
    
    # 从活跃记忆中移除
    del memories[memory_id]
    save_memory_db(db)
    
    return {
        "status": "success",
        "memory_id": memory_id,
        "archive_file": str(archive_file),
        "essence_extracted": extract,
        "essence": essence
    }


def archive_withered_leaves(agent: str = None, dry_run: bool = True) -> Dict[str, Any]:
    """
    归档枯萎的叶子（低置信度记忆）
    
    Args:
        agent: 指定 Agent（可选）
        dry_run: 是否只是预览
    
    Returns:
        归档结果
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    to_archive = []
    
    for mem_id, mem in memories.items():
        # 过滤 Agent
        if agent and mem.get("agent") != agent:
            continue
        
        # 检查置信度
        confidence = mem.get("confidence", 0.5)
        if confidence < CONFIDENCE_THRESHOLDS["withered"]:
            to_archive.append({
                "id": mem_id,
                "agent": mem.get("agent"),
                "title": mem.get("title"),
                "confidence": confidence
            })
    
    if dry_run:
        return {
            "status": "dry_run",
            "to_archive": to_archive,
            "count": len(to_archive)
        }
    
    # 执行归档
    archived = []
    for item in to_archive:
        result = archive_memory(item["id"], extract=True)
        if result["status"] == "success":
            archived.append(item)
    
    return {
        "status": "success",
        "archived": archived,
        "count": len(archived)
    }


def flow_essence_to_trunk() -> Dict[str, Any]:
    """
    养分回流：将精华同步到主树干（Obsidian）
    
    Returns:
        回流结果
    """
    # 确保精华库目录存在
    ESSENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 扫描归档目录
    if not ARCHIVE_DIR.exists():
        return {"status": "success", "message": "没有归档的记忆", "count": 0}
    
    essences = []
    
    for archive_file in ARCHIVE_DIR.glob("*.json"):
        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            essence = data.get("essence")
            if essence:
                essences.append(essence)
        except Exception as e:
            print(f"  ⚠️ 读取 {archive_file} 失败: {e}")
    
    if not essences:
        return {"status": "success", "message": "没有可回流的精华", "count": 0}
    
    # 按 Agent 分组
    by_agent = defaultdict(list)
    for e in essences:
        by_agent[e.get("original_agent", "unknown")].append(e)
    
    # 生成精华文档
    today = datetime.now().strftime("%Y-%m-%d")
    essence_file = ESSENCE_DIR / f"{today}-精华汇总.md"
    
    content = f"# 🌳 精华汇总 ({today})\n\n"
    content += f"> 从 {len(essences)} 条归档记忆中提取的精华\n\n"
    
    for agent, agent_essences in sorted(by_agent.items()):
        content += f"## {agent}\n\n"
        for e in agent_essences:
            content += f"### {e.get('title', '无标题')}\n\n"
            content += f"**关键词**: {', '.join(e.get('keywords', []))}\n\n"
            content += f"{e.get('summary', '')}\n\n"
            if e.get('lessons'):
                content += "**经验教训**:\n"
                for lesson in e['lessons']:
                    content += f"- {lesson}\n"
                content += "\n"
            content += "---\n\n"
    
    essence_file.write_text(content, encoding='utf-8')
    
    return {
        "status": "success",
        "file": str(essence_file),
        "count": len(essences),
        "by_agent": {k: len(v) for k, v in by_agent.items()}
    }


def search_tree(query: str, scope: str = "all") -> List[Dict[str, Any]]:
    """
    在记忆树中搜索
    
    Args:
        query: 搜索关键词
        scope: 搜索范围 ("leaves", "soil", "all")
    
    Returns:
        搜索结果
    """
    results = []
    query_lower = query.lower()
    
    # 搜索活跃记忆（叶子）
    if scope in ["leaves", "all"]:
        db = load_memory_db()
        for mem_id, mem in db.get("memories", {}).items():
            title = mem.get("title", "").lower()
            content = mem.get("content_preview", "").lower()
            
            if query_lower in title or query_lower in content:
                status = get_leaf_status(mem.get("confidence", 0.5))
                results.append({
                    "type": "leaf",
                    "status": status,
                    "emoji": LEAF_STATUS[status],
                    "id": mem_id,
                    "agent": mem.get("agent"),
                    "title": mem.get("title"),
                    "confidence": mem.get("confidence"),
                    "preview": mem.get("content_preview", "")[:100]
                })
    
    # 搜索归档（土壤）
    if scope in ["soil", "all"] and ARCHIVE_DIR.exists():
        for archive_file in ARCHIVE_DIR.glob("*.json"):
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                mem = data.get("original_memory", {})
                title = mem.get("title", "").lower()
                content = mem.get("content_preview", "").lower()
                
                if query_lower in title or query_lower in content:
                    results.append({
                        "type": "soil",
                        "emoji": "🪨",
                        "id": mem.get("id"),
                        "agent": mem.get("agent"),
                        "title": mem.get("title"),
                        "archived_at": data.get("archived_at"),
                        "preview": mem.get("content_preview", "")[:100]
                    })
            except:
                pass
    
    return results


def visualize_tree() -> str:
    """
    生成记忆树的 ASCII 可视化
    
    Returns:
        ASCII 树形图
    """
    status = get_tree_status()
    
    tree = """
🌳 记忆树 (Memory Tree)
│
├── 📊 健康度: {health}%
├── 🍃 总叶子: {total}
│   ├── 🌿 绿叶: {green}
│   ├── 🍂 黄叶: {yellow}
│   ├── 🍁 枯叶: {withered}
│   └── 🪨 土壤: {soil}
│
├── 🌿 分支 (Agents)
""".format(
        health=status["health_percent"],
        total=status["total_leaves"],
        green=status["summary"]["green"],
        yellow=status["summary"]["yellow"],
        withered=status["summary"]["withered"],
        soil=status["summary"]["soil"],
    )
    
    branches = status["branches"]
    sorted_branches = sorted(branches.items(), key=lambda x: -x[1]["total"])
    
    for i, (agent, stats) in enumerate(sorted_branches):
        is_last = i == len(sorted_branches) - 1
        prefix = "└──" if is_last else "├──"
        sub_prefix = "    " if is_last else "│   "
        
        tree += f"{prefix} {agent}: {stats['total']} 叶\n"
        tree += f"{sub_prefix}├── 🌿 {stats['green']} "
        tree += f"🍂 {stats['yellow']} "
        tree += f"🍁 {stats['withered']} "
        tree += f"🪨 {stats['soil']}\n"
    
    return tree


def main():
    parser = argparse.ArgumentParser(description="🌳 记忆树系统")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # status 命令
    subparsers.add_parser("status", help="查看树的状态")
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索知识")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--scope", default="all", choices=["leaves", "soil", "all"])
    
    # archive 命令
    archive_parser = subparsers.add_parser("archive", help="归档低置信度记忆")
    archive_parser.add_argument("--agent", help="指定 Agent")
    archive_parser.add_argument("--execute", action="store_true", help="执行归档（默认只预览）")
    
    # extract 命令
    extract_parser = subparsers.add_parser("extract", help="提取精华")
    extract_parser.add_argument("--memory-id", required=True, help="记忆 ID")
    
    # flow 命令
    subparsers.add_parser("flow", help="养分回流到主树干")
    
    # visualize 命令
    subparsers.add_parser("visualize", help="可视化记忆树")
    
    args = parser.parse_args()
    
    if args.command == "status":
        status = get_tree_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    
    elif args.command == "search":
        results = search_tree(args.query, args.scope)
        print(f"\n🔍 搜索结果: {len(results)} 条\n")
        for r in results:
            print(f"  {r['emoji']} [{r['agent']}] {r['title']}")
            if r['type'] == 'leaf':
                print(f"     置信度: {r['confidence']}")
            print(f"     {r['preview']}...")
            print()
    
    elif args.command == "archive":
        result = archive_withered_leaves(args.agent, dry_run=not args.execute)
        if result["status"] == "dry_run":
            print(f"\n🍁 预览: 将归档 {result['count']} 条记忆\n")
            for item in result["to_archive"]:
                print(f"  - [{item['agent']}] {item['title']} (置信度: {item['confidence']})")
            print("\n使用 --execute 执行归档")
        else:
            print(f"\n✅ 已归档 {result['count']} 条记忆")
    
    elif args.command == "extract":
        db = load_memory_db()
        memory = db.get("memories", {}).get(args.memory_id)
        if memory:
            essence = extract_essence(memory)
            print(json.dumps(essence, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 记忆 {args.memory_id} 不存在")
    
    elif args.command == "flow":
        result = flow_essence_to_trunk()
        if result["count"] > 0:
            print(f"\n✅ 养分回流完成")
            print(f"   精华数: {result['count']}")
            print(f"   文件: {result['file']}")
        else:
            print(f"\n{result['message']}")
    
    elif args.command == "visualize":
        print(visualize_tree())


if __name__ == "__main__":
    main()
