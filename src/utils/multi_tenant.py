"""
多租户架构系统
提供租户隔离、资源配额、数据隔离和租户管理功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class TenantQuota:
    """租户配额"""
    max_users: int = 100
    max_storage_mb: int = 1000
    max_requests_per_minute: int = 1000
    max_projects: int = 10
    custom_limits: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_users": self.max_users,
            "max_storage_mb": self.max_storage_mb,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_projects": self.max_projects,
            "custom_limits": self.custom_limits
        }


@dataclass
class Tenant:
    """租户"""
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    quota: TenantQuota = field(default_factory=TenantQuota)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status.value,
            "quota": self.quota.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at
        }


class TenantContext:
    """租户上下文"""

    def __init__(self):
        self._current_tenant: Optional[str] = None
        self._lock = threading.Lock()

    def set_tenant(self, tenant_id: str) -> None:
        """设置当前租户"""
        with self._lock:
            self._current_tenant = tenant_id

    def get_tenant(self) -> Optional[str]:
        """获取当前租户"""
        with self._lock:
            return self._current_tenant

    def clear(self) -> None:
        """清除当前租户"""
        with self._lock:
            self._current_tenant = None


class TenantManager:
    """租户管理器"""

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("tenant.manager")

    def create_tenant(self, tenant_id: str, name: str,
                      quota: Optional[TenantQuota] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Tenant:
        """创建租户"""
        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"Tenant {tenant_id} already exists")

            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                quota=quota or TenantQuota(),
                metadata=metadata or {}
            )
            self._tenants[tenant_id] = tenant
            self._logger.info(f"Created tenant: {tenant_id}")
            return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        with self._lock:
            return self._tenants.get(tenant_id)

    def update_tenant(self, tenant_id: str,
                      name: Optional[str] = None,
                      quota: Optional[TenantQuota] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False

            if name:
                tenant.name = name
            if quota:
                tenant.quota = quota
            if metadata:
                tenant.metadata.update(metadata)

            return True

    def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.SUSPENDED
            self._logger.info(f"Suspended tenant: {tenant_id}")
            return True

    def activate_tenant(self, tenant_id: str) -> bool:
        """激活租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.ACTIVE
            self._logger.info(f"Activated tenant: {tenant_id}")
            return True

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.DELETED
            self._logger.info(f"Deleted tenant: {tenant_id}")
            return True

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """列出租户"""
        with self._lock:
            tenants = list(self._tenants.values())
            if status:
                tenants = [t for t in tenants if t.status == status]
            return tenants

    def check_quota(self, tenant_id: str, resource: str,
                    current_usage: int) -> bool:
        """检查配额"""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant or tenant.status != TenantStatus.ACTIVE:
                return False

            quota = tenant.quota
            if resource == "users":
                return current_usage < quota.max_users
            elif resource == "storage_mb":
                return current_usage < quota.max_storage_mb
            elif resource == "requests_per_minute":
                return current_usage < quota.max_requests_per_minute
            elif resource == "projects":
                return current_usage < quota.max_projects
            elif resource in quota.custom_limits:
                return current_usage < quota.custom_limits[resource]
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._tenants)
            active = sum(1 for t in self._tenants.values()
                        if t.status == TenantStatus.ACTIVE)
            suspended = sum(1 for t in self._tenants.values()
                          if t.status == TenantStatus.SUSPENDED)
            return {
                "total_tenants": total,
                "active": active,
                "suspended": suspended,
                "deleted": total - active - suspended
            }


class TenantAwareStorage:
    """租户感知存储"""

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("tenant.storage")

    def _get_key(self, tenant_id: str, key: str) -> str:
        """生成租户隔离的键"""
        return f"{tenant_id}:{key}"

    def get(self, tenant_id: str, key: str) -> Optional[Any]:
        """获取数据"""
        with self._lock:
            return self._data.get(tenant_id, {}).get(key)

    def set(self, tenant_id: str, key: str, value: Any) -> None:
        """设置数据"""
        with self._lock:
            if tenant_id not in self._data:
                self._data[tenant_id] = {}
            self._data[tenant_id][key] = value

    def delete(self, tenant_id: str, key: str) -> bool:
        """删除数据"""
        with self._lock:
            if tenant_id in self._data and key in self._data[tenant_id]:
                del self._data[tenant_id][key]
                return True
            return False

    def get_all(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户所有数据"""
        with self._lock:
            return dict(self._data.get(tenant_id, {}))

    def clear_tenant(self, tenant_id: str) -> None:
        """清除租户数据"""
        with self._lock:
            if tenant_id in self._data:
                del self._data[tenant_id]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_tenants": len(self._data),
                "total_keys": sum(len(d) for d in self._data.values())
            }


# 全局实例
_manager: Optional[TenantManager] = None
_storage: Optional[TenantAwareStorage] = None
_context: Optional[TenantContext] = None


def get_tenant_manager() -> TenantManager:
    """获取全局租户管理器"""
    global _manager
    if _manager is None:
        _manager = TenantManager()
    return _manager


def get_tenant_storage() -> TenantAwareStorage:
    """获取全局租户存储"""
    global _storage
    if _storage is None:
        _storage = TenantAwareStorage()
    return _storage


def get_tenant_context() -> TenantContext:
    """获取全局租户上下文"""
    global _context
    if _context is None:
        _context = TenantContext()
    return _context
