"""
性能基准测试框架
提供基准测试执行、结果收集、趋势分析和报告生成功能
"""
import time
import statistics
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.utils.structured_logging import get_logger


class BenchmarkStatus(Enum):
    """基准测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_id: str
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    ops_per_second: float
    status: BenchmarkStatus = BenchmarkStatus.COMPLETED
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "iterations": self.iterations,
            "total_time": round(self.total_time, 6),
            "avg_time": round(self.avg_time, 6),
            "min_time": round(self.min_time, 6),
            "max_time": round(self.max_time, 6),
            "median_time": round(self.median_time, 6),
            "std_dev": round(self.std_dev, 6),
            "ops_per_second": round(self.ops_per_second, 2),
            "status": self.status.value,
            "timestamp": self.timestamp
        }


class BenchmarkFramework:
    """性能基准测试框架"""

    def __init__(self):
        self._results: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._logger = get_logger("benchmark.framework")
        self._counter = 0

    def _generate_id(self) -> str:
        """生成ID"""
        self._counter += 1
        return f"bench_{self._counter}"

    def run(self, name: str, func: Callable[[], Any],
            iterations: int = 1000,
            warmup: int = 10) -> BenchmarkResult:
        """运行基准测试"""
        with self._lock:
            benchmark_id = self._generate_id()
            self._logger.info(f"Benchmark started: {name} iterations={iterations}")

            # Warmup
            for _ in range(warmup):
                try:
                    func()
                except Exception as e:
                    self._logger.warning(f"Warmup error: {e}")

            # 执行测试
            times: List[float] = []
            start_total = time.perf_counter()

            for _ in range(iterations):
                start = time.perf_counter()
                try:
                    func()
                except Exception as e:
                    self._logger.error(f"Benchmark error: {e}")
                    result = BenchmarkResult(
                        benchmark_id=benchmark_id,
                        name=name,
                        iterations=iterations,
                        total_time=0.0,
                        avg_time=0.0,
                        min_time=0.0,
                        max_time=0.0,
                        median_time=0.0,
                        std_dev=0.0,
                        ops_per_second=0.0,
                        status=BenchmarkStatus.FAILED
                    )
                    self._results.append(result)
                    return result
                end = time.perf_counter()
                times.append(end - start)

            total_time = time.perf_counter() - start_total

            result = BenchmarkResult(
                benchmark_id=benchmark_id,
                name=name,
                iterations=iterations,
                total_time=total_time,
                avg_time=statistics.mean(times),
                min_time=min(times),
                max_time=max(times),
                median_time=statistics.median(times),
                std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
                ops_per_second=iterations / total_time if total_time > 0 else 0.0
            )

            self._results.append(result)
            self._logger.info(
                f"Benchmark completed: {name} avg={result.avg_time:.6f}s ops={result.ops_per_second:.2f}"
            )
            return result

    def compare(self, name1: str, name2: str) -> Optional[Dict[str, Any]]:
        """比较两个基准测试"""
        with self._lock:
            results1 = [r for r in self._results if r.name == name1]
            results2 = [r for r in self._results if r.name == name2]

            if not results1 or not results2:
                return None

            r1 = results1[-1]
            r2 = results2[-1]

            speedup = r1.avg_time / r2.avg_time if r2.avg_time > 0 else 0.0

            return {
                "baseline": name1,
                "comparison": name2,
                "baseline_avg": r1.avg_time,
                "comparison_avg": r2.avg_time,
                "speedup": round(speedup, 2),
                "faster": speedup > 1.0
            }

    def get_results(self, name: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """获取测试结果"""
        with self._lock:
            results = list(self._results)
            if name:
                results = [r for r in results if r.name == name]
            return [r.to_dict() for r in results[-limit:]]

    def get_trend(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取趋势"""
        with self._lock:
            results = [r for r in self._results if r.name == name][-limit:]
            return [
                {
                    "timestamp": r.timestamp,
                    "avg_time": r.avg_time,
                    "ops_per_second": r.ops_per_second
                }
                for r in results
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._results)
            completed = sum(1 for r in self._results if r.status == BenchmarkStatus.COMPLETED)
            failed = sum(1 for r in self._results if r.status == BenchmarkStatus.FAILED)
            names = set(r.name for r in self._results)
            return {
                "total_benchmarks": total,
                "completed": completed,
                "failed": failed,
                "unique_names": len(names)
            }


# 全局实例
_framework: Optional[BenchmarkFramework] = None


def get_benchmark_framework() -> BenchmarkFramework:
    """获取全局基准测试框架"""
    global _framework
    if _framework is None:
        _framework = BenchmarkFramework()
    return _framework
