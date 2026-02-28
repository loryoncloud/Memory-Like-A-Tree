#!/usr/bin/env python3
"""
Memory-Like-A-Tree Issue 管理器

在 .issues/ 目录下管理 Issues

用法:
  python3 manager.py create --title "任务标题" --body "描述" --priority P1 --labels bug fix
  python3 manager.py list [--status open|in-progress|closed] [--labels tag1 tag2]
  python3 manager.py show <id>
  python3 manager.py assign <id> <agent_name>
  python3 manager.py close <id> --learnings "学到了什么" [--resolution "解决说明"]
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import os

# 尝试导入权限控制模块（可选）
try:
    from auth import require_create_permission
except ImportError:
    # 如果没有 auth 模块，使用空装饰器
    def require_create_permission(func):
        return func


def find_workspace():
    """查找工作区根目录"""
    # 1. 环境变量
    env_ws = os.environ.get("MLAT_ISSUE_DIR") or os.environ.get("ISSUE_MANAGER_DIR")
    if env_ws and Path(env_ws).exists():
        return Path(env_ws)
    
    # 2. 向上查找 .issues/ 目录
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".issues").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # 3. 默认：用户目录下
    default_dir = Path.home() / ".memory-like-a-tree" / "issue-manager"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir

WORKSPACE = find_workspace()
ISSUES_DIR = WORKSPACE / ".issues"


class IssueManager:
    def __init__(self, workspace=None):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = WORKSPACE
        
        self.issues_dir = self.workspace / ".issues"
        self.open_dir = self.issues_dir / "open"
        self.in_progress_dir = self.issues_dir / "in-progress"
        self.closed_dir = self.issues_dir / "closed"
        
        # 确保目录存在
        for d in [self.open_dir, self.in_progress_dir, self.closed_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 索引文件
        self.index_file = self.issues_dir / "index.json"
        self.load_index()
    
    def load_index(self):
        """加载索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.index = {"issues": [], "next_id": 1}
        else:
            self.index = {"issues": [], "next_id": 1}
    
    def save_index(self):
        """保存索引"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    @require_create_permission()
    def create(self, title, body="", priority="P2", labels=None, assignee=None, assigned_at=None):
        """创建 Issue（需要权限）"""
        if not title or not title.strip():
            print("❌ 标题不能为空")
            return None
        title = title.strip()
        
        if labels is None:
            labels = []
        
        issue_id = self.index["next_id"]
        self.index["next_id"] += 1
        timestamp = datetime.now().isoformat()
        
        issue = {
            "id": issue_id,
            "title": title,
            "priority": priority,
            "labels": labels if isinstance(labels, list) else [labels],
            "status": "open",
            "assignee": assignee or "unassigned",
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        # 如果创建时就指定了 assignee，记录分配时间
        if assignee and assignee != "unassigned":
            issue["assigned_at"] = assigned_at or timestamp
        
        # 文件名：ID-标题slug（保留中文字符）
        slug = title.lower().replace(" ", "-")
        # 保留字母、数字、中文、日文、韩文、连字符、下划线
        import re
        slug = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af-]', '', slug)[:50]
        filename = f"{issue_id:03d}-{slug}.md"
        filepath = self.open_dir / filename
        
        # 写入 Issue 文件
        content = f"""---
id: {issue_id}
title: {title}
priority: {priority}
labels: {', '.join(issue['labels'])}
status: open
assignee: {issue['assignee']}
created_at: {timestamp}
updated_at: {timestamp}
---

{body}
"""
        filepath.write_text(content, encoding='utf-8')
        
        # 创建工作空间目录
        workspace_name = f"#{issue_id:03d}-{slug}"
        workspace_dir = Path.home() / "Desktop" / "Issues" / workspace_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建规范子目录结构
        subdirs = [
            "01-调研",
            "01-调研/参考案例",
            "02-方案",
            "03-实施",
            "03-实施/scripts",
            "03-实施/configs",
            "04-交付",
            "05-日志"
        ]
        for subdir in subdirs:
            (workspace_dir / subdir).mkdir(exist_ok=True)
        
        # 创建工作空间 README
        readme_content = f"""# Issue #{issue_id:03d} 工作空间 - {title}

## 基本信息

