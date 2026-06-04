"""
角色管理系统
提供角色定义、继承、层级和动态权限功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from src.utils.structured_logging import get_logger
from src.utils.permission_manager import Permission, PermissionType


@dataclass
class RoleDefinition:
    """角色定义"""
    role_id: str
    name: str
    description: str = ""
    parent_roles: List[str] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "parent_roles": self.parent_roles,
            "permissions": [p.to_dict() for p in self.permissions],
            "metadata": self.metadata
        }


class RoleManager:
    """角色管理器"""

    def __init__(self):
        self._roles: Dict[str, RoleDefinition] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("role.manager")

    def create_role(self, role_id: str, name: str,
                    description: str = "",
                    parent_roles: Optional[List[str]] = None,
                    permissions: Optional[List[Permission]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> RoleDefinition:
        """创建角色"""
        with self._lock:
            if role_id in self._roles:
                raise ValueError(f"Role {role_id} already exists")

            # 验证父角色存在
            for parent in (parent_roles or []):
                if parent not in self._roles:
                    raise ValueError(f"Parent role {parent} does not exist")

            role = RoleDefinition(
                role_id=role_id,
                name=name,
                description=description,
                parent_roles=parent_roles or [],
                permissions=set(permissions or []),
                metadata=metadata or {}
            )
            self._roles[role_id] = role
            self._logger.info(f"Role created: {role_id}")
            return role

    def get_role(self, role_id: str) -> Optional[RoleDefinition]:
        """获取角色"""
        with self._lock:
            return self._roles.get(role_id)

    def update_role(self, role_id: str,
                    name: Optional[str] = None,
                    description: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新角色"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            if name:
                role.name = name
            if description is not None:
                role.description = description
            if metadata:
                role.metadata.update(metadata)
            return True

    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        with self._lock:
            if role_id not in self._roles:
                return False

            # 检查是否有子角色
            for role in self._roles.values():
                if role_id in role.parent_roles:
                    raise ValueError(f"Cannot delete role {role_id}: has child roles")

            del self._roles[role_id]
            return True

    def add_parent_role(self, role_id: str, parent_id: str) -> bool:
        """添加父角色"""
        with self._lock:
            role = self._roles.get(role_id)
            parent = self._roles.get(parent_id)
            if not role or not parent:
                return False

            if parent_id in role.parent_roles:
                return True

            # 检查循环依赖
            if self._would_create_cycle(role_id, parent_id):
                raise ValueError("Would create circular dependency")

            role.parent_roles.append(parent_id)
            return True

    def remove_parent_role(self, role_id: str, parent_id: str) -> bool:
        """移除父角色"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            if parent_id in role.parent_roles:
                role.parent_roles.remove(parent_id)
                return True
            return False

    def _would_create_cycle(self, role_id: str, parent_id: str) -> bool:
        """检查是否会创建循环依赖"""
        visited = set()
        queue = [parent_id]
        while queue:
            current = queue.pop(0)
            if current == role_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            role = self._roles.get(current)
            if role:
                queue.extend(role.parent_roles)
        return False

    def add_permission(self, role_id: str, permission: Permission) -> bool:
        """添加权限"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            role.permissions.add(permission)
            return True

    def remove_permission(self, role_id: str, permission: Permission) -> bool:
        """移除权限"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return False

            role.permissions.discard(permission)
            return True

    def get_effective_permissions(self, role_id: str) -> Set[Permission]:
        """获取有效权限（包含继承的）"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return set()

            permissions = set(role.permissions)
            visited = set()
            queue = list(role.parent_roles)

            while queue:
                parent_id = queue.pop(0)
                if parent_id in visited:
                    continue
                visited.add(parent_id)

                parent = self._roles.get(parent_id)
                if parent:
                    permissions.update(parent.permissions)
                    queue.extend(parent.parent_roles)

            return permissions

    def get_role_hierarchy(self, role_id: str) -> List[str]:
        """获取角色层级"""
        with self._lock:
            role = self._roles.get(role_id)
            if not role:
                return []

            hierarchy = []
            visited = set()
            queue = [role_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                hierarchy.append(current)

                current_role = self._roles.get(current)
                if current_role:
                    queue.extend(current_role.parent_roles)

            return hierarchy

    def list_roles(self) -> List[RoleDefinition]:
        """列出所有角色"""
        with self._lock:
            return list(self._roles.values())

    def get_child_roles(self, role_id: str) -> List[str]:
        """获取子角色"""
        with self._lock:
            return [
                rid for rid, role in self._roles.items()
                if role_id in role.parent_roles
            ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_roles": len(self._roles),
                "roles_with_parents": sum(1 for r in self._roles.values() if r.parent_roles),
                "total_permissions": sum(len(r.permissions) for r in self._roles.values())
            }


# 全局实例
_manager: Optional[RoleManager] = None


def get_role_manager() -> RoleManager:
    """获取全局角色管理器"""
    global _manager
    if _manager is None:
        _manager = RoleManager()
    return _manager
