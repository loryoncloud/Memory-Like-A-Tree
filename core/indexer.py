#!/usr/bin/env python3
"""
Memory-Like-A-Tree 记忆索引器

扫描所有 workspace，自动标注置信度
支持配置化路径，兼容单 Agent 和多 Agent 场景
"""

import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 尝试导入配置
try:
    from .config import get_config
    from .db import (
        load_db, save_db, content_hash, generate_memory_id,
        get_db_path, get_stats
    )
    _config = get_config()
    WORKSPACES = [Path(a["workspace"]) for a in _config.agents]
except:
    # 回退到相对导入或默认路径
    try:
        from db import (
            load_db, save_db, content_hash, generate_memory_id,
            get_db_path, get_stats
        )
    except:
        from .db import (
            load_db, save_db, content_hash, generate_memory_id,
            get_db_path, get_stats
        )
    
    # 默认扫描 ~/.memory-like-a-tree/workspace
    WORKSPACES = [Path.home() / ".memory-like-a-tree" / "workspace"]

# 置信度推断规则
CONFIDENCE_RULES = {
    "priority": {
        "P0": 0.90,
        "P1": 0.75,
        "P2": 0.60,
        "unknown": 0.50
    },
    "source_keywords": {
        "bro 说": 0.95,
        "bro 确认": 0.95,
        "用户确认": 0.95,
        "手动录入": 0.85,
        "自动提取": 0.50
    },
    "ttl_boost": {
        "never": 0.10,  # 永久记忆加分
        "90d": 0.05,
        "30d": 0.00
    }
}

def parse_memory_section(content: str) -> List[Dict[str, Any]]:
    """解析 MEMORY.md 中的各个 section"""
    sections = []
    
    # 匹配 ## [P0/P1/P2] 标题
    pattern = r'^##\s+\[?(P[012])\]?\s+(.+?)$'
    lines = content.split('\n')
    
    current_section = None
    current_content = []
    current_meta = {}
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line)
        if match:
            # 保存上一个 section
            if current_section:
                sections.append({
                    "title": current_section,
                    "priority": current_meta.get("priority", "unknown"),
                    "ttl": current_meta.get("ttl", "unknown"),
                    "content": '\n'.join(current_content).strip(),
                    "line_start": current_meta.get("line_start", 0)
                })
            
            # 开始新 section
            current_section = match.group(2).strip()
            current_meta = {
                "priority": match.group(1),
                "line_start": i + 1
            }
            current_content = []
            
            # 检查下一行是否有 TTL 注释
            if i + 1 < len(lines):
                ttl_match = re.search(r'TTL:\s*(\w+)', lines[i + 1])
                if ttl_match:
                    current_meta["ttl"] = ttl_match.group(1)
        elif current_section:
            current_content.append(line)
    
    # 保存最后一个 section
    if current_section:
        sections.append({
            "title": current_section,
            "priority": current_meta.get("priority", "unknown"),
            "ttl": current_meta.get("ttl", "unknown"),
            "content": '\n'.join(current_content).strip(),
            "line_start": current_meta.get("line_start", 0)
        })
    
    return sections

def infer_confidence(section: Dict[str, Any], file_mtime: datetime) -> float:
    """推断置信度"""
    # 1. 基础分：按优先级
    priority = section.get("priority", "unknown")
    base = CONFIDENCE_RULES["priority"].get(priority, 0.50)
    
    # 2. 来源关键词加分
    content = section.get("content", "")
    for keyword, boost in CONFIDENCE_RULES["source_keywords"].items():
        if keyword in content:
            base = max(base, boost)
            break
    
    # 3. TTL 加分
    ttl = section.get("ttl", "unknown")
    base += CONFIDENCE_RULES["ttl_boost"].get(ttl, 0)
    
    # 4. 文件年龄衰减
    age_days = (datetime.now() - file_mtime).days
    if age_days > 60:
        base *= 0.90
    elif age_days > 30:
        base *= 0.95
    
    # 确保在 0-1 范围内
    return round(min(1.0, max(0.0, base)), 3)

def infer_source(section: Dict[str, Any]) -> str:
    """推断来源"""
    content = section.get("content", "")
    
    if "bro 说" in content or "bro 确认" in content or "用户确认" in content:
        return "user-confirmed"
    elif section.get("priority") == "P0":
        return "manual"  # P0 通常是手动录入的核心信息
    elif "自动" in content or "提取" in content:
        return "auto-extracted"
    else:
        return "manual"

