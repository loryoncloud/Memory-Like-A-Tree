#!/usr/bin/env python3
"""
Memory-Like-A-Tree 记忆清理器

清理低置信度记忆，提取精华
支持配置化参数
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# 尝试导入配置
try:
    from .config import get_config
    from .db import (
        load_db, save_db, get_all_memories, 
        get_low_confidence_memories, get_memories_by_status,
        delete_memory, get_stats
    )
    _config = get_config()
    _cleanup_config = _config.cleanup
    _archive_dir = _config.archive_dir
except:
    try:
        from db import (
            load_db, save_db, get_all_memories, 
            get_low_confidence_memories, get_memories_by_status,
            delete_memory, get_stats
        )
    except:
        from .db import (
            load_db, save_db, get_all_memories, 
            get_low_confidence_memories, get_memories_by_status,
            delete_memory, get_stats
        )
    _cleanup_config = None
    _archive_dir = Path.home() / ".memory-like-a-tree" / "data" / "archive"

# 清理配置
def get_cleanup_config():
    """获取清理配置"""
    if _cleanup_config:
        return {
            "auto_cleanup_threshold": _cleanup_config.get("auto_cleanup_threshold", 0.05),
            "review_threshold": _cleanup_config.get("review_threshold", 0.10),
            "archive_before_delete": True,
            "archive_dir": _archive_dir
        }
    else:
        return {
            "auto_cleanup_threshold": 0.05,
            "review_threshold": 0.10,
            "archive_before_delete": True,
            "archive_dir": _archive_dir
        }

CLEANUP_CONFIG = get_cleanup_config()

def get_cleanup_candidates() -> Dict[str, List[Dict[str, Any]]]:
    """
    获取清理候选
    
    Returns:
        分类的清理候选
    """
    memories = get_all_memories()
    
    candidates = {
        "auto_cleanup": [],      # 可自动清理
        "needs_review": [],      # 需要人工审核
        "pending_cleanup": []    # 已标记待清理
    }
    
    for mem_id, mem in memories.items():
        confidence = mem.get("confidence", 0.5)
        status = mem.get("status")
        
        if status == "pending_cleanup":
            candidates["pending_cleanup"].append({"id": mem_id, **mem})
        elif confidence < CLEANUP_CONFIG["auto_cleanup_threshold"]:
            candidates["auto_cleanup"].append({"id": mem_id, **mem})
        elif confidence < CLEANUP_CONFIG["review_threshold"]:
            candidates["needs_review"].append({"id": mem_id, **mem})
    
    # 按置信度排序
    for key in candidates:
        candidates[key].sort(key=lambda x: x.get("confidence", 0))
    
    return candidates

def archive_memory(mem: Dict[str, Any]) -> str:
    """
    归档记忆并提取精华
    
    Args:
        mem: 记忆数据
    
    Returns:
        归档文件路径
    """
    archive_dir = CLEANUP_CONFIG["archive_dir"]
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # 按日期组织
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_file = archive_dir / f"{date_str}.jsonl"
    
    # 提取精华
    essence = extract_essence(mem)
    mem["essence"] = essence
    
    # 追加到归档文件
    with open(archive_file, 'a', encoding='utf-8') as f:
        mem["archived_at"] = datetime.now().isoformat()
        f.write(json.dumps(mem, ensure_ascii=False) + "\n")
    
    # 同步精华到 Obsidian
    sync_essence_to_obsidian(mem, essence)
    
    return str(archive_file)


def extract_essence(mem: Dict[str, Any]) -> Dict[str, Any]:
    """
    从记忆中提取精华
    
    Args:
        mem: 记忆数据
    
    Returns:
        精华数据
    """
    import re
    
    content = mem.get("content_preview", "")
    title = mem.get("title", "")
    
    essence = {
        "title": title,
        "agent": mem.get("agent"),
        "extracted_at": datetime.now().isoformat(),
        "keywords": [],
        "summary": "",
        "lessons": [],
    }
    
    # 提取关键词
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)
    english_words = re.findall(r'[a-zA-Z]{4,}', content)
    essence["keywords"] = list(set(chinese_words[:5] + [w.lower() for w in english_words[:5]]))
    
    # 提取经验教训
    lesson_patterns = [
        r'经验[：:](.*?)(?:\n|$)',
        r'教训[：:](.*?)(?:\n|$)',
        r'注意[：:](.*?)(?:\n|$)',
    ]
    for pattern in lesson_patterns:
        matches = re.findall(pattern, content)
        essence["lessons"].extend(matches)
    
    # 生成摘要
    clean_content = re.sub(r'[#\-*`]', '', content)
    essence["summary"] = clean_content[:100].strip() + "..." if len(clean_content) > 100 else clean_content.strip()
    
    return essence


def sync_essence_to_obsidian(mem: Dict[str, Any], essence: Dict[str, Any]):
    """
    同步精华到 Obsidian
    
    Args:
        mem: 记忆数据
        essence: 精华数据
    """
    # 尝试从配置获取 Obsidian 路径
    try:
        from config import get_config
        config = get_config()
        if config.obsidian_vault:
            obsidian_essence_dir = config.obsidian_vault / "03-精华库"
        else:
            # 没有配置 Obsidian，跳过
            return
    except:
        # 没有配置，跳过
        return
    
    obsidian_essence_dir.mkdir(parents=True, exist_ok=True)
    
    # 按月份组织
    month_str = datetime.now().strftime("%Y-%m")
    essence_file = obsidian_essence_dir / f"{month_str}-精华汇总.md"
    
    # 追加精华
    entry = f"""
