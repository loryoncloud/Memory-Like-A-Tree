#!/usr/bin/env python3
"""
Memory-Like-A-Tree 记忆衰减器

定期衰减长期未访问的记忆
支持配置化参数
"""

import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 尝试导入配置
try:
    from .config import get_config
    from .db import load_db, save_db, get_all_memories, get_stats
    _config = get_config()
    _decay_config = _config.decay
except:
    try:
        from db import load_db, save_db, get_all_memories, get_stats
    except:
        from .db import load_db, save_db, get_all_memories, get_stats
    _decay_config = None

# 衰减配置（可被配置文件覆盖）
def get_decay_config():
    """获取衰减配置"""
    if _decay_config:
        return {
            "grace_period_days": _decay_config.get("grace_period_days", 60),
            "decay_interval_days": 7,
            "decay_factor": 0.95,
            "min_confidence": 0.05,
            "cleanup_threshold": 0.10,
            "protected_priorities": ["P0"],
            "daily_decay_rate": _decay_config.get("rates", {
                "P0": 0.0,
                "P1": 0.004,
                "P2": 0.008,
            })
        }
    else:
        return {
            "grace_period_days": 60,
            "decay_interval_days": 7,
            "decay_factor": 0.95,
            "min_confidence": 0.05,
            "cleanup_threshold": 0.10,
            "protected_priorities": ["P0"],
            "daily_decay_rate": {
                "P0": 0.0,
                "P1": 0.004,
                "P2": 0.008,
            }
        }

DECAY_CONFIG = get_decay_config()

def calculate_decay(last_accessed: str, current_confidence: float, priority: str) -> Dict[str, Any]:
    """
    计算衰减后的置信度
    
    Args:
        last_accessed: 最后访问时间 (ISO 格式)
        current_confidence: 当前置信度
        priority: 优先级
    
    Returns:
        衰减结果
    """
    # P0 永不衰减
    if priority in DECAY_CONFIG["protected_priorities"]:
        return {
            "decayed": False,
            "reason": "protected_priority",
            "new_confidence": current_confidence
        }
    
    # 从未访问过的记忆，使用创建时间
    if not last_accessed:
        return {
            "decayed": False,
            "reason": "never_accessed",
            "new_confidence": current_confidence
        }
    
    try:
        last_access_dt = datetime.fromisoformat(last_accessed)
    except ValueError:
        return {
            "decayed": False,
            "reason": "invalid_date",
            "new_confidence": current_confidence
        }
    
    days_since_access = (datetime.now() - last_access_dt).days
    
    # 宽限期内不衰减
    if days_since_access <= DECAY_CONFIG["grace_period_days"]:
        return {
            "decayed": False,
            "reason": "within_grace_period",
            "days_since_access": days_since_access,
            "new_confidence": current_confidence
        }
    
    # 计算衰减轮数（使用每日衰减率）
    decay_days = days_since_access - DECAY_CONFIG["grace_period_days"]
    
    if decay_days <= 0:
        return {
            "decayed": False,
            "reason": "no_decay_days",
            "days_since_access": days_since_access,
            "new_confidence": current_confidence
        }
    
    # 获取每日衰减率
    daily_rate = DECAY_CONFIG.get("daily_decay_rate", {}).get(priority, 0.008)
    
    # 应用衰减：每天减少 daily_rate
    decay_amount = decay_days * daily_rate
    new_confidence = current_confidence - decay_amount
    new_confidence = max(DECAY_CONFIG["min_confidence"], round(new_confidence, 3))
    
    return {
        "decayed": True,
        "days_since_access": days_since_access,
        "decay_rounds": decay_rounds,
        "old_confidence": current_confidence,
        "new_confidence": new_confidence,
        "should_cleanup": new_confidence < DECAY_CONFIG["cleanup_threshold"]
    }

