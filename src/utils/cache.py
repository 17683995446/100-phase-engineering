"""
缓存管理系统
遵循成本最小公理：计算结果复用，降低重复计算成本
"""

import time
import hashlib
import threading
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import wraps
import copy
import heapq

from src.utils.logger import logger


T = TypeVar('T')


class CacheStrategy(Enum):
    """缓存淘汰策略"""
    LRU = auto()       # 最近最少使用
    LFU = auto()       # 最不经常使用
    FIFO = auto()      # 先进先出
    MRU = auto()       # 最近使用
    RANDOM = auto()    # 随机淘汰


class CacheLevel(Enum):
    """缓存层级"""
    L1 = auto()        # 一级缓存（内存）
    L2 = auto()        # 二级缓存
    L3 = auto()        # 三级缓存


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    key: str
    value: T
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    sets: int = 0
    deletes: int = 0
    max_size: int = 0
    current_size: int = 0
    hit_rate: float = 0.0

    def calculate_hit_rate(self) -> float:
        """计算命中率"""
        total = self.hits + self.misses
        if total > 0:
            self.hit_rate = self.hits / total
        else:
            self.hit_rate = 0.0
        return self.hit_rate


class BaseCache(Generic[T]):
    """缓存基类"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                return None

            if entry.expires_at is not None and time.time() > entry.expires_at:
                self._stats.misses += 1
                del self._cache[key]
                return None

            entry.access_count += 1
            entry.last_accessed = time.time()
            self._update_access_order(key)
            self._stats.hits += 1
            self._stats.current_size = len(self._cache)
            self._stats.calculate_hit_rate()
            return copy.deepcopy(entry.value)

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                entry.value = value
                entry.last_accessed = time.time()
                entry.access_count += 1
            else:
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    access_count=1,
                    last_accessed=time.time()
                )

            if ttl is not None:
                entry.expires_at = time.time() + ttl
            elif self.default_ttl is not None:
                entry.expires_at = time.time() + self.default_ttl

            self._cache[key] = entry
            self._stats.sets += 1
            self._stats.current_size = len(self._cache)

            if len(self._cache) > self.max_size:
                self._evict()

            self._update_insert_order(key)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                self._stats.current_size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()

    def has(self, key: str) -> bool:
        """检查缓存是否存在"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.expires_at is not None and time.time() > entry.expires_at:
                del self._cache[key]
                return False
            return True

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        return copy.deepcopy(self._stats)

    def keys(self) -> List[str]:
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())

    def _evict(self) -> None:
        """淘汰缓存项（子类实现）"""
        raise NotImplementedError

    def _update_access_order(self, key: str) -> None:
        """更新访问顺序（子类实现）"""
        pass

    def _update_insert_order(self, key: str) -> None:
        """更新插入顺序（子类实现）"""
        pass


class LRUCache(BaseCache[T]):
    """LRU (Least Recently Used) 缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        super().__init__(max_size, default_ttl)
        self._order: OrderedDict = OrderedDict()

    def _update_access_order(self, key: str) -> None:
        if key in self._order:
            self._order.move_to_end(key)

    def _update_insert_order(self, key: str) -> None:
        if key in self._order:
            self._order.move_to_end(key)
        else:
            self._order[key] = None

    def _evict(self) -> None:
        if self._order:
            evicted_key = next(iter(self._order))
            del self._cache[evicted_key]
            del self._order[evicted_key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)

    def delete(self, key: str) -> bool:
        if key in self._order:
            del self._order[key]
        return super().delete(key)

    def clear(self) -> None:
        self._order.clear()
        super().clear()


class LFUCache(BaseCache[T]):
    """LFU (Least Frequently Used) 缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        super().__init__(max_size, default_ttl)
        self._frequency: Dict[str, int] = {}

    def _update_access_order(self, key: str) -> None:
        self._frequency[key] = self._frequency.get(key, 0) + 1

    def _update_insert_order(self, key: str) -> None:
        self._frequency[key] = 1

    def _evict(self) -> None:
        if not self._frequency:
            return

        min_freq = min(self._frequency.values())
        candidates = [k for k, v in self._frequency.items() if v == min_freq]

        if candidates:
            evicted_key = candidates[0]
            del self._cache[evicted_key]
            del self._frequency[evicted_key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)

    def delete(self, key: str) -> bool:
        if key in self._frequency:
            del self._frequency[key]
        return super().delete(key)

    def clear(self) -> None:
        self._frequency.clear()
        super().clear()


class FIFOCache(BaseCache[T]):
    """FIFO (First In First Out) 缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        super().__init__(max_size, default_ttl)
        self._order: List[str] = []

    def _update_insert_order(self, key: str) -> None:
        if key not in self._order:
            self._order.append(key)

    def _evict(self) -> None:
        if self._order:
            evicted_key = self._order.pop(0)
            if evicted_key in self._cache:
                del self._cache[evicted_key]
                self._stats.evictions += 1
                self._stats.current_size = len(self._cache)

    def delete(self, key: str) -> bool:
        if key in self._order:
            self._order.remove(key)
        return super().delete(key)

    def clear(self) -> None:
        self._order.clear()
        super().clear()


class MRUCache(BaseCache[T]):
    """MRU (Most Recently Used) 缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        super().__init__(max_size, default_ttl)
        self._order: OrderedDict = OrderedDict()

    def _update_access_order(self, key: str) -> None:
        if key in self._order:
            self._order.move_to_end(key)

    def _update_insert_order(self, key: str) -> None:
        if key in self._order:
            self._order.move_to_end(key)
        else:
            self._order[key] = None

    def _evict(self) -> None:
        if self._order:
            evicted_key = next(reversed(self._order))
            del self._cache[evicted_key]
            del self._order[evicted_key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)

    def delete(self, key: str) -> bool:
        if key in self._order:
            del self._order[key]
        return super().delete(key)

    def clear(self) -> None:
        self._order.clear()
        super().clear()


