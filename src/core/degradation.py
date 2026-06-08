"""
降级策略与熔断集成
提供服务降级、熔断器集成、优雅降级和自动恢复功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from src.utils.structured_logging import get_logger


class DegradationLevel(Enum):
    """降级级别"""
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    EMERGENCY = "emergency"


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


T = TypeVar("T")


@dataclass
class DegradationPolicy:
    """降级策略"""
    policy_id: str
    service_name: str
    level: DegradationLevel = DegradationLevel.NONE
    fallback: Optional[Callable[..., Any]] = None
    timeout_ms: int = 5000
    max_retries: int = 3
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "service_name": self.service_name,
            "level": self.level.value,
            "timeout_ms": self.timeout_ms,
            "max_retries": self.max_retries,
            "enabled": self.enabled
        }


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreaker:
    """熔断器"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = threading.RLock()
        self._logger = get_logger(f"circuit_breaker.{name}")

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """执行带熔断保护的调用"""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self._logger.info(f"Circuit {self.name} entering half-open")
                else:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(f"Circuit {self.name} half-open limit reached")
                self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout

    def _on_success(self) -> None:
        """成功回调"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self._logger.info(f"Circuit {self.name} closed")
            else:
                self.failure_count = 0

    def _on_failure(self) -> None:
        """失败回调"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self._logger.warning(f"Circuit {self.name} opened from half-open")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self._logger.warning(f"Circuit {self.name} opened")

    def get_state(self) -> str:
        """获取状态"""
        return self.state.value

    def force_open(self) -> None:
        """强制打开"""
        with self._lock:
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()

    def force_close(self) -> None:
        """强制关闭"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass


class DegradationManager:
    """降级管理器"""

    def __init__(self):
        self._policies: Dict[str, DegradationPolicy] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("degradation.manager")

    def register_policy(self, policy: DegradationPolicy) -> None:
        """注册降级策略"""
        with self._lock:
            self._policies[policy.service_name] = policy
            self._circuit_breakers[policy.service_name] = CircuitBreaker(
                policy.service_name
            )
            self._logger.info(f"Policy registered: {policy.service_name}")

    def execute(self, service_name: str, func: Callable[..., T],
                *args, **kwargs) -> T:
        """执行带降级保护的服务调用"""
        with self._lock:
            policy = self._policies.get(service_name)
            breaker = self._circuit_breakers.get(service_name)

        if not policy or not policy.enabled:
            return func(*args, **kwargs)

        if policy.level == DegradationLevel.FULL:
            if policy.fallback:
                return policy.fallback(*args, **kwargs)
            raise ServiceDegraded(f"Service {service_name} is fully degraded")

        try:
            if breaker:
                return breaker.call(func, *args, **kwargs)
            return func(*args, **kwargs)
        except (CircuitBreakerOpen, Exception) as e:
            self._logger.warning(f"Service {service_name} failed: {e}")
            if policy.fallback:
                return policy.fallback(*args, **kwargs)
            raise

    def set_degradation_level(self, service_name: str,
                              level: DegradationLevel) -> bool:
        """设置降级级别"""
        with self._lock:
            policy = self._policies.get(service_name)
            if not policy:
                return False
            policy.level = level
            self._logger.info(f"Degradation level set: {service_name} -> {level.value}")
            return True

    def get_circuit_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._circuit_breakers.get(service_name)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_policies": len(self._policies),
                "total_circuits": len(self._circuit_breakers),
                "circuits": {
                    name: cb.to_dict()
                    for name, cb in self._circuit_breakers.items()
                }
            }


class ServiceDegraded(Exception):
    """服务降级异常"""
    pass


# 全局实例
_manager: Optional[DegradationManager] = None


def get_degradation_manager() -> DegradationManager:
    """获取全局降级管理器"""
    global _manager
    if _manager is None:
        _manager = DegradationManager()
    return _manager
