#!/usr/bin/env python3
"""
Memory-Like-A-Tree 跨 Agent 知识搜索和推荐系统

功能：
1. 跨 Agent 搜索 - 搜索所有 Agent 的知识
2. 知识推荐 - 根据当前任务推荐相关知识
3. 知识图谱 - 建立知识之间的关联

用法：
    python3 knowledge_flow.py search "关键词" --scope team
    python3 knowledge_flow.py recommend --agent dev --task "当前任务描述"
    python3 knowledge_flow.py graph --output knowledge_graph.json
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

# 尝试导入配置
try:
    from .config import get_config
    _config = get_config()
    BASE_DIR = _config.base_dir
    DATA_DIR = _config.data_dir
    OBSIDIAN_VAULT_DIR = _config.obsidian_vault
    
    # 从配置构建 WORKSPACES
    WORKSPACES = {}
    for agent in _config.agents:
        WORKSPACES[agent["name"]] = Path(agent["workspace"])
except:
    # 回退到默认路径
    BASE_DIR = Path.home() / ".memory-like-a-tree"
    DATA_DIR = BASE_DIR / "data"
    OBSIDIAN_VAULT_DIR = None
    WORKSPACES = {
        "default": BASE_DIR / "workspace"
    }

# Agent 专长领域（用于推荐，可在配置文件中覆盖）
AGENT_EXPERTISE = {
    "default": ["通用", "知识", "记忆"],
}


def load_memory_db() -> Dict[str, Any]:
    """加载 memory-confidence 数据库"""
    db_path = DATA_DIR / "confidence-db.json"
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


def boost_confidence(memory_id: str, amount: float = 0.05) -> bool:
    """
    提升记忆置信度（当记忆被搜索/使用时调用）
    
    Args:
        memory_id: 记忆 ID
        amount: 提升量
    
    Returns:
        是否成功
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    if memory_id not in memories:
        return False
    
    mem = memories[memory_id]
    old_confidence = mem.get("confidence", 0.5)
    new_confidence = min(1.0, old_confidence + amount)
    
    mem["confidence"] = round(new_confidence, 3)
    mem["last_accessed"] = datetime.now().isoformat()
    mem["access_count"] = mem.get("access_count", 0) + 1
    
    save_memory_db(db)
    return True


