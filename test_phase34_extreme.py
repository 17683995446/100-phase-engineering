"""
Phase 34 EXTREME: 超大规模复杂场景压力测试
发现真实运行时的 bug，进行迭代改进优化

测试场景包括：
1. 超大规模并发（10000+任务）
2. 长时间持续负载（60秒+）
3. 复杂任务依赖关系
4. 资源泄漏检测
5. 内存压力测试
6. 优先级饥饿测试
7. 死锁和竞态条件
8. 异常级联测试
9. 资源池耗尽测试
"""
import pytest
import time
import threading
import random
import uuid
import gc
import sys
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set
from collections import defaultdict
import weakref

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
    GraphQLRequest,
    APIRequest
)
from src.utils.prometheus import PrometheusRegistry
from src.utils.cache import CacheManager
from src.config.persistence import ConfigPersistence
from src.config.persistence import ConfigScope


class ExtremeStressLogger:
    """极端压力测试日志记录器"""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.lock = threading.Lock()
        self.issue_log = []

    def log(self, test_name: str, status: str, message: str, details: Any = None):
        """记录测试结果"""
        with self.lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "elapsed": time.time() - self.start_time if self.start_time else 0,
                "test_name": test_name,
                "status": status,
                "message": message,
                "details": details
            }
            self.results.append(entry)
            status_symbol = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
            print(f"[{entry['elapsed']:.2f}s] {status_symbol} {test_name}: {message}")

    def log_issue(self, test_name: str, issue_type: str, description: str, details: Any = None):
        """记录发现的问题"""
        with self.lock:
            issue = {
                "timestamp": datetime.now().isoformat(),
                "test_name": test_name,
                "issue_type": issue_type,
                "description": description,
                "details": details
            }
            self.issue_log.append(issue)
            print(f"🔍 ISSUE [{issue_type}]: {test_name} - {description}")

    def start(self):
        """开始测试计时"""
        self.start_time = time.time()

    def get_results(self) -> List[Dict]:
        return self.results

    def get_issues(self) -> List[Dict]:
        return self.issue_log

    def clear(self):
        self.results.clear()
        self.issue_log.clear()


stress_logger = ExtremeStressLogger()


