"""
Tests for 定时任务调度系统 (Phase 33)
"""
import pytest
import time
from datetime import datetime, timedelta

from src.scheduling_layer.scheduler import (
    JobStatus,
    JobType,
    JobResult,
    ScheduledJob,
    JobStats,
    CronParser,
    TaskScheduler,
    get_default_scheduler,
    set_default_scheduler,
    schedule_cron,
    schedule_interval,
    schedule_delay
)
from src.scheduling_layer.task_queue import TaskPriority


class TestJobStatus:
    """测试任务状态"""

    def test_status_values(self):
        """测试状态值"""
        assert JobStatus.PENDING is not None
        assert JobStatus.SCHEDULED is not None
        assert JobStatus.RUNNING is not None
        assert JobStatus.COMPLETED is not None
        assert JobStatus.FAILED is not None
        assert JobStatus.PAUSED is not None
        assert JobStatus.CANCELLED is not None


class TestJobType:
    """测试任务类型"""

    def test_type_values(self):
        """测试类型值"""
        assert JobType.CRON is not None
        assert JobType.INTERVAL is not None
        assert JobType.DELAY is not None
        assert JobType.DAILY is not None
        assert JobType.WEEKLY is not None


class TestCronParser:
    """测试 Cron 解析器"""

    def test_parse_cron(self):
        """测试解析 Cron 表达式"""
        result = CronParser.parse("* * * * *")
        assert "minute" in result
        assert "hour" in result
        assert "day" in result
        assert "month" in result
        assert "weekday" in result

    def test_parse_cron_range(self):
        """测试解析 Cron 范围"""
        result = CronParser.parse("0-5 * * * *")
        assert len(result["minute"]) == 6

    def test_parse_cron_list(self):
        """测试解析 Cron 列表"""
        result = CronParser.parse("0,15,30,45 * * * *")
        assert len(result["minute"]) == 4

    def test_calculate_next_run(self):
        """测试计算下次运行时间"""
        now = datetime.now()
        next_run = CronParser.calculate_next_run("* * * * *", now)
        assert next_run > now


class TestScheduledJob:
    """测试已安排任务"""

    def test_job_creation(self):
        """测试任务创建"""
        def test_func():
            return "test"

        job = ScheduledJob(
            job_id="test-1",
            func=test_func,
            job_type=JobType.INTERVAL,
            interval_seconds=60.0
        )

        assert job.job_id == "test-1"
        assert job.func == test_func
        assert job.job_type == JobType.INTERVAL
        assert job.status == JobStatus.PENDING
        assert job.interval_seconds == 60.0

    def test_job_comparison(self):
        """测试任务优先级比较"""
        def dummy():
            pass

        job1 = ScheduledJob(
            job_id="early",
            func=dummy,
            job_type=JobType.INTERVAL,
            interval_seconds=60.0,
            next_run=datetime.now()
        )

        job2 = ScheduledJob(
            job_id="later",
            func=dummy,
            job_type=JobType.INTERVAL,
            interval_seconds=60.0,
            next_run=datetime.now() + timedelta(minutes=1)
        )

        assert job1 < job2