def search_memories(
    query: str,
    scope: str = "team",
    agent: str = None,
    min_confidence: float = 0.3,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    搜索记忆
    
    Args:
        query: 搜索关键词
        scope: 搜索范围 ("self", "team", "all")
        agent: 当前 Agent（scope="self" 时使用）
        min_confidence: 最低置信度
        limit: 返回结果数量
    
    Returns:
        匹配的记忆列表
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for mem_id, mem in memories.items():
        # 过滤范围
        if scope == "self" and agent and mem.get("agent") != agent:
            continue
        
        # 过滤置信度
        if mem.get("confidence", 0) < min_confidence:
            continue
        
        # 计算相关性分数
        title = mem.get("title", "").lower()
        content = mem.get("content_preview", "").lower()
        
        score = 0
        
        # 标题匹配
        if query_lower in title:
            score += 10
        for word in query_words:
            if word in title:
                score += 3
        
        # 内容匹配
        if query_lower in content:
            score += 5
        for word in query_words:
            if word in content:
                score += 1
        
        # 置信度加权
        score *= mem.get("confidence", 0.5)
        
        if score > 0:
            # 自动提升被搜索到的记忆的置信度
            boost_confidence(mem_id, 0.03)
            
            results.append({
                "id": mem_id,
                "agent": mem.get("agent"),
                "title": mem.get("title"),
                "confidence": mem.get("confidence"),
                "content_preview": mem.get("content_preview"),
                "file": mem.get("file"),
                "score": round(score, 2)
            })
    
    # 按分数排序
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results[:limit]


def recommend_knowledge(
    agent: str,
    task: str = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    为 Agent 推荐相关知识
    
    Args:
        agent: 目标 Agent
        task: 当前任务描述（可选）
        limit: 推荐数量
    
    Returns:
        推荐的知识列表
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    # 获取 Agent 的专长领域
    expertise = AGENT_EXPERTISE.get(agent, [])
    
    # 如果有任务描述，提取关键词
    task_words = set()
    if task:
        task_words = set(task.lower().split())
    
    recommendations = []
    
    for mem_id, mem in memories.items():
        # 跳过自己的记忆（推荐其他 Agent 的知识）
        if mem.get("agent") == agent:
            continue
        
        # 只推荐高置信度的知识
        if mem.get("confidence", 0) < 0.5:
            continue
        
        title = mem.get("title", "").lower()
        content = mem.get("content_preview", "").lower()
        
        score = 0
        reasons = []
        
        # 专长领域匹配
        for keyword in expertise:
            if keyword in title or keyword in content:
                score += 3
                reasons.append(f"与你的专长「{keyword}」相关")
                break
        
        # 任务关键词匹配
        for word in task_words:
            if len(word) > 2 and (word in title or word in content):
                score += 2
                reasons.append(f"与当前任务关键词「{word}」相关")
        
        # 高置信度加分
        if mem.get("confidence", 0) >= 0.8:
            score += 1
            reasons.append("高置信度知识")
        
        if score > 0:
            recommendations.append({
                "id": mem_id,
                "from_agent": mem.get("agent"),
                "title": mem.get("title"),
                "confidence": mem.get("confidence"),
                "content_preview": mem.get("content_preview")[:100] + "...",
                "score": score,
                "reasons": reasons[:2]  # 最多显示 2 个原因
            })
    
    # 按分数排序
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return recommendations[:limit]


def build_knowledge_graph() -> Dict[str, Any]:
    """
    构建知识图谱
    
    Returns:
        知识图谱数据
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    # 节点：每个记忆是一个节点
    nodes = []
    # 边：相关的记忆之间有边
    edges = []
    
    # 提取所有关键词
    keyword_to_memories = defaultdict(list)
    
    for mem_id, mem in memories.items():
        title = mem.get("title", "")
        content = mem.get("content_preview", "")
        
        # 提取关键词（简单实现：提取中文词和英文词）
        words = set()
        # 中文关键词
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', title + content)
        words.update(chinese_words)
        # 英文关键词
        english_words = re.findall(r'[a-zA-Z]{3,}', title + content)
        words.update([w.lower() for w in english_words])
        
        # 添加节点
        nodes.append({
            "id": mem_id,
            "agent": mem.get("agent"),
            "title": title,
            "confidence": mem.get("confidence", 0.5),
            "keywords": list(words)[:10]  # 最多 10 个关键词
        })
        
        # 记录关键词到记忆的映射
        for word in words:
            keyword_to_memories[word].append(mem_id)
    
    # 构建边：共享关键词的记忆之间有边
    edge_set = set()
    for keyword, mem_ids in keyword_to_memories.items():
        if len(mem_ids) > 1 and len(mem_ids) <= 10:  # 避免太常见的词
            for i, mem1 in enumerate(mem_ids):
                for mem2 in mem_ids[i+1:]:
                    edge_key = tuple(sorted([mem1, mem2]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": mem1,
                            "target": mem2,
                            "keyword": keyword
                        })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "agents": list(set(n["agent"] for n in nodes))
        }
    }


def generate_daily_digest() -> Dict[str, Any]:
    """
    生成每日知识摘要
    
    Returns:
        每日摘要数据
    """
    db = load_memory_db()
    memories = db.get("memories", {})
    
    today = datetime.now().date().isoformat()
    
    # 统计今日新增/更新的记忆
    today_memories = []
    agent_stats = defaultdict(int)
    
    for mem_id, mem in memories.items():
        # 检查是否是今天的记忆（简单实现：检查文件修改时间）
        file_path = mem.get("file")
        if file_path and Path(file_path).exists():
            mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
            if mtime.date().isoformat() == today:
                today_memories.append({
                    "id": mem_id,
                    "agent": mem.get("agent"),
                    "title": mem.get("title"),
                    "confidence": mem.get("confidence")
                })
                agent_stats[mem.get("agent")] += 1
    
    # 高置信度知识
    high_confidence = [
        {
            "id": mem_id,
            "agent": mem.get("agent"),
            "title": mem.get("title"),
            "confidence": mem.get("confidence")
        }
        for mem_id, mem in memories.items()
        if mem.get("confidence", 0) >= 0.8
    ]
    
    return {
        "date": today,
        "today_memories": today_memories,
        "agent_stats": dict(agent_stats),
        "high_confidence_count": len(high_confidence),
        "total_memories": len(memories)
    }


def main():
    parser = argparse.ArgumentParser(description="跨 Agent 知识搜索和推荐")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索知识")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--scope", default="team", choices=["self", "team", "all"])
    search_parser.add_argument("--agent", help="当前 Agent（scope=self 时使用）")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--min-confidence", type=float, default=0.3)
    
    # recommend 命令
    recommend_parser = subparsers.add_parser("recommend", help="推荐知识")
    recommend_parser.add_argument("--agent", required=True, help="目标 Agent")
    recommend_parser.add_argument("--task", help="当前任务描述")
    recommend_parser.add_argument("--limit", type=int, default=5)
    
    # graph 命令
    graph_parser = subparsers.add_parser("graph", help="构建知识图谱")
    graph_parser.add_argument("--output", "-o", help="输出文件路径")
    
    # digest 命令
    digest_parser = subparsers.add_parser("digest", help="生成每日摘要")
    
    args = parser.parse_args()
    
    if args.command == "search":
        results = search_memories(
            args.query,
            scope=args.scope,
            agent=args.agent,
            min_confidence=args.min_confidence,
            limit=args.limit
        )
        print(f"\n🔍 搜索结果: {len(results)} 条\n")
        for r in results:
            print(f"  [{r['agent']}] {r['title']} (置信度: {r['confidence']}, 分数: {r['score']})")
            print(f"    {r['content_preview'][:80]}...")
            print()
    
    elif args.command == "recommend":
        results = recommend_knowledge(
            args.agent,
            task=args.task,
            limit=args.limit
        )
        print(f"\n💡 为 {args.agent} 推荐的知识: {len(results)} 条\n")
        for r in results:
            print(f"  来自 [{r['from_agent']}]: {r['title']}")
            print(f"    原因: {', '.join(r['reasons'])}")
            print(f"    {r['content_preview']}")
            print()
    
    elif args.command == "graph":
        graph = build_knowledge_graph()
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(graph, f, ensure_ascii=False, indent=2)
            print(f"✅ 知识图谱已保存到: {args.output}")
        else:
            print(json.dumps(graph, ensure_ascii=False, indent=2))
        print(f"\n📊 统计: {graph['stats']['total_nodes']} 个节点, {graph['stats']['total_edges']} 条边")
    
    elif args.command == "digest":
        digest = generate_daily_digest()
        print(f"\n📅 {digest['date']} 知识摘要\n")
        print(f"  今日新增: {len(digest['today_memories'])} 条")
        print(f"  高置信度: {digest['high_confidence_count']} 条")
        print(f"  总计: {digest['total_memories']} 条")
        print(f"\n  Agent 贡献:")
        for agent, count in sorted(digest['agent_stats'].items(), key=lambda x: -x[1]):
            print(f"    {agent}: {count} 条")


if __name__ == "__main__":
    main()