def scan_workspace(workspace: Path) -> List[Dict[str, Any]]:
    """扫描单个 workspace"""
    memories = []
    agent = workspace.name.replace("workspace-", "") if "workspace-" in workspace.name else "main"
    
    # 扫描 MEMORY.md
    memory_md = workspace / "MEMORY.md"
    if memory_md.exists():
        try:
            content = memory_md.read_text(encoding='utf-8')
            mtime = datetime.fromtimestamp(memory_md.stat().st_mtime)
            
            sections = parse_memory_section(content)
            for section in sections:
                mem_id = generate_memory_id(workspace.name, section["title"])
                memories.append({
                    "id": mem_id,
                    "agent": agent,
                    "file": str(memory_md),
                    "title": section["title"],
                    "priority": section["priority"],
                    "ttl": section["ttl"],
                    "confidence": infer_confidence(section, mtime),
                    "source": infer_source(section),
                    "content_hash": content_hash(section["content"]),
                    "content_preview": section["content"][:200] + "..." if len(section["content"]) > 200 else section["content"],
                    "line_start": section["line_start"],
                    "last_accessed": None,
                    "access_count": 0
                })
        except Exception as e:
            print(f"  ⚠️ 解析 {memory_md} 失败: {e}")
    
    # 扫描 memory/ 目录下的文件
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        for md_file in memory_dir.glob("*.md"):
            if md_file.name.startswith("."):
                continue
            try:
                content = md_file.read_text(encoding='utf-8')
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                
                mem_id = f"{agent}:memory/{md_file.stem}"
                memories.append({
                    "id": mem_id,
                    "agent": agent,
                    "file": str(md_file),
                    "title": md_file.stem,
                    "priority": "P2",  # memory/ 下的文件默认 P2
                    "ttl": "30d",
                    "confidence": 0.60 * (0.95 if (datetime.now() - mtime).days > 30 else 1.0),
                    "source": "manual",
                    "content_hash": content_hash(content),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "line_start": 1,
                    "last_accessed": None,
                    "access_count": 0
                })
            except Exception as e:
                print(f"  ⚠️ 解析 {md_file} 失败: {e}")
    
    return memories

def scan_all() -> Dict[str, Any]:
    """扫描所有 workspace"""
    print("🔍 开始扫描所有 workspace...\n")
    
    db = load_db()
    total_new = 0
    total_updated = 0
    
    for workspace in WORKSPACES:
        print(f"📁 扫描 {workspace.name}...")
        memories = scan_workspace(workspace)
        
        for mem in memories:
            mem_id = mem["id"]
            if mem_id in db["memories"]:
                # 检查内容是否变化
                old_hash = db["memories"][mem_id].get("content_hash")
                if old_hash != mem["content_hash"]:
                    # 内容变化，更新但保留访问记录
                    mem["last_accessed"] = db["memories"][mem_id].get("last_accessed")
                    mem["access_count"] = db["memories"][mem_id].get("access_count", 0)
                    db["memories"][mem_id] = mem
                    total_updated += 1
                    print(f"  ↻ 更新: {mem['title']}")
            else:
                db["memories"][mem_id] = mem
                total_new += 1
                print(f"  + 新增: {mem['title']} (置信度: {mem['confidence']})")
        
        print(f"  共 {len(memories)} 条记忆\n")
    
    save_db(db)
    
    return {
        "total_scanned": len(db["memories"]),
        "new": total_new,
        "updated": total_updated
    }

def watch_changes() -> Dict[str, Any]:
    """检查文件变更（增量扫描）"""
    db = load_db()
    changes = {"new": 0, "updated": 0}
    
    for workspace in WORKSPACES:
        memory_md = workspace / "MEMORY.md"
        if memory_md.exists():
            mtime = datetime.fromtimestamp(memory_md.stat().st_mtime)
            agent = workspace.name.replace("workspace-", "") if "workspace-" in workspace.name else "main"
            
            # 检查是否有该 agent 的记忆
            agent_memories = [m for m in db["memories"].values() if m.get("agent") == agent]
            
            if agent_memories:
                # 检查最后更新时间
                last_scan = max(
                    datetime.fromisoformat(m.get("updated_at", "2000-01-01")) 
                    for m in agent_memories if m.get("updated_at")
                ) if any(m.get("updated_at") for m in agent_memories) else datetime(2000, 1, 1)
                
                if mtime > last_scan:
                    print(f"📝 检测到变更: {workspace.name}")
                    memories = scan_workspace(workspace)
                    for mem in memories:
                        mem_id = mem["id"]
                        if mem_id not in db["memories"]:
                            db["memories"][mem_id] = mem
                            changes["new"] += 1
                        elif db["memories"][mem_id].get("content_hash") != mem["content_hash"]:
                            mem["last_accessed"] = db["memories"][mem_id].get("last_accessed")
                            mem["access_count"] = db["memories"][mem_id].get("access_count", 0)
                            db["memories"][mem_id] = mem
                            changes["updated"] += 1
    
    if changes["new"] > 0 or changes["updated"] > 0:
        save_db(db)
        print(f"✅ 新增 {changes['new']} 条，更新 {changes['updated']} 条")
    else:
        print("✅ 无变更")
    
    return changes