- **Issue ID**: #{issue_id:03d}
- **标题**: {title}
- **优先级**: {priority}
- **负责人**: {assignee or 'unassigned'}
- **创建时间**: {timestamp}
- **状态**: {issue['status']}

---

## 📋 需求描述

{body or '待补充'}

---

## 📊 进度追踪

| 阶段 | 状态 | 完成时间 |
|------|------|----------|
| 接到任务 | ✅ | {timestamp[:10]} |
| 深度调研 | ⏳ | - |
| 方案设计 | ⏳ | - |
| 审核通过 | ⏳ | - |
| 实操落地 | ⏳ | - |
| 交付留存 | ⏳ | - |

---

## 📁 目录结构

```
{workspace_name}/
├── README.md              # 本文件
├── 01-调研/               # 深度调研材料
│   ├── 技术可行性.md
│   ├── 团队适配分析.md
│   ├── 风险评估.md
│   └── 参考案例/
├── 02-方案/               # 设计方案
│   ├── 设计方案-v1.md
│   └── 审核记录.md
├── 03-实施/               # 实施记录
│   ├── 实施日志.md
│   ├── scripts/
│   └── configs/
├── 04-交付/               # 最终交付物
│   ├── 交付清单.md
│   └── 使用文档.md
└── 05-日志/               # 工作日志
    └── {timestamp[:10]}.md
```

---

## 📦 交付物清单

- [ ] 待添加

---

## 📝 工作流程

1. **深度调研** → 输出调研报告到 `01-调研/`
2. **方案设计** → 输出方案文档到 `02-方案/`
3. **提交审核** → bro 审核通过后进入实施
4. **实操落地** → 脚本和日志放到 `03-实施/`
5. **交付留存** → 整理交付物到 `04-交付/`

---

