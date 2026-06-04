"""
密钥管理系统
提供密钥生成、存储、轮换、访问控制和审计功能
"""
import time
import threading
import uuid
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class SecretType(Enum):
    """密钥类型"""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    ENCRYPTION_KEY = "encryption_key"


class SecretStatus(Enum):
    """密钥状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATING = "rotating"


@dataclass
class Secret:
    """密钥"""
    secret_id: str
    name: str
    secret_type: SecretType
    value_hash: str
    status: SecretStatus = SecretStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_rotated: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    allowed_services: Optional[Set[str]] = None
    access_count: int = 0
    last_accessed: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_id": self.secret_id,
            "name": self.name,
            "secret_type": self.secret_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_rotated": self.last_rotated,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "allowed_services": list(self.allowed_services) if self.allowed_services is not None else None
        }


@dataclass
class AccessLog:
    """访问日志"""
    log_id: str
    secret_id: str
    service_id: str
    action: str
    timestamp: float
    success: bool
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "secret_id": self.secret_id,
            "service_id": self.service_id,
            "action": self.action,
            "timestamp": self.timestamp,
            "success": self.success,
            "reason": self.reason
        }


class SecretManager:
    """密钥管理器"""

    def __init__(self):
        self._secrets: Dict[str, Secret] = {}
        self._values: Dict[str, str] = {}
        self._access_logs: List[AccessLog] = []
        self._lock = threading.RLock()
        self._logger = get_logger("secret.manager")

    def _hash_value(self, value: str) -> str:
        """哈希密钥值"""
        return hashlib.sha256(value.encode()).hexdigest()

    def _generate_id(self) -> str:
        """生成ID"""
        return f"sec_{uuid.uuid4().hex[:8]}"

    def create_secret(self, name: str, secret_type: SecretType,
                      value: str,
                      expires_in_seconds: Optional[int] = None,
                      allowed_services: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Secret:
        """创建密钥"""
        with self._lock:
            secret_id = self._generate_id()
            svc_set = set(allowed_services) if allowed_services is not None else None
            secret = Secret(
                secret_id=secret_id,
                name=name,
                secret_type=secret_type,
                value_hash=self._hash_value(value),
                expires_at=time.time() + expires_in_seconds if expires_in_seconds else None,
                allowed_services=svc_set,
                metadata=metadata or {}
            )
            self._secrets[secret_id] = secret
            self._values[secret_id] = value
            self._logger.info(f"Secret created: {secret_id} type={secret_type.value}")
            return secret

    def generate_api_key(self, name: str,
                         allowed_services: Optional[List[str]] = None,
                         expires_in_seconds: Optional[int] = None) -> tuple[Secret, str]:
        """生成API密钥"""
        value = f"ak_{secrets.token_urlsafe(32)}"
        secret = self.create_secret(
            name=name,
            secret_type=SecretType.API_KEY,
            value=value,
            expires_in_seconds=expires_in_seconds,
            allowed_services=allowed_services
        )
        return secret, value

    def generate_password(self, name: str,
                          length: int = 32,
                          allowed_services: Optional[List[str]] = None) -> tuple[Secret, str]:
        """生成密码"""
        value = secrets.token_urlsafe(length)
        secret = self.create_secret(
            name=name,
            secret_type=SecretType.PASSWORD,
            value=value,
            allowed_services=allowed_services
        )
        return secret, value

    def get_secret_value(self, secret_id: str,
                         service_id: str,
                         action: str = "read") -> Optional[str]:
        """获取密钥值（带访问控制）"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                self._log_access(secret_id, service_id, action, False, "secret_not_found")
                return None

            # 检查状态
            if secret.status != SecretStatus.ACTIVE:
                self._log_access(secret_id, service_id, action, False, f"status_{secret.status.value}")
                return None

            # 检查过期
            if secret.expires_at and time.time() > secret.expires_at:
                secret.status = SecretStatus.EXPIRED
                self._log_access(secret_id, service_id, action, False, "expired")
                return None

            # 检查服务权限
            if secret.allowed_services is not None and service_id not in secret.allowed_services:
                self._log_access(secret_id, service_id, action, False, "unauthorized_service")
                return None

            # 记录访问
            secret.access_count += 1
            secret.last_accessed = time.time()
            self._log_access(secret_id, service_id, action, True)
            return self._values.get(secret_id)

    def _log_access(self, secret_id: str, service_id: str,
                    action: str, success: bool, reason: Optional[str] = None) -> None:
        """记录访问日志"""
        log = AccessLog(
            log_id=f"log_{uuid.uuid4().hex[:8]}",
            secret_id=secret_id,
            service_id=service_id,
            action=action,
            timestamp=time.time(),
            success=success,
            reason=reason
        )
        self._access_logs.append(log)

    def verify_secret(self, secret_id: str, value: str) -> bool:
        """验证密钥"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                return False
            return secret.value_hash == self._hash_value(value)

    def rotate_secret(self, secret_id: str,
                      new_value: Optional[str] = None) -> Optional[Secret]:
        """轮换密钥"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                return None

            secret.status = SecretStatus.ROTATING
            if new_value is None:
                if secret.secret_type == SecretType.API_KEY:
                    _, new_value = self.generate_api_key(secret.name)
                    new_value = new_value
                else:
                    new_value = secrets.token_urlsafe(32)

            secret.value_hash = self._hash_value(new_value)
            self._values[secret_id] = new_value
            secret.last_rotated = time.time()
            secret.status = SecretStatus.ACTIVE
            secret.access_count = 0
            self._logger.info(f"Secret rotated: {secret_id}")
            return secret

    def revoke_secret(self, secret_id: str) -> bool:
        """撤销密钥"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                return False
            secret.status = SecretStatus.REVOKED
            if secret_id in self._values:
                del self._values[secret_id]
            self._logger.info(f"Secret revoked: {secret_id}")
            return True

    def delete_secret(self, secret_id: str) -> bool:
        """删除密钥"""
        with self._lock:
            if secret_id in self._secrets:
                del self._secrets[secret_id]
            if secret_id in self._values:
                del self._values[secret_id]
            self._logger.info(f"Secret deleted: {secret_id}")
            return True

    def get_secret(self, secret_id: str) -> Optional[Secret]:
        """获取密钥信息（不包含值）"""
        with self._lock:
            return self._secrets.get(secret_id)

    def list_secrets(self, secret_type: Optional[SecretType] = None,
                     status: Optional[SecretStatus] = None) -> List[Dict[str, Any]]:
        """列出密钥"""
        with self._lock:
            secrets_list = self._secrets.values()
            if secret_type:
                secrets_list = [s for s in secrets_list if s.secret_type == secret_type]
            if status:
                secrets_list = [s for s in secrets_list if s.status == status]
            return [s.to_dict() for s in secrets_list]

    def get_access_logs(self, secret_id: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """获取访问日志"""
        with self._lock:
            logs = self._access_logs
            if secret_id:
                logs = [l for l in logs if l.secret_id == secret_id]
            return [l.to_dict() for l in logs[-limit:]]

    def grant_access(self, secret_id: str, service_id: str) -> bool:
        """授予服务访问权限"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                return False
            if secret.allowed_services is None:
                secret.allowed_services = set()
            secret.allowed_services.add(service_id)
            return True

    def revoke_access(self, secret_id: str, service_id: str) -> bool:
        """撤销服务访问权限"""
        with self._lock:
            secret = self._secrets.get(secret_id)
            if not secret:
                return False
            if secret.allowed_services is not None:
                secret.allowed_services.discard(service_id)
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._secrets)
            active = sum(1 for s in self._secrets.values() if s.status == SecretStatus.ACTIVE)
            expired = sum(1 for s in self._secrets.values() if s.status == SecretStatus.EXPIRED)
            revoked = sum(1 for s in self._secrets.values() if s.status == SecretStatus.REVOKED)
            return {
                "total_secrets": total,
                "active": active,
                "expired": expired,
                "revoked": revoked,
                "total_access_logs": len(self._access_logs)
            }


# 全局实例
_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """获取全局密钥管理器"""
    global _manager
    if _manager is None:
        _manager = SecretManager()
    return _manager