## {essence.get('title', '无标题')}

- **来源**: {essence.get('agent', 'unknown')}
- **归档时间**: {mem.get('archived_at', 'unknown')}
- **关键词**: {', '.join(essence.get('keywords', []))}

{essence.get('summary', '')}

"""
    
    if essence.get('lessons'):
        entry += "**经验教训**:\n"
        for lesson in essence['lessons']:
            entry += f"- {lesson}\n"
        entry += "\n"
    
    entry += "---\n"
    
    with open(essence_file, 'a', encoding='utf-8') as f:
        f.write(entry)


def cleanup_memory(memory_id: str, archive: bool = True) -> Dict[str, Any]:
    """
    清理单条记忆
    
    Args:
        memory_id: 记忆 ID
        archive: 是否归档
    
    Returns:
        清理结果
    """
    memories = get_all_memories()
    
    if memory_id not in memories:
        return {
            "success": False,
            "error": "Memory not found",
            "memory_id": memory_id
        }
    
    mem = memories[memory_id]
    
    # 归档
    archive_path = None
    if archive and CLEANUP_CONFIG["archive_before_delete"]:
        archive_path = archive_memory({"id": memory_id, **mem})
    
    # 删除
    delete_memory(memory_id)
    
    return {
        "success": True,
        "memory_id": memory_id,
        "title": mem.get("title"),
        "confidence": mem.get("confidence"),
        "archived": archive_path is not None,
        "archive_path": archive_path
    }

def run_auto_cleanup(dry_run: bool = False) -> Dict[str, Any]:
    """
    执行自动清理
    
    Args:
        dry_run: 是否只预览
    
    Returns:
        清理结果
    """
    candidates = get_cleanup_candidates()
    auto_cleanup = candidates["auto_cleanup"] + candidates["pending_cleanup"]
    
    results = {
        "total_candidates": len(auto_cleanup),
        "cleaned": 0,
        "archived": 0,
        "details": [],
        "dry_run": dry_run,
        "timestamp": datetime.now().isoformat()
    }
    
    for mem in auto_cleanup:
        if dry_run:
            results["details"].append({
                "id": mem["id"],
                "title": mem.get("title"),
                "confidence": mem.get("confidence"),
                "action": "would_cleanup"
            })
        else:
            result = cleanup_memory(mem["id"])
            if result["success"]:
                results["cleaned"] += 1
                if result.get("archived"):
                    results["archived"] += 1
                results["details"].append(result)
    
    return results

def generate_cleanup_report() -> str:
    """
    生成清理报告
    
    Returns:
        报告内容
    """
    candidates = get_cleanup_candidates()
    stats = get_stats()
    
    lines = []
    lines.append("# 记忆清理报告\n")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    lines.append("## 📊 总体统计\n")
    lines.append(f"- 总记忆数: {stats.get('total', 0)}")
    lines.append(f"- 平均置信度: {stats.get('avg_confidence', 'N/A')}")
    lines.append(f"- 待清理: {stats.get('pending_cleanup', 0)}")
    
    lines.append("\n## 🗑️ 清理候选\n")
    
    # 可自动清理
    auto = candidates["auto_cleanup"]
    lines.append(f"### 可自动清理 (置信度 < {CLEANUP_CONFIG['auto_cleanup_threshold']}): {len(auto)} 条\n")
    if auto:
        for mem in auto[:20]:
            lines.append(
                f"- [{mem.get('agent', '?')}] {mem.get('title', mem['id'])} "
                f"(置信度: {mem.get('confidence', '?')})")
        if len(auto) > 20:
            lines.append(f"- ... 还有 {len(auto) - 20} 条")
    else:
        lines.append("无")
    
    # 需要审核
    review = candidates["needs_review"]
    lines.append(f"\n### 需要人工审核 (置信度 {CLEANUP_CONFIG['auto_cleanup_threshold']}-{CLEANUP_CONFIG['review_threshold']}): {len(review)} 条\n")
    if review:
        for mem in review[:20]:
            lines.append(
                f"- [{mem.get('agent', '?')}] {mem.get('title', mem['id'])} "
                f"(置信度: {mem.get('confidence', '?')})")
        if len(review) > 20:
            lines.append(f"- ... 还有 {len(review) - 20} 条")
    else:
        lines.append("无")
    
    # 已标记待清理
    pending = candidates["pending_cleanup"]
    lines.append(f"\n### 已标记待清理: {len(pending)} 条\n")
    if pending:
        for mem in pending[:20]:
            lines.append(
                f"- [{mem.get('agent', '?')}] {mem.get('title', mem['id'])} "
                f"(置信度: {mem.get('confidence', '?')})")
        if len(pending) > 20:
            lines.append(f"- ... 还有 {len(pending) - 20} 条")
    else:
        lines.append("无")
    
    # 操作建议
    lines.append("\n## 🔧 操作建议\n")
    if auto or pending:
        lines.append(f"运行自动清理: `python3 cleaner.py --auto-cleanup`")
        lines.append(f"预览清理: `python3 cleaner.py --auto-cleanup --dry-run`")
    if review:
        lines.append(f"审核低置信度记忆后，可手动清理: `python3 cleaner.py --cleanup-id <memory_id>`")
    
    return '\n'.join(lines)

def list_archived() -> List[Dict[str, Any]]:
    """列出已归档的记忆"""
    archive_dir = CLEANUP_CONFIG["archive_dir"]
    if not archive_dir.exists():
        return []
    
    archived = []
    for archive_file in archive_dir.glob("*.jsonl"):
        with open(archive_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    archived.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
    
    return archived

def restore_memory(memory_id: str) -> Dict[str, Any]:
    """
    从归档恢复记忆
    
    Args:
        memory_id: 记忆 ID
    
    Returns:
        恢复结果
    """
    archived = list_archived()
    
    for mem in archived:
        if mem.get("id") == memory_id:
            # 恢复到数据库
            db = load_db()
            mem.pop("archived_at", None)
            mem["confidence"] = 0.30  # 恢复后给一个较低的置信度
            mem["restored_at"] = datetime.now().isoformat()
            db["memories"][memory_id] = mem
            save_db(db)
            
            return {
                "success": True,
                "memory_id": memory_id,
                "title": mem.get("title"),
                "new_confidence": 0.30
            }
    
    return {
        "success": False,
        "error": "Memory not found in archive",
        "memory_id": memory_id
    }

def main():
    parser = argparse.ArgumentParser(description="记忆清理器")
    parser.add_argument("--report", action="store_true", help="生成清理报告")
    parser.add_argument("--auto-cleanup", action="store_true", help="执行自动清理")
    parser.add_argument("--dry-run", action="store_true", help="只预览不实际清理")
    parser.add_argument("--cleanup-id", type=str, help="清理指定记忆 ID")
    parser.add_argument("--list-archived", action="store_true", help="列出已归档记忆")
    parser.add_argument("--restore", type=str, help="从归档恢复记忆")
    parser.add_argument("--candidates", action="store_true", help="显示清理候选")
    
    args = parser.parse_args()
    
    if args.report:
        print(generate_cleanup_report())
    elif args.auto_cleanup:
        results = run_auto_cleanup(dry_run=args.dry_run)
        if args.dry_run:
            print(f"🔍 预览模式")
            print(f"   将清理: {results['total_candidates']} 条")
            for detail in results["details"][:10]:
                print(f"   - {detail['title']} (置信度: {detail['confidence']})")
        else:
            print(f"✅ 清理完成")
            print(f"   已清理: {results['cleaned']} 条")
            print(f"   已归档: {results['archived']} 条")
    elif args.cleanup_id:
        result = cleanup_memory(args.cleanup_id)
        if result["success"]:
            print(f"✅ 已清理: {result['title']}")
            if result.get("archived"):
                print(f"   已归档到: {result['archive_path']}")
        else:
            print(f"❌ 清理失败: {result['error']}")
    elif args.list_archived:
        archived = list_archived()
        print(f"已归档记忆: {len(archived)} 条")
        for mem in archived[:20]:
            print(f"  - [{mem.get('id')}] {mem.get('title')} (归档于: {mem.get('archived_at', '?')})")
    elif args.restore:
        result = restore_memory(args.restore)
        if result["success"]:
            print(f"✅ 已恢复: {result['title']}")
            print(f"   新置信度: {result['new_confidence']}")
        else:
            print(f"❌ 恢复失败: {result['error']}")
    elif args.candidates:
        candidates = get_cleanup_candidates()
        print(json.dumps({
            "auto_cleanup": len(candidates["auto_cleanup"]),
            "needs_review": len(candidates["needs_review"]),
            "pending_cleanup": len(candidates["pending_cleanup"])
        }, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
