#!/usr/bin/env python3
"""
Memory-Like-A-Tree 配置管理

支持：
- 配置文件
- 环境变量
- 默认值
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置管理器"""
    
    _instance = None
    _config = None
    
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        
        # 路径配置
        "paths": {
            "base_dir": "~/.memory-like-a-tree",
            "data_dir": "~/.memory-like-a-tree/data",
            "archive_dir": "~/.memory-like-a-tree/data/archive",
            "obsidian_vault": None  # 可选
        },
        
        # Agent 配置
        "agents": [
            {
                "name": "default",
                "workspace": "~/.memory-like-a-tree/workspace",
                "memory_file": "MEMORY.md",
                "memory_dir": "memory"
            }
        ],
        
        # 置信度配置
        "confidence": {
            "initial": 0.7,
            "min": 0.05,
            "max": 1.0,
            "search_boost": 0.03,
            "use_boost": 0.08,
            "confirm_value": 0.95
        },
        
        # 衰减配置
        "decay": {
            "grace_period_days": 60,
            "rates": {
                "P0": 0.0,
                "P1": 0.004,
                "P2": 0.008
            }
        },
        
        # 清理配置
        "cleanup": {
            "archive_threshold": 0.3,
            "auto_cleanup_threshold": 0.05,
            "review_threshold": 0.1
        },
        
        # 同步配置
        "sync": {
            "enabled": False,
            "interval_hours": 2
        }
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """加载配置"""
        self._config = self.DEFAULT_CONFIG.copy()
        
        # 查找配置文件
        config_paths = [
            Path.cwd() / "memory-like-a-tree.json",
            Path.cwd() / "config.json",
            Path.home() / ".memory-like-a-tree" / "config.json",
            Path(os.environ.get("MLAT_CONFIG", "")) if os.environ.get("MLAT_CONFIG") else None
        ]
        
        for config_path in config_paths:
            if config_path and config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._merge_config(file_config)
                break
        
        # 环境变量覆盖
        self._apply_env_overrides()
        
        # 展开路径
        self._expand_paths()
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """深度合并配置"""
        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = deep_merge(self._config, new_config)
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_map = {
            "MLAT_BASE_DIR": ("paths", "base_dir"),
            "MLAT_DATA_DIR": ("paths", "data_dir"),
            "MLAT_OBSIDIAN_VAULT": ("paths", "obsidian_vault"),
            "MLAT_GRACE_PERIOD": ("decay", "grace_period_days"),
        }
        
        for env_var, path in env_map.items():
            value = os.environ.get(env_var)
            if value:
                if len(path) == 2:
                    if path[1] == "grace_period_days":
                        self._config[path[0]][path[1]] = int(value)
                    else:
                        self._config[path[0]][path[1]] = value
    
    def _expand_paths(self):
        """展开路径中的 ~"""
        for key in ["base_dir", "data_dir", "archive_dir", "obsidian_vault"]:
            if self._config["paths"].get(key):
                self._config["paths"][key] = str(Path(self._config["paths"][key]).expanduser())
        
        for agent in self._config["agents"]:
            if agent.get("workspace"):
                agent["workspace"] = str(Path(agent["workspace"]).expanduser())
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    @property
    def base_dir(self) -> Path:
        return Path(self._config["paths"]["base_dir"])
    
    @property
    def data_dir(self) -> Path:
        return Path(self._config["paths"]["data_dir"])
    
    @property
    def archive_dir(self) -> Path:
        return Path(self._config["paths"]["archive_dir"])
    
    @property
    def obsidian_vault(self) -> Optional[Path]:
        vault = self._config["paths"].get("obsidian_vault")
        return Path(vault) if vault else None
    
    @property
    def agents(self) -> list:
        return self._config["agents"]
    
    @property
    def confidence(self) -> dict:
        return self._config["confidence"]
    
    @property
    def decay(self) -> dict:
        return self._config["decay"]
    
    @property
    def cleanup(self) -> dict:
        return self._config["cleanup"]
    
    @property
    def sync(self) -> dict:
        return self._config["sync"]
    
    def get_agent(self, name: str) -> Optional[dict]:
        """获取指定 Agent 配置"""
        for agent in self.agents:
            if agent["name"] == name:
                return agent
        return None
    
    def get_agent_workspace(self, name: str) -> Optional[Path]:
        """获取 Agent 的 workspace 路径"""
        agent = self.get_agent(name)
        if agent:
            return Path(agent["workspace"])
        return None
    
    def to_dict(self) -> dict:
        """导出配置"""
        return self._config.copy()
    
    def save(self, path: str = None):
        """保存配置到文件"""
        save_path = Path(path) if path else self.base_dir / "config.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def reload(cls):
        """重新加载配置"""
        cls._config = None
        cls._instance = None
        return cls()


# 全局配置实例
def get_config() -> Config:
    return Config()
