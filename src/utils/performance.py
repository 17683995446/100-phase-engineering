"""
系统性能优化与基准测试框架
提供性能基准测试、性能监控和性能报告功能
"""
import time
import threading
import statistics
import gc
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    operations_per_second: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms,
            "max_time_ms": self.max_time_ms,
            "std_dev_ms": self.std_dev_ms,
            "operations_per_second": self.operations_per_second,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    name: str
    cpu_percent: float
    memory_mb: float
    thread_count: int
    gc_collections: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "thread_count": self.thread_count,
            "gc_collections": self.gc_collections,
            "timestamp": self.timestamp.isoformat()
        }


class BenchmarkSuite:
    """基准测试套件"""
    
    def __init__(self, name: str):
        self.name = name
        self.results: List[BenchmarkResult] = []
        self.logger = get_logger(f"benchmark.{name}")
        self._lock = threading.Lock()
    
    def register_result(self, result: BenchmarkResult) -> None:
        """注册测试结果"""
        with self._lock:
            self.results.append(result)
        self.logger.info(
            f"Benchmark completed: {result.name}",
            iterations=result.iterations,
            avg_time_ms=result.avg_time_ms,
            ops_per_sec=result.operations_per_second
        )
    
    def run(
        self,
        name: str,
        func: Callable,
        iterations: int = 1000,
        warmup: int = 10,
        **kwargs
    ) -> BenchmarkResult:
        """运行基准测试"""
        self.logger.info(f"Starting benchmark: {name}", iterations=iterations, warmup=warmup)
        
        # 预热
        for _ in range(warmup):
            func(**kwargs)
        
        # 正式测试
        times: List[float] = []
        start_time = time.time()
        
        for _ in range(iterations):
            iter_start = time.time()
            func(**kwargs)
            iter_time = (time.time() - iter_start) * 1000
            times.append(iter_time)
        
        total_time = (time.time() - start_time) * 1000
        
        # 计算统计信息
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        ops_per_sec = (iterations / total_time) * 1000 if total_time > 0 else 0.0
        
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=total_time,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            std_dev_ms=std_dev,
            operations_per_second=ops_per_sec
        )
        
        self.register_result(result)
        return result
    
    def run_comparison(
        self,
        name: str,
        funcs: Dict[str, Callable],
        iterations: int = 1000,
        warmup: int = 10,
        **kwargs
    ) -> Dict[str, BenchmarkResult]:
        """运行对比测试"""
        results: Dict[str, BenchmarkResult] = {}
        
        for func_name, func in funcs.items():
            full_name = f"{name}.{func_name}"
            result = self.run(full_name, func, iterations, warmup, **kwargs)
            results[func_name] = result
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        with self._lock:
            if not self.results:
                return {"total_benchmarks": 0, "results": []}
            
            return {
                "total_benchmarks": len(self.results),
                "results": [r.to_dict() for r in self.results],
                "fastest": min(self.results, key=lambda r: r.avg_time_ms).name if self.results else None,
                "slowest": max(self.results, key=lambda r: r.avg_time_ms).name if self.results else None
            }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self._lock = threading.Lock()
        self._max_history = 1000
        self.logger = get_logger("performance.monitor")
    
    def record_metric(self, name: str, metric: PerformanceMetrics) -> None:
        """记录性能指标"""
        with self._lock:
            self.metrics_history[name].append(metric)
            if len(self.metrics_history[name]) > self._max_history:
                self.metrics_history[name].pop(0)
    
    def collect_metrics(self, name: str) -> PerformanceMetrics:
        """收集当前性能指标"""
        import resource
        
        try:
            import psutil
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            thread_count = threading.active_count()
        except ImportError:
            cpu_percent = 0.0
            memory_info = resource.getrusage(resource.RUSAGE_SELF)
            memory_mb = memory_info.ru_maxrss / 1024  # Linux in KB
            thread_count = threading.active_count()
        
        gc_stats = gc.get_stats()
        gc_collections = sum(stat.get('collections', 0) for stat in gc_stats)
        
        metric = PerformanceMetrics(
            name=name,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            thread_count=thread_count,
            gc_collections=gc_collections
        )
        
        self.record_metric(name, metric)
        return metric
    
    def get_metrics_summary(self, name: str, limit: int = 100) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            metrics = self.metrics_history.get(name, [])[-limit:]
            
            if not metrics:
                return {"name": name, "count": 0}
            
            cpu_values = [m.cpu_percent for m in metrics]
            mem_values = [m.memory_mb for m in metrics]
            
            return {
                "name": name,
                "count": len(metrics),
                "cpu": {
                    "avg": statistics.mean(cpu_values),
                    "min": min(cpu_values),
                    "max": max(cpu_values)
                },
                "memory": {
                    "avg_mb": statistics.mean(mem_values),
                    "min_mb": min(mem_values),
                    "max_mb": max(mem_values)
                },
                "latest": metrics[-1].to_dict()
            }
    
    def get_all_summaries(self) -> Dict[str, Any]:
        """获取所有指标摘要"""
        with self._lock:
            return {
                name: self.get_metrics_summary(name)
                for name in self.metrics_history.keys()
            }


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.profiles: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self.logger = get_logger("performance.profiler")
    
    def profile(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """分析函数性能"""
        start_time = time.time()
        gc.collect()
        
        result = func(*args, **kwargs)
        
        duration = (time.time() - start_time) * 1000
        
        with self._lock:
            self.profiles[name].append(duration)
        
        self.logger.debug(f"Profile: {name}", duration_ms=duration)
        return result
    
    def get_profile_stats(self, name: str) -> Dict[str, Any]:
        """获取分析统计"""
        with self._lock:
            durations = self.profiles.get(name, [])
            
            if not durations:
                return {"name": name, "count": 0}
            
            return {
                "name": name,
                "count": len(durations),
                "total_ms": sum(durations),
                "avg_ms": statistics.mean(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "std_dev_ms": statistics.stdev(durations) if len(durations) > 1 else 0.0
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有分析统计"""
        with self._lock:
            return {
                name: self.get_profile_stats(name)
                for name in self.profiles.keys()
            }


# 全局实例
_default_benchmark_suite: Optional[BenchmarkSuite] = None
_default_monitor: Optional[PerformanceMonitor] = None
_default_profiler: Optional[PerformanceProfiler] = None


def get_benchmark_suite(name: str = "default") -> BenchmarkSuite:
    """获取基准测试套件"""
    global _default_benchmark_suite
    if _default_benchmark_suite is None:
        _default_benchmark_suite = BenchmarkSuite(name)
    return _default_benchmark_suite


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器"""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = PerformanceMonitor()
    return _default_monitor


def get_performance_profiler() -> PerformanceProfiler:
    """获取性能分析器"""
    global _default_profiler
    if _default_profiler is None:
        _default_profiler = PerformanceProfiler()
    return _default_profiler


def benchmark(name: str, iterations: int = 1000, warmup: int = 10):
    """基准测试装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            suite = get_benchmark_suite()
            result = suite.run(
                f"{func.__module__}.{func.__name__}",
                func,
                iterations=iterations,
                warmup=warmup,
                *args,
                **kwargs
            )
            return result
        return wrapper
    return decorator
