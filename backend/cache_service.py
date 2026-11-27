"""查询结果缓存：相同 SQL 直接返回，减少模型调用与数据库查询。

大厂实践：缓存key用 SQL 规范化后的哈希，导入数据时统一失效，
避免脏读。用 functools 实现进程内 LRU，零外部依赖。
"""
import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

import config


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    size: int = 0


class LRUCache:
    """线程安全的固定容量 LRU 缓存。"""

    def __init__(self, capacity: int = 200):
        if capacity < 1:
            raise ValueError('cache capacity 必须 >= 1')
        self.capacity = capacity
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._data:
                self._misses += 1
                return None
            value = self._data.pop(key)
            self._data[key] = value
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            self._data[key] = value
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(self._hits, self._misses, len(self._data))


# 全局缓存实例。默认关闭（评测需要真实调用模型），通过环境变量开启。
CACHE_ENABLED = config.settings.app_env != 'test'
cache = LRUCache(capacity=200)


def make_key(sql: str) -> str:
    """SQL 规范化后取哈希作为 key。"""
    normalized = ' '.join(sql.strip().lower().split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def get_cached(sql: str) -> Optional[dict]:
    if not CACHE_ENABLED:
        return None
    return cache.get(make_key(sql))


def set_cached(sql: str, value: dict) -> None:
    if CACHE_ENABLED:
        cache.set(make_key(sql), value)


def invalidate() -> None:
    """数据变更后调用，清空全部缓存。"""
    cache.clear()


def cache_info() -> dict:
    s = cache.stats()
    total = s.hits + s.misses
    return {
        'enabled': CACHE_ENABLED,
        'size': s.size,
        'hits': s.hits,
        'misses': s.misses,
        'hit_rate': round(s.hits / total, 4) if total else 0.0,
    }
