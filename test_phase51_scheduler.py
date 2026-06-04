"""
Phase 51 - 任务调度与定时器测试
验证任务调度、定时执行和延迟任务功能是否正常工作
"""
import time
import unittest
from datetime import datetime, timedelta
from src.utils.task_scheduler import (
    TaskScheduler,
    Timer,
    TaskStatus,
    TaskType,
    get_task_scheduler,
    get_timer
)


class TestTaskScheduler(unittest.TestCase):
    """任务调度器测试"""

    def setUp(self):
        """测试前设置"""
        self.scheduler = TaskScheduler(max_workers=2)
        self.results = []

    def tearDown(self):
        """测试后清理"""
        self.scheduler.stop()

    def _task_func(self, value):
        """测试任务函数"""
        self.results.append(value)

    def test_schedule_once(self):
        """测试一次性任务"""
        execute_at = datetime.now() + timedelta(seconds=0.1)
        task_id = self.scheduler.schedule_once(
            "test-once", self._task_func, execute_at, "once"
        )
        self.assertIsNotNone(task_id)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.name, "test-once")
        self.assertEqual(task.task_type, TaskType.ONCE)

    def test_schedule_delayed(self):
        """测试延迟任务"""
        task_id = self.scheduler.schedule_delayed(
            "test-delayed", self._task_func, 0.1, "delayed"
        )
        self.assertIsNotNone(task_id)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.task_type, TaskType.ONCE)

    def test_schedule_periodic(self):
        """测试周期性任务"""
        task_id = self.scheduler.schedule_periodic(
            "test-periodic", self._task_func, 0.1, max_runs=3
        )
        self.assertIsNotNone(task_id)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.task_type, TaskType.PERIODIC)
        self.assertEqual(task.max_runs, 3)

    def test_task_execution(self):
        """测试任务执行"""
        self.scheduler.start()
        execute_at = datetime.now() + timedelta(seconds=0.1)
        task_id = self.scheduler.schedule_once(
            "exec-test", self._task_func, execute_at, "executed"
        )

        # 等待任务执行
        time.sleep(0.3)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIn("executed", self.results)

    def test_periodic_execution(self):
        """测试周期性任务执行"""
        self.scheduler.start()
        task_id = self.scheduler.schedule_periodic(
            "periodic-test", self._task_func, 0.1, max_runs=2, value="periodic"
        )

        # 等待任务执行多次
        time.sleep(0.5)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.run_count, 2)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_cancel_task(self):
        """测试取消任务"""
        execute_at = datetime.now() + timedelta(seconds=1)
        task_id = self.scheduler.schedule_once(
            "cancel-test", self._task_func, execute_at, "cancelled"
        )

        result = self.scheduler.cancel_task(task_id)
        self.assertTrue(result)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.CANCELLED)

    def test_get_all_tasks(self):
        """测试获取所有任务"""
        self.scheduler.schedule_delayed("task1", self._task_func, 1, "a")
        self.scheduler.schedule_delayed("task2", self._task_func, 2, "b")

        tasks = self.scheduler.get_all_tasks()
        self.assertEqual(len(tasks), 2)

    def test_get_tasks_by_status(self):
        """测试按状态获取任务"""
        self.scheduler.schedule_delayed("task1", self._task_func, 1, "a")

        tasks = self.scheduler.get_tasks_by_status(TaskStatus.SCHEDULED)
        self.assertEqual(len(tasks), 1)

    def test_task_failure(self):
        """测试任务失败"""
        def fail_func():
            raise ValueError("Task failed")

        self.scheduler.start()
        execute_at = datetime.now() + timedelta(seconds=0.1)
        task_id = self.scheduler.schedule_once("fail-test", fail_func, execute_at)

        time.sleep(0.3)

        task = self.scheduler.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertIsNotNone(task.error_message)

    def test_stats(self):
        """测试统计"""
        self.scheduler.schedule_delayed("task1", self._task_func, 1, "a")
        self.scheduler.schedule_delayed("task2", self._task_func, 2, "b")

        stats = self.scheduler.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["pending"], 2)


class TestTimer(unittest.TestCase):
    """定时器测试"""

    def setUp(self):
        """测试前设置"""
        self.timer = Timer()
        self.results = []

    def tearDown(self):
        """测试后清理"""
        self.timer.clear()

    def _callback(self, value):
        """测试回调"""
        self.results.append(value)

    def test_set_timeout(self):
        """测试超时设置"""
        self.timer.set_timeout("test-timeout", self._callback, 0.1, "timeout")
        time.sleep(0.2)
        self.assertIn("timeout", self.results)

    def test_set_interval(self):
        """测试间隔设置"""
        self.timer.set_interval("test-interval", self._callback, 0.1, "interval")
        time.sleep(0.35)
        self.timer.cancel("test-interval")

        # 应该执行了2-3次
        self.assertGreaterEqual(len(self.results), 2)

    def test_cancel_timeout(self):
        """测试取消超时"""
        self.timer.set_timeout("test-cancel", self._callback, 0.2, "cancelled")
        result = self.timer.cancel("test-cancel")
        self.assertTrue(result)

        time.sleep(0.3)
        self.assertNotIn("cancelled", self.results)

    def test_clear(self):
        """测试清除所有"""
        self.timer.set_timeout("t1", self._callback, 0.5, "a")
        self.timer.set_timeout("t2", self._callback, 0.5, "b")
        self.timer.clear()

        time.sleep(0.6)
        self.assertEqual(len(self.results), 0)


class TestGlobalInstances(unittest.TestCase):
    """全局实例测试"""

    def test_get_task_scheduler(self):
        """测试获取全局调度器"""
        s1 = get_task_scheduler()
        s2 = get_task_scheduler()
        self.assertIs(s1, s2)

    def test_get_timer(self):
        """测试获取全局定时器"""
        t1 = get_timer()
        t2 = get_timer()
        self.assertIs(t1, t2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 51 - 任务调度与定时器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTaskScheduler))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTimer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstances))

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
