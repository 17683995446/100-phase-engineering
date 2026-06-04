"""
Phase 43 - 缓存策略与多级缓存测试
验证缓存功能是否正常工作
"""
import time
import unittest
from src.utils.cache_manager import (
    CacheStore,
    LRUCacheStore,
    MultiLevelCache,
    CacheManager,
    CacheLevel,
    get_cache_manager,
    cached
)


class TestCacheStore(unittest.TestCase):
    """缓存存储测试"""
    
    def setUp(self):
        """测试前设置"""
        self.cache = CacheStore("test", max_size=5)
    
    def test_set_and_get(self):
        """测试设置和获取"""
        self.cache.set("key1", "value1")
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        value = self.cache.get("nonexistent")
        self.assertIsNone(value)
    
    def test_delete(self):
        """测试删除"""
        self.cache.set("key1", "value1")
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        self.cache.set("key1", "value1", ttl=0.1)
        self.assertEqual(self.cache.get("key1"), "value1")
        time.sleep(0.2)
        self.assertIsNone(self.cache.get("key1"))
    
    def test_eviction(self):
        """测试淘汰"""
        for i in range(7):
            self.cache.set(f"key{i}", f"value{i}")
        
        # 应该只保留5个
        stats = self.cache.get_stats()
        self.assertEqual(stats["size"], 5)


class TestLRUCacheStore(unittest.TestCase):
    """LRU缓存测试"""
    
    def setUp(self):
        """测试前设置"""
        self.cache = LRUCacheStore("lru_test", max_size=3)
    
    def test_lru_order(self):
        """测试LRU顺序"""
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.set("c", 3)
        
        # 访问a，使其变为最近使用
        self.cache.get("a")
        
        # 添加d，应该淘汰b
        self.cache.set("d", 4)
        
        self.assertIsNotNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))  # 应该被淘汰
        self.assertIsNotNone(self.cache.get("c"))
        self.assertIsNotNone(self.cache.get("d"))


class TestMultiLevelCache(unittest.TestCase):
    """多级缓存测试"""
    
    def setUp(self):
        """测试前设置"""
        self.multi = MultiLevelCache()
        self.l1 = LRUCacheStore("L1", max_size=10)
        self.l2 = LRUCacheStore("L2", max_size=100)
        self.multi.add_level(CacheLevel.L1_MEMORY, self.l1)
        self.multi.add_level(CacheLevel.L2_LOCAL, self.l2)
    
    def test_multi_level_get(self):
        """测试多级获取"""
        # 只在L2设置
        self.l2.set("key1", "value1")
        
        # 从多级缓存获取，应该回填到L1
        value = self.multi.get("key1")
        self.assertEqual(value, "value1")
        
        # 验证L1也有
        self.assertEqual(self.l1.get("key1"), "value1")
    
    def test_multi_level_set(self):
        """测试多级设置"""
        self.multi.set("key1", "value1")
        
        # 验证所有级别都有
        self.assertEqual(self.l1.get("key1"), "value1")
        self.assertEqual(self.l2.get("key1"), "value1")
    
    def test_multi_level_delete(self):
        """测试多级删除"""
        self.multi.set("key1", "value1")
        self.multi.delete("key1")
        
        # 验证所有级别都删除
        self.assertIsNone(self.l1.get("key1"))
        self.assertIsNone(self.l2.get("key1"))


class TestCacheManager(unittest.TestCase):
    """缓存管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = CacheManager()
    
    def test_get_or_set(self):
        """测试获取或设置"""
        # 第一次应该调用工厂函数
        value = self.manager.get_or_set("key1", lambda: "computed")
        self.assertEqual(value, "computed")
        
        # 第二次应该直接返回缓存
        value = self.manager.get_or_set("key1", lambda: "other")
        self.assertEqual(value, "computed")
    
    def test_stats(self):
        """测试统计"""
        self.manager.set("key1", "value1")
        self.manager.get("key1")
        self.manager.get("key1")
        
        stats = self.manager.get_stats()
        self.assertIn("L1_MEMORY", stats)


class TestCachedDecorator(unittest.TestCase):
    """缓存装饰器测试"""
    
    def test_cached_function(self):
        """测试缓存装饰器"""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * x
        
        # 第一次调用
        result1 = expensive_function(5)
        self.assertEqual(result1, 25)
        self.assertEqual(call_count, 1)
        
        # 第二次调用，应该使用缓存
        result2 = expensive_function(5)
        self.assertEqual(result2, 25)
        self.assertEqual(call_count, 1)  # 没有增加


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 43 - 缓存策略与多级缓存测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCacheStore))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLRUCacheStore))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMultiLevelCache))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCacheManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCachedDecorator))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
