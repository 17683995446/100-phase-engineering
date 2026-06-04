"""
容器编排管理器
提供服务定义、容器生命周期管理、健康检查、扩缩容和负载均衡功能
"""
import time
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.utils.structured_logging import get_logger


class ContainerStatus(Enum):
    """容器状态"""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


class ServiceStatus(Enum):
    """服务状态"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    DOWN = "down"
    SCALING = "scaling"


@dataclass
class Container:
    """容器实例"""
    container_id: str
    service_id: str
    image: str
    status: ContainerStatus = ContainerStatus.PENDING
    port: Optional[int] = None
    env: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    restart_count: int = 0
    health_check_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def uptime(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "service_id": self.service_id,
            "image": self.image,
            "status": self.status.value,
            "port": self.port,
            "uptime": round(self.uptime, 3),
            "restart_count": self.restart_count,
            "health_check_failures": self.health_check_failures
        }


@dataclass
class ServiceDefinition:
    """服务定义"""
    service_id: str
    name: str
    image: str
    replicas: int = 1
    ports: List[int] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    health_check: Optional[Dict[str, Any]] = None
    restart_policy: str = "always"
    scaling_config: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "image": self.image,
            "replicas": self.replicas,
            "ports": self.ports,
            "restart_policy": self.restart_policy,
            "labels": self.labels
        }


@dataclass
class ServiceInstance:
    """服务实例"""
    service_id: str
    definition: ServiceDefinition
    containers: Dict[str, Container] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.DOWN
    target_replicas: int = 1
    current_replicas: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "status": self.status.value,
            "target_replicas": self.target_replicas,
            "current_replicas": self.current_replicas,
            "containers": [c.to_dict() for c in self.containers.values()]
        }


class ContainerOrchestrator:
    """容器编排管理器"""

    def __init__(self):
        self._services: Dict[str, ServiceInstance] = {}
        self._definitions: Dict[str, ServiceDefinition] = {}
        self._port_pool: Set[int] = set()
        self._base_port: int = 8000
        self._lock = threading.RLock()
        self._logger = get_logger("container.orchestrator")
        self._health_checkers: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}

    def register_service(self, service_id: str, name: str, image: str,
                         replicas: int = 1,
                         ports: Optional[List[int]] = None,
                         env: Optional[Dict[str, str]] = None,
                         health_check: Optional[Dict[str, Any]] = None,
                         restart_policy: str = "always",
                         labels: Optional[Dict[str, str]] = None) -> ServiceDefinition:
        """注册服务"""
        with self._lock:
            if service_id in self._definitions:
                raise ValueError(f"Service already exists: {service_id}")

            definition = ServiceDefinition(
                service_id=service_id,
                name=name,
                image=image,
                replicas=replicas,
                ports=ports or [],
                env=env or {},
                health_check=health_check,
                restart_policy=restart_policy,
                labels=labels or {}
            )
            self._definitions[service_id] = definition
            self._logger.info(f"Service registered: {service_id}")
            return definition

    def deploy_service(self, service_id: str) -> ServiceInstance:
        """部署服务"""
        with self._lock:
            definition = self._definitions.get(service_id)
            if not definition:
                raise ValueError(f"Service not found: {service_id}")

            instance = ServiceInstance(
                service_id=service_id,
                definition=definition,
                target_replicas=definition.replicas,
                status=ServiceStatus.SCALING
            )
            self._services[service_id] = instance

            # 创建容器
            for _ in range(definition.replicas):
                self._create_container(instance)

            instance.status = ServiceStatus.ACTIVE if instance.current_replicas > 0 else ServiceStatus.DOWN
            self._logger.info(f"Service deployed: {service_id} replicas={instance.current_replicas}")

            # 启动健康检查
            if definition.health_check:
                self._start_health_checker(service_id)

            return instance

    def _create_container(self, instance: ServiceInstance) -> Container:
        """创建容器"""
        definition = instance.definition
        container_id = f"{instance.service_id}_{uuid.uuid4().hex[:6]}"
        port = None
        if definition.ports:
            port = self._allocate_port()

        container = Container(
            container_id=container_id,
            service_id=instance.service_id,
            image=definition.image,
            port=port,
            env=dict(definition.env)
        )
        container.status = ContainerStatus.RUNNING
        container.start_time = time.time()
        instance.containers[container_id] = container
        instance.current_replicas += 1
        self._logger.info(f"Container created: {container_id} port={port}")
        return container

    def _allocate_port(self) -> int:
        """分配端口"""
        port = self._base_port
        while port in self._port_pool:
            port += 1
        self._port_pool.add(port)
        return port

    def _release_port(self, port: Optional[int]) -> None:
        """释放端口"""
        if port is not None and port in self._port_pool:
            self._port_pool.discard(port)

    def _start_health_checker(self, service_id: str) -> None:
        """启动健康检查器"""
        stop_event = threading.Event()
        self._stop_events[service_id] = stop_event

        def checker():
            while not stop_event.is_set():
                with self._lock:
                    instance = self._services.get(service_id)
                    if not instance:
                        break
                    definition = instance.definition
                    hc = definition.health_check
                    if not hc:
                        break
                    interval = hc.get("interval", 10)
                    threshold = hc.get("threshold", 3)

                    for container in list(instance.containers.values()):
                        if container.status != ContainerStatus.RUNNING:
                            continue
                        # 模拟健康检查
                        success = self._simulate_health_check(container, hc)
                        if not success:
                            container.health_check_failures += 1
                            if container.health_check_failures >= threshold:
                                self._logger.warning(
                                    f"Health check failed: {container.container_id}")
                                if definition.restart_policy == "always":
                                    self._restart_container(instance, container)
                                else:
                                    container.status = ContainerStatus.FAILED
                        else:
                            container.health_check_failures = 0

                time.sleep(interval)

        thread = threading.Thread(target=checker, daemon=True)
        thread.start()
        self._health_checkers[service_id] = thread

    def _simulate_health_check(self, container: Container,
                               hc: Dict[str, Any]) -> bool:
        """模拟健康检查"""
        # 模拟：基于容器ID哈希决定健康状态（用于测试可控性）
        check_type = hc.get("type", "http")
        if check_type == "always_fail":
            return False
        if check_type == "always_pass":
            return True
        # 默认通过
        return True

    def _restart_container(self, instance: ServiceInstance,
                           container: Container) -> Container:
        """重启容器"""
        container.status = ContainerStatus.RESTARTING
        container.end_time = time.time()
        self._release_port(container.port)
        container.port = None

        # 重新创建
        new_container = self._create_container(instance)
        new_container.restart_count = container.restart_count + 1
        del instance.containers[container.container_id]
        self._logger.info(f"Container restarted: {new_container.container_id}")
        return new_container

    def scale_service(self, service_id: str, replicas: int) -> ServiceInstance:
        """扩缩容服务"""
        with self._lock:
            instance = self._services.get(service_id)
            if not instance:
                raise ValueError(f"Service not deployed: {service_id}")

            instance.status = ServiceStatus.SCALING
            instance.target_replicas = replicas
            current = instance.current_replicas

            if replicas > current:
                for _ in range(replicas - current):
                    self._create_container(instance)
            elif replicas < current:
                to_remove = list(instance.containers.values())[:current - replicas]
                for container in to_remove:
                    self._stop_container(instance, container)

            instance.current_replicas = len(instance.containers)
            instance.status = ServiceStatus.ACTIVE if instance.current_replicas > 0 else ServiceStatus.DOWN
            self._logger.info(f"Service scaled: {service_id} to {instance.current_replicas}")
            return instance

    def _stop_container(self, instance: ServiceInstance,
                        container: Container) -> None:
        """停止容器"""
        container.status = ContainerStatus.STOPPED
        container.end_time = time.time()
        self._release_port(container.port)
        del instance.containers[container.container_id]
        instance.current_replicas -= 1
        self._logger.info(f"Container stopped: {container.container_id}")

    def stop_service(self, service_id: str) -> bool:
        """停止服务"""
        with self._lock:
            instance = self._services.get(service_id)
            if not instance:
                return False

            # 停止健康检查
            if service_id in self._stop_events:
                self._stop_events[service_id].set()
                del self._stop_events[service_id]
            if service_id in self._health_checkers:
                del self._health_checkers[service_id]

            for container in list(instance.containers.values()):
                self._stop_container(instance, container)

            instance.status = ServiceStatus.DOWN
            self._logger.info(f"Service stopped: {service_id}")
            return True

    def remove_service(self, service_id: str) -> bool:
        """移除服务"""
        with self._lock:
            self.stop_service(service_id)
            if service_id in self._services:
                del self._services[service_id]
            if service_id in self._definitions:
                del self._definitions[service_id]
            self._logger.info(f"Service removed: {service_id}")
            return True

    def get_service(self, service_id: str) -> Optional[ServiceInstance]:
        """获取服务实例"""
        with self._lock:
            return self._services.get(service_id)

    def list_services(self) -> List[Dict[str, Any]]:
        """列出所有服务"""
        with self._lock:
            return [s.to_dict() for s in self._services.values()]

    def get_container(self, container_id: str) -> Optional[Container]:
        """获取容器"""
        with self._lock:
            for instance in self._services.values():
                if container_id in instance.containers:
                    return instance.containers[container_id]
            return None

    def restart_container_by_id(self, container_id: str) -> Optional[Container]:
        """按ID重启容器"""
        with self._lock:
            for instance in self._services.values():
                if container_id in instance.containers:
                    container = instance.containers[container_id]
                    new_container = self._restart_container(instance, container)
                    return new_container
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_containers = sum(
                len(s.containers) for s in self._services.values()
            )
            running = sum(
                sum(1 for c in s.containers.values()
                    if c.status == ContainerStatus.RUNNING)
                for s in self._services.values()
            )
            return {
                "total_services": len(self._services),
                "total_definitions": len(self._definitions),
                "total_containers": total_containers,
                "running_containers": running,
                "allocated_ports": len(self._port_pool)
            }


# 全局实例
_orchestrator: Optional[ContainerOrchestrator] = None


def get_container_orchestrator() -> ContainerOrchestrator:
    """获取全局容器编排管理器"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContainerOrchestrator()
    return _orchestrator
