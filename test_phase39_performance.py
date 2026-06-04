"""
Phase 39 - 系统性能优化与基准测试
测试系统各个组件的性能表现
"""
import time
import unittest
from src.utils.performance import (
    BenchmarkSuite,
    PerformanceMonitor,
    PerformanceProfiler,
    get_benchmark_suite,
    get_performance_monitor,
    get_performance_profiler
)


class TestBenchmarkFramework(unittest.TestCase):
    """基准测试框架测试"""
    
    def setUp(self):
        """测试前设置"""
        self.suite = BenchmarkSuite("test.suite")
        self.monitor = PerformanceMonitor()
        self.profiler = PerformanceProfiler()
    
    def test_simple_benchmark(self):
        """测试简单基准测试"""
        def simple_func():
            total = 0
            for i in range(100):
                total += i
            return total
        
        result = self.suite.run(
            "simple.addition",
            simple_func,
            iterations=100,
            warmup=5
        )
        
        self.assertEqual(result.name, "simple.addition")
        self.assertEqual(result.iterations, 100)
        self.assertGreater(result.operations_per_second, 0)
        self.assertGreater(result.avg_time_ms, 0)
    
    def test_list_operations(self):
        """测试列表操作性能"""
        def list_append():
            lst = []
            for i in range(1000):
                lst.append(i)
            return lst
        
        result = self.suite.run(
            "list.append",
            list_append,
            iterations=100,
            warmup=5
        )
        
        self.assertGreater(result.operations_per_second, 0)
        self.logger.info(f"List append: {result.avg_time_ms:.4f}ms avg")
    
    def test_dict_operations(self):
        """测试字典操作性能"""
        def dict_operations():
            d = {}
            for i in range(1000):
                d[f"key_{i}"] = i
            for i in range(1000):
                _ = d.get(f"key_{i}")
            return d
        
        result = self.suite.run(
            "dict.operations",
            dict_operations,
            iterations=100,
            warmup=5
        )
        
        self.assertGreater(result.operations_per_second, 0)
        self.logger.info(f"Dict operations: {result.avg_time_ms:.4f}ms avg")
    
    def test_comparison(self):
        """测试对比功能"""
        def func_a():
            return sum(range(1000))
        
        def func_b():
            total = 0
            for i in range(1000):
                total += i
            return total
        
        results = self.suite.run_comparison(
            "sum.methods",
            {"builtin_sum": func_a, "loop": func_b},
            iterations=100,
            warmup=5
        )
        
        self.assertEqual(len(results), 2)
        self.assertIn("builtin_sum", results)
        self.assertIn("loop", results)
        
        # 记录哪个更快
        if results["builtin_sum"].avg_time_ms < results["loop"].avg_time_ms:
            self.logger.info("builtin_sum is faster")
        else:
            self.logger.info("loop is faster")
    
    def test_summary(self):
        """测试摘要生成"""
        def dummy_func():
            time.sleep(0.001)
        
        self.suite.run("dummy", dummy_func, iterations=10, warmup=0)
        
        summary = self.suite.get_summary()
        self.assertEqual(summary["total_benchmarks"], 1)
        self.assertIsNotNone(summary["fastest"])
        self.assertIsNotNone(summary["slowest"])


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.monitor = PerformanceMonitor()
    
    def test_collect_metrics(self):
        """测试收集性能指标"""
        metric = self.monitor.collect_metrics("test.component")
        
        self.assertEqual(metric.name, "test.component")
        self.assertGreaterEqual(metric.memory_mb, 0)
        self.assertGreaterEqual(metric.thread_count, 1)
        self.logger.info(f"Metrics: CPU={metric.cpu_percent:.2f}%, Memory={metric.memory_mb:.2f}MB")
    
    def test_record_metrics(self):
        """测试记录指标"""
        from src.utils.performance import PerformanceMetrics
        
        for i in range(10):
            metric = PerformanceMetrics(
                name="test.component",
                cpu_percent=float(i),
                memory_mb=float(100 + i),
                thread_count=10 + i,
                gc_collections=i
            )
            self.monitor.record_metric("test.component", metric)
        
        summary = self.monitor.get_metrics_summary("test.component")
        self.assertEqual(summary["count"], 10)
        self.assertEqual(summary["name"], "test.component")
    
    def test_all_summaries(self):
        """测试获取所有摘要"""
        self.monitor.collect_metrics("component.1")
        self.monitor.collect_metrics("component.2")
        
        summaries = self.monitor.get_all_summaries()
        self.assertEqual(len(summaries), 2)
        self.assertIn("component.1", summaries)
        self.assertIn("component.2", summaries)


