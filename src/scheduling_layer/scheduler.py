"""
定时任务调度系统
支持 Cron 表达式、固定间隔、一次性延迟等多种调度方式
"""
import uuid
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from queue import PriorityQueue, Empty

from src.utils.logger import logger
from src.utils.structured_logging import get_logger
from src.utils.prometheus import PrometheusRegistry
from src.scheduling_layer.task_queue import TaskPriority


class JobStatus(Enum):
    """定时任务状态"""
    PENDING = auto()      # 等待中
    SCHEDULED = auto()    # 已安排
    RUNNING = auto()      # 运行中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    PAUSED = auto()       # 已暂停
    CANCELLED = auto()    # 已取消


class JobType(Enum):
    """定时任务类型"""
    CRON = auto()          # Cron 表达式
    INTERVAL = auto()      # 固定间隔
    DELAY = auto()         # 一次性延迟
    DAILY = auto()         # 每日固定时间
    WEEKLY = auto()        # 每周固定时间


@dataclass
class JobResult:
    """定时任务执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ScheduledJob:
    """已安排的任务"""
    job_id: str
    func: Callable
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_result: Optional[JobResult] = None
    cron_expr: Optional[str] = None
    interval_seconds: Optional[float] = None
    delay_seconds: Optional[float] = None
    daily_time: Optional[str] = None
    weekly_day: Optional[int] = None  # 0=周一, 1=周二...
    weekly_time: Optional[str] = None
    max_runs: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "ScheduledJob") -> bool:
        """优先级队列比较（按下次运行时间）"""
        if not self.next_run:
            return False
        if not other.next_run:
            return True
        return self.next_run < other.next_run


@dataclass
class JobStats:
    """任务统计"""
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    paused_jobs: int = 0
    total_executions: int = 0
    avg_execution_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class CronParser:
    """简单的 Cron 表达式解析器"""

    @staticmethod
    def parse(cron_expr: str) -> Dict[str, Any]:
        """解析 Cron 表达式（简化版）"""
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression. Expected 5 parts: minute hour day month weekday")

        return {
            'minute': CronParser._parse_field(parts[0], 0, 59),
            'hour': CronParser._parse_field(parts[1], 0, 23),
            'day': CronParser._parse_field(parts[2], 1, 31),
            'month': CronParser._parse_field(parts[3], 1, 12),
            'weekday': CronParser._parse_field(parts[4], 0, 6)  # 0=周一, 6=周日
        }

    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """解析单个 Cron 字段"""
        if field == '*':
            return list(range(min_val, max_val + 1))

        if '-' in field:
            start, end = map(int, field.split('-'))
            return list(range(start, end + 1))

        if ',' in field:
            return list(map(int, field.split(',')))

        try:
            return [int(field)]
        except ValueError:
            raise ValueError(f"Invalid cron field: {field}")

    @staticmethod
    def calculate_next_run(cron_expr: str, now: Optional[datetime] = None) -> datetime:
        """计算下次运行时间（简化版）"""
        if now is None:
            now = datetime.now()

        parts = CronParser.parse(cron_expr)

        # 简单实现：每分钟运行一次（实际项目需要完整解析）
        next_run = now + timedelta(minutes=1)

        # 重置秒和微秒
        next_run = next_run.replace(second=0, microsecond=0)

        return next_run


class ScheduledJobExecutor:
    """定时任务执行器"""

    def __init__(self, scheduler: "TaskScheduler", job: ScheduledJob):
        self.scheduler = scheduler
        self.job = job

    def execute(self):
        """执行任务"""
        start_time = time.time()
        started_at = datetime.now()

        try:
            result_data = self.job.func(*self.job.args, **self.job.kwargs)
            execution_time = (time.time() - start_time) * 1000

            result = JobResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                started_at=started_at,
                completed_at=datetime.now()
            )

            self.scheduler._on_job_success(self.job, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            result = JobResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                started_at=started_at,
                completed_at=datetime.now()
            )

            self.scheduler._on_job_failure(self.job, result)


class TaskScheduler:
    """任务调度器"""

    def __init__(
        self,
        name: str = "default",
        prom_registry: Optional[PrometheusRegistry] = None
    ):
        self.name = name
        self.prom_registry = prom_registry or PrometheusRegistry(namespace="scheduler")
        self.logger = get_logger(f"scheduler_{name}")

        self.jobs: Dict[str, ScheduledJob] = {}
        self.schedule_queue: PriorityQueue[ScheduledJob] = PriorityQueue()
        self.stats = JobStats()
        self._lock = threading.RLock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._worker_threads: List[threading.Thread] = []
        self._work_queue: deque[ScheduledJob] = deque()
        self._num_workers = 1

        self._setup_metrics()

    def _setup_metrics(self):
        """设置 Prometheus 指标"""
        self.jobs_submitted = self.prom_registry.create_counter(
            f"jobs_submitted_total",
            f"Total jobs submitted for {self.name}"
        )
        self.jobs_completed = self.prom_registry.create_counter(
            f"jobs_completed_total",
            f"Total jobs completed for {self.name}"
        )
        self.jobs_failed = self.prom_registry.create_counter(
            f"jobs_failed_total",
            f"Total jobs failed for {self.name}"
        )
        self.jobs_running = self.prom_registry.create_gauge(
            f"jobs_running",
            f"Current jobs running for {self.name}"
        )

    def add_cron_job(
        self,
        func: Callable,
        cron_expr: str,
        job_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """添加 Cron 任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = ScheduledJob(
            job_id=job_id,
            func=func,
            job_type=JobType.CRON,
            cron_expr=cron_expr,
            priority=priority,
            max_runs=max_runs,
            metadata=metadata or {},
            args=args,
            kwargs=kwargs
        )

        return self._add_job(job)

    def add_interval_job(
        self,
        func: Callable,
        interval_seconds: float,
        job_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """添加固定间隔任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = ScheduledJob(
            job_id=job_id,
            func=func,
            job_type=JobType.INTERVAL,
            interval_seconds=interval_seconds,
            priority=priority,
            max_runs=max_runs,
            metadata=metadata or {},
            args=args,
            kwargs=kwargs
        )

        return self._add_job(job)

    def add_delay_job(
        self,
        func: Callable,
        delay_seconds: float,
        job_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """添加一次性延迟任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = ScheduledJob(
            job_id=job_id,
            func=func,
            job_type=JobType.DELAY,
            delay_seconds=delay_seconds,
            priority=priority,
            max_runs=1,
            metadata=metadata or {},
            args=args,
            kwargs=kwargs
        )

        return self._add_job(job)

    def add_daily_job(
        self,
        func: Callable,
        daily_time: str,
        job_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """添加每日固定时间任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = ScheduledJob(
            job_id=job_id,
            func=func,
            job_type=JobType.DAILY,
            daily_time=daily_time,
            priority=priority,
            max_runs=max_runs,
            metadata=metadata or {},
            args=args,
            kwargs=kwargs
        )

        return self._add_job(job)

    def add_weekly_job(
        self,
        func: Callable,
        weekly_day: int,
        weekly_time: str,
        job_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_runs: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> str:
        """添加每周固定时间任务"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = ScheduledJob(
            job_id=job_id,
            func=func,
            job_type=JobType.WEEKLY,
            weekly_day=weekly_day,
            weekly_time=weekly_time,
            priority=priority,
            max_runs=max_runs,
            metadata=metadata or {},
            args=args,
            kwargs=kwargs
        )

        return self._add_job(job)

    def _add_job(self, job: ScheduledJob) -> str:
        """添加任务（内部方法）"""
        with self._lock:
            job.status = JobStatus.SCHEDULED
            job.next_run = self._calculate_next_run(job)
            self.jobs[job.job_id] = job
            self.schedule_queue.put(job)
            self.stats.total_jobs += 1
            self.stats.pending_jobs += 1

        self.jobs_submitted.inc()
        self.logger.info(
            f"Scheduled job {job.job_id} ({job.job_type.name})",
            job_id=job.job_id,
            job_type=job.job_type.name,
            next_run=job.next_run.isoformat() if job.next_run else None
        )

        return job.job_id

    def _calculate_next_run(self, job: ScheduledJob) -> Optional[datetime]:
        """计算下次运行时间"""
        now = datetime.now()

        if job.job_type == JobType.CRON:
            if job.cron_expr:
                return CronParser.calculate_next_run(job.cron_expr, now)

        elif job.job_type == JobType.INTERVAL:
            if job.interval_seconds:
                if job.last_run:
                    return job.last_run + timedelta(seconds=job.interval_seconds)
                else:
                    return now + timedelta(seconds=job.interval_seconds)

        elif job.job_type == JobType.DELAY:
            if job.delay_seconds:
                if job.last_run is None:
                    return now + timedelta(seconds=job.delay_seconds)
                return None  # 只运行一次

        elif job.job_type == JobType.DAILY:
            if job.daily_time:
                try:
                    hour, minute = map(int, job.daily_time.split(':'))
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    return next_run
                except (ValueError, TypeError):
                    pass

        elif job.job_type == JobType.WEEKLY:
            if job.weekly_day is not None and job.weekly_time:
                try:
                    hour, minute = map(int, job.weekly_time.split(':'))
                    # 简单实现：从现在开始算下周的对应日期
                    days_ahead = (job.weekly_day - now.weekday()) % 7
                    if days_ahead == 0 and (now.hour, now.minute) >= (hour, minute):
                        days_ahead = 7
                    next_run = now + timedelta(days=days_ahead)
                    next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return next_run
                except (ValueError, TypeError):
                    pass

        return None

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
                return False

            job.status = JobStatus.PAUSED
            self.stats.paused_jobs += 1
            self.logger.info(f"Paused job {job_id}")
            return True

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False

            job.status = JobStatus.SCHEDULED
            job.next_run = self._calculate_next_run(job)
            self.schedule_queue.put(job)
            self.stats.paused_jobs -= 1
            self.logger.info(f"Resumed job {job_id}")
            return True

    def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status == JobStatus.COMPLETED:
                return False

            job.status = JobStatus.CANCELLED
            self.logger.info(f"Cancelled job {job_id}")
            return True

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """获取任务"""
        with self._lock:
            return self.jobs.get(job_id)

    def get_jobs(self, status: Optional[JobStatus] = None) -> List[ScheduledJob]:
        """获取所有任务（可选状态过滤）"""
        with self._lock:
            if status:
                return [job for job in self.jobs.values() if job.status == status]
            return list(self.jobs.values())

    def start(self, num_workers: int = 1):
        """启动调度器"""
        if self._running:
            self.logger.warning("Scheduler already running")
            return

        self._running = True
        self._num_workers = num_workers

        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self._scheduler_thread.start()

        # 启动工作线程
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True
            )
            worker.start()
            self._worker_threads.append(worker)

        self.logger.info(f"Started scheduler {self.name} with {num_workers} workers")

    def stop(self):
        """停止调度器"""
        if not self._running:
            return

        self._running = False

        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2.0)

        for worker in self._worker_threads:
            worker.join(timeout=2.0)

        self._worker_threads.clear()
        self.logger.info(f"Stopped scheduler {self.name}")

    def _scheduler_loop(self):
        """调度器主循环"""
        loop_count = 0
        while self._running:
            loop_count += 1
            try:
                job = self.schedule_queue.get(timeout=1.0)
            except Empty:
                if loop_count % 10 == 0:
                    self.logger.debug(f"Scheduler loop idle, checked {loop_count} iterations")
                continue

            if not job or job.job_id not in self.jobs:
                self.logger.warning(f"Job not found in scheduler: {job.job_id if job else 'None'}")
                continue

            with self._lock:
                current_job = self.jobs.get(job.job_id)
                if not current_job:
                    self.logger.warning(f"Job disappeared: {job.job_id}")
                    continue

                if current_job.status != JobStatus.SCHEDULED:
                    self.logger.debug(f"Job {current_job.job_id} status is {current_job.status}, skipping")
                    continue

                now = datetime.now()
                if current_job.next_run and now < current_job.next_run:
                    # 还没到运行时间，重新入队
                    self.schedule_queue.put(current_job)
                    if loop_count % 100 == 0:
                        self.logger.debug(f"Job {current_job.job_id} not ready, waiting until {current_job.next_run}")
                    continue

                # 检查最大运行次数
                if current_job.max_runs and current_job.run_count >= current_job.max_runs:
                    current_job.status = JobStatus.COMPLETED
                    self.stats.pending_jobs -= 1
                    self.logger.info(f"Job {current_job.job_id} reached max runs")
                    continue

                # 加入工作队列
                current_job.status = JobStatus.RUNNING
                self.stats.pending_jobs -= 1
                self.stats.running_jobs += 1
                self.jobs_running.inc()
                self._work_queue.append(current_job)
                self.logger.info(f"Job {current_job.job_id} added to work queue")

    def _worker_loop(self, worker_id: int):
        """工作线程循环"""
        self.logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                job = self._work_queue.popleft()
            except IndexError:
                time.sleep(0.1)
                continue

            executor = ScheduledJobExecutor(self, job)
            executor.execute()

        self.logger.debug(f"Worker {worker_id} stopped")

    def _on_job_success(self, job: ScheduledJob, result: JobResult):
        """任务成功回调"""
        with self._lock:
            job.last_run = datetime.now()
            job.last_result = result
            job.run_count += 1
            job.success_count += 1
            self.stats.total_executions += 1

            # 检查是否需要继续运行
            if job.max_runs and job.run_count >= job.max_runs:
                job.status = JobStatus.COMPLETED
                self.stats.completed_jobs += 1
            else:
                # 计算下次运行时间
                job.next_run = self._calculate_next_run(job)
                if job.next_run:
                    job.status = JobStatus.SCHEDULED
                    self.schedule_queue.put(job)
                else:
                    job.status = JobStatus.COMPLETED
                    self.stats.completed_jobs += 1

            self.stats.running_jobs -= 1

        self.jobs_completed.inc()
        self.jobs_running.dec()
        self.logger.info(
            f"Job {job.job_id} completed successfully in {result.execution_time_ms:.2f}ms",
            job_id=job.job_id,
            execution_time_ms=result.execution_time_ms
        )

    def _on_job_failure(self, job: ScheduledJob, result: JobResult):
        """任务失败回调"""
        with self._lock:
            job.last_run = datetime.now()
            job.last_result = result
            job.run_count += 1
            job.failure_count += 1
            self.stats.total_executions += 1

            # 检查是否需要继续运行
            if job.max_runs and job.run_count >= job.max_runs:
                job.status = JobStatus.FAILED
                self.stats.failed_jobs += 1
            else:
                # 计算下次运行时间
                job.next_run = self._calculate_next_run(job)
                if job.next_run:
                    job.status = JobStatus.SCHEDULED
                    self.schedule_queue.put(job)
                else:
                    job.status = JobStatus.FAILED
                    self.stats.failed_jobs += 1

            self.stats.running_jobs -= 1

        self.jobs_failed.inc()
        self.jobs_running.dec()
        self.logger.error(
            f"Job {job.job_id} failed: {result.error}",
            job_id=job.job_id,
            error=result.error
        )

    def get_stats(self) -> JobStats:
        """获取统计信息"""
        with self._lock:
            self.stats.last_updated = datetime.now()
            return self.stats


# 全局调度器实例
_default_scheduler: Optional[TaskScheduler] = None


def get_default_scheduler() -> TaskScheduler:
    """获取默认调度器"""
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = TaskScheduler()
    return _default_scheduler


def set_default_scheduler(scheduler: TaskScheduler) -> None:
    """设置默认调度器"""
    global _default_scheduler
    _default_scheduler = scheduler


def schedule_cron(
    func: Callable,
    cron_expr: str,
    *args,
    **kwargs
) -> str:
    """便捷函数：安排 Cron 任务"""
    scheduler = get_default_scheduler()
    return scheduler.add_cron_job(func, cron_expr, *args, **kwargs)


def schedule_interval(
    func: Callable,
    interval_seconds: float,
    *args,
    **kwargs
) -> str:
    """便捷函数：安排固定间隔任务"""
    scheduler = get_default_scheduler()
    return scheduler.add_interval_job(func, interval_seconds, *args, **kwargs)


def schedule_delay(
    func: Callable,
    delay_seconds: float,
    *args,
    **kwargs
) -> str:
    """便捷函数：安排延迟任务"""
    scheduler = get_default_scheduler()
    return scheduler.add_delay_job(func, delay_seconds, *args, **kwargs)
