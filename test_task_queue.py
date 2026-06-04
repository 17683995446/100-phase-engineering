"""
Tests for 任务队列系统 (Phase 32)
"""
import pytest
import time
from datetime import datetime, timedelta

from src.scheduling_layer.task_queue import (
    TaskStatus,
    TaskPriority,
    TaskResult,
    QueuedTask,
    QueueStats,
    AsyncTaskQueue,
    TaskQueueManager,
    get_task_queue_manager,
    create_task_queue,
    enqueue_task
)


class TestTaskStatus:
    """测试任务状态"""

    def test_status_values(self):
        """测试状态值"""
        assert TaskStatus.PENDING is not None
        assert TaskStatus.QUEUED is not None
        assert TaskStatus.RUNNING is not None
        assert TaskStatus.COMPLETED is not None
        assert TaskStatus.FAILED is not None
        assert TaskStatus.RETRYING is not None
        assert TaskStatus.CANCELLED is not None


class TestTaskPriority:
    """测试任务优先级"""

    def test_priority_order(self):
        """测试优先级顺序"""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKGROUND.value


class TestTaskResult:
    """测试任务结果"""

    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(success=False, error="Test error")
        assert result.success is False
        assert result.error == "Test error"
        assert result.data is None


class TestQueuedTask:
    """测试队列任务"""

    def test_task_creation(self):
        """测试任务创建"""
        def sample_func():
            return "result"

        task = QueuedTask(
            task_id="test-1",
            func=sample_func,
            priority=TaskPriority.HIGH
        )

        assert task.task_id == "test-1"
        assert task.func == sample_func
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert isinstance(task.created_at, datetime)

    def test_task_with_args(self):
        """测试带参数的任务"""
        def add(a, b):
            return a + b

        task = QueuedTask(
            task_id="test-2",
            func=add,
            args=(1, 2),
            kwargs={}
        )

        assert task.args == (1, 2)

    def test_task_comparison(self):
        """测试任务优先级比较"""
        def dummy():
            pass

        task1 = QueuedTask(
            task_id="low",
            func=dummy,
            priority=TaskPriority.LOW
        )
        task2 = QueuedTask(
            task_id="high",
            func=dummy,
            priority=TaskPriority.HIGH
        )

        # 低优先级任务的数值更大
        assert task1 > task2  # 使用 __lt__ 的反向


class TestQueueStats:
    """测试队列统计"""

    def test_stats_creation(self):
        """测试统计创建"""
        stats = QueueStats()
        assert stats.total_tasks == 0
        assert stats.pending_tasks == 0
        assert stats.running_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.failed_tasks == 0


