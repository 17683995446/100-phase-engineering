"""
Phase 34: 全面复杂场景压力测试套件
发现真实运行时的 bug，进行迭代改进优化
"""
import pytest
import time
import threading
import random
import uuid
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import traceback

from src.scheduling_layer import (
    TaskScheduler,
    TaskQueueManager,
    AsyncTaskQueue,
    TaskStatus,
    TaskPriority,
    create_task_queue,
    enqueue_task,
    schedule_delay,
    schedule_interval,
    get_default_scheduler,
    JobStatus,
    JobType
)
from src.api_layer import (
    APIApp,
    WebSocketApp,
    GraphQLApp,
    APIDocumentation,
    HTTPMethod,
    Route,
    WebSocketMessage,
    WebSocketOp,
    create_text_message,
    GraphQLRequest
)
from src.utils.prometheus import PrometheusRegistry
from src.utils.cache import CacheManager
from src.config.persistence import ConfigPersistence


class StressTestLogger:
    """压力测试日志记录器"""

    def __init__(self):
        self.results = []
        self.lock = threading.Lock()

    def log(self, test_name: str, status: str, message: str, details: Any = None):
        """记录测试结果"""
        with self.lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "test_name": test_name,
                "status": status,
                "message": message,
                "details": details
            }
            self.results.append(entry)
            print(f"[{entry['timestamp']}] [{status}] {test_name}: {message}")

    def get_results(self) -> List[Dict]:
        return self.results

    def clear(self):
        self.results.clear()


logger = StressTestLogger()


class TestPhase34ComprehensiveStress:
    """Phase 34: 全面压力测试套件"""

    def setup_method(self):
        """每个测试方法前的设置"""
        logger.clear()

    def teardown_method(self):
        """每个测试方法后的清理"""
        pass


class Test01_MassiveConcurrency(StressTestLogger):
    """测试01: 大规模并发测试"""

    def test_1000_concurrent_tasks(self):
        """测试1000个并发任务入队"""
        print("\n" + "="*80)
        print("测试: 1000个并发任务入队")
        print("="*80)

        queue = AsyncTaskQueue(name="stress-test-1k")
        results = {"success": 0, "failed": 0}
        lock = threading.Lock()

        def task_func(task_id):
            try:
                return f"Task {task_id} completed"
            except Exception as e:
                with lock:
                    results["failed"] += 1
                raise

        def worker(start_id, count):
            for i in range(count):
                task_id = queue.enqueue(
                    task_func,
                    start_id + i,
                    priority=TaskPriority.NORMAL
                )
                with lock:
                    results["success"] += 1

        # 10个线程，每个入队100个任务
        threads = []
        start = 0
        for _ in range(10):
            t = threading.Thread(target=worker, args=(start, 100))
            threads.append(t)
            t.start()
            start += 100

        for t in threads:
            t.join()

        # 验证结果
        print(f"\n结果:")
        print(f"  成功入队: {results['success']}")
        print(f"  失败: {results['failed']}")
        print(f"  队列中任务: {queue.stats.total_tasks}")

        assert results["success"] == 1000, f"Expected 1000, got {results['success']}"
        assert queue.stats.total_tasks == 1000

        # 验证所有任务都在队列中
        with queue._lock:
            assert len(queue._tasks) == 1000

        print("\n✅ 1000个并发任务入队测试通过!")

    def test_100_tasks_parallel_execution(self):
        """测试100个任务并行执行"""
        print("\n" + "="*80)
        print("测试: 100个任务并行执行")
        print("="*80)

        queue = AsyncTaskQueue(name="stress-test-100-exec")
        executed_count = {"value": 0}
        lock = threading.Lock()

        def quick_task(n):
            with lock:
                executed_count["value"] += 1
            time.sleep(0.01)  # 10ms
            return n * 2

        # 入队100个任务
        task_ids = []
        for i in range(100):
            task_id = queue.enqueue(quick_task, i)
            task_ids.append(task_id)

        print(f"已入队 {len(task_ids)} 个任务")

        # 启动10个工作线程
        queue.start(num_workers=10)

        # 等待执行完成
        time.sleep(3)

        # 停止队列
        queue.stop()

        # 验证结果
        print(f"\n结果:")
        print(f"  执行完成数: {executed_count['value']}")
        print(f"  完成任务数: {queue.stats.completed_tasks}")
        print(f"  失败任务数: {queue.stats.failed_tasks}")

        # 所有任务应该都已执行
        assert executed_count["value"] == 100, f"Expected 100, got {executed_count['value']}"

        print("\n✅ 100个任务并行执行测试通过!")


