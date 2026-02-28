#!/usr/bin/env python3
"""
Memory-Like-A-Tree 统一沉淀脚本

功能：
1. 更新 MEMORY.md
2. 触发记忆索引
3. 同步到 Obsidian Vault（可选）
4. 建立知识关联

用法：
    python3 sediment.py --agent default --content "学到的知识" --type knowledge
    python3 sediment.py --agent default --issue 24 --summary "任务总结"
    python3 sediment.py --sync-all  # 同步所有系统
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 尝试导入配置
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
    from config import get_config
    _config = get_config()
    BASE_DIR = _config.base_dir
    DATA_DIR = _config.data_dir
    OBSIDIAN_VAULT_DIR = _config.obsidian_vault
    
    # 从配置构建 WORKSPACES
    WORKSPACES = {}
    for agent in _config.agents:
        WORKSPACES[agent["name"]] = Path(agent["workspace"])
except:
    # 回退到默认配置
    BASE_DIR = Path.home() / ".memory-like-a-tree"
    DATA_DIR = BASE_DIR / "data"
    OBSIDIAN_VAULT_DIR = None
    WORKSPACES = {
        "default": BASE_DIR / "workspace"
    }

# 内容类型映射
CONTENT_TYPES = {
    "knowledge": "技术知识",
    "lesson": "经验教训",
    "rule": "规则/规范",
    "tool": "工具/技巧",
    "decision": "决策记录",
    "summary": "任务总结",
}


def get_workspace(agent: str) -> Path:
    """获取 Agent 的 workspace 路径"""
    return WORKSPACES.get(agent, OPENCLAW_DIR / f"workspace-{agent}")


def update_memory_md(agent: str, content: str, content_type: str, title: str = None) -> Dict[str, Any]:
    """
    更新 Agent 的 MEMORY.md
    
    Args:
        agent: Agent 名称
        content: 要添加的内容
        content_type: 内容类型
        title: 标题（可选）
    
    Returns:
        更新结果
    """
    workspace = get_workspace(agent)
    memory_md = workspace / "MEMORY.md"
    
    if not memory_md.exists():
        return {"status": "error", "message": f"MEMORY.md not found: {memory_md}"}
    
    # 读取现有内容
    with open(memory_md, 'r', encoding='utf-8') as f:
        existing = f.read()
    
    # 生成新内容
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    if not title:
        title = f"{date_str} {CONTENT_TYPES.get(content_type, content_type)}"
    
    # 确定优先级
    priority = "P2"
    if content_type in ["rule", "lesson"]:
        priority = "P1"
    
    # 构建新条目
    new_entry = f"""
## [{priority}] {title}
<!-- TTL: 30d | added: {date_str} {time_str} | type: {content_type} -->

{content}

"""
    
    # 找到合适的插入位置（在最后一个 ## 之前，或文件末尾）
    # 简单起见，追加到文件末尾
    with open(memory_md, 'a', encoding='utf-8') as f:
        f.write(new_entry)
    
    return {
        "status": "success",
        "agent": agent,
        "file": str(memory_md),
        "title": title,
        "type": content_type,
        "priority": priority
    }


def trigger_memory_indexer() -> Dict[str, Any]:
    """触发 memory-confidence 索引器"""
    indexer = MEMORY_CONFIDENCE_DIR / "indexer.py"
    
    if not indexer.exists():
        return {"status": "error", "message": "memory-confidence indexer not found"}
    
    try:
        result = subprocess.run(
            ["python3", str(indexer), "--watch"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Indexer timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def sync_to_obsidian(agent: str, content: str, content_type: str, title: str = None) -> Dict[str, Any]:
    """同步内容到 Obsidian Vault"""
    if not OBSIDIAN_SYNC_SCRIPT.exists():
        return {"status": "error", "message": "Obsidian sync script not found"}
    
    # 映射内容类型到 Obsidian 类型
    obsidian_type_map = {
        "knowledge": "knowledge",
        "lesson": "methodology",
        "rule": "rule",
        "tool": "tool",
        "decision": "decision",
        "summary": "work",
    }
    obsidian_type = obsidian_type_map.get(content_type, "knowledge")
    
    try:
        cmd = [
            "python3", str(OBSIDIAN_SYNC_SCRIPT),
            "--content", content,
            "--type", obsidian_type,
            "--agent", agent
        ]
        if title:
            cmd.extend(["--title", title])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def sediment(
    agent: str,
    content: str,
    content_type: str = "knowledge",
    title: str = None,
    issue_id: int = None,
    skip_obsidian: bool = False,
    skip_indexer: bool = False
) -> Dict[str, Any]:
    """
    统一沉淀入口
    
    Args:
        agent: Agent 名称
        content: 沉淀内容
        content_type: 内容类型
        title: 标题
        issue_id: 关联的 Issue ID
        skip_obsidian: 跳过 Obsidian 同步
        skip_indexer: 跳过 memory-confidence 索引
    
    Returns:
        沉淀结果
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "content_type": content_type,
        "issue_id": issue_id,
        "steps": {}
    }
    
    # 如果有 Issue ID，添加到标题
    if issue_id and not title:
        title = f"Issue #{issue_id} 总结"
    
    # Step 1: 更新 MEMORY.md
    print(f"📝 更新 {agent} 的 MEMORY.md...")
    memory_result = update_memory_md(agent, content, content_type, title)
    results["steps"]["memory_md"] = memory_result
    
    if memory_result["status"] != "success":
        results["status"] = "partial"
        print(f"  ⚠️ MEMORY.md 更新失败: {memory_result.get('message')}")
    else:
        print(f"  ✅ MEMORY.md 已更新")
    
    # Step 2: 触发 memory-confidence 索引
    if not skip_indexer:
        print(f"🔍 触发 memory-confidence 索引...")
        indexer_result = trigger_memory_indexer()
        results["steps"]["indexer"] = indexer_result
        
        if indexer_result["status"] == "success":
            print(f"  ✅ 索引已更新")
        else:
            print(f"  ⚠️ 索引更新失败")
    
    # Step 3: 同步到 Obsidian
    if not skip_obsidian:
        print(f"📚 同步到 Obsidian Vault...")
        obsidian_result = sync_to_obsidian(agent, content, content_type, title)
        results["steps"]["obsidian"] = obsidian_result
        
        if obsidian_result["status"] == "success":
            print(f"  ✅ Obsidian 已同步")
        else:
            print(f"  ⚠️ Obsidian 同步失败")
    
    # 判断整体状态
    all_success = all(
        step.get("status") == "success" 
        for step in results["steps"].values()
    )
    results["status"] = "success" if all_success else "partial"
    
    return results


