"""Memory-Like-A-Tree 核心模块"""

from .config import Config, get_config
from .db import (
    load_db, save_db, get_memory, set_memory,
    get_all_memories, get_stats, content_hash
)

__version__ = "1.0.0"
__all__ = [
    "Config",
    "get_config",
    "load_db",
    "save_db",
    "get_memory",
    "set_memory",
    "get_all_memories",
    "get_stats",
    "content_hash",
]
