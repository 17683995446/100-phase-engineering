"""
任务队列系统
提供异步任务调度、延迟执行、重试机制和优先级管理
"""
import uuid
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Callable, Union
from collections import defaultdict, deque
from queue import PriorityQueue, Empty

from src.utils.logger import logger
from src.utils.structured_logging import get_logger
from src.utils.prometheus import PrometheusRegistry
from src.utils.telemetry import (
    get_tracer,
    SpanKind,
    SpanStatus,
    Tracer,
    SpanContext,
)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = auto()      # 等待中
    QUEUED = auto()       # 已入队
    RUNNING = auto()      # 执行中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    RETRYING = auto()     # 重试中
    CANCELLED = auto()    # 已取消


class TaskPriority(Enum):
    """任务优先级（数值越小优先级越高）"""
    CRITICAL = 0   # 关键任务
    HIGH = 10      # 高优先级
    NORMAL = 20    # 普通优先级
    LOW = 30       # 低优先级
    BACKGROUND = 40 # 后台任务


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class QueuedTask:
    """队列任务"""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    trace_context: Optional[Dict[str, str]] = None  # 分布式追踪上下文

    def __lt__(self, other: "QueuedTask") -> bool:
        """优先级队列比较"""
        if self.scheduled_at and other.scheduled_at:
            if self.scheduled_at != other.scheduled_at:
                return self.scheduled_at < other.scheduled_at
        elif self.scheduled_at:
            return True
        elif other.scheduled_at:
            return False
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


@dataclass
class QueueStats:
    """队列统计"""
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    retry_tasks: int = 0
    avg_execution_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class AsyncTaskQueue:
    """异步任务队列"""

    def __init__(
        self,
        name: str = "default",
        max_size: int = 0,
        prom_registry: Optional[PrometheusRegistry] = None
    ):
        self.name = name
        self.max_size = max_size
        self.prom_registry = prom_registry or PrometheusRegistry(namespace="task_queue")
        self.logger = get_logger(f"task_queue_{name}")
        self._tracer = get_tracer(f"task_queue.{name}")

        self._queue: PriorityQueue = PriorityQueue()
        self._tasks: Dict[str, QueuedTask] = {}
        self._running: Dict[str, QueuedTask] = {}
        self._lock = threading.RLock()
        self._workers: List[threading.Thread] = []
        self._shutdown = threading.Event()
        self._num_workers = 1

        self.stats = QueueStats()

        self._setup_metrics()

    def _setup_metrics(self):
        """设置 Prometheus 指标"""
        self.tasks_queued = self.prom_registry.create_counter(
            f"tasks_queued_total",
            f"Total tasks queued for {self.name}",
            labels={"priority": "normal"}
        )
        self.tasks_completed = self.prom_registry.create_counter(
            f"tasks_completed_total",
            f"Total tasks completed for {self.name}",
            labels={"status": "success"}
        )
        self.tasks_in_progress = self.prom_registry.create_gauge(
            f"tasks_in_progress",
            f"Current tasks in progress for {self.name}"
        )
        self.queue_size = self.prom_registry.create_gauge(
            f"queue_size",
            f"Current queue size for {self.name}"
        )

    def enqueue(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        trace_context: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """入队任务"""
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # 保存当前追踪上下文
        if trace_context is None:
            current_span = self._tracer.current_span
            if current_span:
                trace_context = {
                    "trace_id": current_span.context.trace_id,
                    "span_id": current_span.context.span_id,
                }

        task = QueuedTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {},
            dependencies=dependencies or [],
            trace_context=trace_context
        )

        with self._lock:
            if self.max_size > 0 and len(self._tasks) >= self.max_size:
                raise RuntimeError(f"Queue is full (max_size={self.max_size})")

            self._tasks[task_id] = task
            self._queue.put(task)
            self.stats.total_tasks += 1
            self.stats.pending_tasks += 1

        self.tasks_queued.inc()
        self.queue_size.inc()

        self.logger.info(
            f"Enqueued task {task_id}",
            task_id=task_id,
            priority=priority.name,
            scheduled=scheduled_at.isoformat() if scheduled_at else None
        )

        return task_id

    def dequeue(self, timeout: Optional[float] = None) -> Optional[QueuedTask]:
        """出队任务"""
        try:
            task = self._queue.get(timeout=timeout)
            with self._lock:
                task.status = TaskStatus.QUEUED
                self.stats.pending_tasks -= 1
            return task
        except Empty:
            return None

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.get_task(task_id)
        return task.status if task else None

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        task = self.get_task(task_id)
        return task.result if task else None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return False

            task.status = TaskStatus.CANCELLED
            self.logger.info(f"Cancelled task {task_id}")
            return True

    def start(self, num_workers: int = 1):
        """启动队列处理器"""
        self._num_workers = num_workers
        self._shutdown.clear()

        for i in range(num_workers):
            worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self._workers.append(worker)

        self.logger.info(f"Started {num_workers} workers for queue {self.name}")

    def stop(self, timeout: Optional[float] = None):
        """停止队列处理器"""
        self._shutdown.set()

        for worker in self._workers:
            worker.join(timeout=timeout)

        self._workers.clear()
        self.logger.info(f"Stopped workers for queue {self.name}")

    def _worker(self, worker_id: int):
        """工作线程"""
        self.logger.debug(f"Worker {worker_id} started")

        while not self._shutdown.is_set():
            task = self.dequeue(timeout=1.0)
            if not task:
                continue

            self._execute_task(task, worker_id)

        self.logger.debug(f"Worker {worker_id} stopped")

    def _execute_task(self, task: QueuedTask, worker_id: int):
        """执行任务"""
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self._running[task.task_id] = task
            self.stats.running_tasks += 1

        self.tasks_in_progress.inc()
        self.logger.info(f"Executing task {task.task_id}", task_id=task.task_id)

        # 构建 Span 上下文
        span_context = None
        if task.trace_context:
            # 从追踪上下文重建 SpanContext
            span_context = SpanContext(
                trace_id=task.trace_context["trace_id"],
                span_id=task.trace_context["span_id"],
                trace_flags=1,  # 默认采样
            )
        
        # 开始任务追踪 Span
        span = self._tracer.start_span(
            name=f"task.{task.func.__name__}",
            kind=SpanKind.CONSUMER,
            context=span_context,
            attributes={
                "task.id": task.task_id,
                "task.priority": task.priority.name,
                "task.worker_id": worker_id,
                "task.retry_count": task.retry_count,
            }
        )

        start_time = time.time()

        try:
            if task.timeout:
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Task timed out after {task.timeout}s")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(task.timeout))

            result = task.func(*task.args, **task.kwargs)

            if task.timeout:
                signal.alarm(0)

            execution_time = (time.time() - start_time) * 1000

            span.set_status(SpanStatus.OK)
            span.set_attributes({
                "task.execution_time_ms": execution_time,
            })
            
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = TaskResult(success=True, data=result, execution_time_ms=execution_time)
                self.stats.completed_tasks += 1
                self.stats.running_tasks -= 1
                if task.task_id in self._running:
                    del self._running[task.task_id]

            self.tasks_completed.inc()
            self.tasks_in_progress.dec()

            self.logger.info(
                f"Task {task.task_id} completed in {execution_time:.2f}ms",
                task_id=task.task_id,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            span.set_status(SpanStatus.ERROR, error_msg)
            span.add_event("exception", {
                "exception.type": type(e).__name__,
                "exception.message": error_msg,
            })

            with self._lock:
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.RETRYING
                    task.retry_count += 1
                    self.stats.retry_tasks += 1
                    self._queue.put(task)
                    self.logger.warning(
                        f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries}): {error_msg}",
                        task_id=task.task_id
                    )
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    task.result = TaskResult(success=False, error=error_msg, execution_time_ms=execution_time)
                    self.stats.failed_tasks += 1
                    self.stats.running_tasks -= 1
                    if task.task_id in self._running:
                        del self._running[task.task_id]

            self.tasks_completed.inc()
            self.tasks_in_progress.dec()

            if task.status == TaskStatus.FAILED:
                self.logger.error(
                    f"Task {task.task_id} failed after {task.max_retries} retries: {error_msg}",
                    task_id=task.task_id,
                    error=error_msg
                )
        finally:
            # 结束 Span
            self._tracer.end_current_span()

    def get_stats(self) -> QueueStats:
        """获取队列统计"""
        with self._lock:
            self.stats.pending_tasks = self._queue.qsize()
            self.stats.running_tasks = len(self._running)
            self.stats.last_updated = datetime.now()
            return self.stats

    def clear_completed(self, before: Optional[datetime] = None):
        """清除已完成的任务"""
        with self._lock:
            if before is None:
                before = datetime.now()

            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task.completed_at and task.completed_at < before:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]

            self.logger.info(f"Cleared {len(to_remove)} completed tasks")