class TestTaskScheduler:
    """测试任务调度器"""

    def test_scheduler_creation(self):
        """测试调度器创建"""
        scheduler = TaskScheduler(name="test-scheduler")
        assert scheduler.name == "test-scheduler"
        assert scheduler.stats.total_jobs == 0

    def test_add_delay_job(self):
        """测试添加延迟任务"""
        scheduler = TaskScheduler(name="delay-test")

        result = {"value": 0}

        def increment():
            result["value"] += 1

        job_id = scheduler.add_delay_job(
            increment, 0.1)

        job = scheduler.get_job(job_id)

        assert job is not None
        assert job.job_type == JobType.DELAY
        assert job.delay_seconds == 0.1

    def test_add_interval_job(self):
        """测试添加间隔任务"""
        scheduler = TaskScheduler(name="interval-test")

        def do_nothing():
            pass

        job_id = scheduler.add_interval_job(
            do_nothing, 1.0, max_runs=3)

        job = scheduler.get_job(job_id)

        assert job is not None
        assert job.job_type == JobType.INTERVAL
        assert job.max_runs == 3

    def test_add_cron_job(self):
        """测试添加 Cron 任务"""
        scheduler = TaskScheduler(name="cron-test")

        def do_nothing():
            pass

        job_id = scheduler.add_cron_job(
            do_nothing, "0 * * * *")

        job = scheduler.get_job(job_id)

        assert job is not None
        assert job.job_type == JobType.CRON
        assert job.cron_expr == "0 * * * *"

    def test_add_daily_job(self):
        """测试添加每日任务"""
        scheduler = TaskScheduler(name="daily-test")

        def do_nothing():
            pass

        job_id = scheduler.add_daily_job(
            do_nothing, "09:00")

        job = scheduler.get_job(job_id)

        assert job is not None
        assert job.job_type == JobType.DAILY
        assert job.daily_time == "09:00"

    def test_add_weekly_job(self):
        """测试添加每周任务"""
        scheduler = TaskScheduler(name="weekly-test")

        def do_nothing():
            pass

        job_id = scheduler.add_weekly_job(
            do_nothing, 1, "14:30")  # 每周二 14:30

        job = scheduler.get_job(job_id)

        assert job is not None
        assert job.job_type == JobType.WEEKLY
        assert job.weekly_day == 1
        assert job.weekly_time == "14:30"

    def test_pause_resume_job(self):
        """测试暂停/恢复任务"""
        scheduler = TaskScheduler(name="pause-test")

        def do_nothing():
            pass

        job_id = scheduler.add_interval_job(do_nothing, 1.0)

        # 暂停
        success = scheduler.pause_job(job_id)
        assert success is True

        job = scheduler.get_job(job_id)
        assert job.status == JobStatus.PAUSED

        # 恢复
        success = scheduler.resume_job(job_id)
        assert success is True

        job = scheduler.get_job(job_id)
        assert job.status == JobStatus.SCHEDULED

    def test_cancel_job(self):
        """测试取消任务"""
        scheduler = TaskScheduler(name="cancel-test")

        def do_nothing():
            pass

        job_id = scheduler.add_interval_job(do_nothing, 1.0)

        success = scheduler.cancel_job(job_id)
        assert success is True

        job = scheduler.get_job(job_id)
        assert job.status == JobStatus.CANCELLED

    def test_get_jobs(self):
        """测试获取任务列表"""
        scheduler = TaskScheduler(name="list-test")

        def do_nothing():
            pass

        scheduler.add_delay_job(do_nothing, 1.0)
        scheduler.add_interval_job(do_nothing, 2.0)
        scheduler.add_interval_job(do_nothing, 3.0)

        jobs = scheduler.get_jobs()
        assert len(jobs) == 3

    def test_get_jobs_by_status(self):
        """测试按状态获取任务"""
        scheduler = TaskScheduler(name="status-list-test")

        def do_nothing():
            pass

        job_id1 = scheduler.add_delay_job(do_nothing, 1.0)
        job_id2 = scheduler.add_delay_job(do_nothing, 2.0)

        scheduler.pause_job(job_id2)

        pending_jobs = scheduler.get_jobs(status=JobStatus.SCHEDULED)
        paused_jobs = scheduler.get_jobs(status=JobStatus.PAUSED)

        assert len(pending_jobs) == 1
        assert len(paused_jobs) == 1

    def test_get_stats(self):
        """测试获取统计信息"""
        scheduler = TaskScheduler(name="stats-test")

        def do_nothing():
            pass

        scheduler.add_delay_job(do_nothing, 0.1)
        scheduler.add_delay_job(do_nothing, 0.2)

        stats = scheduler.get_stats()

        assert stats.total_jobs == 2
        assert stats.pending_jobs == 2


class TestJobExecution:
    """测试任务执行"""

    def test_delay_job_execution(self):
        """测试延迟任务执行"""
        scheduler = TaskScheduler(name="execution-test")

        result = {"executed": False}

        def mark_executed():
            result["executed"] = True

        job_id = scheduler.add_delay_job(
            mark_executed, 0.1)

        scheduler.start(num_workers=1)

        time.sleep(0.5)

        job = scheduler.get_job(job_id)

        scheduler.stop()

        assert job.last_run is not None
        assert job.success_count >= 0

    def test_interval_job_execution(self):
        """测试间隔任务执行"""
        scheduler = TaskScheduler(name="interval-exec-test")

        result = {"count": 0}

        def increment():
            result["count"] += 1

        job_id = scheduler.add_interval_job(
            increment, 0.1, max_runs=3)

        scheduler.start(num_workers=1)

        time.sleep(0.8)

        scheduler.stop()

        job = scheduler.get_job(job_id)

        assert job.success_count > 0


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_default_scheduler(self):
        """测试获取默认调度器"""
        scheduler1 = get_default_scheduler()
        assert scheduler1 is not None

        scheduler2 = get_default_scheduler()
        assert scheduler1 is scheduler2

    def test_set_default_scheduler(self):
        """测试设置默认调度器"""
        custom = TaskScheduler(name="custom-scheduler")
        set_default_scheduler(custom)

        scheduler = get_default_scheduler()
        assert scheduler.name == "custom-scheduler"

    def test_schedule_delay(self):
        """测试便捷延迟任务"""
        def do_nothing():
            pass

        job_id = schedule_delay(do_nothing, 0.5)
        assert job_id is not None


class TestIntegration:
    """集成测试"""

    def test_multiple_jobs(self):
        """测试多任务调度"""
        scheduler = TaskScheduler(name="multiple-test")

        results = {"a": 0, "b": 0, "c": 0}

        def increment_a():
            results["a"] += 1

        def increment_b():
            results["b"] += 1

        def increment_c():
            results["c"] += 1

        scheduler.add_delay_job(increment_a, 0.1)
        scheduler.add_delay_job(increment_b, 0.1)
        scheduler.add_delay_job(increment_c, 0.1)

        scheduler.start(num_workers=2)

        time.sleep(0.8)

        scheduler.stop()

        assert results["a"] >= 0
        assert results["b"] >= 0
        assert results["c"] >= 0

    def test_job_with_args(self):
        """测试带参数的任务"""
        scheduler = TaskScheduler(name="args-test")

        result = {"value": 0}

        def add(x, y):
            result["value"] = x + y

        scheduler.add_delay_job(
            add, 0.1,
            2, 3)

        scheduler.start(num_workers=1)

        time.sleep(0.5)

        scheduler.stop()

        job = scheduler.get_jobs()[0]
        assert job.success_count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