def rebuild_indexes() -> None:
    """为所有 workspace 重建 index.json"""
    print("🔄 重建所有 workspace 的 index.json...\n")
    
    for workspace in WORKSPACES:
        memory_dir = workspace / "memory"
        if not memory_dir.exists():
            memory_dir.mkdir(parents=True, exist_ok=True)
        
        index = {
            "keywords": {},
            "tags": {},
            "priorities": {},
            "files": {},
            "last_updated": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        # 扫描 MEMORY.md
        memory_md = workspace / "MEMORY.md"
        if memory_md.exists():
            content = memory_md.read_text(encoding='utf-8')
            sections = parse_memory_section(content)
            
            for section in sections:
                priority = section["priority"]
                if priority not in index["priorities"]:
                    index["priorities"][priority] = []
                index["priorities"][priority].append({
                    "title": section["title"],
                    "location": f"MEMORY.md#L{section['line_start']}"
                })
            
            stat = memory_md.stat()
            index["files"]["MEMORY.md"] = {
                "size": stat.st_size,
                "hash": content_hash(content),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        
        # 扫描 memory/ 目录
        for md_file in memory_dir.glob("*.md"):
            if md_file.name.startswith(".") or md_file.name == "index.json":
                continue
            try:
                content = md_file.read_text(encoding='utf-8')
                stat = md_file.stat()
                rel_path = f"memory/{md_file.name}"
                index["files"][rel_path] = {
                    "size": stat.st_size,
                    "hash": content_hash(content),
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            except Exception:
                pass
        
        # 保存 index.json
        index_path = memory_dir / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {workspace.name}: {len(index['files'])} 个文件")
    
    print("\n✅ 所有 index.json 重建完成")

def generate_report() -> str:
    """生成整理报告"""
    stats = get_stats()
    db = load_db()
    
    report = []
    report.append("# 记忆系统整理报告")
    report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    report.append("## 📊 总体统计\n")
    report.append(f"- 总记忆数: {stats['total']}")
    report.append(f"- 平均置信度: {stats.get('avg_confidence', 'N/A')}")
    report.append(f"- 最低置信度: {stats.get('min_confidence', 'N/A')}")
    report.append(f"- 最高置信度: {stats.get('max_confidence', 'N/A')}")
    report.append(f"- 待清理: {stats.get('pending_cleanup', 0)}")
    
    report.append("\n## 📁 按 Agent 分布\n")
    for agent, count in sorted(stats.get('by_agent', {}).items()):
        report.append(f"- {agent}: {count} 条")
    
    report.append("\n## 🏷️ 按优先级分布\n")
    for priority, count in sorted(stats.get('by_priority', {}).items()):
        report.append(f"- {priority}: {count} 条")
    
    report.append("\n## 📝 按来源分布\n")
    for source, count in sorted(stats.get('by_source', {}).items()):
        report.append(f"- {source}: {count} 条")
    
    # 低置信度记忆
    low_conf = [m for m in db.get("memories", {}).values() if m.get("confidence", 1) < 0.5]
    if low_conf:
        report.append(f"\n## ⚠️ 低置信度记忆 (<0.5): {len(low_conf)} 条\n")
        for mem in sorted(low_conf, key=lambda x: x.get("confidence", 0))[:10]:
            report.append(f"- [{mem.get('agent')}] {mem.get('title')} (置信度: {mem.get('confidence')})")
    
    return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(description="记忆索引器")
    parser.add_argument("--scan-all", action="store_true", help="扫描所有 workspace")
    parser.add_argument("--watch", action="store_true", help="检查文件变更（增量扫描）")
    parser.add_argument("--rebuild-indexes", action="store_true", help="重建所有 index.json")
    parser.add_argument("--report", action="store_true", help="生成整理报告")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    
    args = parser.parse_args()
    
    if args.scan_all:
        result = scan_all()
        print(f"\n✅ 扫描完成: 共 {result['total_scanned']} 条记忆")
        print(f"   新增: {result['new']}, 更新: {result['updated']}")
    elif args.watch:
        watch_changes()
    elif args.rebuild_indexes:
        rebuild_indexes()
    elif args.report:
        report = generate_report()
        print(report)
    elif args.stats:
        stats = get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