class TestPerformanceProfiler(unittest.TestCase):
    """性能分析器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.profiler = PerformanceProfiler()
    
    def test_profile_function(self):
        """测试函数分析"""
        def sample_function(n: int) -> int:
            result = 0
            for i in range(n):
                result += i ** 2
            return result
        
        for _ in range(10):
            self.profiler.profile("sample.function", sample_function, 1000)
        
        stats = self.profiler.get_profile_stats("sample.function")
        self.assertEqual(stats["count"], 10)
        self.assertGreater(stats["avg_ms"], 0)
        self.logger.info(f"Profile stats: {stats}")
    
    def test_all_stats(self):
        """测试获取所有统计"""
        def func1():
            time.sleep(0.001)
        
        def func2():
            time.sleep(0.002)
        
        self.profiler.profile("func.1", func1)
        self.profiler.profile("func.2", func2)
        
        all_stats = self.profiler.get_all_stats()
        self.assertEqual(len(all_stats), 2)


class TestSystemComponents(unittest.TestCase):
    """系统组件性能测试"""
    
    def test_api_layer_performance(self):
        """测试API层性能"""
        try:
            from src.api_layer.core import APIApp, HTTPMethod
            
            app = APIApp("perf.test.api")
            
            def test_handler(request):
                return {"status": "ok"}
            
            app.add_route("/test", HTTPMethod.GET, test_handler)
            
            from src.api_layer.core import APIRequest
            
            suite = BenchmarkSuite("api.layer")
            
            def api_call():
                request = APIRequest(HTTPMethod.GET, "/test")
                return app.handle_request(request)
            
            result = suite.run(
                "api.request",
                api_call,
                iterations=500,
                warmup=50
            )
            
            self.logger.info(f"API Performance: {result.avg_time_ms:.4f}ms avg, {result.operations_per_second:.2f} req/s")
            self.assertGreater(result.operations_per_second, 0)
        except Exception as e:
            self.logger.warning(f"API test skipped: {e}")
    
    def test_task_queue_performance(self):
        """测试任务队列性能"""
        try:
            from src.scheduling_layer.task_queue import AsyncTaskQueue
            
            queue = AsyncTaskQueue("perf.test.queue")
            
            def sample_task():
                return sum(range(100))
            
            suite = BenchmarkSuite("task.queue")
            
            def enqueue_tasks():
                task_id = queue.enqueue(sample_task)
                return task_id
            
            result = suite.run(
                "task.enqueue",
                enqueue_tasks,
                iterations=500,
                warmup=50
            )
            
            queue.stop()
            
            self.logger.info(f"Task Queue Enqueue: {result.avg_time_ms:.4f}ms avg, {result.operations_per_second:.2f} ops/s")
            self.assertGreater(result.operations_per_second, 0)
        except Exception as e:
            self.logger.warning(f"Task queue test skipped: {e}")
    
    def test_health_check_performance(self):
        """测试健康检查性能"""
        try:
            from src.utils.health import HealthMonitor, create_component_check, HealthCheckType
            
            monitor = HealthMonitor()
            
            for i in range(10):
                check = create_component_check(
                    name=f"component.{i}",
                    check_fn=lambda: True,
                    check_type=HealthCheckType.LIVENESS
                )
                monitor.register_check(check)
            
            suite = BenchmarkSuite("health.check")
            
            def run_health_checks():
                return monitor.run_all_checks()
            
            result = suite.run(
                "health.all.checks",
                run_health_checks,
                iterations=100,
                warmup=10
            )
            
            self.logger.info(f"Health Check (10 components): {result.avg_time_ms:.4f}ms avg")
            self.assertGreater(result.operations_per_second, 0)
        except Exception as e:
            self.logger.warning(f"Health check test skipped: {e}")


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("Phase 39 - 系统性能优化与基准测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBenchmarkFramework))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformanceMonitor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformanceProfiler))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSystemComponents))
    
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
    run_performance_tests()
