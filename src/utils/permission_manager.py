"""
权限管理系统
提供权限定义、角色分配、资源访问控制和权限校验功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class PermissionType(Enum):
    """权限类型"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class Permission:
    """权限"""
    resource: str
    action: PermissionType
    conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource,
            "action": self.action.value,
            "conditions": self.conditions
        }

    def __hash__(self):
        return hash((self.resource, self.action.value))

    def __eq__(self, other):
        if isinstance(other, Permission):
            return self.resource == other.resource and self.action == other.action
        return False


@dataclass
class Role:
    """角色"""
    role_id: str
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "permissions": [p.to_dict() for p in self.permissions],
            "metadata": self.metadata
        }


class PermissionManager:
    """权限管理器"""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("permission.manager")

    def create_role(self, role_id: str, name: str,
                    permissions: Optional[List[Permission]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Role:
        """创建角色"""
        with self._lock:
            if role_id in self._roles:
                raise ValueError(f"Role {role_id} already exists")

            role = Role(
                role_id=role_id,
                name=name,
                permissions=set(permissions or []),
                metadata=metadata or {}
            )
            self._roles[role_id] = role
            self._logger.info(f"Role created: {role_id}")
            return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """获取角色"""
        with self._lock:
            return self._roles.get(role_id)

    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        with self._lock:
            if role_id in self._roles:
                del self._roles[role_id]
                # 从所有用户中移除该角色
                for user_roles in self._user_roles.values():
                    user_roles.discard(role_id)
                return True
            return False

    def add_permission_to_role(self, role_id: str,
                               permission: Permission) -> bool:
        """添加权限到角色"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            role.permissions.add(permission)
            return True

    def remove_permission_from_role(self, role_id: str,
                                    permission: Permission) -> bool:
        """从角色移除权限"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            role.permissions.discard(permission)
            return True

    def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """分配角色给用户"""
        with self._lock:
            if role_id not in self._roles:
                return False

            if user_id not in self._user_roles:
                self._user_roles[user_id] = set()

            self._user_roles[user_id].add(role_id)
            self._logger.info(f"Role {role_id} assigned to user {user_id}")
            return True

    def revoke_role_from_user(self, user_id: str, role_id: str) -> bool:
        """撤销用户角色"""
        with self._lock:
            if user_id in self._user_roles:
                self._user_roles[user_id].discard(role_id)
                return True
            return False

    def get_user_roles(self, user_id: str) -> List[Role]:
        """获取用户角色"""
        with self._lock:
            role_ids = self._user_roles.get(user_id, set())
            return [self._roles[rid] for rid in role_ids if rid in self._roles]

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户所有权限"""
        with self._lock:
            role_ids = self._user_roles.get(user_id, set())
            permissions = set()
            for rid in role_ids:
                role = self._roles.get(rid)
                if role:
                    permissions.update(role.permissions)
            return permissions

    def check_permission(self, user_id: str, resource: str,
                         action: PermissionType) -> bool:
        """检查用户权限"""
        with self._lock:
            permissions = self.get_user_permissions(user_id)
            for perm in permissions:
                if perm.resource == resource and perm.action == action:
                    return True
                # 管理员拥有所有权限
                if perm.action == PermissionType.ADMIN:
                    return True
            return False

    def check_any_permission(self, user_id: str,
                             permissions: List[Permission]) -> bool:
        """检查用户是否有任意一个权限"""
        with self._lock:
            user_perms = self.get_user_permissions(user_id)
            for perm in permissions:
                if perm in user_perms:
                    return True
            return False

    def check_all_permissions(self, user_id: str,
                              permissions: List[Permission]) -> bool:
        """检查用户是否拥有所有权限"""
        with self._lock:
            user_perms = self.get_user_permissions(user_id)
            for perm in permissions:
                if perm not in user_perms:
                    return False
            return True

    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        with self._lock:
            return list(self._roles.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_roles": len(self._roles),
                "total_user_assignments": sum(len(roles) for roles in self._user_roles.values()),
                "unique_users": len(self._user_roles)
            }


# 全局实例
_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取全局权限管理器"""
    global _manager
    if _manager is None:
        _manager = PermissionManager()
    return _manager
