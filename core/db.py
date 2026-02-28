#!/usr/bin/env python3
"""
Memory-Like-A-Tree 置信度数据库操作模块

支持配置化路径，兼容单 Agent 和多 Agent 场景
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import fcntl

# 尝试导入配置，如果失败则使用默认路径
try:
    from .config import get_config
    _config = get_config()
    DB_PATH = _config.data_dir / "confidence-db.json"
    LOCK_PATH = _config.data_dir / ".db.lock"
except:
    # 回退到默认路径
    DB_PATH = Path.home() / ".memory-like-a-tree" / "data" / "confidence-db.json"
    LOCK_PATH = Path.home() / ".memory-like-a-tree" / "data" / ".db.lock"


def get_db_path() -> Path:
    """获取数据库路径"""
    return DB_PATH


def ensure_db_dir():
    """确保数据库目录存在"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_db() -> Dict[str, Any]:
    """加载置信度数据库"""
    ensure_db_dir()
    if not DB_PATH.exists():
        return {"version": "1.0.0", "memories": {}, "last_updated": None}
    
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(db: Dict[str, Any]) -> None:
    """保存置信度数据库（带文件锁）"""
    ensure_db_dir()
    db["last_updated"] = datetime.now().isoformat()
    
    LOCK_PATH.touch(exist_ok=True)
    with open(LOCK_PATH, 'w') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            with open(DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

def content_hash(content: str) -> str:
    """计算内容哈希"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

def generate_memory_id(workspace: str, section_title: str) -> str:
    """生成记忆 ID"""
    agent = workspace.split('workspace-')[-1] if 'workspace-' in workspace else 'main'
    safe_title = section_title.replace(' ', '_')[:30]
    return f"{agent}:{safe_title}"

def get_memory(memory_id: str) -> Optional[Dict[str, Any]]:
    """获取单条记忆"""
    db = load_db()
    return db["memories"].get(memory_id)

def set_memory(memory_id: str, data: Dict[str, Any]) -> None:
    """设置单条记忆"""
    db = load_db()
    if memory_id not in db["memories"]:
        data["created_at"] = datetime.now().isoformat()
    data["updated_at"] = datetime.now().isoformat()
    db["memories"][memory_id] = data
    save_db(db)

def update_access(memory_id: str) -> None:
    """更新访问记录"""
    db = load_db()
    if memory_id in db["memories"]:
        mem = db["memories"][memory_id]
        mem["last_accessed"] = datetime.now().isoformat()
        mem["access_count"] = mem.get("access_count", 0) + 1
        # 小幅提升置信度（上限 0.95）
        mem["confidence"] = min(0.95, mem.get("confidence", 0.5) * 1.02)
        save_db(db)

def get_all_memories() -> Dict[str, Dict[str, Any]]:
    """获取所有记忆"""
    db = load_db()
    return db.get("memories", {})

def get_memories_by_status(status: str) -> List[Dict[str, Any]]:
    """按状态获取记忆"""
    db = load_db()
    return [
        {"id": k, **v} 
        for k, v in db.get("memories", {}).items() 
        if v.get("status") == status
    ]

def get_low_confidence_memories(threshold: float = 0.1) -> List[Dict[str, Any]]:
    """获取低置信度记忆"""
    db = load_db()
    return [
        {"id": k, **v} 
        for k, v in db.get("memories", {}).items() 
        if v.get("confidence", 1.0) < threshold
    ]

def delete_memory(memory_id: str) -> bool:
    """删除记忆"""
    db = load_db()
    if memory_id in db["memories"]:
        del db["memories"][memory_id]
        save_db(db)
        return True
    return False

def get_stats() -> Dict[str, Any]:
    """获取统计信息"""
    db = load_db()
    memories = db.get("memories", {})
    
    if not memories:
        return {"total": 0}
    
    confidences = [m.get("confidence", 0.5) for m in memories.values()]
    priorities = {}
    sources = {}
    agents = {}
    
    for mem in memories.values():
        p = mem.get("priority", "unknown")
        priorities[p] = priorities.get(p, 0) + 1
        
        s = mem.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
        
        a = mem.get("agent", "unknown")
        agents[a] = agents.get(a, 0) + 1
    
    return {
        "total": len(memories),
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "min_confidence": round(min(confidences), 3),
        "max_confidence": round(max(confidences), 3),
        "by_priority": priorities,
        "by_source": sources,
        "by_agent": agents,
        "pending_cleanup": len([m for m in memories.values() if m.get("status") == "pending_cleanup"]),
        "last_updated": db.get("last_updated")
    }
