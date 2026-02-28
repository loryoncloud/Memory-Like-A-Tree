#!/usr/bin/env python3
"""
记忆树 API - 供 Agent 调用的统一记忆接口

所有 Agent 必须通过这个接口访问记忆，不能直接读文件。

用法：
    from memory_tree_api import MemoryTreeAPI
    
    api = MemoryTreeAPI(agent="dev")
    
    # 搜索
    results = api.search("关键词")
    
    # 获取推荐
    recommendations = api.get_recommendations(task="当前任务")
    
    # 添加记忆
    api.add_memory(title="标题", content="内容", priority="P2")
    
    # 获取树状态
    status = api.get_status()
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 导入核心模块
from memory_tree import (
    load_memory_db, save_memory_db, get_tree_status,
    search_tree, get_leaf_status, LEAF_STATUS, CONFIDENCE_THRESHOLDS
)
from knowledge_flow import search_memories, recommend_knowledge


class MemoryTreeAPI:
    """记忆树统一 API"""
    
    def __init__(self, agent: str):
        """
        初始化 API
        
        Args:
            agent: Agent 名称
        """
        self.agent = agent
        
        # 尝试从配置获取路径
        try:
            from config import get_config
            config = get_config()
            agent_config = config.get_agent(agent)
            if agent_config:
                self.workspace = Path(agent_config["workspace"])
            else:
                self.workspace = config.base_dir / "workspace"
            self.base_dir = config.base_dir
        except:
            self.base_dir = Path.home() / ".memory-like-a-tree"
            self.workspace = self.base_dir / "workspace"
    
    def search(
        self,
        query: str,
        scope: str = "team",
        min_confidence: float = 0.3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索关键词
            scope: 搜索范围 ("self", "team", "all")
            min_confidence: 最低置信度
            limit: 返回数量
        
        Returns:
            搜索结果列表
        """
        if scope == "self":
            # 只搜索自己的记忆
            results = search_tree(query, scope="leaves")
            return [r for r in results if r.get("agent") == self.agent][:limit]
        else:
            # 搜索团队记忆
            return search_memories(
                query,
                scope=scope,
                agent=self.agent,
                min_confidence=min_confidence,
                limit=limit
            )
    
    def get_recommendations(
        self,
        task: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取知识推荐
        
        Args:
            task: 当前任务描述
            limit: 推荐数量
        
        Returns:
            推荐列表
        """
        return recommend_knowledge(self.agent, task=task, limit=limit)
    
    def add_memory(
        self,
        title: str,
        content: str,
        priority: str = "P2",
        ttl: str = "30d",
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        添加新记忆
        
        Args:
            title: 标题
            content: 内容
            priority: 优先级 (P0, P1, P2)
            ttl: 生存时间 (never, 90d, 30d)
            source: 来源
        
        Returns:
            添加结果
        """
        # 使用 sediment.py 添加
        import subprocess
        
        sediment_path = Path(__file__).parent.parent / "sediment" / "sediment.py"
        
        cmd = [
            "python3", str(sediment_path),
            "--agent", self.agent,
            "--content", content,
            "--type", "knowledge",
            "--title", title
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"status": "success", "title": title}
            else:
                return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取记忆树状态
        
        Returns:
            树状态
        """
        status = get_tree_status()
        
        # 添加当前 Agent 的统计
        my_stats = status["branches"].get(self.agent, {
            "green": 0, "yellow": 0, "withered": 0, "soil": 0, "total": 0
        })
        
        return {
            "tree_health": status["health_percent"],
            "total_leaves": status["total_leaves"],
            "my_leaves": my_stats,
            "summary": status["summary"]
        }
    
    def get_my_memories(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """
        获取自己的记忆
        
        Args:
            status_filter: 状态过滤 ("green", "yellow", "withered", "soil")
        
        Returns:
            记忆列表
        """
        db = load_memory_db()
        memories = []
        
        for mem_id, mem in db.get("memories", {}).items():
            if mem.get("agent") != self.agent:
                continue
            
            confidence = mem.get("confidence", 0.5)
            leaf_status = get_leaf_status(confidence)
            
            if status_filter and leaf_status != status_filter:
                continue
            
            memories.append({
                "id": mem_id,
                "title": mem.get("title"),
                "confidence": confidence,
                "status": leaf_status,
                "emoji": LEAF_STATUS[leaf_status],
                "preview": mem.get("content_preview", "")[:100]
            })
        
        return memories
    
    def boost_confidence(self, memory_id: str, amount: float = 0.1) -> Dict[str, Any]:
        """
        提升记忆置信度（当记忆被访问/使用时调用）
        
        Args:
            memory_id: 记忆 ID
            amount: 提升量
        
        Returns:
            更新结果
        """
        db = load_memory_db()
        memories = db.get("memories", {})
        
        if memory_id not in memories:
            return {"status": "error", "message": f"记忆 {memory_id} 不存在"}
        
        mem = memories[memory_id]
        old_confidence = mem.get("confidence", 0.5)
        new_confidence = min(1.0, old_confidence + amount)
        
        mem["confidence"] = round(new_confidence, 3)
        mem["last_accessed"] = datetime.now().isoformat()
        mem["access_count"] = mem.get("access_count", 0) + 1
        
        save_memory_db(db)
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "old_confidence": old_confidence,
            "new_confidence": new_confidence
        }


# 命令行接口
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="记忆树 API")
    parser.add_argument("--agent", required=True, help="Agent 名称")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # search
    search_p = subparsers.add_parser("search")
    search_p.add_argument("query")
    search_p.add_argument("--scope", default="team")
    search_p.add_argument("--limit", type=int, default=10)
    
    # recommend
    rec_p = subparsers.add_parser("recommend")
    rec_p.add_argument("--task", default="")
    rec_p.add_argument("--limit", type=int, default=5)
    
    # status
    subparsers.add_parser("status")
    
    # my-memories
    my_p = subparsers.add_parser("my-memories")
    my_p.add_argument("--status", choices=["green", "yellow", "withered", "soil"])
    
    args = parser.parse_args()
    api = MemoryTreeAPI(args.agent)
    
    if args.command == "search":
        results = api.search(args.query, scope=args.scope, limit=args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif args.command == "recommend":
        results = api.get_recommendations(task=args.task, limit=args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif args.command == "status":
        status = api.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    
    elif args.command == "my-memories":
        memories = api.get_my_memories(status_filter=args.status)
        print(json.dumps(memories, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
