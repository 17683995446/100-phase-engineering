"""
分布式锁与并发控制
提供分布式锁、信号量和并发控制功能
"""
import threading
import time
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from contextlib import contextmanager

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class LockStatus(Enum):
    """锁状态"""
    ACQUIRED = auto()
    RELEASED = auto()
    EXPIRED = auto()


@dataclass
class LockInfo:
    """锁信息"""
    lock_id: str
    resource: str
    owner: str
    acquired_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: LockStatus = LockStatus.ACQUIRED
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class DistributedLock:
    """分布式锁（基于内存实现）"""
    
    def __init__(self, resource: str, timeout: float = 30.0):
        self.resource = resource
        self.timeout = timeout
        self._lock = threading.Lock()
        self._acquired = False
        self._lock_info: Optional[LockInfo] = None
        self._logger = get_logger("distributed.lock")
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """获取锁"""
        if self._acquired:
            return True
        
        try:
            if blocking:
                acquired = self._lock.acquire(timeout=timeout or self.timeout)
            else:
                acquired = self._lock.acquire(blocking=False)
            
            if acquired:
                self._acquired = True
                expires = None
                if self.timeout:
                    expires = datetime.now().timestamp() + self.timeout
                
                self._lock_info = LockInfo(
                    lock_id=str(uuid.uuid4()),
                    resource=self.resource,
                    owner=str(threading.current_thread().ident),
                    expires_at=datetime.fromtimestamp(expires) if expires else None
                )
                
                self._logger.debug(f"Lock acquired: {self.resource}")
                return True
            
            return False
        except Exception as e:
            self._logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self) -> bool:
        """释放锁"""
        if not self._acquired:
            return False
        
        try:
            self._lock.release()
            self._acquired = False
            if self._lock_info:
                self._lock_info.status = LockStatus.RELEASED
            
            self._logger.debug(f"Lock released: {self.resource}")
            return True
        except RuntimeError:
            # 锁未被当前线程持有
            self._acquired = False
            return True
        except Exception as e:
            self._logger.error(f"Failed to release lock: {e}")
            return False
    
    @contextmanager
    def __call__(self, blocking: bool = True, timeout: Optional[float] = None):
        """上下文管理器"""
        try:
            if self.acquire(blocking, timeout):
                yield self
            else:
                raise TimeoutError(f"Failed to acquire lock: {self.resource}")
        finally:
            self.release()
    
    def is_locked(self) -> bool:
        """检查是否已锁定"""
        return self._acquired


class LockManager:
    """锁管理器"""
    
    def __init__(self):
        self._locks: Dict[str, DistributedLock] = {}
        self._global_lock = threading.Lock()
        self._logger = get_logger("lock.manager")
    
    def get_lock(self, resource: str, timeout: float = 30.0) -> DistributedLock:
        """获取锁实例"""
        with self._global_lock:
            if resource not in self._locks:
                self._locks[resource] = DistributedLock(resource, timeout)
            return self._locks[resource]
    
    @contextmanager
    def lock(self, resource: str, timeout: float = 30.0, blocking: bool = True):
        """获取锁的上下文管理器"""
        lock = self.get_lock(resource, timeout)
        try:
            if lock.acquire(blocking, timeout):
                yield lock
            else:
                raise TimeoutError(f"Failed to acquire lock: {resource}")
        finally:
            lock.release()
    
    def release_all(self) -> None:
        """释放所有锁"""
        with self._global_lock:
            for lock in self._locks.values():
                if lock.is_locked():
                    lock.release()
            self._locks.clear()


class Semaphore:
    """信号量"""
    
    def __init__(self, name: str, max_concurrent: int = 5):
        self.name = name
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._logger = get_logger(f"semaphore.{name}")
        self._active_count = 0
        self._lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """获取信号量"""
        try:
            if blocking:
                acquired = self._semaphore.acquire(timeout=timeout)
            else:
                acquired = self._semaphore.acquire(blocking=False)
            
            if acquired:
                with self._lock:
                    self._active_count += 1
                self._logger.debug(f"Semaphore acquired: {self.name} ({self._active_count}/{self.max_concurrent})")
            
            return acquired
        except Exception as e:
            self._logger.error(f"Failed to acquire semaphore: {e}")
            return False
    
    def release(self) -> None:
        """释放信号量"""
        try:
            self._semaphore.release()
            with self._lock:
                self._active_count -= 1
            self._logger.debug(f"Semaphore released: {self.name} ({self._active_count}/{self.max_concurrent})")
        except Exception as e:
            self._logger.error(f"Failed to release semaphore: {e}")
    
    @contextmanager
    def __call__(self, blocking: bool = True, timeout: Optional[float] = None):
        """上下文管理器"""
        try:
            if self.acquire(blocking, timeout):
                yield self
            else:
                raise TimeoutError(f"Failed to acquire semaphore: {self.name}")
        finally:
            self.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "name": self.name,
                "max_concurrent": self.max_concurrent,
                "active_count": self._active_count,
                "available": self.max_concurrent - self._active_count
            }


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, name: str, max_requests: int = 100, window_seconds: float = 60.0):
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = threading.Lock()
        self._logger = get_logger(f"rate.limiter.{name}")
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            
            # 清理过期的请求记录
            self._requests[key] = [
                t for t in self._requests[key]
                if t > window_start
            ]
            
            # 检查是否超过限制
            if len(self._requests[key]) >= self.max_requests:
                self._logger.warning(f"Rate limit exceeded: {key}")
                return False
            
            # 记录请求
            self._requests[key].append(now)
            return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._lock:
            if key not in self._requests:
                return self.max_requests
            
            # 清理过期记录
            self._requests[key] = [
                t for t in self._requests[key]
                if t > window_start
            ]
            
            return max(0, self.max_requests - len(self._requests[key]))
    
    def get_stats(self, key: Optional[str] = None) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            if key:
                return {
                    "name": self.name,
                    "key": key,
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "remaining": self.get_remaining(key)
                }
            else:
                return {
                    "name": self.name,
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "tracked_keys": len(self._requests)
                }


# 全局实例
_lock_manager: Optional[LockManager] = None


def get_lock_manager() -> LockManager:
    """获取锁管理器"""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = LockManager()
    return _lock_manager


def synchronized(resource: str = "default", timeout: float = 30.0):
    """同步装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            manager = get_lock_manager()
            with manager.lock(resource, timeout):
                return func(*args, **kwargs)
        return wrapper
    return decorator
