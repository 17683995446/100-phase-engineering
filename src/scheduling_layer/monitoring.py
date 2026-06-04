"""
系统健康检查注册中心
提供预定义的系统组件健康检查
"""

import time
import threading
import gc
from typing import Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.utils.health import (
    HealthMonitor,
    HealthCheck,
    ComponentHealthCheck,
    ThresholdHealthCheck,
    DependencyHealthCheck,
    HealthCheckType,
    HealthStatus,
    get_health_monitor,
    create_component_check,
    create_threshold_check,
)
from src.utils.logger import logger


class SystemHealthChecks:
    """系统健康检查集合"""
    
    _initialized = False
    _lock = threading.Lock()
    
    @classmethod
    def initialize(cls, monitor: HealthMonitor = None) -> None:
        """初始化系统健康检查"""
        if cls._initialized:
            return
        
        with cls._lock:
            if cls._initialized:
                return
            
            monitor = monitor or get_health_monitor()
            
            cls._register_memory_check(monitor)
            cls._register_gc_check(monitor)
            cls._register_thread_check(monitor)
            cls._register_cache_check(monitor)
            cls._register_task_queue_check(monitor)
            
            cls._initialized = True
            logger.info("System health checks initialized")
    
    @classmethod
    def _register_memory_check(cls, monitor: HealthMonitor) -> None:
        """注册内存健康检查"""
        if not HAS_PSUTIL:
            logger.warning("psutil not available, skipping memory health check")
            return
        
        def check_memory() -> bool:
            mem = psutil.virtual_memory()
            return mem.percent < 90.0
        
        def get_memory_details() -> Dict[str, Any]:
            mem = psutil.virtual_memory()
            return {
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "used_mb": mem.used / (1024 * 1024),
                "percent": mem.percent
            }
        
        check = create_component_check(
            name="system.memory",
            check_fn=check_memory,
            check_type=HealthCheckType.LIVENESS,
            details_fn=get_memory_details,
            tags=["system", "resource"]
        )
        monitor.register_check(check)
        
        threshold_check = ThresholdHealthCheck(
            name="system.memory.usage",
            metric_fn=lambda: psutil.virtual_memory().percent,
            healthy_threshold=80.0,
            degraded_threshold=70.0,
            higher_is_healthier=False,
            check_type=HealthCheckType.LIVENESS,
            tags=["system", "resource", "threshold"]
        )
        monitor.register_check(threshold_check)
    
    @classmethod
    def _register_gc_check(cls, monitor: HealthMonitor) -> None:
        """注册GC健康检查"""
        
        def check_gc() -> bool:
            gc_stats = gc.get_stats()
            if not gc_stats:
                return True
            for stat in gc_stats:
                if stat.get('collections', 0) > 10000:
                    return False
            return True
        
        def get_gc_details() -> Dict[str, Any]:
            gc_stats = gc.get_stats()
            thresholds = gc.get_threshold()
            return {
                "thresholds": list(thresholds),
                "stats": gc_stats,
                "collected": gc.collect(0)
            }
        
        check = create_component_check(
            name="system.gc",
            check_fn=check_gc,
            check_type=HealthCheckType.LIVENESS,
            details_fn=get_gc_details,
            tags=["system", "gc"]
        )
        monitor.register_check(check)
    
    @classmethod
    def _register_thread_check(cls, monitor: HealthMonitor) -> None:
        """注册线程健康检查"""
        if not HAS_PSUTIL:
            logger.warning("psutil not available, skipping thread health check")
            return
        
        def check_threads() -> bool:
            thread_count = threading.active_count()
            return thread_count < 100
        
        def get_thread_details() -> Dict[str, Any]:
            threads = threading.enumerate()
            return {
                "active_threads": threading.active_count(),
                "daemon_threads": sum(1 for t in threads if t.daemon),
                "thread_names": [t.name for t in threads[:10]]
            }
        
        check = create_component_check(
            name="system.threads",
            check_fn=check_threads,
            check_type=HealthCheckType.LIVENESS,
            details_fn=get_thread_details,
            tags=["system", "threads"]
        )
        monitor.register_check(check)
        
        threshold_check = ThresholdHealthCheck(
            name="system.thread_count",
            metric_fn=lambda: float(threading.active_count()),
            healthy_threshold=80.0,
            degraded_threshold=50.0,
            higher_is_healthier=False,
            check_type=HealthCheckType.LIVENESS,
            tags=["system", "threads", "threshold"]
        )
        monitor.register_check(threshold_check)
    
    @classmethod
    def _register_cache_check(cls, monitor: HealthMonitor) -> None:
        """注册缓存健康检查"""
        try:
            from src.utils.cache import get_cache_manager
            
            def check_cache() -> bool:
                try:
                    manager = get_cache_manager()
                    return manager is not None
                except:
                    return False
            
            def get_cache_details() -> Dict[str, Any]:
                try:
                    manager = get_cache_manager()
                    if manager:
                        return {
                            "cache_count": len(manager._caches),
                            "cache_names": list(manager._caches.keys())
                        }
                    return {}
                except:
                    return {"error": "Cache manager not available"}
            
            check = create_component_check(
                name="cache.manager",
                check_fn=check_cache,
                check_type=HealthCheckType.READINESS,
                details_fn=get_cache_details,
                tags=["cache", "infrastructure"]
            )
            monitor.register_check(check)
        except Exception as e:
            logger.warning(f"Failed to register cache health check: {e}")
    
    @classmethod
    def _register_task_queue_check(cls, monitor: HealthMonitor) -> None:
        """注册任务队列健康检查"""
        try:
            from src.scheduling_layer.task_queue import get_task_queue_manager
            
            def check_queue_manager() -> bool:
                try:
                    manager = get_task_queue_manager()
                    return manager is not None
                except:
                    return False
            
            def get_queue_details() -> Dict[str, Any]:
                try:
                    manager = get_task_queue_manager()
                    if manager:
                        all_stats = manager.get_all_stats()
                        return {
                            "queue_count": len(manager.queues),
                            "queues": list(manager.queues.keys()),
                            "total_tasks": sum(s.total_tasks for s in all_stats.values()),
                            "pending_tasks": sum(s.pending_tasks for s in all_stats.values()),
                            "running_tasks": sum(s.running_tasks for s in all_stats.values())
                        }
                    return {}
                except:
                    return {"error": "Task queue manager not available"}
            
            check = create_component_check(
                name="task.queue.manager",
                check_fn=check_queue_manager,
                check_type=HealthCheckType.READINESS,
                details_fn=get_queue_details,
                tags=["task", "queue", "infrastructure"]
            )
            monitor.register_check(check)
        except Exception as e:
            logger.warning(f"Failed to register task queue health check: {e}")


def setup_system_health_checks() -> HealthMonitor:
    """设置系统健康检查"""
    monitor = get_health_monitor()
    SystemHealthChecks.initialize(monitor)
    return monitor


def get_liveness_status() -> Dict[str, Any]:
    """获取存活探针状态"""
    monitor = get_health_monitor()
    result = monitor.run_all_checks(HealthCheckType.LIVENESS)
    return result.to_dict()


def get_readiness_status() -> Dict[str, Any]:
    """获取就绪探针状态"""
    monitor = get_health_monitor()
    result = monitor.run_all_checks(HealthCheckType.READINESS)
    return result.to_dict()


def get_startup_status() -> Dict[str, Any]:
    """获取启动探针状态"""
    monitor = get_health_monitor()
    result = monitor.run_all_checks(HealthCheckType.STARTUP)
    return result.to_dict()
