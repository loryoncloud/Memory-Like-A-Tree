#!/usr/bin/env python3
"""
沉淀检查模块 - 在关闭 Issue 时检查是否有知识沉淀

功能：
1. 检查 Agent 的 MEMORY.md 是否在 Issue 期间有更新
2. 检查是否有相关的 memory/ 文件
3. 提醒 Agent 沉淀知识

用法：
    python3 sediment_check.py check <issue_id> <agent>
    python3 sediment_check.py report
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 尝试导入配置
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
    from config import get_config
    _config = get_config()
    BASE_DIR = _config.base_dir
    
    # 从配置构建 WORKSPACES
    WORKSPACES = {}
    for agent in _config.agents:
        WORKSPACES[agent["name"]] = Path(agent["workspace"])
except:
    # 回退到默认配置
    BASE_DIR = Path.home() / ".memory-like-a-tree"
    WORKSPACES = {
        "default": BASE_DIR / "workspace"
    }

# Issue 目录
ISSUES_DIR = BASE_DIR / "issue-manager" / ".issues"


def get_issue_info(issue_id: int) -> dict:
    """获取 Issue 信息"""
    index_path = ISSUES_DIR / "index.json"
    if not index_path.exists():
        return None
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    for issue in index.get("issues", []):
        if issue.get("id") == issue_id:
            return issue
    
    return None


def check_memory_update(agent: str, since: str = None) -> dict:
    """
    检查 Agent 的 MEMORY.md 是否有更新
    
    Args:
        agent: Agent 名称
        since: ISO 格式的时间字符串，检查这个时间之后的更新
    
    Returns:
        检查结果
    """
    workspace = WORKSPACES.get(agent)
    if not workspace or not workspace.exists():
        return {"status": "error", "message": f"Agent {agent} 的 workspace 不存在"}
    
    memory_md = workspace / "MEMORY.md"
    if not memory_md.exists():
        return {"status": "warning", "message": f"Agent {agent} 没有 MEMORY.md"}
    
    # 获取文件修改时间
    mtime = datetime.fromtimestamp(memory_md.stat().st_mtime)
    
    # 如果指定了 since，检查是否在这之后有更新
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            if mtime < since_dt:
                return {
                    "status": "warning",
                    "message": f"MEMORY.md 在 Issue 分配后没有更新",
                    "last_modified": mtime.isoformat(),
                    "assigned_at": since
                }
        except:
            pass
    
    # 检查今天是否有更新
    today = datetime.now().date()
    if mtime.date() < today:
        days_ago = (today - mtime.date()).days
        return {
            "status": "warning",
            "message": f"MEMORY.md 已 {days_ago} 天没有更新",
            "last_modified": mtime.isoformat()
        }
    
    return {
        "status": "ok",
        "message": "MEMORY.md 今天有更新",
        "last_modified": mtime.isoformat()
    }


def check_memory_files(agent: str, issue_id: int = None) -> dict:
    """
    检查 Agent 的 memory/ 目录是否有相关文件
    
    Args:
        agent: Agent 名称
        issue_id: Issue ID（可选，用于检查是否有相关文件）
    
    Returns:
        检查结果
    """
    workspace = WORKSPACES.get(agent)
    if not workspace or not workspace.exists():
        return {"status": "error", "message": f"Agent {agent} 的 workspace 不存在"}
    
    memory_dir = workspace / "memory"
    if not memory_dir.exists():
        return {"status": "warning", "message": f"Agent {agent} 没有 memory/ 目录"}
    
    # 统计 memory/ 下的文件
    md_files = list(memory_dir.glob("*.md"))
    today = datetime.now().date()
    today_files = [f for f in md_files if datetime.fromtimestamp(f.stat().st_mtime).date() == today]
    
    # 如果指定了 issue_id，检查是否有相关文件
    issue_related = []
    if issue_id:
        for f in md_files:
            if f"issue-{issue_id}" in f.name.lower() or f"#{issue_id}" in f.name:
                issue_related.append(f.name)
    
    return {
        "status": "ok" if today_files or issue_related else "warning",
        "total_files": len(md_files),
        "today_files": len(today_files),
        "issue_related": issue_related,
        "message": f"memory/ 有 {len(md_files)} 个文件，今天更新 {len(today_files)} 个"
    }


def check_sediment(issue_id: int, agent: str = None) -> dict:
    """
    检查 Issue 的沉淀情况
    
    Args:
        issue_id: Issue ID
        agent: Agent 名称（可选，如果不指定则从 Issue 中获取）
    
    Returns:
        检查结果
    """
    # 获取 Issue 信息
    issue = get_issue_info(issue_id)
    if not issue:
        return {"status": "error", "message": f"Issue #{issue_id} 不存在"}
    
    # 获取 assignee
    if not agent:
        agent = issue.get("assignee")
    
    if not agent or agent == "unassigned":
        return {"status": "error", "message": f"Issue #{issue_id} 没有分配给任何 Agent"}
    
    # 获取分配时间
    assigned_at = issue.get("assigned_at")
    
    # 检查 MEMORY.md
    memory_check = check_memory_update(agent, assigned_at)
    
    # 检查 memory/ 目录
    files_check = check_memory_files(agent, issue_id)
    
    # 综合判断
    has_sediment = (
        memory_check.get("status") == "ok" or 
        files_check.get("issue_related") or
        files_check.get("today_files", 0) > 0
    )
    
    return {
        "issue_id": issue_id,
        "agent": agent,
        "has_sediment": has_sediment,
        "memory_md": memory_check,
        "memory_files": files_check,
        "recommendation": None if has_sediment else "建议在关闭 Issue 前沉淀学到的知识到 MEMORY.md"
    }


def generate_report() -> dict:
    """生成所有 Agent 的沉淀报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "agents": {}
    }
    
    for agent, workspace in WORKSPACES.items():
        if not workspace.exists():
            continue
        
        memory_check = check_memory_update(agent)
        files_check = check_memory_files(agent)
        
        report["agents"][agent] = {
            "memory_md": memory_check,
            "memory_files": files_check
        }
    
    return report


def main():
    parser = argparse.ArgumentParser(description="沉淀检查模块")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # check 命令
    check_parser = subparsers.add_parser("check", help="检查 Issue 的沉淀情况")
    check_parser.add_argument("issue_id", type=int, help="Issue ID")
    check_parser.add_argument("--agent", "-a", help="Agent 名称（可选）")
    
    # report 命令
    report_parser = subparsers.add_parser("report", help="生成沉淀报告")
    
    args = parser.parse_args()
    
    if args.command == "check":
        result = check_sediment(args.issue_id, args.agent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if not result.get("has_sediment"):
            print("\n⚠️ 沉淀检查未通过！")
            print(f"   {result.get('recommendation')}")
            sys.exit(1)
        else:
            print("\n✅ 沉淀检查通过")
    
    elif args.command == "report":
        result = generate_report()
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