class TaskQueueManager:
    """任务队列管理器"""

    def __init__(self):
        self.queues: Dict[str, AsyncTaskQueue] = {}
        self.logger = get_logger("task_queue_manager")

    def create_queue(
        self,
        name: str,
        num_workers: int = 1,
        prom_registry: Optional[PrometheusRegistry] = None
    ) -> AsyncTaskQueue:
        """创建队列"""
        if name in self.queues:
            self.logger.warning(f"Queue {name} already exists, returning existing queue")
            return self.queues[name]

        queue = AsyncTaskQueue(name=name, prom_registry=prom_registry)
        queue.start(num_workers=num_workers)
        self.queues[name] = queue

        self.logger.info(f"Created queue {name} with {num_workers} workers")
        return queue

    def get_queue(self, name: str) -> Optional[AsyncTaskQueue]:
        """获取队列"""
        return self.queues.get(name)

    def delete_queue(self, name: str, timeout: float = 5.0) -> bool:
        """删除队列"""
        queue = self.queues.get(name)
        if not queue:
            return False

        queue.stop(timeout=timeout)
        del self.queues[name]

        self.logger.info(f"Deleted queue {name}")
        return True

    def enqueue(
        self,
        queue_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Optional[str]:
        """入队到指定队列"""
        queue = self.queues.get(queue_name)
        if not queue:
            self.logger.error(f"Queue {queue_name} not found")
            return None

        return queue.enqueue(func, *args, **kwargs)

    def get_all_stats(self) -> Dict[str, QueueStats]:
        """获取所有队列统计"""
        return {
            name: queue.get_stats()
            for name, queue in self.queues.items()
        }


_default_manager: Optional[TaskQueueManager] = None


def get_task_queue_manager() -> TaskQueueManager:
    """获取默认任务队列管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = TaskQueueManager()
    return _default_manager


def create_task_queue(
    name: str,
    num_workers: int = 1
) -> TaskQueue:
    """创建任务队列（便捷函数）"""
    manager = get_task_queue_manager()
    return manager.create_queue(name, num_workers=num_workers)


def enqueue_task(
    queue_name: str,
    func: Callable,
    *args,
    **kwargs
) -> Optional[str]:
    """入队任务（便捷函数）"""
    manager = get_task_queue_manager()
    return manager.enqueue(queue_name, func, *args, **kwargs)