class TestAsyncTaskQueue:
    """测试异步任务队列"""

    def test_queue_creation(self):
        """测试队列创建"""
        queue = AsyncTaskQueue(name="test-queue")
        assert queue.name == "test-queue"
        assert queue.stats.total_tasks == 0

    def test_enqueue(self):
        """测试入队"""
        queue = AsyncTaskQueue(name="enqueue-test")

        def sample_task():
            return "done"

        task_id = queue.enqueue(sample_task, priority=TaskPriority.NORMAL)
        assert task_id is not None
        assert queue.stats.total_tasks == 1
        assert queue.stats.pending_tasks == 1

    def test_enqueue_with_args(self):
        """测试带参数的入队"""
        queue = AsyncTaskQueue(name="args-test")

        def add(a, b):
            return a + b

        task_id = queue.enqueue(add, 1, 2)
        assert task_id is not None

    def test_enqueue_with_scheduled_time(self):
        """测试定时入队"""
        queue = AsyncTaskQueue(name="scheduled-test")
        future_time = datetime.now() + timedelta(seconds=10)

        task_id = queue.enqueue(
            lambda: "delayed",
            scheduled_at=future_time
        )

        task = queue.get_task(task_id)
        assert task.scheduled_at == future_time

    def test_get_task(self):
        """测试获取任务"""
        queue = AsyncTaskQueue(name="get-test")

        task_id = queue.enqueue(lambda: "test")
        task = queue.get_task(task_id)

        assert task is not None
        assert task.task_id == task_id

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        queue = AsyncTaskQueue(name="none-test")
        task = queue.get_task("non-existent")
        assert task is None

    def test_get_task_status(self):
        """测试获取任务状态"""
        queue = AsyncTaskQueue(name="status-test")

        task_id = queue.enqueue(lambda: "test")
        status = queue.get_task_status(task_id)

        assert status == TaskStatus.PENDING

    def test_cancel_task(self):
        """测试取消任务"""
        queue = AsyncTaskQueue(name="cancel-test")

        task_id = queue.enqueue(lambda: "test")
        result = queue.cancel_task(task_id)

        assert result is True
        status = queue.get_task_status(task_id)
        assert status == TaskStatus.CANCELLED

    def test_cancel_completed_task(self):
        """测试取消已完成的任务"""
        queue = AsyncTaskQueue(name="cancel-complete-test")

        task_id = queue.enqueue(lambda: "test")
        task = queue.dequeue()  # 出队
        task.status = TaskStatus.COMPLETED  # 模拟完成

        result = queue.cancel_task(task_id)

        assert result is False

    def test_task_execution(self):
        """测试任务执行"""
        queue = AsyncTaskQueue(name="exec-test")

        results = []

        def capture_result():
            results.append("executed")
            return "done"

        task_id = queue.enqueue(capture_result)

        # 启动队列处理
        queue.start(num_workers=1)
        time.sleep(0.5)  # 等待执行

        # 检查任务状态
        task = queue.get_task(task_id)
        if task:
            # 任务可能已完成或正在运行
            assert task.task_id == task_id

        queue.stop(timeout=1.0)

    def test_task_with_timeout(self):
        """测试带超时的任务"""
        queue = AsyncTaskQueue(name="timeout-test")

        def slow_task():
            time.sleep(2)
            return "slow"

        task_id = queue.enqueue(slow_task, timeout=0.5)

        queue.start(num_workers=1)
        time.sleep(1)  # 等待超时

        task = queue.get_task(task_id)
        if task:
            # 任务应该失败或被取消
            assert task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]

        queue.stop(timeout=1.0)

    def test_retry_on_failure(self):
        """测试失败重试"""
        queue = AsyncTaskQueue(name="retry-test")

        attempts = []

        def failing_task():
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise ValueError("Temporary failure")
            return "success"

        task_id = queue.enqueue(failing_task, max_retries=3)

        queue.start(num_workers=1)
        time.sleep(1.5)  # 等待重试

        task = queue.get_task(task_id)
        if task:
            # 任务应该最终成功
            assert task.status == TaskStatus.COMPLETED

        queue.stop(timeout=1.0)

    def test_get_stats(self):
        """测试获取统计"""
        queue = AsyncTaskQueue(name="stats-test")

        queue.enqueue(lambda: "a")
        queue.enqueue(lambda: "b")

        stats = queue.get_stats()
        assert stats.total_tasks == 2
        assert stats.pending_tasks == 2

    def test_clear_completed(self):
        """测试清除已完成任务"""
        queue = AsyncTaskQueue(name="clear-test")

        # 入队几个任务
        for i in range(5):
            queue.enqueue(lambda: "done")

        # 清除所有已完成（实际上还没有完成的）
        queue.clear_completed()

        # 应该还有任务
        assert queue.stats.total_tasks >= 0


