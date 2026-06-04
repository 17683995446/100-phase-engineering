"""
Phase 45 - 分布式锁与并发控制测试
验证锁功能是否正常工作
"""
import time
import threading
import unittest
from src.utils.distributed_lock import (
    DistributedLock,
    LockManager,
    Semaphore,
    RateLimiter,
    get_lock_manager,
    synchronized
)


class TestDistributedLock(unittest.TestCase):
    """分布式锁测试"""
    
    def test_acquire_and_release(self):
        """测试获取和释放锁"""
        lock = DistributedLock("test_resource", timeout=5.0)
        
        self.assertTrue(lock.acquire())
        self.assertTrue(lock.is_locked())
        
        self.assertTrue(lock.release())
        self.assertFalse(lock.is_locked())
    
    def test_context_manager(self):
        """测试上下文管理器"""
        lock = DistributedLock("test_resource", timeout=5.0)
        
        with lock():
            self.assertTrue(lock.is_locked())
        
        self.assertFalse(lock.is_locked())
    
    def test_timeout(self):
        """测试锁超时功能"""
        lock = DistributedLock("timeout_resource", timeout=0.1)
        
        # 获取锁
        self.assertTrue(lock.acquire())
        self.assertTrue(lock.is_locked())
        
        # 释放锁
        self.assertTrue(lock.release())
        self.assertFalse(lock.is_locked())
        
        # 再次获取应该成功
        self.assertTrue(lock.acquire(blocking=False))
        self.assertTrue(lock.is_locked())
        lock.release()


class TestLockManager(unittest.TestCase):
    """锁管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = LockManager()
    
    def test_get_lock(self):
        """测试获取锁"""
        lock = self.manager.get_lock("resource1")
        self.assertIsNotNone(lock)
        
        # 再次获取应该返回同一个锁
        lock2 = self.manager.get_lock("resource1")
        self.assertEqual(lock, lock2)
    
    def test_lock_context(self):
        """测试锁上下文"""
        with self.manager.lock("resource2", timeout=5.0) as lock:
            self.assertTrue(lock.is_locked())
        
        # 锁应该已释放
        lock = self.manager.get_lock("resource2")
        self.assertFalse(lock.is_locked())


class TestSemaphore(unittest.TestCase):
    """信号量测试"""
    
    def test_acquire_and_release(self):
        """测试获取和释放信号量"""
        sem = Semaphore("test_sem", max_concurrent=2)
        
        self.assertTrue(sem.acquire())
        self.assertTrue(sem.acquire())
        
        stats = sem.get_stats()
        self.assertEqual(stats["active_count"], 2)
        
        sem.release()
        sem.release()
    
    def test_max_concurrent(self):
        """测试最大并发数"""
        sem = Semaphore("test_sem2", max_concurrent=1)
        
        self.assertTrue(sem.acquire())
        self.assertFalse(sem.acquire(blocking=False))
        
        sem.release()


class TestRateLimiter(unittest.TestCase):
    """速率限制器测试"""
    
    def test_rate_limit(self):
        """测试速率限制"""
        limiter = RateLimiter("test", max_requests=3, window_seconds=1.0)
        
        # 前3次应该允许
        self.assertTrue(limiter.is_allowed("user1"))
        self.assertTrue(limiter.is_allowed("user1"))
        self.assertTrue(limiter.is_allowed("user1"))
        
        # 第4次应该拒绝
        self.assertFalse(limiter.is_allowed("user1"))
    
    def test_window_reset(self):
        """测试窗口重置"""
        limiter = RateLimiter("test", max_requests=1, window_seconds=0.1)
        
        self.assertTrue(limiter.is_allowed("user2"))
        self.assertFalse(limiter.is_allowed("user2"))
        
        # 等待窗口过期
        time.sleep(0.2)
        
        self.assertTrue(limiter.is_allowed("user2"))
    
    def test_remaining(self):
        """测试剩余请求数"""
        limiter = RateLimiter("test", max_requests=5, window_seconds=60.0)
        
        self.assertEqual(limiter.get_remaining("user3"), 5)
        
        limiter.is_allowed("user3")
        self.assertEqual(limiter.get_remaining("user3"), 4)


class TestSynchronizedDecorator(unittest.TestCase):
    """同步装饰器测试"""
    
    def test_synchronized(self):
        """测试同步装饰器"""
        counter = {"value": 0}
        
        @synchronized(resource="counter_test", timeout=5.0)
        def increment():
            counter["value"] += 1
        
        # 多线程并发执行
        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(counter["value"], 10)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 45 - 分布式锁与并发控制测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDistributedLock))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLockManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSemaphore))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRateLimiter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSynchronizedDecorator))
    
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
