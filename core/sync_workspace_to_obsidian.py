#!/usr/bin/env python3
"""
Memory-Like-A-Tree Workspace → Obsidian 同步脚本

功能：同步所有 Agent 的 MEMORY.md 和 memory/ 到 Obsidian Vault

用法：
    python3 sync_workspace_to_obsidian.py           # 同步所有 Agent
    python3 sync_workspace_to_obsidian.py --agent dev  # 只同步指定 Agent
    python3 sync_workspace_to_obsidian.py --dry-run    # 预览不执行

自动化：
    Cron 任务每 2 小时运行一次
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 尝试导入配置
try:
    from .config import get_config
    _config = get_config()
    OBSIDIAN_VAULT = _config.obsidian_vault
    AGENTS = [a["name"] for a in _config.agents]
    
    def get_workspace_path(agent: str) -> Path:
        """获取 Agent 的 workspace 路径"""
        agent_config = _config.get_agent(agent)
        if agent_config:
            return Path(agent_config["workspace"])
        return _config.base_dir / "workspace"
except:
    # 回退到默认配置
    BASE_DIR = Path.home() / ".memory-like-a-tree"
    OBSIDIAN_VAULT = BASE_DIR / "obsidian-vault"
    AGENTS = ["default"]
    
    def get_workspace_path(agent: str) -> Path:
        """获取 Agent 的 workspace 路径"""
        return BASE_DIR / "workspace"

AGENT_DIR = OBSIDIAN_VAULT / "01-Agent" if OBSIDIAN_VAULT else None


def get_obsidian_path(agent: str) -> Path:
    """获取 Agent 在 Obsidian 中的路径"""
    # 首字母大写
    agent_cap = agent.capitalize()
    return AGENT_DIR / agent_cap


def sync_agent(agent: str, dry_run: bool = False) -> dict:
    """
    同步单个 Agent 的内容到 Obsidian
    
    Args:
        agent: Agent 名称
        dry_run: 是否只预览
    
    Returns:
        同步结果
    """
    workspace = get_workspace_path(agent)
    obsidian = get_obsidian_path(agent)
    
    result = {
        "agent": agent,
        "workspace": str(workspace),
        "obsidian": str(obsidian),
        "memory_md": False,
        "memory_files": 0,
        "errors": []
    }
    
    if not workspace.exists():
        result["errors"].append(f"Workspace 不存在: {workspace}")
        return result
    
    # 确保 Obsidian 目录存在
    if not dry_run:
        obsidian.mkdir(parents=True, exist_ok=True)
        (obsidian / "memory").mkdir(exist_ok=True)
    
    # 同步 MEMORY.md
    memory_md_src = workspace / "MEMORY.md"
    memory_md_dst = obsidian / "MEMORY.md"
    
    if memory_md_src.exists():
        if not dry_run:
            shutil.copy2(memory_md_src, memory_md_dst)
        result["memory_md"] = True
    
    # 同步 memory/*.md
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        md_files = list(memory_dir.glob("*.md"))
        for md_file in md_files:
            dst = obsidian / "memory" / md_file.name
            if not dry_run:
                shutil.copy2(md_file, dst)
        result["memory_files"] = len(md_files)
    
    return result


def sync_all(agents: list = None, dry_run: bool = False) -> dict:
    """
    同步所有 Agent
    
    Args:
        agents: 要同步的 Agent 列表（None 表示全部）
        dry_run: 是否只预览
    
    Returns:
        同步结果
    """
    if agents is None:
        agents = AGENTS
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "agents": [],
        "total_memory_md": 0,
        "total_memory_files": 0,
        "errors": []
    }
    
    for agent in agents:
        result = sync_agent(agent, dry_run)
        results["agents"].append(result)
        
        if result["memory_md"]:
            results["total_memory_md"] += 1
        results["total_memory_files"] += result["memory_files"]
        results["errors"].extend(result["errors"])
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Workspace → Obsidian 同步")
    parser.add_argument("--agent", help="只同步指定 Agent")
    parser.add_argument("--dry-run", action="store_true", help="预览不执行")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    if args.agent:
        agents = [args.agent]
    else:
        agents = AGENTS
    
    results = sync_all(agents, args.dry_run)
    
    if not args.quiet:
        if args.dry_run:
            print("🔍 预览模式（不实际执行）\n")
        
        print(f"=== Workspace → Obsidian 同步 ===")
        print(f"时间: {results['timestamp']}")
        print(f"Agent 数: {len(results['agents'])}")
        print(f"MEMORY.md: {results['total_memory_md']} 个")
        print(f"memory/*.md: {results['total_memory_files']} 个")
        
        if results['errors']:
            print(f"\n⚠️ 错误: {len(results['errors'])}")
            for err in results['errors']:
                print(f"  - {err}")
        else:
            print(f"\n✅ 同步完成")


if __name__ == "__main__":
    main()