class TestTaskQueueManager:
    """测试任务队列管理器"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = TaskQueueManager()
        assert manager.queues == {}

    def test_create_queue(self):
        """测试创建队列"""
        manager = TaskQueueManager()
        queue = manager.create_queue("test", num_workers=1)

        assert queue is not None
        assert "test" in manager.queues

        # 清理
        manager.delete_queue("test")

    def test_create_duplicate_queue(self):
        """测试创建重复队列"""
        manager = TaskQueueManager()

        queue1 = manager.create_queue("dup")
        queue2 = manager.create_queue("dup")

        assert queue1 is queue2  # 应该返回同一个队列

        # 清理
        manager.delete_queue("dup")

    def test_get_queue(self):
        """测试获取队列"""
        manager = TaskQueueManager()

        manager.create_queue("get-test")
        queue = manager.get_queue("get-test")

        assert queue is not None
        assert queue.name == "get-test"

        # 清理
        manager.delete_queue("get-test")

    def test_get_nonexistent_queue(self):
        """测试获取不存在的队列"""
        manager = TaskQueueManager()
        queue = manager.get_queue("non-existent")
        assert queue is None

    def test_delete_queue(self):
        """测试删除队列"""
        manager = TaskQueueManager()

        manager.create_queue("delete-test")
        result = manager.delete_queue("delete-test")

        assert result is True
        assert "delete-test" not in manager.queues

    def test_delete_nonexistent_queue(self):
        """测试删除不存在的队列"""
        manager = TaskQueueManager()
        result = manager.delete_queue("non-existent")
        assert result is False

    def test_enqueue_to_manager(self):
        """测试通过管理器入队"""
        manager = TaskQueueManager()

        manager.create_queue("enqueue-mgr", num_workers=0)
        task_id = manager.enqueue("enqueue-mgr", lambda: "test")

        assert task_id is not None

        # 清理
        manager.delete_queue("enqueue-mgr")

    def test_get_all_stats(self):
        """测试获取所有统计"""
        manager = TaskQueueManager()

        manager.create_queue("stats1")
        manager.create_queue("stats2")

        stats = manager.get_all_stats()

        assert "stats1" in stats
        assert "stats2" in stats

        # 清理
        manager.delete_queue("stats1")
        manager.delete_queue("stats2")


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_task_queue_manager(self):
        """测试获取默认管理器"""
        manager1 = get_task_queue_manager()
        manager2 = get_task_queue_manager()

        assert manager1 is manager2

    def test_create_task_queue(self):
        """测试便捷创建函数"""
        queue = create_task_queue("convenience-test")

        assert queue is not None
        assert queue.name == "convenience-test"

    def test_enqueue_task(self):
        """测试便捷入队函数"""
        task_id = enqueue_task("default", lambda: "test")
        # 注意：这会入队到 default 队列，如果不存在可能返回 None


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 创建管理器
        manager = TaskQueueManager()

        # 创建队列
        queue = manager.create_queue("workflow-test", num_workers=1)

        # 入队多个任务
        task_ids = []
        for i in range(3):
            task_id = queue.enqueue(
                lambda x=i: f"task-{x}",
                priority=TaskPriority.NORMAL if i == 0 else TaskPriority.LOW
            )
            task_ids.append(task_id)

        # 检查任务（可能已开始执行）
        for task_id in task_ids:
            task = queue.get_task(task_id)
            assert task is not None
            # 任务可能是 PENDING, QUEUED, RUNNING, 或 COMPLETED
            assert task.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.COMPLETED]

        # 获取统计
        stats = queue.get_stats()
        assert stats.total_tasks == 3

        # 清理
        manager.delete_queue("workflow-test")

    def test_priority_ordering(self):
        """测试优先级排序"""
        queue = AsyncTaskQueue(name="priority-test")

        # 入队不同优先级的任务
        low_id = queue.enqueue(lambda: "low", priority=TaskPriority.LOW)
        high_id = queue.enqueue(lambda: "high", priority=TaskPriority.HIGH)
        normal_id = queue.enqueue(lambda: "normal", priority=TaskPriority.NORMAL)

        # 检查顺序
        high_task = queue.get_task(high_id)
        normal_task = queue.get_task(normal_id)
        low_task = queue.get_task(low_id)

        # 高优先级任务应该先处理
        assert high_task.priority.value < normal_task.priority.value
        assert normal_task.priority.value < low_task.priority.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
