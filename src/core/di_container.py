"""
依赖注入容器
提供服务注册、解析、生命周期管理和接口绑定功能
"""
import threading
from typing import Dict, Any, Type, TypeVar, Callable, Optional, get_type_hints
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class Lifecycle(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


T = TypeVar("T")


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    interface: Type
    implementation: Type
    factory: Optional[Callable[..., Any]] = None
    lifecycle: Lifecycle = Lifecycle.SINGLETON
    instance: Optional[Any] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)


class DIContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("di.container")

    def register(self, interface: Type[T], implementation: Type[T],
                 lifecycle: Lifecycle = Lifecycle.SINGLETON,
                 factory: Optional[Callable[..., T]] = None,
                 **kwargs: Any) -> None:
        """注册服务"""
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                factory=factory,
                lifecycle=lifecycle,
                kwargs=kwargs
            )
            self._logger.info(
                f"Service registered: {interface.__name__} -> {implementation.__name__}"
            )

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """注册已有实例"""
        with self._lock:
            self._services[interface] = ServiceDescriptor(
                interface=interface,
                implementation=type(instance),
                lifecycle=Lifecycle.SINGLETON,
                instance=instance
            )
            self._logger.info(f"Instance registered: {interface.__name__}")

    def resolve(self, interface: Type[T]) -> T:
        """解析服务"""
        with self._lock:
            descriptor = self._services.get(interface)
            if not descriptor:
                raise KeyError(f"Service not registered: {interface.__name__}")

            if descriptor.lifecycle == Lifecycle.SINGLETON:
                if descriptor.instance is None:
                    descriptor.instance = self._create_instance(descriptor)
                return descriptor.instance

            if descriptor.lifecycle == Lifecycle.TRANSIENT:
                return self._create_instance(descriptor)

            if descriptor.lifecycle == Lifecycle.SCOPED:
                return self._create_instance(descriptor)

            return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例"""
        if descriptor.factory:
            return descriptor.factory(**descriptor.kwargs)

        try:
            return descriptor.implementation(**descriptor.kwargs)
        except TypeError:
            return descriptor.implementation()

    def is_registered(self, interface: Type) -> bool:
        """检查是否已注册"""
        with self._lock:
            return interface in self._services

    def unregister(self, interface: Type) -> bool:
        """注销服务"""
        with self._lock:
            if interface in self._services:
                del self._services[interface]
                self._logger.info(f"Service unregistered: {interface.__name__}")
                return True
            return False

    def build_provider(self) -> "ServiceProvider":
        """构建服务提供者"""
        return ServiceProvider(self)

    def get_registered_services(self) -> Dict[str, str]:
        """获取已注册服务列表"""
        with self._lock:
            return {
                k.__name__: v.implementation.__name__
                for k, v in self._services.items()
            }


class ServiceProvider:
    """服务提供者（只读视图）"""

    def __init__(self, container: DIContainer):
        self._container = container

    def get_service(self, interface: Type[T]) -> T:
        """获取服务"""
        return self._container.resolve(interface)

    def get_required_service(self, interface: Type[T]) -> T:
        """获取必需的服务"""
        if not self._container.is_registered(interface):
            raise KeyError(f"Required service not registered: {interface.__name__}")
        return self._container.resolve(interface)

    def get_services(self) -> Dict[str, str]:
        """获取所有服务"""
        return self._container.get_registered_services()


# 全局容器
_container: Optional[DIContainer] = None


def get_di_container() -> DIContainer:
    """获取全局DI容器"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def get_service_provider() -> ServiceProvider:
    """获取全局服务提供者"""
    return get_di_container().build_provider()