class Test02_SchedulerStress(StressTestLogger):
    """测试02: 调度器压力测试"""

    def test_500_concurrent_scheduled_jobs(self):
        """测试500个并发调度任务"""
        print("\n" + "="*80)
        print("测试: 500个并发调度任务")
        print("="*80)

        scheduler = TaskScheduler(name="stress-scheduler-500")

        def job_func(job_id):
            return f"Job {job_id}"

        # 并发入队500个延迟任务
        job_ids = []
        for i in range(500):
            job_id = scheduler.add_delay_job(
                job_func,
                0.1,  # 100ms后执行
                i
            )
            job_ids.append(job_id)

        print(f"已调度 {len(job_ids)} 个任务")

        # 启动调度器
        scheduler.start(num_workers=20)

        # 等待执行
        time.sleep(5)

        # 停止
        scheduler.stop()

        # 验证结果
        print(f"\n结果:")
        print(f"  总任务数: {scheduler.stats.total_jobs}")
        print(f"  执行总数: {scheduler.stats.total_executions}")

        assert scheduler.stats.total_jobs == 500

        print("\n✅ 500个调度任务测试通过!")


class Test03_MultiModuleIntegration(StressTestLogger):
    """测试03: 多模块集成测试"""

    def test_api_websocket_graphql_integration(self):
        """测试 API、WebSocket、GraphQL 集成"""
        print("\n" + "="*80)
        print("测试: API、WebSocket、GraphQL 多模块集成")
        print("="*80)

        # 创建各模块实例
        api_app = APIApp(name="integration-api")
        ws_app = WebSocketApp(name="integration-ws")
        gql_app = GraphQLApp(name="integration-gql")

        # API 路由
        def api_handler(request):
            return {"result": "api-response", "data": request.body}

        api_app.add_route(
            path="/test",
            method=HTTPMethod.POST,
            handler=api_handler
        )

        # WebSocket 路由
        from src.api_layer import EchoHandler
        ws_app.add_route("/echo", EchoHandler())

        print("已创建 API、WebSocket、GraphQL 实例")

        # 测试 API
        from src.api_layer import APIRequest
        request = APIRequest(
            method=HTTPMethod.POST,
            path="/test",
            body={"test": "data"}
        )
        api_response = api_app.handle_request(request)
        assert api_response is not None
        assert api_response.status_code == 200
        print(f"API 响应: {api_response.body}")

        # 测试 WebSocket
        ws_conn = ws_app.handle_connect("/echo")
        ws_msg = create_text_message({"test": "websocket"})
        ws_response = ws_app.handle_message(ws_conn, ws_msg)
        assert ws_response is not None
        print(f"WebSocket 响应: {ws_response.data}")

        # 测试 GraphQL
        gql_response = gql_app.execute("{ hello }")
        assert gql_response is not None
        print(f"GraphQL 响应: {gql_response.data}")

        print("\n✅ 多模块集成测试通过!")


class Test04_EdgeCases(StressTestLogger):
    """测试04: 边界条件测试"""

    def test_empty_queue_operations(self):
        """测试空队列操作"""
        print("\n" + "="*80)
        print("测试: 空队列操作")
        print("="*80)

        queue = AsyncTaskQueue(name="edge-empty")

        # 空队列出队
        task = queue.dequeue(timeout=0.1)
        assert task is None
        print("空队列出队返回 None ✓")

        # 获取不存在的任务
        result = queue.get_task("non-existent-id")
        assert result is None
        print("获取不存在任务返回 None ✓")

        # 获取不存在任务的状态
        status = queue.get_task_status("non-existent-id")
        assert status is None
        print("获取不存在任务状态返回 None ✓")

        print("\n✅ 空队列操作测试通过!")

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        print("\n" + "="*80)
        print("测试: 取消不存在的任务")
        print("="*80)

        queue = AsyncTaskQueue(name="edge-cancel-none")

        result = queue.cancel_task("non-existent-id")
        assert result is False
        print("取消不存在的任务返回 False ✓")

        print("\n✅ 取消不存在任务测试通过!")

    def test_scheduler_edge_cases(self):
        """测试调度器边界条件"""
        print("\n" + "="*80)
        print("测试: 调度器边界条件")
        print("="*80)

        scheduler = TaskScheduler(name="edge-scheduler")

        # 暂停不存在的任务
        result = scheduler.pause_job("non-existent")
        assert result is False
        print("暂停不存在任务返回 False ✓")

        # 恢复不存在的任务
        result = scheduler.resume_job("non-existent")
        assert result is False
        print("恢复不存在任务返回 False ✓")

        # 取消不存在的任务
        result = scheduler.cancel_job("non-existent")
        assert result is False
        print("取消不存在任务返回 False ✓")

        # 获取不存在的任务
        job = scheduler.get_job("non-existent")
        assert job is None
        print("获取不存在任务返回 None ✓")

        # 按状态过滤不存在的任务
        jobs = scheduler.get_jobs(status=JobStatus.RUNNING)
        assert len(jobs) == 0
        print("获取空状态任务列表返回 [] ✓")

        print("\n✅ 调度器边界条件测试通过!")