def sync_all_systems() -> Dict[str, Any]:
    """同步所有系统"""
    print("🔄 开始同步所有系统...\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "systems": {}
    }
    
    # 1. 运行 memory-confidence 全量扫描
    print("1️⃣ memory-confidence 全量扫描...")
    indexer = MEMORY_CONFIDENCE_DIR / "indexer.py"
    if indexer.exists():
        try:
            result = subprocess.run(
                ["python3", str(indexer), "--scan-all"],
                capture_output=True,
                text=True,
                timeout=120
            )
            results["systems"]["memory_confidence"] = {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout[-500:] if result.stdout else None
            }
            print("   ✅ 完成")
        except Exception as e:
            results["systems"]["memory_confidence"] = {"status": "error", "message": str(e)}
            print(f"   ❌ 失败: {e}")
    
    # 2. 重建所有 index.json
    print("\n2️⃣ 重建所有 workspace 的 index.json...")
    if indexer.exists():
        try:
            result = subprocess.run(
                ["python3", str(indexer), "--rebuild-indexes"],
                capture_output=True,
                text=True,
                timeout=60
            )
            results["systems"]["indexes"] = {
                "status": "success" if result.returncode == 0 else "error"
            }
            print("   ✅ 完成")
        except Exception as e:
            results["systems"]["indexes"] = {"status": "error", "message": str(e)}
            print(f"   ❌ 失败: {e}")
    
    # 3. 同步所有 MEMORY.md 到 Obsidian
    print("\n3️⃣ 同步 MEMORY.md 到 Obsidian...")
    synced = 0
    for agent, workspace in WORKSPACES.items():
        memory_md = workspace / "MEMORY.md"
        if memory_md.exists():
            try:
                with open(memory_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 同步到 Obsidian
                if OBSIDIAN_SYNC_SCRIPT.exists():
                    subprocess.run(
                        ["python3", str(OBSIDIAN_SYNC_SCRIPT),
                         "--file", str(memory_md),
                         "--type", "knowledge",
                         "--agent", agent],
                        capture_output=True,
                        timeout=30
                    )
                    synced += 1
            except Exception:
                pass
    
    results["systems"]["obsidian_sync"] = {
        "status": "success",
        "synced_agents": synced
    }
    print(f"   ✅ 同步了 {synced} 个 Agent")
    
    print("\n✅ 所有系统同步完成")
    return results


def check_sediment_status(agent: str = None) -> Dict[str, Any]:
    """检查沉淀状态"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "agents": {}
    }
    
    agents_to_check = [agent] if agent else list(WORKSPACES.keys())
    
    for a in agents_to_check:
        workspace = get_workspace(a)
        memory_md = workspace / "MEMORY.md"
        
        agent_status = {
            "memory_md_exists": memory_md.exists(),
            "memory_md_lines": 0,
            "memory_md_last_modified": None,
            "memory_files_count": 0
        }
        
        if memory_md.exists():
            stat = memory_md.stat()
            agent_status["memory_md_last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            with open(memory_md, 'r', encoding='utf-8') as f:
                agent_status["memory_md_lines"] = len(f.readlines())
        
        memory_dir = workspace / "memory"
        if memory_dir.exists():
            agent_status["memory_files_count"] = len(list(memory_dir.glob("*.md")))
        
        status["agents"][a] = agent_status
    
    return status


def main():
    parser = argparse.ArgumentParser(description="统一沉淀脚本")
    parser.add_argument("--agent", "-a", help="Agent 名称", choices=list(WORKSPACES.keys()))
    parser.add_argument("--content", "-c", help="沉淀内容")
    parser.add_argument("--type", "-t", default="knowledge", 
                        help="内容类型", choices=list(CONTENT_TYPES.keys()))
    parser.add_argument("--title", help="标题")
    parser.add_argument("--issue", type=int, help="关联的 Issue ID")
    parser.add_argument("--sync-all", action="store_true", help="同步所有系统")
    parser.add_argument("--status", action="store_true", help="检查沉淀状态")
    parser.add_argument("--skip-obsidian", action="store_true", help="跳过 Obsidian 同步")
    parser.add_argument("--skip-indexer", action="store_true", help="跳过索引更新")
    
    args = parser.parse_args()
    
    if args.sync_all:
        result = sync_all_systems()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.status:
        result = check_sediment_status(args.agent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.agent and args.content:
        result = sediment(
            agent=args.agent,
            content=args.content,
            content_type=args.type,
            title=args.title,
            issue_id=args.issue,
            skip_obsidian=args.skip_obsidian,
            skip_indexer=args.skip_indexer
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
