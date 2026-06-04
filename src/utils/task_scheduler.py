"""
任务调度与定时器
提供任务调度、定时执行、延迟任务和周期性任务功能
"""
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from queue import PriorityQueue

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    SCHEDULED = auto()


class TaskType(Enum):
    """任务类型"""
    ONCE = auto()       # 一次性任务
    PERIODIC = auto()   # 周期性任务
    DELAYED = auto()    # 延迟任务
    CRON = auto()       # Cron表达式任务


@dataclass
class ScheduledTask:
    """计划任务"""
    task_id: str
    name: str
    task_type: TaskType
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime = field(default_factory=datetime.now)
    execute_at: Optional[datetime] = None
    interval_seconds: Optional[float] = None
    max_runs: Optional[int] = None
    status: TaskStatus = TaskStatus.SCHEDULED
    run_count: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type.name,
            "status": self.status.name,
            "scheduled_at": self.scheduled_at.isoformat(),
            "execute_at": self.execute_at.isoformat() if self.execute_at else None,
            "interval_seconds": self.interval_seconds,
            "max_runs": self.max_runs,
            "run_count": self.run_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None
        }


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 5):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("task.scheduler")
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._max_workers = max_workers
        self._worker_semaphore = threading.Semaphore(max_workers)
    
    def schedule_once(self, name: str, func: Callable, 
                      execute_at: datetime,
                      *args, **kwargs) -> str:
        """调度一次性任务"""
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            task_type=TaskType.ONCE,
            func=func,
            args=args,
            kwargs=kwargs,
            execute_at=execute_at,
            next_run=execute_at
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        self._logger.info(f"Scheduled once task: {name} at {execute_at}")
        return task_id
    
    def schedule_delayed(self, name: str, func: Callable,
                         delay_seconds: float,
                         *args, **kwargs) -> str:
        """调度延迟任务"""
        execute_at = datetime.now() + timedelta(seconds=delay_seconds)
        return self.schedule_once(name, func, execute_at, *args, **kwargs)
    
    def schedule_periodic(self, name: str, func: Callable,
                          interval_seconds: float,
                          max_runs: Optional[int] = None,
                          *args, **kwargs) -> str:
        """调度周期性任务"""
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            task_type=TaskType.PERIODIC,
            func=func,
            args=args,
            kwargs=kwargs,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
            next_run=datetime.now() + timedelta(seconds=interval_seconds)
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        self._logger.info(f"Scheduled periodic task: {name} every {interval_seconds}s")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
                self._logger.info(f"Cancelled task: {task_id}")
                return True
            return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        with self._lock:
            return [task.to_dict() for task in self._tasks.values()]
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[ScheduledTask]:
        """按状态获取任务"""
        with self._lock:
            return [
                task for task in self._tasks.values()
                if task.status == status
            ]
    
    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self._scheduler_thread.start()
        self._logger.info("Task scheduler started")
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        self._logger.info("Task scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """调度循环"""
        while self._running:
            now = datetime.now()
            
            with self._lock:
                tasks_to_run = []
                for task in list(self._tasks.values()):
                    if task.status not in (TaskStatus.SCHEDULED, TaskStatus.PENDING):
                        continue
                    
                    if task.next_run and task.next_run <= now:
                        tasks_to_run.append(task)
            
            for task in tasks_to_run:
                self._execute_task(task)
            
            time.sleep(0.1)
    
    def _execute_task(self, task: ScheduledTask) -> None:
        """执行任务"""
        if not self._worker_semaphore.acquire(blocking=False):
            return
        
        def run():
            try:
                task.status = TaskStatus.RUNNING
                task.last_run = datetime.now()
                task.run_count += 1
                
                self._logger.info(f"Executing task: {task.name}")
                task.func(*task.args, **task.kwargs)
                
                if task.task_type == TaskType.PERIODIC:
                    if task.max_runs and task.run_count >= task.max_runs:
                        task.status = TaskStatus.COMPLETED
                        task.next_run = None
                    else:
                        task.status = TaskStatus.SCHEDULED
                        task.next_run = datetime.now() + timedelta(
                            seconds=task.interval_seconds or 0
                        )
                else:
                    task.status = TaskStatus.COMPLETED
                    task.next_run = None
                
                self._logger.info(f"Task completed: {task.name}")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                self._logger.error(f"Task failed: {task.name} - {e}")
            
            finally:
                self._worker_semaphore.release()
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._tasks)
            completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
            running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
            pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.SCHEDULED)
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": pending
            }


class Timer:
    """简单定时器"""
    
    def __init__(self):
        self._callbacks: Dict[str, Tuple[Callable, float, bool]] = {}
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("timer")
    
    def set_timeout(self, name: str, callback: Callable, 
                    delay_seconds: float, *args, **kwargs) -> str:
        """设置超时回调"""
        with self._lock:
            self._cancel_existing(name)
            
            def wrapper():
                try:
                    callback(*args, **kwargs)
                finally:
                    with self._lock:
                        self._timers.pop(name, None)
            
            timer = threading.Timer(delay_seconds, wrapper)
            self._timers[name] = timer
            timer.start()
            
            return name
    
    def set_interval(self, name: str, callback: Callable,
                     interval_seconds: float, *args, **kwargs) -> str:
        """设置间隔回调"""
        with self._lock:
            self._cancel_existing(name)
            
            def wrapper():
                try:
                    callback(*args, **kwargs)
                finally:
                    with self._lock:
                        if name in self._callbacks:
                            _, interval, _ = self._callbacks[name]
                            self._schedule_interval(name, interval)
            
            self._callbacks[name] = (wrapper, interval_seconds, True)
            return self._schedule_interval(name, interval_seconds)
    
    def _schedule_interval(self, name: str, interval: float) -> str:
        """调度间隔任务"""
        timer = threading.Timer(interval, self._callbacks[name][0])
        self._timers[name] = timer
        timer.start()
        return name
    
    def cancel(self, name: str) -> bool:
        """取消定时器"""
        with self._lock:
            return self._cancel_existing(name)
    
    def _cancel_existing(self, name: str) -> bool:
        """取消现有定时器"""
        cancelled = False
        if name in self._timers:
            self._timers[name].cancel()
            del self._timers[name]
            cancelled = True
        if name in self._callbacks:
            del self._callbacks[name]
            cancelled = True
        return cancelled
    
    def clear(self) -> None:
        """清除所有定时器"""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            self._callbacks.clear()


# 全局实例
_scheduler: Optional[TaskScheduler] = None
_timer: Optional[Timer] = None


def get_task_scheduler(max_workers: int = 5) -> TaskScheduler:
    """获取任务调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler(max_workers)
    return _scheduler


def get_timer() -> Timer:
    """获取定时器"""
    global _timer
    if _timer is None:
        _timer = Timer()
    return _timer
