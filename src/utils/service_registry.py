"""
服务发现与注册中心
提供服务注册、发现、健康检查和心跳机制
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class ServiceStatus(Enum):
    """服务状态"""
    HEALTHY = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()
    DEREGISTERED = auto()


@dataclass
class ServiceInstance:
    """服务实例"""
    service_id: str
    service_name: str
    host: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.HEALTHY
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: Optional[datetime] = None
    health_check_url: Optional[str] = None
    
    @property
    def instance_id(self) -> str:
        """获取实例ID"""
        return f"{self.service_name}@{self.host}:{self.port}"
    
    @property
    def address(self) -> str:
        """获取服务地址"""
        return f"{self.host}:{self.port}"
    
    def is_expired(self, timeout_seconds: float = 30.0) -> bool:
        """检查是否过期（心跳超时）"""
        if self.last_heartbeat is None:
            return False
        return (datetime.now() - self.last_heartbeat).total_seconds() > timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "host": self.host,
            "port": self.port,
            "address": self.address,
            "metadata": self.metadata,
            "status": self.status.name,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }


class ServiceRegistry:
    """服务注册中心"""
    
    def __init__(self, heartbeat_timeout: float = 30.0, check_interval: float = 10.0):
        self._services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("service.registry")
        self._heartbeat_timeout = heartbeat_timeout
        self._check_interval = check_interval
        self._running = False
        self._check_thread: Optional[threading.Thread] = None
        self._watchers: List[Callable] = []
    
    def register(self, instance: ServiceInstance) -> bool:
        """注册服务"""
        with self._lock:
            if instance.service_name not in self._services:
                self._services[instance.service_name] = {}
            
            instance.last_heartbeat = datetime.now()
            self._services[instance.service_name][instance.service_id] = instance
        
        self._logger.info(f"Service registered: {instance.instance_id}")
        self._notify_watchers("REGISTER", instance)
        return True
    
    def deregister(self, service_name: str, service_id: str) -> bool:
        """注销服务"""
        with self._lock:
            if service_name in self._services:
                if service_id in self._services[service_name]:
                    instance = self._services[service_name].pop(service_id)
                    instance.status = ServiceStatus.DEREGISTERED
                    
                    # 清理空服务
                    if not self._services[service_name]:
                        del self._services[service_name]
                    
                    self._logger.info(f"Service deregistered: {instance.instance_id}")
                    self._notify_watchers("DEREGISTER", instance)
                    return True
        
        return False
    
    def heartbeat(self, service_name: str, service_id: str) -> bool:
        """服务心跳"""
        with self._lock:
            if service_name in self._services:
                if service_id in self._services[service_name]:
                    instance = self._services[service_name][service_id]
                    instance.last_heartbeat = datetime.now()
                    instance.status = ServiceStatus.HEALTHY
                    return True
        
        return False
    
    def discover(self, service_name: str) -> List[ServiceInstance]:
        """发现服务"""
        with self._lock:
            if service_name not in self._services:
                return []
            
            return [
                instance for instance in self._services[service_name].values()
                if instance.status == ServiceStatus.HEALTHY
            ]
    
    def get_instance(self, service_name: str, service_id: str) -> Optional[ServiceInstance]:
        """获取特定实例"""
        with self._lock:
            if service_name in self._services:
                return self._services[service_name].get(service_id)
            return None
    
    def get_all_services(self) -> List[str]:
        """获取所有服务名称"""
        with self._lock:
            return list(self._services.keys())
    
    def get_all_instances(self) -> List[ServiceInstance]:
        """获取所有实例"""
        with self._lock:
            instances = []
            for service_instances in self._services.values():
                instances.extend(service_instances.values())
            return instances
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """获取健康实例"""
        return self.discover(service_name)
    
    def update_status(self, service_name: str, service_id: str, status: ServiceStatus) -> bool:
        """更新服务状态"""
        with self._lock:
            if service_name in self._services:
                if service_id in self._services[service_name]:
                    self._services[service_name][service_id].status = status
                    return True
        return False
    
    def add_watcher(self, watcher: Callable[[str, ServiceInstance], None]) -> None:
        """添加服务变更监听器"""
        self._watchers.append(watcher)
    
    def _notify_watchers(self, event: str, instance: ServiceInstance) -> None:
        """通知监听器"""
        for watcher in self._watchers:
            try:
                watcher(event, instance)
            except Exception as e:
                self._logger.error(f"Watcher error: {e}")
    
    def start_health_check(self) -> None:
        """启动健康检查"""
        if self._running:
            return
        
        self._running = True
        self._check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._check_thread.start()
        self._logger.info("Health check started")
    
    def stop_health_check(self) -> None:
        """停止健康检查"""
        self._running = False
        if self._check_thread:
            self._check_thread.join(timeout=5)
        self._logger.info("Health check stopped")
    
    def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            self._check_expired_services()
            time.sleep(self._check_interval)
    
    def _check_expired_services(self) -> None:
        """检查过期服务"""
        with self._lock:
            for service_name, instances in self._services.items():
                for service_id, instance in list(instances.items()):
                    if instance.is_expired(self._heartbeat_timeout):
                        if instance.status == ServiceStatus.HEALTHY:
                            instance.status = ServiceStatus.UNHEALTHY
                            self._logger.warning(
                                f"Service unhealthy: {instance.instance_id}"
                            )
                            self._notify_watchers("UNHEALTHY", instance)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_instances = sum(len(instances) for instances in self._services.values())
            healthy_instances = sum(
                1 for instances in self._services.values()
                for instance in instances.values()
                if instance.status == ServiceStatus.HEALTHY
            )
            
            return {
                "total_services": len(self._services),
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "unhealthy_instances": total_instances - healthy_instances,
                "services": {
                    name: {
                        "total": len(instances),
                        "healthy": sum(
                            1 for i in instances.values()
                            if i.status == ServiceStatus.HEALTHY
                        )
                    }
                    for name, instances in self._services.items()
                }
            }


class ServiceDiscoveryClient:
    """服务发现客户端"""
    
    def __init__(self, registry: ServiceRegistry):
        self._registry = registry
        self._logger = get_logger("service.discovery")
        self._cache: Dict[str, List[ServiceInstance]] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 5.0
        self._cache_timestamp: Dict[str, float] = {}
    
    def discover(self, service_name: str, use_cache: bool = True) -> List[ServiceInstance]:
        """发现服务"""
        if use_cache:
            cached = self._get_cached(service_name)
            if cached is not None:
                return cached
        
        instances = self._registry.discover(service_name)
        
        if use_cache:
            self._set_cache(service_name, instances)
        
        return instances
    
    def get_one_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """获取一个实例（轮询）"""
        instances = self.discover(service_name)
        if not instances:
            return None
        return instances[0]
    
    def _get_cached(self, service_name: str) -> Optional[List[ServiceInstance]]:
        """获取缓存"""
        with self._cache_lock:
            if service_name in self._cache:
                timestamp = self._cache_timestamp.get(service_name, 0)
                if time.time() - timestamp < self._cache_ttl:
                    return self._cache[service_name]
            return None
    
    def _set_cache(self, service_name: str, instances: List[ServiceInstance]) -> None:
        """设置缓存"""
        with self._cache_lock:
            self._cache[service_name] = instances
            self._cache_timestamp[service_name] = time.time()
    
    def invalidate_cache(self, service_name: Optional[str] = None) -> None:
        """使缓存失效"""
        with self._cache_lock:
            if service_name:
                self._cache.pop(service_name, None)
                self._cache_timestamp.pop(service_name, None)
            else:
                self._cache.clear()
                self._cache_timestamp.clear()


class ServiceRegistrar:
    """服务注册客户端"""
    
    def __init__(self, registry: ServiceRegistry):
        self._registry = registry
        self._logger = get_logger("service.registrar")
        self._registered_instances: Set[str] = set()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._heartbeat_interval = 10.0
    
    def register(self, instance: ServiceInstance) -> bool:
        """注册服务"""
        if self._registry.register(instance):
            self._registered_instances.add(
                f"{instance.service_name}:{instance.service_id}"
            )
            return True
        return False
    
    def deregister(self, service_name: str, service_id: str) -> bool:
        """注销服务"""
        key = f"{service_name}:{service_id}"
        if key in self._registered_instances:
            self._registered_instances.remove(key)
        return self._registry.deregister(service_name, service_id)
    
    def start_heartbeat(self, interval: float = 10.0) -> None:
        """启动心跳"""
        self._heartbeat_interval = interval
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()
        self._logger.info("Heartbeat started")
    
    def stop_heartbeat(self) -> None:
        """停止心跳"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        self._logger.info("Heartbeat stopped")
    
    def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            for key in list(self._registered_instances):
                parts = key.split(":", 1)
                if len(parts) == 2:
                    service_name, service_id = parts
                    self._registry.heartbeat(service_name, service_id)
            
            time.sleep(self._heartbeat_interval)


# 全局实例
_registry: Optional[ServiceRegistry] = None
_discovery_client: Optional[ServiceDiscoveryClient] = None
_registrar: Optional[ServiceRegistrar] = None


def get_service_registry() -> ServiceRegistry:
    """获取服务注册中心"""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def get_discovery_client(registry: Optional[ServiceRegistry] = None) -> ServiceDiscoveryClient:
    """获取服务发现客户端"""
    global _discovery_client
    if _discovery_client is None:
        _discovery_client = ServiceDiscoveryClient(registry or get_service_registry())
    return _discovery_client


def get_registrar(registry: Optional[ServiceRegistry] = None) -> ServiceRegistrar:
    """获取服务注册客户端"""
    global _registrar
    if _registrar is None:
        _registrar = ServiceRegistrar(registry or get_service_registry())
    return _registrar
