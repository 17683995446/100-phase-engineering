"""
高级健康检查与系统状态监控系统
提供组件级健康检查、状态聚合、告警集成
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from abc import ABC, abstractmethod

from src.utils.logger import logger
from src.utils.structured_logging import get_logger
from src.utils.telemetry import get_tracer, SpanKind, SpanStatus


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = auto()      # 健康
    DEGRADED = auto()     # 降级
    UNHEALTHY = auto()    # 不健康
    UNKNOWN = auto()       # 未知


class HealthCheckType(Enum):
    """健康检查类型"""
    LIVENESS = auto()     # 存活探针
    READINESS = auto()    # 就绪探针
    STARTUP = auto()      # 启动探针


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "component": self.component,
            "status": self.status.name,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class AggregatedHealthStatus:
    """聚合健康状态"""
    overall_status: HealthStatus
    components: Dict[str, HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    total_components: int = 0
    healthy_components: int = 0
    degraded_components: int = 0
    unhealthy_components: int = 0
    unknown_components: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.overall_status.name,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total": self.total_components,
                "healthy": self.healthy_components,
                "degraded": self.degraded_components,
                "unhealthy": self.unhealthy_components,
                "unknown": self.unknown_components
            },
            "components": {
                name: result.to_dict()
                for name, result in self.components.items()
            }
        }


class HealthCheck(ABC):
    """健康检查基类"""
    
    def __init__(
        self,
        name: str,
        check_type: HealthCheckType = HealthCheckType.LIVENESS,
        timeout: float = 5.0,
        interval: float = 30.0,
        tags: Optional[List[str]] = None
    ):
        self.name = name
        self.check_type = check_type
        self.timeout = timeout
        self.interval = interval
        self.tags = tags or []
        self.logger = get_logger(f"health.{name}")
        self._tracer = get_tracer("health.check")
        
    @abstractmethod
    def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass
    
    def run(self) -> HealthCheckResult:
        """运行健康检查（带追踪）"""
        start_time = time.time()
        try:
            with self._tracer.span(f"health_check.{self.name}") as span:
                result = self.check()
                span.set_status(SpanStatus.OK)
                span.set_attributes({
                    "health.component": self.name,
                    "health.status": result.status.name,
                })
                return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed: {self.name}", error=str(e))
            span = self._tracer.current_span
            if span:
                span.set_status(SpanStatus.ERROR, str(e))
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                duration_ms=duration_ms,
                tags=self.tags
            )


class ComponentHealthCheck(HealthCheck):
    """组件健康检查"""
    
    def __init__(
        self,
        component_name: str,
        check_fn: Callable[[], bool],
        check_type: HealthCheckType = HealthCheckType.LIVENESS,
        timeout: float = 5.0,
        interval: float = 30.0,
        tags: Optional[List[str]] = None,
        details_fn: Optional[Callable[[], Dict[str, Any]]] = None
    ):
        super().__init__(
            name=component_name,
            check_type=check_type,
            timeout=timeout,
            interval=interval,
            tags=tags
        )
        self.check_fn = check_fn
        self.details_fn = details_fn
    
    def check(self) -> HealthCheckResult:
        """执行检查"""
        start_time = time.time()
        
        try:
            is_healthy = self.check_fn()
            duration_ms = (time.time() - start_time) * 1000
            
            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "Component is healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Component check failed"
            
            details = {}
            if self.details_fn:
                details = self.details_fn()
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details=details,
                duration_ms=duration_ms,
                tags=self.tags
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}",
                duration_ms=duration_ms,
                tags=self.tags
            )


class ThresholdHealthCheck(HealthCheck):
    """阈值健康检查"""
    
    def __init__(
        self,
        name: str,
        metric_fn: Callable[[], float],
        healthy_threshold: float,
        degraded_threshold: Optional[float] = None,
        check_type: HealthCheckType = HealthCheckType.LIVENESS,
        timeout: float = 5.0,
        interval: float = 30.0,
        tags: Optional[List[str]] = None,
        higher_is_healthier: bool = True
    ):
        super().__init__(
            name=name,
            check_type=check_type,
            timeout=timeout,
            interval=interval,
            tags=tags
        )
        self.metric_fn = metric_fn
        self.healthy_threshold = healthy_threshold
        self.degraded_threshold = degraded_threshold
        self.higher_is_healthier = higher_is_healthier
        self.tags = self.tags or []
        self.tags.append("threshold")
    
    def check(self) -> HealthCheckResult:
        """执行阈值检查"""
        start_time = time.time()
        
        try:
            value = self.metric_fn()
            duration_ms = (time.time() - start_time) * 1000
            
            if self.higher_is_healthier:
                if value >= self.healthy_threshold:
                    status = HealthStatus.HEALTHY
                    message = f"Metric {value:.2f} is healthy"
                elif self.degraded_threshold and value >= self.degraded_threshold:
                    status = HealthStatus.DEGRADED
                    message = f"Metric {value:.2f} is degraded"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Metric {value:.2f} is below threshold {self.healthy_threshold}"
            else:
                if value <= self.healthy_threshold:
                    status = HealthStatus.HEALTHY
                    message = f"Metric {value:.2f} is healthy"
                elif self.degraded_threshold and value <= self.degraded_threshold:
                    status = HealthStatus.DEGRADED
                    message = f"Metric {value:.2f} is degraded"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Metric {value:.2f} exceeds threshold {self.healthy_threshold}"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "value": value,
                    "healthy_threshold": self.healthy_threshold,
                    "degraded_threshold": self.degraded_threshold
                },
                duration_ms=duration_ms,
                tags=self.tags
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}",
                duration_ms=duration_ms,
                tags=self.tags
            )


class DependencyHealthCheck(HealthCheck):
    """依赖健康检查"""
    
    def __init__(
        self,
        name: str,
        check_fn: Callable[[], bool],
        dependencies: Optional[List[str]] = None,
        check_type: HealthCheckType = HealthCheckType.READINESS,
        timeout: float = 5.0,
        interval: float = 30.0,
        tags: Optional[List[str]] = None
    ):
        super().__init__(
            name=name,
            check_type=check_type,
            timeout=timeout,
            interval=interval,
            tags=tags or []
        )
        self.check_fn = check_fn
        self.dependencies = dependencies or []
        self.tags.extend(["dependency"])
    
    def check(self) -> HealthCheckResult:
        """执行依赖检查"""
        start_time = time.time()
        
        try:
            is_ready = self.check_fn()
            duration_ms = (time.time() - start_time) * 1000
            
            if is_ready:
                status = HealthStatus.HEALTHY
                message = "All dependencies are ready"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Dependencies not ready"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "dependencies": self.dependencies
                },
                duration_ms=duration_ms,
                tags=self.tags
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Dependency check error: {str(e)}",
                duration_ms=duration_ms,
                tags=self.tags
            )


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()
        self.logger = get_logger("health.monitor")
        self._tracer = get_tracer("health.monitor")
        self._history: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        self._max_history = 100
    
    def register_check(self, check: HealthCheck) -> None:
        """注册健康检查"""
        with self._lock:
            self.checks[check.name] = check
            self.logger.info(f"Registered health check: {check.name}")
    
    def unregister_check(self, name: str) -> bool:
        """取消注册健康检查"""
        with self._lock:
            if name in self.checks:
                del self.checks[name]
                self.logger.info(f"Unregistered health check: {name}")
                return True
            return False
    
    def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """运行单个健康检查"""
        with self._lock:
            check = self.checks.get(name)
            if not check:
                self.logger.warning(f"Health check not found: {name}")
                return None
        
        result = check.run()
        
        with self._lock:
            self.last_results[name] = result
            self._history[name].append(result)
            if len(self._history[name]) > self._max_history:
                self._history[name].pop(0)
        
        return result
    
    def run_all_checks(
        self,
        check_type: Optional[HealthCheckType] = None
    ) -> AggregatedHealthStatus:
        """运行所有健康检查"""
        with self._tracer.span("run_all_health_checks") as span:
            with self._lock:
                checks_to_run = self.checks
                if check_type:
                    checks_to_run = {
                        name: check for name, check in self.checks.items()
                        if check.check_type == check_type
                    }
            
            results: Dict[str, HealthCheckResult] = {}
            total = len(checks_to_run)
            
            for name, check in checks_to_run.items():
                result = check.run()
                results[name] = result
                
                with self._lock:
                    self.last_results[name] = result
                    self._history[name].append(result)
                    if len(self._history[name]) > self._max_history:
                        self._history[name].pop(0)
            
            healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
            degraded = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
            unhealthy = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)
            unknown = sum(1 for r in results.values() if r.status == HealthStatus.UNKNOWN)
            
            if unhealthy > 0:
                overall = HealthStatus.UNHEALTHY
            elif degraded > 0:
                overall = HealthStatus.DEGRADED
            elif unknown > 0:
                overall = HealthStatus.UNKNOWN
            else:
                overall = HealthStatus.HEALTHY
            
            aggregated = AggregatedHealthStatus(
                overall_status=overall,
                components=results,
                total_components=total,
                healthy_components=healthy,
                degraded_components=degraded,
                unhealthy_components=unhealthy,
                unknown_components=unknown
            )
            
            span.set_attributes({
                "health.total": total,
                "health.healthy": healthy,
                "health.degraded": degraded,
                "health.unhealthy": unhealthy,
                "health.overall": overall.name
            })
            
            return aggregated
    
    def get_status(self, name: str) -> Optional[HealthCheckResult]:
        """获取健康检查状态"""
        with self._lock:
            return self.last_results.get(name)
    
    def get_history(
        self,
        name: str,
        limit: int = 10
    ) -> List[HealthCheckResult]:
        """获取历史状态"""
        with self._lock:
            history = self._history.get(name, [])
            return history[-limit:]
    
    def get_all_checks_info(self) -> Dict[str, Any]:
        """获取所有检查信息"""
        with self._lock:
            return {
                name: {
                    "name": check.name,
                    "type": check.check_type.name,
                    "interval": check.interval,
                    "timeout": check.timeout,
                    "tags": check.tags
                }
                for name, check in self.checks.items()
            }


_default_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """获取全局健康监控器"""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = HealthMonitor()
    return _default_monitor


def create_component_check(
    name: str,
    check_fn: Callable[[], bool],
    **kwargs
) -> ComponentHealthCheck:
    """创建组件健康检查"""
    return ComponentHealthCheck(
        component_name=name,
        check_fn=check_fn,
        **kwargs
    )


def create_threshold_check(
    name: str,
    metric_fn: Callable[[], float],
    threshold: float,
    **kwargs
) -> ThresholdHealthCheck:
    """创建阈值健康检查"""
    return ThresholdHealthCheck(
        name=name,
        metric_fn=metric_fn,
        healthy_threshold=threshold,
        **kwargs
    )
