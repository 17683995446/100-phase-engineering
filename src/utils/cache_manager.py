"""
缓存策略与多级缓存
提供多级缓存管理、缓存策略和缓存失效机制
"""
import time
import threading
import hashlib
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from collections import OrderedDict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = auto()    # 内存缓存
    L2_LOCAL = auto()     # 本地缓存（文件/磁盘）
    L3_DISTRIBUTED = auto()  # 分布式缓存


class EvictionPolicy(Enum):
    """淘汰策略"""
    LRU = auto()    # 最近最少使用
    LFU = auto()    # 最少使用频率
    TTL = auto()    # 生存时间
    FIFO = auto()   # 先进先出


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def touch(self) -> None:
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheStore:
    """缓存存储基类"""
    
    def __init__(self, name: str, max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._logger = get_logger(f"cache.{name}")
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._miss_count += 1
                return None
            
            if entry.is_expired():
                del self._store[key]
                self._miss_count += 1
                return None
            
            entry.touch()
            self._hit_count += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        with self._lock:
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at
            )
            
            self._store[key] = entry
            
            # 检查是否需要淘汰
            if len(self._store) > self.max_size:
                self._evict()
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._store.clear()
    
    def _evict(self) -> None:
        """淘汰缓存"""
        # 默认LRU策略
        if self._store:
            oldest_key = min(
                self._store.keys(),
                key=lambda k: self._store[k].last_accessed
            )
            del self._store[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total if total > 0 else 0
            
            return {
                "name": self.name,
                "size": len(self._store),
                "max_size": self.max_size,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": hit_rate,
                "eviction_policy": "LRU"
            }


class LRUCacheStore(CacheStore):
    """LRU缓存存储"""
    
    def __init__(self, name: str, max_size: int = 1000):
        super().__init__(name, max_size)
        self._store = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（LRU）"""
        with self._lock:
            if key not in self._store:
                self._miss_count += 1
                return None
            
            entry = self._store[key]
            if entry.is_expired():
                del self._store[key]
                self._miss_count += 1
                return None
            
            # 移动到末尾（最近使用）
            self._store.move_to_end(key)
            entry.touch()
            self._hit_count += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值（LRU）"""
        with self._lock:
            if key in self._store:
                # 更新现有值
                self._store.move_to_end(key)
                self._store[key].value = value
                if ttl is not None:
                    self._store[key].expires_at = time.time() + ttl
            else:
                expires_at = None
                if ttl is not None:
                    expires_at = time.time() + ttl
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    expires_at=expires_at
                )
                self._store[key] = entry
            
            # 淘汰最旧的
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)
    
    def _evict(self) -> None:
        """LRU淘汰"""
        if self._store:
            self._store.popitem(last=False)


class MultiLevelCache:
    """多级缓存"""
    
    def __init__(self):
        self._caches: Dict[CacheLevel, CacheStore] = {}
        self._logger = get_logger("cache.multilevel")
        self._lock = threading.RLock()
    
    def add_level(self, level: CacheLevel, cache: CacheStore) -> None:
        """添加缓存级别"""
        with self._lock:
            self._caches[level] = cache
            self._logger.info(f"Added cache level: {level.name}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（从多级缓存）"""
        with self._lock:
            # 从L1到L3依次查找
            for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_LOCAL, CacheLevel.L3_DISTRIBUTED]:
                if level in self._caches:
                    value = self._caches[level].get(key)
                    if value is not None:
                        # 回填到更高级别
                        self._backfill(key, value, level)
                        return value
            
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值（到多级缓存）"""
        with self._lock:
            for level, cache in self._caches.items():
                cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存（从多级缓存）"""
        with self._lock:
            deleted = False
            for cache in self._caches.values():
                if cache.delete(key):
                    deleted = True
            return deleted
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()
    
    def _backfill(self, key: str, value: Any, found_level: CacheLevel) -> None:
        """回填缓存到更高级别"""
        levels_order = [CacheLevel.L1_MEMORY, CacheLevel.L2_LOCAL, CacheLevel.L3_DISTRIBUTED]
        found_index = levels_order.index(found_level)
        
        # 回填到更高级别的缓存
        for i in range(found_index):
            level = levels_order[i]
            if level in self._caches:
                self._caches[level].set(key, value)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计"""
        with self._lock:
            return {
                level.name: cache.get_stats()
                for level, cache in self._caches.items()
            }


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self._multi_level = MultiLevelCache()
        self._local_cache = LRUCacheStore("local", max_size=1000)
        self._multi_level.add_level(CacheLevel.L1_MEMORY, self._local_cache)
        self._logger = get_logger("cache.manager")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        return self._multi_level.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存"""
        self._multi_level.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self._multi_level.delete(key)
    
    def clear(self) -> None:
        """清空缓存"""
        self._multi_level.clear()
    
    def get_or_set(self, key: str, default_factory: Callable, ttl: Optional[float] = None) -> Any:
        """获取或设置缓存"""
        value = self.get(key)
        if value is None:
            value = default_factory()
            self.set(key, value, ttl)
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self._multi_level.get_stats()


# 全局实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: Optional[float] = None, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.append(str(args))
            if kwargs:
                key_parts.append(str(sorted(kwargs.items())))
            
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # 尝试获取缓存
            value = cache.get(cache_key)
            if value is not None:
                return value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
