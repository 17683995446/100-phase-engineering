"""
Phase 39 - 系统性能优化与基准测试（简化版）
"""
import time
import unittest
import logging
from src.utils.performance import (
    BenchmarkSuite,
    PerformanceMonitor,
    PerformanceProfiler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestPerformanceBasic(unittest.TestCase):
    """基础性能测试"""
    
    def test_simple_benchmark(self):
        """测试简单基准测试"""
        suite = BenchmarkSuite("test")
        
        def simple_func():
            total = 0
            for i in range(100):
                total += i
            return total
        
        result = suite.run(
            "simple.addition",
            simple_func,
            iterations=100,
            warmup=5
        )
        
        self.assertGreater(result.operations_per_second, 0)
        logger.info(f"Result: {result.avg_time_ms:.4f}ms avg")
    
    def test_performance_monitor(self):
        """测试性能监控"""
        monitor = PerformanceMonitor()
        metric = monitor.collect_metrics("test.component")
        
        self.assertGreaterEqual(metric.memory_mb, 0)
        logger.info(f"Memory: {metric.memory_mb:.2f}MB")
    
    def test_performance_profiler(self):
        """测试性能分析"""
        profiler = PerformanceProfiler()
        
        def sample_func():
            return sum(range(100))
        
        for _ in range(5):
            profiler.profile("sample", sample_func)
        
        stats = profiler.get_profile_stats("sample")
        self.assertEqual(stats["count"], 5)
    
    def test_summary(self):
        """测试摘要"""
        suite = BenchmarkSuite("test")
        
        def dummy():
            pass
        
        suite.run("dummy", dummy, iterations=10, warmup=0)
        
        summary = suite.get_summary()
        self.assertEqual(summary["total_benchmarks"], 1)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 39 - 系统性能优化与基准测试（简化版）")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceBasic)
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
    run_tests()