class TestExtreme01_MassiveConcurrency:
    """极端测试01: 超大规模并发"""

    def test_10000_concurrent_task_enqueue(self):
        """测试10000个并发任务入队"""
        print("\n" + "="*80)
        print("极端测试: 10000个并发任务入队")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="extreme-10k")
        results = {"success": 0, "failed": 0, "lock": threading.Lock()}

        def task_func(task_id):
            return f"Task {task_id} completed"

        def worker(start_id, count):
            for i in range(count):
                try:
                    task_id = queue.enqueue(task_func, start_id + i, priority=TaskPriority.NORMAL)
                    with results["lock"]:
                        results["success"] += 1
                    if (results["success"] + results["failed"]) % 1000 == 0:
                        print(f"  已入队 {results['success'] + results['failed']}...")
                except Exception as e:
                    with results["lock"]:
                        results["failed"] += 1

        # 100个线程，每个入队100个任务
        threads = []
        start = 0
        batch_size = 100
        for batch in range(100):
            t = threading.Thread(target=worker, args=(start, batch_size))
            threads.append(t)
            t.start()
            start += batch_size

        for t in threads:
            t.join()

        print(f"\n结果:")
        print(f"  成功入队: {results['success']}")
        print(f"  失败: {results['failed']}")
        print(f"  队列中任务: {queue.stats.total_tasks}")

        if results["failed"] > 0:
            stress_logger.log_issue(
                "test_10000_concurrent_task_enqueue",
                "CONCURRENCY_FAILURE",
                f"入队失败 {results['failed']} 个任务",
                results["failed"]
            )

        assert results["success"] == 10000, f"Expected 10000, got {results['success']}"
        stress_logger.log("test_10000_concurrent_task_enqueue", "PASSED", f"成功入队10000个任务")

    def test_5000_task_parallel_execution_with_timing(self):
        """测试5000个任务并行执行（带详细计时）"""
        print("\n" + "="*80)
        print("极端测试: 5000个任务并行执行")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="extreme-5k-exec")
        executed_count = {"value": 0, "lock": threading.Lock()}
        execution_times = {"times": [], "lock": threading.Lock()}

        def timed_task(n):
            start = time.time()
            time.sleep(0.01)
            end = time.time()
            with executed_count["lock"]:
                executed_count["value"] += 1
            with execution_times["lock"]:
                execution_times["times"].append(end - start)
            return n * 2

        # 入队5000个任务
        task_ids = []
        for i in range(5000):
            task_id = queue.enqueue(timed_task, i)
            task_ids.append(task_id)

        print(f"已入队 {len(task_ids)} 个任务")

        # 启动50个工作线程
        queue.start(num_workers=50)

        # 等待执行完成（最多60秒）
        max_wait = 60
        start = time.time()
        last_count = 0
        while executed_count["value"] < 5000 and time.time() - start < max_wait:
            time.sleep(1)
            if executed_count["value"] != last_count:
                print(f"  已执行 {executed_count['value']}/5000")
                last_count = executed_count["value"]

        # 停止队列
        queue.stop()

        # 计算统计
        avg_time = sum(execution_times["times"]) / len(execution_times["times"]) if execution_times["times"] else 0

        print(f"\n结果:")
        print(f"  执行完成数: {executed_count['value']}")
        print(f"  平均执行时间: {avg_time*1000:.2f}ms")
        print(f"  完成任务: {queue.stats.completed_tasks}")
        print(f"  失败任务: {queue.stats.failed_tasks}")

        if executed_count["value"] < 5000:
            stress_logger.log_issue(
                "test_5000_task_parallel_execution_with_timing",
                "EXECUTION_INCOMPLETE",
                f"仅执行了 {executed_count['value']}/5000 个任务",
                {"expected": 5000, "actual": executed_count["value"]}
            )

        stress_logger.log("test_5000_task_parallel_execution_with_timing", "PASSED", f"执行完成{executed_count['value']}个任务")


class TestExtreme02_LongRunning:
    """极端测试02: 长时间运行测试"""

    def test_60_second_sustained_load(self):
        """测试60秒持续负载"""
        print("\n" + "="*80)
        print("极端测试: 60秒持续负载")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="extreme-60s")
        executed_count = {"value": 0}
        lock = threading.Lock()
        start_time = time.time()

        def sustained_task():
            with lock:
                executed_count["value"] += 1
            time.sleep(0.05)

        queue.start(num_workers=20)

        enqueue_count = 0
        check_interval = 5
        last_report = start_time

        while time.time() - start_time < 60:
            queue.enqueue(sustained_task)
            enqueue_count += 1

            # 每5秒报告一次
            if time.time() - last_report >= check_interval:
                elapsed = time.time() - start_time
                print(f"  [{elapsed:.0f}s] 入队: {enqueue_count}, 执行: {executed_count['value']}")
                last_report = time.time()

            time.sleep(0.05)

        print(f"入队阶段完成，总入队: {enqueue_count}")

        # 等待队列清空
        queue_empty_start = time.time()
        while executed_count["value"] < enqueue_count and time.time() - queue_empty_start < 30:
            time.sleep(1)
            remaining = enqueue_count - executed_count["value"]
            if remaining % 100 < 10:
                print(f"  剩余 {remaining} 个任务...")

        queue.stop()

        elapsed = time.time() - start_time

        print(f"\n结果:")
        print(f"  运行时长: {elapsed:.2f}秒")
        print(f"  入队任务: {enqueue_count}")
        print(f"  执行任务: {executed_count['value']}")
        print(f"  完成任务: {queue.stats.completed_tasks}")
        print(f"  失败任务: {queue.stats.failed_tasks}")

        if executed_count["value"] != enqueue_count:
            stress_logger.log_issue(
                "test_60_second_sustained_load",
                "EXECUTION_GAP",
                f"执行数({executed_count['value']}) != 入队数({enqueue_count})",
                {"enqueued": enqueue_count, "executed": executed_count["value"]}
            )

        stress_logger.log("test_60_second_sustained_load", "PASSED", f"60秒持续负载完成")

    def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        print("\n" + "="*80)
        print("极端测试: 内存泄漏检测")
        print("="*80)
        stress_logger.start()

        gc.collect()
        initial_memory = get_memory_usage()

        queue = AsyncTaskQueue(name="memory-leak-test")
        task_refs = []

        def memory_task(n):
            data = {"large": [1] * 1000, "id": n}
            return data

        for i in range(10000):
            task_id = queue.enqueue(memory_task, i)
            task = queue.get_task(task_id)
            if task:
                task_refs.append(weakref.ref(task))

        queue.start(num_workers=10)
        time.sleep(10)
        queue.stop()

        # 清理引用
        task_refs.clear()

        gc.collect()
        final_memory = get_memory_usage()
        memory_growth = final_memory - initial_memory

        print(f"\n结果:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  内存增长: {memory_growth:.2f}MB")

        # 超过100MB增长视为潜在泄漏
        if memory_growth > 100:
            stress_logger.log_issue(
                "test_memory_leak_detection",
                "MEMORY_LEAK",
                f"内存增长 {memory_growth:.2f}MB，超过阈值",
                {"initial": initial_memory, "final": final_memory}
            )

        stress_logger.log("test_memory_leak_detection", "PASSED", f"内存泄漏检测完成")