def run_decay(dry_run: bool = False) -> Dict[str, Any]:
    """
    执行衰减
    
    Args:
        dry_run: 是否只预览不实际修改
    
    Returns:
        衰减结果
    """
    db = load_db()
    memories = db.get("memories", {})
    
    results = {
        "total": len(memories),
        "decayed": 0,
        "protected": 0,
        "unchanged": 0,
        "marked_cleanup": 0,
        "details": [],
        "dry_run": dry_run,
        "timestamp": datetime.now().isoformat()
    }
    
    for mem_id, mem in memories.items():
        decay_result = calculate_decay(
            mem.get("last_accessed"),
            mem.get("confidence", 0.5),
            mem.get("priority", "P2")
        )
        
        if decay_result["reason"] == "protected_priority":
            results["protected"] += 1
        elif decay_result["decayed"]:
            results["decayed"] += 1
            
            if not dry_run:
                mem["confidence"] = decay_result["new_confidence"]
                if decay_result.get("should_cleanup"):
                    mem["status"] = "pending_cleanup"
                    results["marked_cleanup"] += 1
            
            results["details"].append({
                "id": mem_id,
                "title": mem.get("title", mem_id),
                "agent": mem.get("agent", "unknown"),
                **decay_result
            })
        else:
            results["unchanged"] += 1
    
    if not dry_run and results["decayed"] > 0:
        save_db(db)
    
    return results

def preview_decay() -> str:
    """预览衰减结果"""
    results = run_decay(dry_run=True)
    
    lines = []
    lines.append("# 记忆衰减预览\n")
    lines.append(f"时间: {results['timestamp']}\n")
    lines.append(f"## 统计\n")
    lines.append(f"- 总记忆数: {results['total']}")
    lines.append(f"- 将衰减: {results['decayed']}")
    lines.append(f"- 受保护 (P0): {results['protected']}")
    lines.append(f"- 无变化: {results['unchanged']}")
    lines.append(f"- 将标记清理: {results['marked_cleanup']}")
    
    if results["details"]:
        lines.append(f"\n## 衰减详情\n")
        for detail in sorted(results["details"], key=lambda x: x.get("new_confidence", 1)):
            lines.append(
                f"- [{detail['agent']}] {detail['title']}: "
                f"{detail['old_confidence']:.3f} → {detail['new_confidence']:.3f} "
                f"(未访问 {detail['days_since_access']} 天, 衰减 {detail['decay_rounds']} 轮)"
                + (" ⚠️ 待清理" if detail.get('should_cleanup') else "")
            )
    
    return '\n'.join(lines)

def get_decay_stats() -> Dict[str, Any]:
    """获取衰减统计"""
    memories = get_all_memories()
    
    if not memories:
        return {"total": 0}
    
    now = datetime.now()
    stats = {
        "total": len(memories),
        "protected": 0,
        "at_risk": 0,  # 即将衰减
        "decaying": 0,  # 正在衰减
        "low_confidence": 0,  # 低置信度
        "pending_cleanup": 0
    }
    
    for mem in memories.values():
        priority = mem.get("priority", "P2")
        confidence = mem.get("confidence", 0.5)
        last_accessed = mem.get("last_accessed")
        
        if priority in DECAY_CONFIG["protected_priorities"]:
            stats["protected"] += 1
        elif last_accessed:
            try:
                days = (now - datetime.fromisoformat(last_accessed)).days
                if days > DECAY_CONFIG["grace_period_days"]:
                    stats["decaying"] += 1
                elif days > DECAY_CONFIG["grace_period_days"] - 14:
                    stats["at_risk"] += 1
            except ValueError:
                pass
        
        if confidence < DECAY_CONFIG["cleanup_threshold"]:
            stats["pending_cleanup"] += 1
        elif confidence < 0.5:
            stats["low_confidence"] += 1
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="记忆衰减器")
    parser.add_argument("--run", action="store_true", help="执行衰减")
    parser.add_argument("--dry-run", action="store_true", help="预览衰减（不实际修改）")
    parser.add_argument("--preview", action="store_true", help="生成预览报告")
    parser.add_argument("--stats", action="store_true", help="显示衰减统计")
    parser.add_argument("--config", action="store_true", help="显示衰减配置")
    
    args = parser.parse_args()
    
    if args.run:
        results = run_decay(dry_run=False)
        print(f"✅ 衰减完成")
        print(f"   衰减: {results['decayed']} 条")
        print(f"   标记清理: {results['marked_cleanup']} 条")
        print(f"   受保护: {results['protected']} 条")
    elif args.dry_run or args.preview:
        print(preview_decay())
    elif args.stats:
        stats = get_decay_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.config:
        print(json.dumps(DECAY_CONFIG, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
