"""
Phase 107 - 降级策略与熔断集成测试
"""
import unittest
import time
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("degradation", "/workspace/src/core/degradation.py")
deg_module = importlib.util.module_from_spec(spec)
sys.modules["degradation"] = deg_module
spec.loader.exec_module(deg_module)

DegradationManager = deg_module.DegradationManager
DegradationPolicy = deg_module.DegradationPolicy
DegradationLevel = deg_module.DegradationLevel
CircuitBreaker = deg_module.CircuitBreaker
CircuitBreakerConfig = deg_module.CircuitBreakerConfig
CircuitBreakerOpen = deg_module.CircuitBreakerOpen
ServiceDegraded = deg_module.ServiceDegraded
get_degradation_manager = deg_module.get_degradation_manager


class TestCircuitBreaker(unittest.TestCase):
    """熔断器测试"""

    def setUp(self):
        self.cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=2,
            success_threshold=2
        ))

    def test_successful_call(self):
        """测试成功调用"""
        result = self.cb.call(lambda: 42)
        self.assertEqual(result, 42)
        self.assertEqual(self.cb.get_state(), "closed")

    def test_failure_opens_circuit(self):
        """测试失败打开熔断器"""
        def fail():
            raise ValueError("error")

        for _ in range(3):
            try:
                self.cb.call(fail)
            except ValueError:
                pass

        self.assertEqual(self.cb.get_state(), "open")

    def test_open_circuit_rejects(self):
        """测试打开状态拒绝调用"""
        self.cb.force_open()
        with self.assertRaises(CircuitBreakerOpen):
            self.cb.call(lambda: 42)

    def test_half_open_recovery(self):
        """测试半开恢复"""
        self.cb.force_open()
        time.sleep(0.15)
        result = self.cb.call(lambda: 42)
        self.assertEqual(result, 42)
        self.assertEqual(self.cb.get_state(), "half_open")

    def test_full_recovery(self):
        """测试完全恢复"""
        self.cb.force_open()
        time.sleep(0.15)
        self.cb.call(lambda: 1)
        self.cb.call(lambda: 2)
        self.assertEqual(self.cb.get_state(), "closed")

    def test_force_close(self):
        """测试强制关闭"""
        self.cb.force_open()
        self.cb.force_close()
        self.assertEqual(self.cb.get_state(), "closed")


class TestDegradationManager(unittest.TestCase):
    """降级管理器测试"""

    def setUp(self):
        self.mgr = DegradationManager()

    def test_register_policy(self):
        """测试注册策略"""
        policy = DegradationPolicy("p1", "service_a")
        self.mgr.register_policy(policy)
        stats = self.mgr.get_stats()
        self.assertEqual(stats["total_policies"], 1)

    def test_execute_success(self):
        """测试正常执行"""
        policy = DegradationPolicy("p1", "service_a")
        self.mgr.register_policy(policy)
        result = self.mgr.execute("service_a", lambda: 42)
        self.assertEqual(result, 42)

    def test_execute_with_fallback(self):
        """测试带降级执行"""
        def fallback():
            return "fallback"

        policy = DegradationPolicy("p1", "service_a", fallback=fallback)
        self.mgr.register_policy(policy)

        def fail():
            raise ValueError("error")

        result = self.mgr.execute("service_a", fail)
        self.assertEqual(result, "fallback")

    def test_full_degradation(self):
        """测试完全降级"""
        def fallback():
            return "fallback"

        policy = DegradationPolicy("p1", "service_a",
                                    level=DegradationLevel.FULL,
                                    fallback=fallback)
        self.mgr.register_policy(policy)
        result = self.mgr.execute("service_a", lambda: 42)
        self.assertEqual(result, "fallback")

    def test_full_degradation_no_fallback(self):
        """测试完全降级无 fallback"""
        policy = DegradationPolicy("p1", "service_a",
                                    level=DegradationLevel.FULL)
        self.mgr.register_policy(policy)
        with self.assertRaises(ServiceDegraded):
            self.mgr.execute("service_a", lambda: 42)

    def test_set_degradation_level(self):
        """测试设置降级级别"""
        policy = DegradationPolicy("p1", "service_a")
        self.mgr.register_policy(policy)
        self.assertTrue(self.mgr.set_degradation_level("service_a", DegradationLevel.PARTIAL))
        self.assertEqual(policy.level, DegradationLevel.PARTIAL)

    def test_circuit_breaker_integration(self):
        """测试熔断器集成"""
        policy = DegradationPolicy("p1", "service_a")
        self.mgr.register_policy(policy)

        def fail():
            raise ValueError("error")

        for _ in range(5):
            try:
                self.mgr.execute("service_a", fail)
            except ValueError:
                pass

        cb = self.mgr.get_circuit_breaker("service_a")
        self.assertEqual(cb.get_state(), "open")

    def test_stats(self):
        """测试统计信息"""
        self.mgr.register_policy(DegradationPolicy("p1", "svc1"))
        self.mgr.register_policy(DegradationPolicy("p2", "svc2"))
        stats = self.mgr.get_stats()
        self.assertEqual(stats["total_policies"], 2)
        self.assertEqual(stats["total_circuits"], 2)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_degradation_manager(self):
        """测试获取全局降级管理器"""
        m1 = get_degradation_manager()
        m2 = get_degradation_manager()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 107 - 降级策略与熔断集成测试")
    print("=" * 60)
    unittest.main(verbosity=2)
