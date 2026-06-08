"""
Phase 104 - 性能基准测试框架测试
"""
import unittest
import time
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("benchmark", "/workspace/src/core/benchmark.py")
bench_module = importlib.util.module_from_spec(spec)
sys.modules["benchmark"] = bench_module
spec.loader.exec_module(bench_module)
BenchmarkFramework = bench_module.BenchmarkFramework
BenchmarkStatus = bench_module.BenchmarkStatus
get_benchmark_framework = bench_module.get_benchmark_framework


class TestBenchmarkFramework(unittest.TestCase):
    """基准测试框架测试"""

    def setUp(self):
        self.bench = BenchmarkFramework()

    def test_run_benchmark(self):
        """测试运行基准测试"""
        def func():
            sum(range(100))

        result = self.bench.run("sum_100", func, iterations=100, warmup=5)
        self.assertEqual(result.status, BenchmarkStatus.COMPLETED)
        self.assertEqual(result.iterations, 100)
        self.assertGreater(result.avg_time, 0)
        self.assertGreater(result.ops_per_second, 0)

    def test_benchmark_stats(self):
        """测试基准统计信息"""
        def func():
            pass

        result = self.bench.run("noop", func, iterations=50)
        self.assertGreaterEqual(result.min_time, 0)
        self.assertGreaterEqual(result.max_time, result.min_time)
        self.assertGreaterEqual(result.median_time, result.min_time)
        self.assertGreaterEqual(result.max_time, result.median_time)

    def test_benchmark_failed(self):
        """测试失败的基准测试"""
        def func():
            raise ValueError("error")

        result = self.bench.run("fail", func, iterations=10)
        self.assertEqual(result.status, BenchmarkStatus.FAILED)

    def test_compare_benchmarks(self):
        """测试比较基准测试"""
        def fast():
            sum(range(10))

        def slow():
            time.sleep(0.002)

        self.bench.run("fast", fast, iterations=50)
        self.bench.run("slow", slow, iterations=50)

        comparison = self.bench.compare("slow", "fast")
        self.assertIsNotNone(comparison)
        self.assertTrue(comparison["faster"])
        self.assertGreater(comparison["speedup"], 1.0)

    def test_compare_not_found(self):
        """测试比较不存在的基准测试"""
        result = self.bench.compare("a", "b")
        self.assertIsNone(result)

    def test_get_results(self):
        """测试获取结果"""
        def func():
            pass

        self.bench.run("test", func, iterations=10)
        results = self.bench.get_results("test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "test")

    def test_get_trend(self):
        """测试获取趋势"""
        def func():
            pass

        self.bench.run("trend", func, iterations=10)
        self.bench.run("trend", func, iterations=10)
        trend = self.bench.get_trend("trend")
        self.assertEqual(len(trend), 2)

    def test_get_stats(self):
        """测试获取统计信息"""
        def func():
            pass

        self.bench.run("s1", func, iterations=10)
        self.bench.run("s2", func, iterations=10)
        stats = self.bench.get_stats()
        self.assertEqual(stats["total_benchmarks"], 2)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["unique_names"], 2)

    def test_multiple_iterations_consistency(self):
        """测试多次迭代一致性"""
        data = []

        def func():
            data.append(1)

        result = self.bench.run("append", func, iterations=20, warmup=0)
        self.assertEqual(len(data), 20 + 0)  # 无 warmup
        self.assertEqual(result.status, BenchmarkStatus.COMPLETED)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_benchmark_framework(self):
        """测试获取全局基准测试框架"""
        b1 = get_benchmark_framework()
        b2 = get_benchmark_framework()
        self.assertIs(b1, b2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 104 - 性能基准测试框架测试")
    print("=" * 60)
    unittest.main(verbosity=2)
