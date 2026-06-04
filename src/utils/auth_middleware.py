"""
认证与授权中间件
为API层提供认证和授权功能
"""
from typing import Optional, Callable, List
from functools import wraps

from src.api_layer.core import APIRequest, APIResponse, APIMiddleware, HTTPStatus
from src.api_layer.responses import create_success_response, create_error_response
from src.utils.security import AuthManager, Permission, get_auth_manager
from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class AuthMiddleware(APIMiddleware):
    """认证中间件"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or get_auth_manager()
        self._logger = get_logger("auth.middleware")
        self._public_paths = {
            "/health", "/health/live", "/health/ready",
            "/metrics", "/api/info"
        }
    
    def is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        for public_path in self._public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    def extract_api_key(self, request: APIRequest) -> Optional[str]:
        """从请求中提取API密钥"""
        # 从请求头提取
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # 从查询参数提取
        if "api_key" in request.params:
            return request.params["api_key"]
        
        return None
    
    def before_request(self, request: APIRequest) -> Optional[APIResponse]:
        """请求前验证"""
        # 公开路径不需要认证
        if self.is_public_path(request.path):
            return None
        
        # 提取API密钥
        api_key = self.extract_api_key(request)
        
        if not api_key:
            self._logger.warning(f"No API key provided: {request.path}")
            return create_error_response(
                "AUTH_REQUIRED",
                "API key is required",
                HTTPStatus.UNAUTHORIZED.value
            )
        
        # 验证密钥
        key_info = self.auth_manager.validate_api_key(api_key)
        
        if not key_info:
            self._logger.warning(f"Invalid API key: {request.path}")
            return create_error_response(
                "INVALID_KEY",
                "Invalid or expired API key",
                HTTPStatus.UNAUTHORIZED.value
            )
        
        # 检查速率限制
        if not self.auth_manager.check_rate_limit(key_info.key_id, key_info.rate_limit):
            self._logger.warning(f"Rate limit exceeded: {key_info.key_id}")
            return create_error_response(
                "RATE_LIMIT_EXCEEDED",
                "Rate limit exceeded. Please try again later.",
                HTTPStatus.TOO_MANY_REQUESTS.value
            )
        
        # 将认证信息添加到请求
        request.headers["X-Auth-Key-Id"] = key_info.key_id
        request.headers["X-Auth-Key-Name"] = key_info.name
        
        return None
    
    def after_request(self, request: APIRequest, response: APIResponse) -> APIResponse:
        """请求后记录日志"""
        key_id = request.headers.get("X-Auth-Key-Id", "anonymous")
        
        result = "success" if response.status_code < 400 else "failure"
        
        self.auth_manager.log_request(
            key_id=key_id,
            path=request.path,
            method=request.method.name,
            result=result,
            ip_address=request.headers.get("X-Forwarded-For", ""),
            user_agent=request.headers.get("User-Agent", "")
        )
        
        return response


class RequirePermission:
    """权限要求装饰器"""
    
    def __init__(self, *permissions: Permission):
        self.permissions = set(permissions)
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: APIRequest, *args, **kwargs):
            key_id = request.headers.get("X-Auth-Key-Id")
            
            if not key_id:
                return create_error_response(
                    "AUTH_REQUIRED",
                    "Authentication required",
                    HTTPStatus.UNAUTHORIZED.value
                )
            
            auth_manager = get_auth_manager()
            
            for permission in self.permissions:
                if not auth_manager.has_permission(key_id, permission):
                    auth_manager._log_audit(
                        user_id=key_id,
                        action="PERMISSION_DENIED",
                        resource=request.path,
                        result="denied",
                        details={"required_permission": permission.name}
                    )
                    
                    return create_error_response(
                        "PERMISSION_DENIED",
                        f"Permission '{permission.name}' is required",
                        HTTPStatus.FORBIDDEN.value
                    )
            
            return func(request, *args, **kwargs)
        
        return wrapper


def require_permissions(*permissions: Permission):
    """权限要求装饰器工厂"""
    return RequirePermission(*permissions)


def require_auth(func: Callable) -> Callable:
    """认证要求装饰器"""
    @wraps(func)
    def wrapper(request: APIRequest, *args, **kwargs):
        key_id = request.headers.get("X-Auth-Key-Id")
        
        if not key_id:
            return create_error_response(
                "AUTH_REQUIRED",
                "Authentication required",
                HTTPStatus.UNAUTHORIZED.value
            )
        
        return func(request, *args, **kwargs)
    
    return wrapper


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
