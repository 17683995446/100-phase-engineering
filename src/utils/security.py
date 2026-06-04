"""
安全认证与授权系统
提供API密钥管理、认证中间件、权限控制和审计日志功能
"""
import os
import hashlib
import secrets
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import json

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class Permission(Enum):
    """权限枚举"""
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    ADMIN = auto()
    EXECUTE = auto()


class AuthMethod(Enum):
    """认证方法"""
    API_KEY = auto()
    BEARER_TOKEN = auto()
    BASIC_AUTH = auto()


@dataclass
class APIKey:
    """API密钥"""
    key_id: str
    key_hash: str
    name: str
    permissions: Set[Permission]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True
    rate_limit: int = 1000  # 每分钟请求限制
    description: str = ""
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查是否有效"""
        return self.is_active and not self.is_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含密钥）"""
        return {
            "key_id": self.key_id,
            "name": self.name,
            "permissions": [p.name for p in self.permissions],
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "rate_limit": self.rate_limit,
            "description": self.description
        }


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str = ""
    action: str = ""
    resource: str = ""
    result: str = "success"  # success, failure, denied
    ip_address: str = ""
    user_agent: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details
        }


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self._api_keys: Dict[str, APIKey] = {}
        self._audit_logs: List[AuditLog] = []
        self._max_audit_logs = 10000
        self._rate_limit_cache: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
        self.logger = get_logger("auth.manager")
        self._secret_key = self._generate_secret_key()
    
    def _generate_secret_key(self) -> str:
        """生成密钥"""
        return secrets.token_urlsafe(32)
    
    def _hash_key(self, key: str) -> str:
        """哈希密钥"""
        return hashlib.sha256(f"{self._secret_key}{key}".encode()).hexdigest()
    
    def generate_api_key(
        self,
        name: str,
        permissions: Set[Permission],
        expires_days: Optional[int] = None,
        rate_limit: int = 1000,
        description: str = ""
    ) -> tuple[str, str]:
        """生成API密钥，返回 (原始密钥, key_id)"""
        key = secrets.token_urlsafe(32)
        key_id = secrets.token_hex(16)
        key_hash = self._hash_key(key)
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            expires_at=expires_at,
            rate_limit=rate_limit,
            description=description
        )
        
        with self._lock:
            self._api_keys[key_id] = api_key
        
        self._log_audit(
            user_id=key_id,
            action="CREATE_API_KEY",
            resource="auth",
            result="success",
            details={"name": name, "key_id": key_id}
        )
        
        self.logger.info(f"API key created: {name} ({key_id})")
        return key, key_id
    
    def validate_api_key(self, key: str) -> Optional[APIKey]:
        """验证API密钥"""
        key_hash = self._hash_key(key)
        
        with self._lock:
            for api_key in self._api_keys.values():
                if api_key.key_hash == key_hash:
                    if not api_key.is_valid():
                        self._log_audit(
                            user_id=api_key.key_id,
                            action="VALIDATE_KEY",
                            resource="auth",
                            result="failure",
                            details={"reason": "invalid or expired"}
                        )
                        return None
                    
                    api_key.last_used = datetime.now()
                    return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """撤销API密钥"""
        with self._lock:
            if key_id in self._api_keys:
                api_key = self._api_keys[key_id]
                api_key.is_active = False
                
                self._log_audit(
                    user_id=key_id,
                    action="REVOKE_KEY",
                    resource="auth",
                    result="success"
                )
                
                self.logger.info(f"API key revoked: {key_id}")
                return True
        return False
    
    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """获取API密钥信息"""
        with self._lock:
            api_key = self._api_keys.get(key_id)
            return api_key.to_dict() if api_key else None
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """列出所有API密钥"""
        with self._lock:
            return [key.to_dict() for key in self._api_keys.values()]
    
    def check_rate_limit(self, key_id: str, rate_limit: int = 1000) -> bool:
        """检查速率限制"""
        now = time.time()
        one_minute_ago = now - 60
        
        with self._lock:
            if key_id not in self._rate_limit_cache:
                self._rate_limit_cache[key_id] = []
            
            # 清理过期的记录
            self._rate_limit_cache[key_id] = [
                t for t in self._rate_limit_cache[key_id]
                if t > one_minute_ago
            ]
            
            # 检查是否超过限制
            if len(self._rate_limit_cache[key_id]) >= rate_limit:
                return False
            
            # 添加新请求
            self._rate_limit_cache[key_id].append(now)
            return True
    
    def has_permission(self, key_id: str, permission: Permission) -> bool:
        """检查权限"""
        with self._lock:
            api_key = self._api_keys.get(key_id)
            if api_key and api_key.is_valid():
                return permission in api_key.permissions
        return False
    
    def _log_audit(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str = "success",
        ip_address: str = "",
        user_agent: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录审计日志"""
        log = AuditLog(
            log_id=secrets.token_hex(16),
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
        
        with self._lock:
            self._audit_logs.append(log)
            if len(self._audit_logs) > self._max_audit_logs:
                self._audit_logs.pop(0)
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取审计日志"""
        with self._lock:
            logs = self._audit_logs[-limit:]
            
            if user_id:
                logs = [l for l in logs if l.user_id == user_id]
            if action:
                logs = [l for l in logs if l.action == action]
            
            return [log.to_dict() for log in reversed(logs)]
    
    def log_request(
        self,
        key_id: str,
        path: str,
        method: str,
        result: str = "success",
        ip_address: str = "",
        user_agent: str = ""
    ) -> None:
        """记录请求日志"""
        self._log_audit(
            user_id=key_id,
            action=f"REQUEST:{method}",
            resource=path,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent
        )


# 全局实例
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """获取认证管理器"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
