"""
Phase 74 - 限流熔断器系统测试
验证熔断、限流、降级和自适应保护功能
"""
import time
import unittest
from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    TokenBucket,
    SlidingWindow,
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    AdaptiveRateLimiter,
    Bulkhead,
    BulkheadFull,
    get_circuit_breaker,
    get_rate_limiter
)


class TestCircuitBreaker(unittest.TestCase):
    """熔断器测试"""

    def setUp(self):
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=0.1,
            half_open_max_calls=2
        )
        self.cb = CircuitBreaker("test", self.config)

    def test_successful_calls(self):
        """测试成功调用"""
        result = self.cb.call(lambda: "success")
        self.assertEqual(result, "success")
        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

    def test_open_after_failures(self):
        """测试失败后熔断"""
        for _ in range(3):
            try:
                self.cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass

        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)
        with self.assertRaises(CircuitBreakerOpen):
            self.cb.call(lambda: "success")

    def test_half_open_recovery(self):
        """测试半开恢复"""
        for _ in range(3):
            try:
                self.cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass

        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)
        time.sleep(0.15)

        # 半开状态下成功调用
        self.cb.call(lambda: "success")
        self.cb.call(lambda: "success")
        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

    def test_reset(self):
        """测试手动重置"""
        for _ in range(3):
            try:
                self.cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass

        self.cb.reset()
        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

    def test_stats(self):
        """测试统计信息"""
        self.cb.call(lambda: "success")
        stats = self.cb.get_stats()
        self.assertEqual(stats["state"], "closed")
        self.assertEqual(stats["name"], "test")


class TestTokenBucket(unittest.TestCase):
    """令牌桶测试"""

    def test_consume(self):
        """测试消费令牌"""
        bucket = TokenBucket(max_tokens=5, refill_rate=1)
        self.assertTrue(bucket.consume(1))
        self.assertTrue(bucket.consume(4))
        self.assertFalse(bucket.consume(1))

    def test_refill(self):
        """测试令牌补充"""
        bucket = TokenBucket(max_tokens=2, refill_rate=10)
        bucket.consume(2)
        self.assertFalse(bucket.consume(1))
        time.sleep(0.2)
        self.assertTrue(bucket.consume(1))


class TestSlidingWindow(unittest.TestCase):
    """滑动窗口测试"""

    def test_allow(self):
        """测试允许请求"""
        window = SlidingWindow(window_seconds=1, max_requests=2)
        self.assertTrue(window.allow())
        self.assertTrue(window.allow())
        self.assertFalse(window.allow())

    def test_window_slide(self):
        """测试窗口滑动"""
        window = SlidingWindow(window_seconds=0.1, max_requests=1)
        self.assertTrue(window.allow())
        self.assertFalse(window.allow())
        time.sleep(0.15)
        self.assertTrue(window.allow())


class TestRateLimiter(unittest.TestCase):
    """限流器测试"""

    def test_token_bucket_limiter(self):
        """测试令牌桶限流器"""
        config = RateLimitConfig(
            max_requests=2,
            window_seconds=1,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter("test", config)
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())

    def test_sliding_window_limiter(self):
        """测试滑动窗口限流器"""
        config = RateLimitConfig(
            max_requests=2,
            window_seconds=1,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        limiter = RateLimiter("test2", config)
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())

    def test_stats(self):
        """测试统计信息"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        limiter = RateLimiter("test3", config)
        stats = limiter.get_stats()
        self.assertEqual(stats["name"], "test3")
        self.assertEqual(stats["max_requests"], 10)


class TestAdaptiveRateLimiter(unittest.TestCase):
    """自适应限流器测试"""

    def test_allow(self):
        """测试允许请求"""
        limiter = AdaptiveRateLimiter("test", initial_limit=2)
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())

    def test_adapt_up(self):
        """测试自适应增加"""
        limiter = AdaptiveRateLimiter("test", initial_limit=10,
                                       min_limit=5, max_limit=20)
        for _ in range(10):
            limiter.record_success()
        stats = limiter.get_stats()
        self.assertGreater(stats["current_limit"], 10)

    def test_adapt_down(self):
        """测试自适应减少"""
        limiter = AdaptiveRateLimiter("test", initial_limit=20,
                                       min_limit=5, max_limit=30)
        for _ in range(5):
            limiter.record_failure()
        stats = limiter.get_stats()
        self.assertLess(stats["current_limit"], 20)


class TestBulkhead(unittest.TestCase):
    """舱壁隔离器测试"""

    def test_execute(self):
        """测试执行"""
        bulkhead = Bulkhead("test", max_concurrent=2)
        result = bulkhead.execute(lambda: "success")
        self.assertEqual(result, "success")

    def test_concurrent_limit(self):
        """测试并发限制"""
        import threading
        bulkhead = Bulkhead("test", max_concurrent=1)
        results = []
        def task():
            try:
                bulkhead.execute(lambda: time.sleep(0.1) or "done")
                results.append("success")
            except BulkheadFull:
                results.append("rejected")

        threads = [threading.Thread(target=task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertIn("success", results)

    def test_stats(self):
        """测试统计信息"""
        bulkhead = Bulkhead("test", max_concurrent=5)
        stats = bulkhead.get_stats()
        self.assertEqual(stats["max_concurrent"], 5)
        self.assertEqual(stats["name"], "test")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_circuit_breaker(self):
        """测试获取全局熔断器"""
        cb1 = get_circuit_breaker("cb1")
        cb2 = get_circuit_breaker("cb1")
        self.assertIs(cb1, cb2)

    def test_get_rate_limiter(self):
        """测试获取全局限流器"""
        rl1 = get_rate_limiter("rl1")
        rl2 = get_rate_limiter("rl1")
        self.assertIs(rl1, rl2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 74 - 限流熔断器系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCircuitBreaker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTokenBucket))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSlidingWindow))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRateLimiter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdaptiveRateLimiter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBulkhead))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstance))

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