**最后更新**: {timestamp}
"""
        readme_path = workspace_dir / "README.md"
        readme_path.write_text(readme_content, encoding='utf-8')
        
        # 更新索引
        issue["file"] = str(filepath.relative_to(self.workspace))
        issue["workspace"] = str(workspace_dir)  # 使用绝对路径
        self.index["issues"].append(issue)
        self.save_index()
        
        print(f"✅ Issue #{issue_id} 创建: {title}")
        print(f"📁 工作空间: {workspace_dir}")
        return issue
    
    def list_issues(self, status="open", labels=None, priority=None, assignee=None):
        """列出 Issues（支持过滤）"""
        results = []
        for issue in self.index["issues"]:
            if status and issue.get("status") != status:
                continue
            if labels and not any(l in issue.get("labels", []) for l in labels):
                continue
            if priority and issue.get("priority") != priority:
                continue
            if assignee and issue.get("assignee") != assignee:
                continue
            results.append(issue)
        return results
    
    def get(self, issue_id):
        """获取单个 Issue 详情"""
        issue = self._find(issue_id)
        if not issue:
            return None
        filepath = self.workspace / issue["file"]
        if filepath.exists():
            issue["content"] = filepath.read_text(encoding='utf-8')
        return issue
    
    def assign(self, issue_id, assignee):
        """分配 Issue 给某个 Agent"""
        issue = self._find(issue_id)
        if not issue:
            print(f"❌ Issue #{issue_id} 不存在")
            return None
        
        old_path = self.workspace / issue["file"]
        new_path = self.in_progress_dir / old_path.name
        
        assigned_at = datetime.now().isoformat()
        
        # 更新文件内容
        if old_path.exists():
            content = old_path.read_text(encoding='utf-8')
            content = content.replace(f"assignee: {issue.get('assignee', 'unassigned')}", f"assignee: {assignee}")
            content = content.replace("status: open", "status: in-progress")
            
            # 在 updated_at 后面插入 assigned_at
            import re
            content = re.sub(
                r'(updated_at: [^\n]+)',
                f'\\1\nassigned_at: {assigned_at}',
                content
            )
            
            new_path.write_text(content, encoding='utf-8')
            old_path.unlink()
        
        # 更新索引
        issue["assignee"] = assignee
        issue["status"] = "in-progress"
        issue["assigned_at"] = assigned_at
        issue["updated_at"] = datetime.now().isoformat()
        issue["file"] = str(new_path.relative_to(self.workspace))
        self.save_index()
        
        print(f"✅ Issue #{issue_id} → {assignee} (分配时间: {assigned_at})")
        return issue
    
    def unassign(self, issue_id):
        """取消分配 Issue，将状态改回 open"""
        issue = self._find(issue_id)
        if not issue:
            print(f"❌ Issue #{issue_id} 不存在")
            return None
        
        old_path = self.workspace / issue["file"]
        new_path = self.open_dir / old_path.name
        
        # 更新文件内容
        if old_path.exists():
            content = old_path.read_text(encoding='utf-8')
            # 替换 assignee
            import re
            content = re.sub(r'assignee: .+', 'assignee: unassigned', content)
            # 替换 status
            content = re.sub(r'status: in-progress', 'status: open', content)
            # 移除 assigned_at 行
            content = re.sub(r'\nassigned_at: [^\n]+', '', content)
            
            new_path.write_text(content, encoding='utf-8')
            old_path.unlink()
        
        # 更新索引
        issue["assignee"] = "unassigned"
        issue["status"] = "open"
        if "assigned_at" in issue:
            del issue["assigned_at"]
        issue["updated_at"] = datetime.now().isoformat()
        issue["file"] = str(new_path.relative_to(self.workspace))
        self.save_index()
        
        print(f"✅ Issue #{issue_id} 已取消分配，状态改回 open")
        return issue
    
    def close(self, issue_id, resolution="", check_deliverable=True, check_sediment=True, learnings=None, skip_learnings=False):
        """关闭 Issue（需要检查交付物和沉淀）"""
        issue = self._find(issue_id)
        if not issue:
            print(f"❌ Issue #{issue_id} 不存在")
            return None
        
        # 检查 learnings 参数
        if not learnings and not skip_learnings:
            print(f"❌ 关闭 Issue 必须填写经验教训")
            print(f"   使用 --learnings \"学到了什么\" 填写经验")
            print(f"   或使用 --skip-learnings 跳过（不推荐）")
            return None
        
        if skip_learnings:
            print(f"⚠️ 跳过经验沉淀（不推荐）")
            learnings = "[跳过了经验沉淀]"
        
        # 检查是否有交付物
        if check_deliverable:
            try:
                from deliverable import DeliverableManager
                dm = DeliverableManager()
                deliverables = [d for d in dm.index["deliverables"] if d["issue_id"] == issue_id]
                if not deliverables:
                    print(f"❌ Issue #{issue_id} 没有交付物，无法关闭")
                    print(f"   请先使用 deliverable.py add {issue_id} --file <path> 添加交付物")
                    print(f"   或使用 --no-check-deliverable 跳过检查（不推荐）")
                    return None
            except Exception as e:
                print(f"⚠️ 无法检查交付物: {e}")
        
        # 检查是否有知识沉淀
        if check_sediment:
            try:
                from sediment_check import check_sediment as do_check_sediment
                agent = issue.get("assignee")
                if agent and agent != "unassigned":
                    result = do_check_sediment(issue_id, agent)
                    if not result.get("has_sediment"):
                        print(f"⚠️ Issue #{issue_id} 没有知识沉淀")
                        print(f"   建议先更新 MEMORY.md 或 memory/ 目录")
                        print(f"   使用 sediment.py 沉淀知识：")
                        print(f"   python3 sediment/sediment.py --agent {agent} --content \"学到的内容\" --type knowledge")
                        # 只是警告，不阻止关闭
            except Exception as e:
                print(f"⚠️ 无法检查沉淀: {e}")
        
        # 检查桌面工作空间是否有内容
        desktop_issues_dir = Path.home() / "Desktop" / "Issues"
        workspace_found = False
        workspace_has_content = False
        
        if desktop_issues_dir.exists():
            for dir_name in desktop_issues_dir.iterdir():
                if dir_name.is_dir() and dir_name.name.startswith(f"#{issue_id:03d}-"):
                    workspace_found = True
                    # 检查是否有实际内容（排除 README.md 和空目录）
                    files = [f for f in dir_name.rglob("*") if f.is_file() and f.name != "README.md"]
                    if files:
                        workspace_has_content = True
                    break
        
        if workspace_found and not workspace_has_content:
            print(f"⚠️ Issue #{issue_id} 的桌面工作空间没有实际内容")
            print(f"   请确保交付物已复制到 {desktop_issues_dir}/#{issue_id:03d}-*/")
            print(f"   或使用 quick_sync.py 一键沉淀")
        
        old_path = self.workspace / issue["file"]
        new_path = self.closed_dir / old_path.name
        
        closed_at = datetime.now().isoformat()
        
        if old_path.exists():
            content = old_path.read_text(encoding='utf-8')
            # 更新状态
            for old_status in ["status: open", "status: in-progress"]:
                content = content.replace(old_status, "status: closed")
            # 追加解决方案
            if resolution:
                content += f"\n\n## 解决方案\n\n{resolution}\n\n关闭时间: {closed_at}\n"
            new_path.write_text(content, encoding='utf-8')
            old_path.unlink()
        
        # 更新索引
        issue["status"] = "closed"
        issue["closed_at"] = closed_at
        issue["resolution"] = resolution
        issue["file"] = str(new_path.relative_to(self.workspace))
        self.save_index()
        
        # 自动沉淀到记忆树（萌芽）
        self._auto_sediment_on_close(issue, learnings)
        
        print(f"✅ Issue #{issue_id} 已关闭")
        return issue
    
    def _auto_sediment_on_close(self, issue, learnings=None):
        """
        Issue 关闭时自动沉淀知识到记忆树
        
        Args:
            issue: Issue 数据
            learnings: 经验教训
        """
        agent = issue.get("assignee")
        if not agent or agent == "unassigned":
            return
        
        try:
            import subprocess
            
            # 构建沉淀内容
            issue_id = issue.get("id")
            title = issue.get("title", "")
            resolution = issue.get("resolution", "")
            
            content = f"## Issue #{issue_id}: {title}\n\n"
            if resolution:
                content += f"### 解决方案\n{resolution}\n\n"
            if learnings and learnings != "[跳过了经验沉淀]":
                content += f"### 经验教训\n{learnings}\n\n"
            content += f"### 完成时间\n{issue.get('closed_at', '')}\n"
            
            # 调用 sediment.py 自动沉淀
            sediment_path = Path(__file__).parent.parent / "sediment" / "sediment.py"
            if sediment_path.exists():
                cmd = [
                    "python3", str(sediment_path),
                    "--agent", agent,
                    "--content", content,
                    "--type", "issue",
                    "--title", f"Issue #{issue_id} 完成记录"
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)
                print(f"🌱 已自动沉淀 Issue #{issue_id} 到记忆树")
            
            # 记录进度到 progress.jsonl
            from sync_progress import ProgressTracker
            tracker = ProgressTracker()
            tracker.update(
                issue_id,
                f"Issue 已关闭: {title}",
                status="closed",
                agent=agent
            )
        except Exception as e:
            print(f"⚠️ 自动沉淀失败: {e}")
    
    def sync(self):
        """同步 index.json 与实际文件目录状态"""
        import re
        
        status_dirs = {
            "open": self.open_dir,
            "in-progress": self.in_progress_dir,
            "closed": self.closed_dir,
        }
        
        file_status = {}
        for status, dir_path in status_dirs.items():
            for f in dir_path.glob("*.md"):
                m = re.match(r'^(\d+)-', f.name)
                if m:
                    iid = int(m.group(1))
                    file_status[iid] = (status, str(f.relative_to(self.workspace)))
        
        fixed = 0
        orphans = 0
        
        for issue in self.index["issues"]:
            iid = issue["id"]
            if iid in file_status:
                actual_status, actual_file = file_status[iid]
                if issue["status"] != actual_status or issue.get("file") != actual_file:
                    old_status = issue["status"]
                    issue["status"] = actual_status
                    issue["file"] = actual_file
                    if actual_status == "closed" and "closed_at" not in issue:
                        issue["closed_at"] = datetime.now().isoformat()
                    print(f"  🔧 #{iid:03d} {old_status} → {actual_status}")
                    fixed += 1
                del file_status[iid]
            else:
                if issue["status"] != "closed":
                    print(f"  ⚠️ #{iid:03d} 文件不存在，标记 closed")
                    issue["status"] = "closed"
                    issue["closed_at"] = datetime.now().isoformat()
                    fixed += 1
        
        for iid, (status, filepath) in file_status.items():
            full_path = self.workspace / filepath
            title = f"(孤儿 Issue #{iid})"
            try:
                content = full_path.read_text(encoding='utf-8')
                m = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                if m:
                    title = m.group(1).strip()
            except:
                pass
            
            self.index["issues"].append({
                "id": iid, "title": title, "status": status,
                "file": filepath, "priority": "P2", "labels": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })
            print(f"  ➕ #{iid:03d} 孤儿文件纳入 index ({status})")
            orphans += 1
            if iid >= self.index["next_id"]:
                self.index["next_id"] = iid + 1
        
        self.save_index()
        
        total = len(self.index["issues"])
        by_status = {}
        for issue in self.index["issues"]:
            s = issue["status"]
            by_status[s] = by_status.get(s, 0) + 1
        
        print(f"\n📊 同步完成: 修正 {fixed} 个, 新增孤儿 {orphans} 个")
        print(f"   总计 {total} 个: ", end="")
        print(" | ".join(f"{s}: {c}" for s, c in sorted(by_status.items())))
        return {"fixed": fixed, "orphans": orphans, "total": total, "by_status": by_status}
    
    def stats(self):
        """统计概览"""
        total = len(self.index["issues"])
        by_status = {}
        for issue in self.index["issues"]:
            s = issue.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return {"total": total, "by_status": by_status, "next_id": self.index["next_id"]}
    
    def _find(self, issue_id):
        """按 ID 查找"""
        for issue in self.index["issues"]:
            if issue["id"] == int(issue_id):
                return issue
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="本地 Issue 管理器")
    sub = parser.add_subparsers(dest="cmd")
    
    # create
    p = sub.add_parser("create")
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--priority", default="P2")
    p.add_argument("--labels", nargs="+", default=[])
    
    # list
    p = sub.add_parser("list")
    p.add_argument("--status", default="open")
    p.add_argument("--labels", nargs="+")
    p.add_argument("--priority")
    p.add_argument("--assignee")
    
    # show
    p = sub.add_parser("show")
    p.add_argument("issue_id", type=int)
    
    # assign
    p = sub.add_parser("assign")
    p.add_argument("issue_id", type=int)
    p.add_argument("assignee")
    
    # unassign
    p = sub.add_parser("unassign")
    p.add_argument("issue_id", type=int)
    
    # close
    p = sub.add_parser("close")
    p.add_argument("issue_id", type=int)
    p.add_argument("--resolution", default="")
    p.add_argument("--learnings", help="经验教训（必填，或使用 --skip-learnings）")
    p.add_argument("--skip-learnings", action="store_true", help="跳过经验沉淀（不推荐）")
    p.add_argument("--no-check-deliverable", action="store_true", help="跳过交付物检查（不推荐）")
    
    # stats
    sub.add_parser("stats")
    
    # sync
    sub.add_parser("sync")
    
    args = parser.parse_args()
    mgr = IssueManager()
    
    if args.cmd == "create":
        mgr.create(args.title, args.body, args.priority, args.labels)
    elif args.cmd == "list":
        issues = mgr.list_issues(args.status, args.labels, args.priority, getattr(args, 'assignee', None))
        print(f"\n{'='*50}")
        print(f"📋 {args.status} Issues ({len(issues)})")
        print(f"{'='*50}")
        for i in issues:
            labels_str = ", ".join(i.get("labels", []))
            print(f"  #{i['id']:03d} [{i['priority']}] {i['title']}")
            print(f"        {i['status']} | {i.get('assignee','?')} | {labels_str}")
    elif args.cmd == "show":
        issue = mgr.get(args.issue_id)
        if issue:
            print(issue.get("content", ""))
        else:
            print(f"❌ Issue #{args.issue_id} 不存在")
    elif args.cmd == "assign":
        mgr.assign(args.issue_id, args.assignee)
    elif args.cmd == "unassign":
        mgr.unassign(args.issue_id)
    elif args.cmd == "close":
        check_deliverable = not getattr(args, 'no_check_deliverable', False)
        learnings = getattr(args, 'learnings', None)
        skip_learnings = getattr(args, 'skip_learnings', False)
        mgr.close(args.issue_id, args.resolution, check_deliverable=check_deliverable, learnings=learnings, skip_learnings=skip_learnings)
    elif args.cmd == "sync":
        mgr.sync()
    elif args.cmd == "stats":
        s = mgr.stats()
        print(f"\n📊 Issue 统计")
        print(f"  总计: {s['total']} | 下一个 ID: #{s['next_id']}")
        for status, count in s["by_status"].items():
            print(f"  {status}: {count}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