class RandomCache(BaseCache[T]):
    """Random 缓存"""

    import random
    _random = random

    def _evict(self) -> None:
        if self._cache:
            import random
            evicted_key = random.choice(list(self._cache.keys()))
            del self._cache[evicted_key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)


def create_cache(strategy: CacheStrategy, max_size: int = 1000, default_ttl: Optional[int] = None) -> BaseCache:
    """创建缓存实例"""
    if strategy == CacheStrategy.LRU:
        return LRUCache(max_size, default_ttl)
    elif strategy == CacheStrategy.LFU:
        return LFUCache(max_size, default_ttl)
    elif strategy == CacheStrategy.FIFO:
        return FIFOCache(max_size, default_ttl)
    elif strategy == CacheStrategy.MRU:
        return MRUCache(max_size, default_ttl)
    elif strategy == CacheStrategy.RANDOM:
        return RandomCache(max_size, default_ttl)
    else:
        return LRUCache(max_size, default_ttl)


class CacheManager:
    """缓存管理器 - 多级缓存统一管理"""

    def __init__(self):
        self._caches: Dict[str, BaseCache] = {}
        self._levels: Dict[CacheLevel, Dict[str, BaseCache]] = {
            CacheLevel.L1: {},
            CacheLevel.L2: {},
            CacheLevel.L3: {}
        }

    def register_cache(
        self,
        name: str,
        strategy: CacheStrategy = CacheStrategy.LRU,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        level: CacheLevel = CacheLevel.L1
    ) -> BaseCache:
        """注册缓存"""
        cache = create_cache(strategy, max_size, default_ttl)
        self._caches[name] = cache
        self._levels[level][name] = cache
        return cache

    def get_cache(self, name: str) -> Optional[BaseCache]:
        """获取缓存"""
        return self._caches.get(name)

    def get_or_create_cache(
        self,
        name: str,
        strategy: CacheStrategy = CacheStrategy.LRU,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        level: CacheLevel = CacheLevel.L1
    ) -> BaseCache:
        """获取或创建缓存"""
        if name in self._caches:
            return self._caches[name]
        return self.register_cache(name, strategy, max_size, default_ttl, level)

    def list_caches(self) -> List[str]:
        """列出所有缓存"""
        return list(self._caches.keys())

    def get_all_stats(self) -> Dict[str, CacheStats]:
        """获取所有缓存统计"""
        return {name: cache.get_stats() for name, cache in self._caches.items()}

    def clear_all(self) -> None:
        """清空所有缓存"""
        for cache in self._caches.values():
            cache.clear()

    def unregister_cache(self, name: str) -> bool:
        """注销缓存"""
        if name not in self._caches:
            return False

        cache = self._caches[name]
        del self._caches[name]

        for level in self._levels.values():
            if name in level:
                del level[name]

        return True


def _generate_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键"""
    key_parts = [func_name]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()


_default_cache_manager = CacheManager()


def cached(
    name: Optional[str] = None,
    strategy: CacheStrategy = CacheStrategy.LRU,
    max_size: int = 1000,
    ttl: Optional[int] = None,
    cache_manager: Optional[CacheManager] = None
):
    """缓存装饰器"""

    manager = cache_manager or _default_cache_manager

    def decorator(func: Callable) -> Callable:

        cache_name = name or func.__name__
        cache = manager.get_or_create_cache(cache_name, strategy, max_size, ttl)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = _generate_key(func.__name__, args, kwargs)
            cached_value = cache.get(key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_name}::{key}")
                return cached_value

            logger.debug(f"Cache miss: {cache_name}::{key}")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator


def cache_result(
    cache: BaseCache,
    ttl: Optional[int] = None,
    key_prefix: str = ""
):
    """基于指定缓存的装饰器"""

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{key_prefix}{_generate_key(func.__name__, args, kwargs)}"
            cached_value = cache.get(key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {key_prefix}::{key}")
                return cached_value

            logger.debug(f"Cache miss: {key_prefix}::{key}")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_pattern(pattern: str, cache_manager: Optional[CacheManager] = None):
    """按模式失效缓存"""
    manager = cache_manager or _default_cache_manager

    for cache_name, cache in manager._caches.items():
        if pattern in cache_name:
            cache.clear()
            logger.info(f"Cache invalidated: {cache_name}")


def invalidate_cache(name: str, cache_manager: Optional[CacheManager] = None) -> bool:
    """失效指定缓存"""
    manager = cache_manager or _default_cache_manager
    cache = manager.get_cache(name)

    if cache:
        cache.clear()
        logger.info(f"Cache cleared: {name}")
        return True

    return False


def get_default_cache_manager() -> CacheManager:
    """获取默认缓存管理器"""
    return _default_cache_manager
