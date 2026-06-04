"""
缓存管理系统测试
遵循成本最小公理：验证缓存效果和命中率
"""

import time
import pytest

from src.utils.cache import (
    CacheStrategy,
    CacheLevel,
    CacheEntry,
    CacheStats,
    BaseCache,
    LRUCache,
    LFUCache,
    FIFOCache,
    MRUCache,
    RandomCache,
    create_cache,
    CacheManager,
    cached,
    cache_result,
    invalidate_cache,
    invalidate_pattern,
    get_default_cache_manager,
)


class TestCacheEntry:
    """缓存条目测试"""

    def test_create_cache_entry(self):
        """测试创建缓存条目"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=time.time()
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0

    def test_cache_entry_with_expiry(self):
        """测试带过期时间的缓存条目"""
        entry = CacheEntry(
            key="expiring",
            value="value",
            created_at=time.time(),
            expires_at=time.time() + 3600
        )
        assert entry.expires_at is not None


class TestCacheStats:
    """缓存统计测试"""

    def test_initial_stats(self):
        """测试初始统计"""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    def test_calculate_hit_rate(self):
        """测试计算命中率"""
        stats = CacheStats(hits=70, misses=30)
        rate = stats.calculate_hit_rate()
        assert rate == 0.7

    def test_hit_rate_zero(self):
        """测试零命中率"""
        stats = CacheStats(hits=0, misses=0)
        rate = stats.calculate_hit_rate()
        assert rate == 0.0


class TestLRUCache:
    """LRU缓存测试"""

    def test_basic_set_get(self):
        """测试基本设置和获取"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_eviction(self):
        """测试淘汰机制"""
        cache = LRUCache(max_size=3)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.set("3", "3")
        cache.set("4", "4")
        assert cache.get("1") is None
        assert cache.get("4") == "4"

    def test_lru_ordering(self):
        """测试LRU顺序"""
        cache = LRUCache(max_size=3)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.set("3", "3")
        cache.get("1")  # 访问1，使其变为最近使用
        cache.set("4", "4")
        assert cache.get("1") == "1"
        assert cache.get("2") is None

    def test_ttl(self):
        """测试TTL"""
        cache = LRUCache(max_size=10, default_ttl=0.1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_delete(self):
        """测试删除"""
        cache = LRUCache(max_size=10)
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None

    def test_clear(self):
        """测试清空"""
        cache = LRUCache(max_size=10)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.clear()
        assert cache.get("1") is None
        assert cache.get_stats().current_size == 0

    def test_has(self):
        """测试检查存在"""
        cache = LRUCache(max_size=10)
        cache.set("key", "value")
        assert cache.has("key") is True
        assert cache.has("nonexistent") is False

    def test_stats(self):
        """测试统计"""
        cache = LRUCache(max_size=10)
        cache.set("1", "1")
        cache.get("1")
        cache.get("2")
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1


class TestLFUCache:
    """LFU缓存测试"""

    def test_basic_set_get(self):
        """测试基本操作"""
        cache = LFUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_lfu_eviction(self):
        """测试LFU淘汰"""
        cache = LFUCache(max_size=3)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.set("3", "3")
        cache.get("2")  # 访问2一次
        cache.get("3")  # 访问3两次
        cache.get("3")
        cache.set("4", "4")
        assert cache.get("1") is None
        assert cache.get("3") == "3"

    def test_clear(self):
        """测试清空"""
        cache = LFUCache(max_size=10)
        cache.set("1", "1")
        cache.clear()
        assert cache.get("1") is None


class TestFIFOCache:
    """FIFO缓存测试"""

    def test_basic_operations(self):
        """测试基本操作"""
        cache = FIFOCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_fifo_eviction(self):
        """测试FIFO淘汰"""
        cache = FIFOCache(max_size=3)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.set("3", "3")
        cache.set("4", "4")
        assert cache.get("1") is None
        assert cache.get("4") == "4"


class TestMRUCache:
    """MRU缓存测试"""

    def test_basic_operations(self):
        """测试基本操作"""
        cache = MRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_mru_eviction(self):
        """测试MRU淘汰"""
        cache = MRUCache(max_size=3)
        cache.set("1", "1")
        cache.set("2", "2")
        cache.set("3", "3")
        cache.get("3")  # 访问3
        cache.set("4", "4")
        assert cache.get("3") is None
        assert cache.get("2") == "2"


class TestRandomCache:
    """Random缓存测试"""

    def test_basic_operations(self):
        """测试基本操作"""
        cache = RandomCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_eviction(self):
        """测试随机淘汰（只验证缓存大小）"""
        cache = RandomCache(max_size=5)
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")
        assert len(cache.keys()) <= 5


class TestCreateCache:
    """创建缓存测试"""

    def test_create_all_strategies(self):
        """测试创建所有策略"""
        for strategy in CacheStrategy:
            cache = create_cache(strategy, max_size=100)
            cache.set("test", "value")
            assert cache.get("test") == "value"


class TestCacheManager:
    """缓存管理器测试"""

    def test_register_and_get_cache(self):
        """测试注册和获取缓存"""
        manager = CacheManager()
        cache = manager.register_cache("test_cache", CacheStrategy.LRU, max_size=10)
        assert cache is not None
        assert manager.get_cache("test_cache") is cache

    def test_get_or_create(self):
        """测试获取或创建"""
        manager = CacheManager()
        cache1 = manager.get_or_create_cache("my_cache")
        cache2 = manager.get_or_create_cache("my_cache")
        assert cache1 is cache2

    def test_list_caches(self):
        """测试列出缓存"""
        manager = CacheManager()
        manager.register_cache("cache1")
        manager.register_cache("cache2")
        assert "cache1" in manager.list_caches()
        assert "cache2" in manager.list_caches()

    def test_get_all_stats(self):
        """测试获取所有统计"""
        manager = CacheManager()
        cache = manager.register_cache("stats_cache")
        cache.set("key", "value")
        stats = manager.get_all_stats()
        assert "stats_cache" in stats

    def test_clear_all(self):
        """测试清空所有"""
        manager = CacheManager()
        cache1 = manager.register_cache("cache1")
        cache2 = manager.register_cache("cache2")
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")
        manager.clear_all()
        assert cache1.get("key1") is None
        assert cache2.get("key2") is None

    def test_unregister_cache(self):
        """测试注销缓存"""
        manager = CacheManager()
        manager.register_cache("to_unregister")
        assert manager.unregister_cache("to_unregister") is True
        assert manager.get_cache("to_unregister") is None


class TestDecorators:
    """装饰器测试"""

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        call_count = [0]

        @cached(name="decorator_test", max_size=10)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2

        assert expensive_function(5) == 10
        assert call_count[0] == 1
        assert expensive_function(5) == 10
        assert call_count[0] == 1

    def test_cache_result_decorator(self):
        """测试cache_result装饰器"""
        cache = LRUCache(max_size=10)
        call_count = [0]

        @cache_result(cache=cache)
        def another_function(x):
            call_count[0] += 1
            return x * 3

        assert another_function(5) == 15
        assert call_count[0] == 1
        assert another_function(5) == 15
        assert call_count[0] == 1


class TestCacheInvalidation:
    """缓存失效测试"""

    def test_invalidate_cache(self):
        """测试失效指定缓存"""
        manager = CacheManager()
        cache = manager.register_cache("invalidate_me")
        cache.set("key", "value")
        assert invalidate_cache("invalidate_me", manager) is True
        assert cache.get("key") is None

    def test_invalidate_pattern(self):
        """测试按模式失效"""
        manager = CacheManager()
        cache1 = manager.register_cache("user_data_1")
        cache2 = manager.register_cache("user_data_2")
        cache3 = manager.register_cache("other_cache")
        cache1.set("k", "v")
        cache2.set("k", "v")
        cache3.set("k", "v")
        invalidate_pattern("user_data", manager)
        assert cache1.get("k") is None
        assert cache2.get("k") is None
        assert cache3.get("k") == "v"


class TestDefaultManager:
    """默认管理器测试"""

    def test_get_default_manager(self):
        """测试获取默认管理器"""
        manager1 = get_default_cache_manager()
        manager2 = get_default_cache_manager()
        assert manager1 is manager2


class TestIntegration:
    """集成测试"""

    def test_multiple_levels(self):
        """测试多级缓存"""
        manager = CacheManager()
        l1_cache = manager.register_cache("l1", level=CacheLevel.L1, max_size=100)
        l2_cache = manager.register_cache("l2", level=CacheLevel.L2, max_size=1000)

        for i in range(10):
            l1_cache.set(f"k{i}", f"v{i}")
            l2_cache.set(f"k{i}", f"v{i}")

        assert l1_cache.get_stats().current_size == 10
        assert l2_cache.get_stats().current_size == 10

    def test_hit_rate_improvement(self):
        """测试命中率改善"""
        cache = LRUCache(max_size=100)

        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        for _ in range(100):
            cache.get("key0")
            cache.get("key1")

        stats = cache.get_stats()
        assert stats.hit_rate > 0.5


def test_thread_safety():
    """测试线程安全（简单测试）"""
    import threading
    cache = LRUCache(max_size=1000)
    errors = []

    def writer():
        try:
            for i in range(100):
                cache.set(f"w{i}", i)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for i in range(100):
                cache.get(f"r{i}")
        except Exception as e:
            errors.append(e)

    threads = []
    for _ in range(5):
        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        threads.extend([t1, t2])

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0
