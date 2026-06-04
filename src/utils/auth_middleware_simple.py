"""
认证与授权中间件（简化版）
为API层提供认证和授权功能
"""
from typing import Optional, Callable, List
from functools import wraps

from src.utils.security import AuthManager, Permission, get_auth_manager
from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or get_auth_manager()
    
    def check_read(self, key_id: str) -> bool:
        """检查读权限"""
        return self.auth_manager.has_permission(key_id, Permission.READ)
    
    def check_write(self, key_id: str) -> bool:
        """检查写权限"""
        return self.auth_manager.has_permission(key_id, Permission.WRITE)
    
    def check_delete(self, key_id: str) -> bool:
        """检查删除权限"""
        return self.auth_manager.has_permission(key_id, Permission.DELETE)
    
    def check_admin(self, key_id: str) -> bool:
        """检查管理员权限"""
        return self.auth_manager.has_permission(key_id, Permission.ADMIN)
    
    def check_execute(self, key_id: str) -> bool:
        """检查执行权限"""
        return self.auth_manager.has_permission(key_id, Permission.EXECUTE)
    
    def check_all(self, key_id: str, *permissions: Permission) -> bool:
        """检查所有权限"""
        return all(
            self.auth_manager.has_permission(key_id, perm)
            for perm in permissions
        )
    
    def check_any(self, key_id: str, *permissions: Permission) -> bool:
        """检查任意权限"""
        return any(
            self.auth_manager.has_permission(key_id, perm)
            for perm in permissions
        )


def get_permission_checker() -> PermissionChecker:
    """获取权限检查器"""
    return PermissionChecker()