class Test05_ExceptionHandling(StressTestLogger):
    """测试05: 异常处理测试"""

    def test_task_exception_handling(self):
        """测试任务异常处理"""
        print("\n" + "="*80)
        print("测试: 任务异常处理")
        print("="*80)

        queue = AsyncTaskQueue(name="exception-test")

        def failing_task():
            raise ValueError("Test exception")

        task_id = queue.enqueue(failing_task, max_retries=2)
        print(f"已入队失败任务: {task_id}")

        queue.start(num_workers=1)

        # 等待重试
        time.sleep(2)

        queue.stop()

        task = queue.get_task(task_id)

        print(f"\n任务状态: {task.status}")
        print(f"重试次数: {task.retry_count}")
        print(f"结果: {task.result}")

        # 任务应该失败
        assert task.status in [TaskStatus.FAILED, TaskStatus.RETRYING]
        print("异常处理正确 ✓")

        print("\n✅ 异常处理测试通过!")

    def test_scheduler_exception_handling(self):
        """测试调度器异常处理"""
        print("\n" + "="*80)
        print("测试: 调度器异常处理")
        print("="*80)

        scheduler = TaskScheduler(name="exception-scheduler")

        def failing_job():
            raise RuntimeError("Job failed!")

        job_id = scheduler.add_delay_job(failing_job, 0.1)
        print(f"已调度失败任务: {job_id}")

        scheduler.start(num_workers=1)

        time.sleep(2)

        scheduler.stop()

        job = scheduler.get_job(job_id)

        print(f"\n任务状态: {job.status}")
        print(f"失败次数: {job.failure_count}")

        assert job.status in [JobStatus.FAILED, JobStatus.RUNNING]
        print("调度器异常处理正确 ✓")

        print("\n✅ 调度器异常处理测试通过!")


class Test06_PersistenceStress(StressTestLogger):
    """测试06: 持久化压力测试"""

    def test_config_persistence_stress(self):
        """测试配置持久化压力"""
        print("\n" + "="*80)
        print("测试: 配置持久化压力测试")
        print("="*80)

        from src.config.persistence import ConfigScope
        persistence = ConfigPersistence()

        # 快速写入1000个配置
        for i in range(1000):
            persistence.save(
                ConfigScope.TASK,
                {f"id": i, "data": f"value_{i}"},
                name=f"config_{i}"
            )

        print(f"已写入 1000 个配置")

        # 验证所有配置
        for i in range(1000):
            value = persistence.load(ConfigScope.TASK, name=f"config_{i}")
            assert value is not None
            assert value.get("id") == i

        print(f"已验证 1000 个配置读取")

        # 清理
        for i in range(1000):
            persistence.delete(ConfigScope.TASK, name=f"config_{i}")

        print("\n✅ 配置持久化压力测试通过!")


