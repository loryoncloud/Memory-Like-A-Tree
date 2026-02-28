#!/usr/bin/env python3
"""记忆访问追踪器 - Hook memory_search，记录每次访问"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from db import load_db, save_db, update_access, get_all_memories

def find_matching_memories(query: str, results: List[str] = None) -> List[str]:
    """
    根据搜索查询或结果找到匹配的记忆 ID
    
    Args:
        query: 搜索关键词
        results: memory_search 返回的结果片段列表
    
    Returns:
        匹配的记忆 ID 列表
    """
    memories = get_all_memories()
    matched_ids = []
    
    query_lower = query.lower() if query else ""
    
    for mem_id, mem in memories.items():
        # 方法1: 通过结果片段匹配
        if results:
            content_preview = mem.get("content_preview", "").lower()
            title = mem.get("title", "").lower()
            for result in results:
                result_lower = result.lower()
                if result_lower in content_preview or result_lower in title:
                    matched_ids.append(mem_id)
                    break
        
        # 方法2: 通过查询关键词匹配
        elif query_lower:
            content_preview = mem.get("content_preview", "").lower()
            title = mem.get("title", "").lower()
            if query_lower in content_preview or query_lower in title:
                matched_ids.append(mem_id)
    
    return list(set(matched_ids))

def track_search(query: str, results: List[str] = None) -> Dict[str, Any]:
    """
    追踪一次 memory_search 调用
    
    Args:
        query: 搜索关键词
        results: 搜索结果片段
    
    Returns:
        追踪结果
    """
    matched_ids = find_matching_memories(query, results)
    
    updated = []
    for mem_id in matched_ids:
        update_access(mem_id)
        updated.append(mem_id)
    
    return {
        "query": query,
        "matched": len(matched_ids),
        "updated_ids": updated,
        "timestamp": datetime.now().isoformat()
    }

def track_by_id(memory_id: str) -> Dict[str, Any]:
    """
    直接通过 ID 追踪访问
    
    Args:
        memory_id: 记忆 ID
    
    Returns:
        追踪结果
    """
    memories = get_all_memories()
    
    if memory_id in memories:
        update_access(memory_id)
        return {
            "memory_id": memory_id,
            "success": True,
            "new_confidence": memories[memory_id].get("confidence"),
            "access_count": memories[memory_id].get("access_count", 0) + 1,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "memory_id": memory_id,
            "success": False,
            "error": "Memory not found",
            "timestamp": datetime.now().isoformat()
        }

def track_batch(memory_ids: List[str]) -> Dict[str, Any]:
    """
    批量追踪访问
    
    Args:
        memory_ids: 记忆 ID 列表
    
    Returns:
        追踪结果
    """
    results = []
    for mem_id in memory_ids:
        result = track_by_id(mem_id)
        results.append(result)
    
    return {
        "total": len(memory_ids),
        "success": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

def get_access_stats() -> Dict[str, Any]:
    """获取访问统计"""
    memories = get_all_memories()
    
    if not memories:
        return {"total": 0, "accessed": 0, "never_accessed": 0}
    
    accessed = [m for m in memories.values() if m.get("last_accessed")]
    never_accessed = [m for m in memories.values() if not m.get("last_accessed")]
    
    # 按访问次数排序
    top_accessed = sorted(
        [(k, v.get("access_count", 0), v.get("title", k)) for k, v in memories.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return {
        "total": len(memories),
        "accessed": len(accessed),
        "never_accessed": len(never_accessed),
        "access_rate": round(len(accessed) / len(memories) * 100, 1) if memories else 0,
        "top_accessed": [
            {"id": t[0], "count": t[1], "title": t[2]} 
            for t in top_accessed if t[1] > 0
        ]
    }

def main():
    parser = argparse.ArgumentParser(description="记忆访问追踪器")
    parser.add_argument("--search", type=str, help="追踪搜索查询")
    parser.add_argument("--id", type=str, help="追踪单个记忆 ID")
    parser.add_argument("--ids", type=str, help="追踪多个记忆 ID（逗号分隔）")
    parser.add_argument("--stats", action="store_true", help="显示访问统计")
    parser.add_argument("--results", type=str, help="搜索结果片段（JSON 数组）")
    
    args = parser.parse_args()
    
    if args.search:
        results = json.loads(args.results) if args.results else None
        result = track_search(args.search, results)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.id:
        result = track_by_id(args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.ids:
        ids = [i.strip() for i in args.ids.split(",")]
        result = track_batch(ids)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.stats:
        stats = get_access_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