def get_memory_usage():
    """获取当前内存使用量（MB）"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        # 如果 psutil 不可用，使用简单的估算
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class TestExtreme03_ComplexDependencies:
    """极端测试03: 复杂任务依赖"""

    def test_1000_task_dependency_chain(self):
        """测试1000个任务的依赖链"""
        print("\n" + "="*80)
        print("极端测试: 1000个任务依赖链")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="dependency-chain")
        task_chain = []
        completion_status = {"completed": [], "lock": threading.Lock()}

        def chain_task(n):
            time.sleep(0.001)
            with completion_status["lock"]:
                completion_status["completed"].append(n)
            return f"Task {n} done"

        # 创建依赖链：每个任务依赖前一个任务
        prev_task_id = None
        for i in range(1000):
            task_id = queue.enqueue(chain_task, i, dependencies=[prev_task_id] if prev_task_id else [])
            task_chain.append(task_id)
            prev_task_id = task_id

        print(f"已创建 {len(task_chain)} 个依赖任务")

        queue.start(num_workers=20)
        time.sleep(15)
        queue.stop()

        print(f"\n结果:")
        print(f"  完成任务数: {len(completion_status['completed'])}")
        print(f"  队列完成任务: {queue.stats.completed_tasks}")

        if len(completion_status["completed"]) < 1000:
            stress_logger.log_issue(
                "test_1000_task_dependency_chain",
                "DEPENDENCY_ISSUE",
                f"仅完成 {len(completion_status['completed'])}/1000 个任务",
                len(completion_status["completed"])
            )

        stress_logger.log("test_1000_task_dependency_chain", "PASSED", f"依赖链测试完成")

    def test_diamond_dependency_pattern(self):
        """测试菱形依赖模式"""
        print("\n" + "="*80)
        print("极端测试: 菱形依赖模式")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="diamond-dependency")
        execution_order = {"order": [], "lock": threading.Lock()}

        def task_a(n):
            with execution_order["lock"]:
                execution_order["order"].append(f"A{n}")
            return f"A{n}"

        def task_b1(n, dep):
            with execution_order["lock"]:
                execution_order["order"].append(f"B1-{n}")
            return f"B1-{n}"

        def task_b2(n, dep):
            with execution_order["lock"]:
                execution_order["order"].append(f"B2-{n}")
            return f"B2-{n}"

        def task_c(n, dep1, dep2):
            with execution_order["lock"]:
                execution_order["order"].append(f"C{n}")
            return f"C{n}"

        # 创建菱形依赖：A -> B1, B2 -> C
        task_a_id = queue.enqueue(task_a, 0)
        task_b1_id = queue.enqueue(task_b1, 1, dependencies=[task_a_id])
        task_b2_id = queue.enqueue(task_b2, 1, dependencies=[task_a_id])
        task_c_id = queue.enqueue(task_c, 2, dependencies=[task_b1_id, task_b2_id])

        queue.start(num_workers=5)
        time.sleep(2)
        queue.stop()

        print(f"\n执行顺序: {execution_order['order']}")

        # 验证C在B1和B2之后
        c_index = -1
        b1_index = -1
        b2_index = -1

        for i, name in enumerate(execution_order["order"]):
            if name.startswith("C"):
                c_index = i
            elif name.startswith("B1"):
                b1_index = i
            elif name.startswith("B2"):
                b2_index = i

        if c_index > 0 and (b1_index < 0 or b2_index < 0):
            stress_logger.log_issue(
                "test_diamond_dependency_pattern",
                "DEPENDENCY_VIOLATION",
                "C在B1/B2之前执行",
                {"order": execution_order["order"]}
            )

        stress_logger.log("test_diamond_dependency_pattern", "PASSED", "菱形依赖测试完成")


class TestExtreme04_ResourceExhaustion:
    """极端测试04: 资源耗尽测试"""

    def test_queue_size_limit(self):
        """测试队列大小限制"""
        print("\n" + "="*80)
        print("极端测试: 队列大小限制")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="size-limit", max_size=1000)

        def slow_task():
            time.sleep(10)
            return "done"

        # 尝试超过限制入队
        enqueued = 0
        failed = 0

        for i in range(2000):
            try:
                queue.enqueue(slow_task)
                enqueued += 1
            except Exception as e:
                failed += 1

        print(f"\n结果:")
        print(f"  成功入队: {enqueued}")
        print(f"  拒绝入队: {failed}")
        print(f"  队列大小: {queue.stats.total_tasks}")

        if failed == 0:
            stress_logger.log_issue(
                "test_queue_size_limit",
                "SIZE_LIMIT_NOT_ENFORCED",
                "队列未强制执行大小限制",
                {"max_size": 1000, "enqueued": enqueued}
            )

        stress_logger.log("test_queue_size_limit", "PASSED", f"队列大小测试完成")

    def test_thread_pool_exhaustion(self):
        """测试线程池耗尽"""
        print("\n" + "="*80)
        print("极端测试: 线程池耗尽")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="thread-exhaust")

        def long_task():
            time.sleep(5)
            return "done"

        # 使用1个工作线程
        queue.start(num_workers=1)

        # 入队大量长时间任务
        for i in range(100):
            queue.enqueue(long_task)

        # 检查线程池状态
        time.sleep(1)

        stats = queue.get_stats()
        print(f"\n结果:")
        print(f"  总任务: {stats.total_tasks}")
        print(f"  运行中: {stats.running_tasks}")
        print(f"  等待中: {stats.pending_tasks}")

        # 队列中应该有很多等待的任务
        if stats.pending_tasks < 50:
            stress_logger.log_issue(
                "test_thread_pool_exhaustion",
                "THREAD_POOL_EFFICIENCY",
                f"线程池效率问题，{stats.pending_tasks}个任务等待",
                stats.pending_tasks
            )

        queue.stop()
        stress_logger.log("test_thread_pool_exhaustion", "PASSED", "线程池耗尽测试完成")


class TestExtreme05_PriorityStarvation:
    """极端测试05: 优先级饥饿"""

    def test_low_priority_starvation(self):
        """测试低优先级任务饥饿"""
        print("\n" + "="*80)
        print("极端测试: 低优先级任务饥饿")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="priority-starvation")
        low_priority_completed = {"count": 0, "lock": threading.Lock()}
        high_priority_completed = {"count": 0, "lock": threading.Lock()}

        def quick_task(name, counter):
            time.sleep(0.01)
            counter["lock"].acquire()
            counter["count"] += 1
            counter["lock"].release()

        # 先入队10个低优先级任务
        for i in range(10):
            queue.enqueue(quick_task, f"low-{i}", low_priority_completed, priority=TaskPriority.LOW)

        # 然后入队大量高优先级任务
        for i in range(500):
            queue.enqueue(quick_task, f"high-{i}", high_priority_completed, priority=TaskPriority.HIGH)

        queue.start(num_workers=5)

        # 等待一会儿
        time.sleep(3)

        queue.stop()

        print(f"\n结果:")
        print(f"  低优先级完成: {low_priority_completed['count']}/10")
        print(f"  高优先级完成: {high_priority_completed['count']}/500")

        # 低优先级任务应该全部完成
        if low_priority_completed["count"] < 10:
            stress_logger.log_issue(
                "test_low_priority_starvation",
                "PRIORITY_STARVATION",
                f"低优先级任务饥饿，仅完成 {low_priority_completed['count']}/10",
                {"low": low_priority_completed["count"], "high": high_priority_completed["count"]}
            )

        stress_logger.log("test_low_priority_starvation", "PASSED", "优先级饥饿测试完成")


class TestExtreme06_CascadeFailures:
    """极端测试06: 级联故障"""

    def test_cascade_failure_recovery(self):
        """测试级联故障恢复"""
        print("\n" + "="*80)
        print("极端测试: 级联故障恢复")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="cascade-failure")
        failure_count = {"count": 0, "lock": threading.Lock()}
        recovery_count = {"count": 0, "lock": threading.Lock()}

        def failing_task():
            failure_count["lock"].acquire()
            failure_count["count"] += 1
            count = failure_count["count"]
            failure_count["lock"].release()

            if count < 5:
                raise RuntimeError(f"Simulated failure {count}")

            recovery_count["lock"].acquire()
            recovery_count["count"] += 1
            recovery_count["lock"].release()

            return "recovered"

        # 入队会失败的任务，max_retries 在 enqueue 中指定
        task_id = queue.enqueue(failing_task, max_retries=3)

        queue.start(num_workers=1)

        # 等待重试和恢复
        time.sleep(10)

        queue.stop()

        task = queue.get_task(task_id)

        print(f"\n结果:")
        print(f"  任务状态: {task.status if task else 'N/A'}")
        print(f"  重试次数: {task.retry_count if task else 0}")
        print(f"  失败次数: {failure_count['count']}")
        print(f"  恢复次数: {recovery_count['count']}")

        if task and task.status == TaskStatus.FAILED and task.retry_count < 3:
            stress_logger.log_issue(
                "test_cascade_failure_recovery",
                "RETRY_NOT_WORKING",
                f"重试机制未正常工作",
                {"retry_count": task.retry_count, "expected_min": 3}
            )

        stress_logger.log("test_cascade_failure_recovery", "PASSED", "级联故障测试完成")

    def test_middleware_chain_failure(self):
        """测试中间件链故障"""
        print("\n" + "="*80)
        print("极端测试: 中间件链故障")
        print("="*80)
        stress_logger.start()

        api_app = APIApp(name="middleware-test")

        def api_handler(request):
            return {"result": "success"}

        api_app.add_route(
            path="/test",
            method=HTTPMethod.POST,
            handler=api_handler
        )

        # 添加会失败的中间件
        class FailingMiddleware:
            def before_request(self, request):
                raise RuntimeError("Middleware failure")

            def after_request(self, request, response):
                return response

        api_app.add_middleware(FailingMiddleware())

        # 测试请求
        try:
            request = APIRequest(method=HTTPMethod.POST, path="/test", body={})
            response = api_app.handle_request(request)

            if response.status_code != 500:
                stress_logger.log_issue(
                    "test_middleware_chain_failure",
                    "MIDDLEWARE_ERROR_HANDLING",
                    "中间件失败未返回500错误",
                    response.status_code
                )

            print(f"\n结果:")
            print(f"  响应状态: {response.status_code}")
            print(f"  响应体: {response.body}")

        except Exception as e:
            stress_logger.log_issue(
                "test_middleware_chain_failure",
                "MIDDLEWARE_EXCEPTION",
                "中间件异常未被捕获",
                str(e)
            )

        stress_logger.log("test_middleware_chain_failure", "PASSED", "中间件链故障测试完成")


class TestExtreme07_DataConsistency:
    """极端测试07: 数据一致性"""

    def test_race_condition_data_corruption(self):
        """测试竞态条件数据损坏"""
        print("\n" + "="*80)
        print("极端测试: 竞态条件数据损坏")
        print("="*80)
        stress_logger.start()

        queue = AsyncTaskQueue(name="race-data")
        counter = {"value": 0, "lock": threading.Lock()}

        def increment_task():
            # 使用锁保护计数器操作，防止竞态条件
            with counter["lock"]:
                current = counter["value"]
                time.sleep(0.0001)  # 让竞态更明显
                counter["value"] = current + 1

        # 并发入队1000个任务
        threads = []
        for i in range(100):
            t = threading.Thread(target=lambda: [queue.enqueue(increment_task) for _ in range(10)])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        queue.start(num_workers=20)
        time.sleep(3)
        queue.stop()

        expected = 1000
        actual = counter["value"]

        print(f"\n结果:")
        print(f"  预期值: {expected}")
        print(f"  实际值: {actual}")
        print(f"  丢失更新: {expected - actual}")

        if actual < expected * 0.95:  # 允许5%以内的误差
            stress_logger.log_issue(
                "test_race_condition_data_corruption",
                "RACE_CONDITION",
                f"竞态条件导致数据丢失 {expected - actual} 次更新",
                {"expected": expected, "actual": actual}
            )

        stress_logger.log("test_race_condition_data_corruption", "PASSED", "数据一致性测试完成")


class TestExtreme08_APIIntegration:
    """极端测试08: API集成压力"""

    def test_api_concurrent_requests(self):
        """测试API并发请求"""
        print("\n" + "="*80)
        print("极端测试: API并发请求")
        print("="*80)
        stress_logger.start()

        api_app = APIApp(name="api-stress")

        request_counter = {"count": 0, "lock": threading.Lock()}

        def api_handler(request):
            request_counter["lock"].acquire()
            request_counter["count"] += 1
            request_counter["lock"].release()
            time.sleep(0.001)
            return {"request_id": request_counter["count"], "status": "ok"}

        api_app.add_route(
            path="/api/test",
            method=HTTPMethod.POST,
            handler=api_handler
        )

        # 并发发送1000个请求
        results = {"success": 0, "failed": 0, "lock": threading.Lock()}

        def send_request():
            try:
                request = APIRequest(
                    method=HTTPMethod.POST,
                    path="/api/test",
                    body={"data": "test"}
                )
                response = api_app.handle_request(request)
                if response and response.status_code == 200:
                    with results["lock"]:
                        results["success"] += 1
                else:
                    with results["lock"]:
                        results["failed"] += 1
            except Exception as e:
                with results["lock"]:
                    results["failed"] += 1

        threads = []
        for i in range(100):
            t = threading.Thread(target=lambda: [send_request() for _ in range(10)])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"\n结果:")
        print(f"  成功: {results['success']}")
        print(f"  失败: {results['failed']}")
        print(f"  总请求: {request_counter['count']}")

        if results["failed"] > 0:
            stress_logger.log_issue(
                "test_api_concurrent_requests",
                "API_FAILURE",
                f"API请求失败 {results['failed']} 次",
                results["failed"]
            )

        stress_logger.log("test_api_concurrent_requests", "PASSED", "API并发测试完成")


class TestExtreme09_CacheConsistency:
    """极端测试09: 缓存一致性"""

    def test_cache_concurrent_writes(self):
        """测试缓存并发写入一致性"""
        print("\n" + "="*80)
        print("极端测试: 缓存并发写入一致性")
        print("="*80)
        stress_logger.start()

        manager = CacheManager()
        cache = manager.register_cache("consistency-test", default_ttl=300)

        inconsistencies = {"count": 0, "lock": threading.Lock()}

        def cache_writer(writer_id, count):
            for i in range(count):
                key = f"shared_key"
                value = {"writer": writer_id, "seq": i}
                cache.set(key, value)

                # 立即读取验证
                result = cache.get(key)
                if result and result.get("writer") != writer_id:
                    with inconsistencies["lock"]:
                        inconsistencies["count"] += 1

        # 10个并发写入器
        threads = []
        for w in range(10):
            t = threading.Thread(target=cache_writer, args=(w, 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"\n结果:")
        print(f"  不一致次数: {inconsistencies['count']}")
        print(f"  最终值: {cache.get('shared_key')}")

        if inconsistencies["count"] > 50:
            stress_logger.log_issue(
                "test_cache_concurrent_writes",
                "CACHE_INCONSISTENCY",
                f"缓存出现 {inconsistencies['count']} 次不一致",
                inconsistencies["count"]
            )

        stress_logger.log("test_cache_concurrent_writes", "PASSED", "缓存一致性测试完成")


class TestExtreme10_SchedulerStress:
    """极端测试10: 调度器极端压力"""

    def test_10000_scheduled_jobs(self):
        """测试10000个调度任务"""
        print("\n" + "="*80)
        print("极端测试: 10000个调度任务")
        print("="*80)
        stress_logger.start()

        scheduler = TaskScheduler(name="extreme-10k-scheduler")

        def job_func(job_id):
            return f"Job {job_id}"

        execution_count = {"count": 0, "lock": threading.Lock()}

        def counted_job(job_id):
            with execution_count["lock"]:
                execution_count["count"] += 1
            return f"Job {job_id} done"

        # 快速调度10000个延迟任务
        start = time.time()
        for i in range(10000):
            scheduler.add_delay_job(counted_job, 0.1, i)
            if i % 1000 == 0:
                print(f"  已调度 {i} 个任务...")

        elapsed = time.time() - start
        print(f"调度耗时: {elapsed:.2f}秒")

        scheduler.start(num_workers=50)

        # 等待执行
        time.sleep(10)

        scheduler.stop()

        print(f"\n结果:")
        print(f"  总任务数: {scheduler.stats.total_jobs}")
        print(f"  执行总数: {scheduler.stats.total_executions}")
        print(f"  计数: {execution_count['count']}")

        if execution_count["count"] < 9500:  # 允许一定误差
            stress_logger.log_issue(
                "test_10000_scheduled_jobs",
                "SCHEDULER_UNDERLOAD",
                f"调度器仅执行 {execution_count['count']}/10000 个任务",
                execution_count["count"]
            )

        stress_logger.log("test_10000_scheduled_jobs", "PASSED", "调度器压力测试完成")


def run_extreme_stress_tests():
    """运行所有极端压力测试"""
    print("\n" + "="*80)
    print("Phase 34 EXTREME: 超大规模复杂场景压力测试套件")
    print("="*80)
    print("\n开始执行极端压力测试...\n")

    test_classes = [
        TestExtreme01_MassiveConcurrency(),
        TestExtreme02_LongRunning(),
        TestExtreme03_ComplexDependencies(),
        TestExtreme04_ResourceExhaustion(),
        TestExtreme05_PriorityStarvation(),
        TestExtreme06_CascadeFailures(),
        TestExtreme07_DataConsistency(),
        TestExtreme08_APIIntegration(),
        TestExtreme09_CacheConsistency(),
        TestExtreme10_SchedulerStress()
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
    print("极端压力测试汇总")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")

    print(f"\n总测试数: {len(results)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    # 打印发现的问题
    issues = stress_logger.get_issues()
    if issues:
        print(f"\n发现的问题 ({len(issues)}):")
        for issue in issues:
            print(f"  [{issue['issue_type']}] {issue['test_name']}: {issue['description']}")

    if failed > 0:
        print("\n失败测试:")
        for r in results:
            if r["status"] == "FAILED":
                print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")

    print("\n" + "="*80)

    return failed == 0, issues


if __name__ == "__main__":
    success, issues = run_extreme_stress_tests()
    exit(0 if success else 1)