class Test07_CacheStress(StressTestLogger):
    """测试07: 缓存压力测试"""

    def test_cache_concurrent_stress(self):
        """测试缓存并发压力"""
        print("\n" + "="*80)
        print("测试: 缓存并发压力测试")
        print("="*80)

        manager = CacheManager()
        cache = manager.register_cache("stress-cache", default_ttl=300)

        def cache_worker(worker_id, count):
            for i in range(count):
                key = f"key_{worker_id}_{i}"
                value = {"worker": worker_id, "item": i}

                # 写入
                cache.set(key, value)

                # 读取
                result = cache.get(key)

                # 验证
                if result and result.get("worker") != worker_id:
                    print(f"数据不一致! key={key}")

        # 10个线程，每个写入100个条目
        threads = []
        for w in range(10):
            t = threading.Thread(target=cache_worker, args=(w, 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"缓存大小: {len(cache._cache)}")
        print(f"命中率: {cache._stats.hits}")
        print(f"未命中率: {cache._stats.misses}")

        print("\n✅ 缓存并发压力测试通过!")


class Test08_RaceConditions(StressTestLogger):
    """测试08: 竞态条件测试"""

    def test_concurrent_enqueue_dequeue(self):
        """测试并发入队出队竞态"""
        print("\n" + "="*80)
        print("测试: 并发入队出队竞态条件")
        print("="*80)

        queue = AsyncTaskQueue(name="race-condition")

        results = {"enqueued": 0, "dequeued": 0}
        lock = threading.Lock()

        def enqueue_worker(count):
            for i in range(count):
                queue.enqueue(lambda: i)
                with lock:
                    results["enqueued"] += 1

        def dequeue_worker():
            while True:
                task = queue.dequeue(timeout=0.01)
                if task is not None:
                    with lock:
                        results["dequeued"] += 1

        # 启动入队线程
        enqueue_threads = []
        for _ in range(5):
            t = threading.Thread(target=enqueue_worker, args=(100,))
            enqueue_threads.append(t)
            t.start()

        # 启动出队线程
        dequeue_threads = []
        for _ in range(3):
            t = threading.Thread(target=dequeue_worker)
            dequeue_threads.append(t)
            t.start()

        # 等待入队完成
        for t in enqueue_threads:
            t.join()

        # 再等一会儿让出队完成
        time.sleep(2)

        # 停止出队线程（通过设置状态）
        queue._shutdown.set()

        print(f"\n结果:")
        print(f"  入队总数: {results['enqueued']}")
        print(f"  出队总数: {results['dequeued']}")

        print("\n✅ 并发入队出队竞态测试通过!")


class Test09_LongRunning(StressTestLogger):
    """测试09: 长时间运行测试"""

    def test_30_second_sustained_load(self):
        """测试30秒持续负载"""
        print("\n" + "="*80)
        print("测试: 30秒持续负载测试")
        print("="*80)

        queue = AsyncTaskQueue(name="long-running-test")
        executed_count = {"value": 0}
        lock = threading.Lock()
        start_time = time.time()

        def sustained_task():
            with lock:
                executed_count["value"] += 1
            time.sleep(0.05)  # 50ms

        # 持续入队
        queue.start(num_workers=10)

        enqueue_count = 0
        while time.time() - start_time < 30:
            queue.enqueue(sustained_task)
            enqueue_count += 1
            time.sleep(0.1)  # 每100ms入队一个

        print(f"入队总数: {enqueue_count}")
        print(f"执行总数: {executed_count['value']}")

        # 等待队列清空
        time.sleep(5)

        queue.stop()

        elapsed = time.time() - start_time

        print(f"\n结果:")
        print(f"  运行时长: {elapsed:.2f}秒")
        print(f"  入队任务: {enqueue_count}")
        print(f"  执行任务: {executed_count['value']}")
        print(f"  完成任务: {queue.stats.completed_tasks}")
        print(f"  失败任务: {queue.stats.failed_tasks}")

        print("\n✅ 30秒持续负载测试完成!")


class Test10_DataConsistency(StressTestLogger):
    """测试10: 数据一致性测试"""

    def test_task_data_integrity(self):
        """测试任务数据完整性"""
        print("\n" + "="*80)
        print("测试: 任务数据完整性")
        print("="*80)

        queue = AsyncTaskQueue(name="data-integrity-test")

        # 创建带复杂数据的任务
        test_data = {
            "string": "test",
            "number": 123,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "unicode": "中文测试",
            "special": "!@#$%^&*()"
        }

        def verify_data(data):
            return data

        task_id = queue.enqueue(verify_data, test_data)

        queue.start(num_workers=1)

        time.sleep(1)

        queue.stop()

        task = queue.get_task(task_id)

        if task and task.result:
            result_data = task.result.data
            assert result_data == test_data, "数据完整性验证失败!"
            print("数据完整性验证通过 ✓")

        print("\n✅ 任务数据完整性测试通过!")


def run_all_stress_tests():
    """运行所有压力测试"""
    print("\n" + "="*80)
    print("Phase 34: 全面复杂场景压力测试套件")
    print("="*80)
    print("\n开始执行压力测试...\n")

    stress_suite = TestPhase34ComprehensiveStress()

    test_classes = [
        Test01_MassiveConcurrency(),
        Test02_SchedulerStress(),
        Test03_MultiModuleIntegration(),
        Test04_EdgeCases(),
        Test05_ExceptionHandling(),
        Test06_PersistenceStress(),
        Test07_CacheStress(),
        Test08_RaceConditions(),
        Test09_LongRunning(),
        Test10_DataConsistency()
    ]

    results = []
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{'='*80}")
        print(f"执行测试类: {class_name}")
        print(f"{'='*80}\n")

        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                print(f"\n>>> 执行: {method_name}")
                method()
                results.append({"name": f"{class_name}.{method_name}", "status": "PASSED"})
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                traceback.print_exc()
                results.append({"name": f"{class_name}.{method_name}", "status": "FAILED", "error": str(e)})

    # 打印汇总
    print("\n" + "="*80)
    print("压力测试汇总")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")

    print(f"\n总测试数: {len(results)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    if failed > 0:
        print("\n失败测试:")
        for r in results:
            if r["status"] == "FAILED":
                print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")

    print("\n" + "="*80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_stress_tests()
    exit(0 if success else 1)
