"""
限流熔断器系统
提供熔断、限流、降级和自适应保护功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.utils.structured_logging import get_logger


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 熔断
    HALF_OPEN = "half_open"  # 半开


class RateLimitStrategy(Enum):
    """限流策略"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class RateLimitConfig:
    """限流配置"""
    max_requests: int = 100
    window_seconds: float = 60.0
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


class CircuitBreaker:
    """熔断器"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
        self._logger = get_logger(f"circuit.breaker.{name}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行受保护的调用"""
        if not self._can_execute():
            raise CircuitBreakerOpen(f"Circuit breaker {self._name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        """检查是否可以执行"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    return True
                return False
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return False

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self._config.timeout_seconds

    def _on_success(self) -> None:
        """成功回调"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._half_open_calls = 0
                    self._logger.info(f"Circuit {self._name} CLOSED")
            else:
                self._failure_count = 0

    def _on_failure(self) -> None:
        """失败回调"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._logger.warning(f"Circuit {self._name} OPEN (half-open failure)")
            elif self._failure_count >= self._config.failure_threshold:
                self._state = CircuitState.OPEN
                self._logger.warning(f"Circuit {self._name} OPEN")

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            return self._state

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self._name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls
            }

    def reset(self) -> None:
        """手动重置"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass


class TokenBucket:
    """令牌桶"""

    def __init__(self, max_tokens: int, refill_rate: float):
        self._max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._refill_rate = refill_rate
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """消费令牌"""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def get_tokens(self) -> float:
        """获取当前令牌数"""
        with self._lock:
            self._refill()
            return self._tokens


class SlidingWindow:
    """滑动窗口"""

    def __init__(self, window_seconds: float, max_requests: int):
        self._window_seconds = window_seconds
        self._max_requests = max_requests
        self._requests: deque = deque()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds

            # 移除过期请求
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            if len(self._requests) < self._max_requests:
                self._requests.append(now)
                return True
            return False

    def get_current_count(self) -> int:
        """获取当前窗口内请求数"""
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            return len(self._requests)


class RateLimiter:
    """限流器"""

    def __init__(self, name: str, config: Optional[RateLimitConfig] = None):
        self._name = name
        self._config = config or RateLimitConfig()
        self._lock = threading.RLock()
        self._logger = get_logger(f"rate.limiter.{name}")

        if self._config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self._bucket = TokenBucket(
                max_tokens=self._config.max_requests,
                refill_rate=self._config.max_requests / self._config.window_seconds
            )
            self._window = None
        else:
            self._bucket = None
            self._window = SlidingWindow(
                window_seconds=self._config.window_seconds,
                max_requests=self._config.max_requests
            )

    def allow(self) -> bool:
        """检查是否允许请求"""
        if self._bucket:
            return self._bucket.consume(1)
        elif self._window:
            return self._window.allow()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "name": self._name,
            "strategy": self._config.strategy.value,
            "max_requests": self._config.max_requests,
            "window_seconds": self._config.window_seconds
        }
        if self._bucket:
            stats["current_tokens"] = round(self._bucket.get_tokens(), 2)
        elif self._window:
            stats["current_requests"] = self._window.get_current_count()
        return stats


class AdaptiveRateLimiter:
    """自适应限流器"""

    def __init__(self, name: str, initial_limit: int = 100,
                 min_limit: int = 10, max_limit: int = 1000):
        self._name = name
        self._current_limit = initial_limit
        self._min_limit = min_limit
        self._max_limit = max_limit
        self._window = SlidingWindow(window_seconds=60, max_requests=initial_limit)
        self._success_count = 0
        self._failure_count = 0
        self._lock = threading.RLock()
        self._logger = get_logger(f"adaptive.limiter.{name}")

    def allow(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            # 动态调整窗口大小
            self._window._max_requests = self._current_limit
            return self._window.allow()

    def record_success(self) -> None:
        """记录成功"""
        with self._lock:
            self._success_count += 1
            if self._success_count >= 10:
                self._current_limit = min(self._max_limit, self._current_limit + 5)
                self._success_count = 0
                self._logger.info(f"Limit increased to {self._current_limit}")

    def record_failure(self) -> None:
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= 5:
                self._current_limit = max(self._min_limit, self._current_limit - 10)
                self._failure_count = 0
                self._logger.warning(f"Limit decreased to {self._current_limit}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self._name,
                "current_limit": self._current_limit,
                "min_limit": self._min_limit,
                "max_limit": self._max_limit,
                "current_requests": self._window.get_current_count()
            }


class Bulkhead:
    """舱壁隔离器"""

    def __init__(self, name: str, max_concurrent: int = 10,
                 max_wait_queue: int = 100):
        self._name = name
        self._max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._wait_queue = 0
        self._max_wait_queue = max_wait_queue
        self._lock = threading.Lock()
        self._logger = get_logger(f"bulkhead.{name}")

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行受保护的调用"""
        with self._lock:
            if self._wait_queue >= self._max_wait_queue:
                raise BulkheadFull(f"Bulkhead {self._name} wait queue full")
            self._wait_queue += 1

        try:
            acquired = self._semaphore.acquire(timeout=5.0)
            if not acquired:
                raise BulkheadFull(f"Bulkhead {self._name} timeout")
            try:
                return func(*args, **kwargs)
            finally:
                self._semaphore.release()
        finally:
            with self._lock:
                self._wait_queue -= 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self._name,
                "max_concurrent": self._max_concurrent,
                "available": self._semaphore._value,
                "wait_queue": self._wait_queue
            }


class BulkheadFull(Exception):
    """舱壁已满异常"""
    pass


# 全局实例
_breakers: Dict[str, CircuitBreaker] = {}
_limiters: Dict[str, RateLimiter] = {}


def get_circuit_breaker(name: str,
                        config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """获取熔断器"""
    global _breakers
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name, config)
    return _breakers[name]


def get_rate_limiter(name: str,
                     config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """获取限流器"""
    global _limiters
    if name not in _limiters:
        _limiters[name] = RateLimiter(name, config)
    return _limiters[name]
