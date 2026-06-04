"""
用户中心系统
提供用户注册、认证、资料管理和账户安全功能
"""
import time
import hashlib
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class UserStatus(Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class AccountType(Enum):
    """账户类型"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class UserProfile:
    """用户资料"""
    display_name: str = ""
    avatar_url: str = ""
    bio: str = ""
    phone: str = ""
    address: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "phone": self.phone,
            "address": self.address,
            "preferences": self.preferences
        }


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    email: str
    password_hash: str
    status: UserStatus = UserStatus.ACTIVE
    account_type: AccountType = AccountType.FREE
    profile: UserProfile = field(default_factory=UserProfile)
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "status": self.status.value,
            "account_type": self.account_type.value,
            "profile": self.profile.to_dict(),
            "created_at": self.created_at,
            "last_login": self.last_login,
            "metadata": self.metadata
        }


class PasswordHasher:
    """密码哈希器"""

    _store: Dict[str, str] = {}

    @classmethod
    def hash(cls, password: str) -> str:
        """哈希密码"""
        salt = str(time.time())
        hashed = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        cls._store[hashed] = password
        return hashed

    @classmethod
    def verify(cls, password: str, password_hash: str) -> bool:
        """验证密码"""
        stored = cls._store.get(password_hash)
        return stored == password


class UserCenter:
    """用户中心"""

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}
        self._email_index: Dict[str, str] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("user.center")

    def register(self, user_id: str, username: str, email: str,
                 password: str, account_type: AccountType = AccountType.FREE,
                 profile: Optional[UserProfile] = None) -> User:
        """注册用户"""
        with self._lock:
            if user_id in self._users:
                raise ValueError(f"User {user_id} already exists")
            if username in self._username_index:
                raise ValueError(f"Username {username} already taken")
            if email in self._email_index:
                raise ValueError(f"Email {email} already registered")

            password_hash = PasswordHasher.hash(password)
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                account_type=account_type,
                profile=profile or UserProfile()
            )

            self._users[user_id] = user
            self._username_index[username] = user_id
            self._email_index[email] = user_id
            self._logger.info(f"User registered: {user_id}")
            return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """认证用户"""
        with self._lock:
            user_id = self._username_index.get(username)
            if not user_id:
                return None

            user = self._users.get(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                return None

            if PasswordHasher.verify(password, user.password_hash):
                user.last_login = time.time()
                return user
            return None

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        with self._lock:
            return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        with self._lock:
            user_id = self._username_index.get(username)
            if user_id:
                return self._users.get(user_id)
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        with self._lock:
            user_id = self._email_index.get(email)
            if user_id:
                return self._users.get(user_id)
            return None

    def update_profile(self, user_id: str,
                       profile: UserProfile) -> bool:
        """更新用户资料"""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            user.profile = profile
            return True

    def update_status(self, user_id: str, status: UserStatus) -> bool:
        """更新用户状态"""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            user.status = status
            self._logger.info(f"User {user_id} status updated to {status.value}")
            return True

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> bool:
        """修改密码"""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            if not PasswordHasher.verify(old_password, user.password_hash):
                return False

            user.password_hash = PasswordHasher.hash(new_password)
            return True

    def upgrade_account(self, user_id: str,
                        account_type: AccountType) -> bool:
        """升级账户"""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            user.account_type = account_type
            self._logger.info(f"User {user_id} upgraded to {account_type.value}")
            return True

    def list_users(self, status: Optional[UserStatus] = None,
                   account_type: Optional[AccountType] = None) -> List[User]:
        """列出用户"""
        with self._lock:
            users = list(self._users.values())
            if status:
                users = [u for u in users if u.status == status]
            if account_type:
                users = [u for u in users if u.account_type == account_type]
            return users

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False

            del self._username_index[user.username]
            del self._email_index[user.email]
            del self._users[user_id]
            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._users)
            active = sum(1 for u in self._users.values()
                        if u.status == UserStatus.ACTIVE)
            by_type = {}
            for u in self._users.values():
                t = u.account_type.value
                by_type[t] = by_type.get(t, 0) + 1

            return {
                "total_users": total,
                "active_users": active,
                "by_account_type": by_type
            }


# 全局实例
_user_center: Optional[UserCenter] = None


def get_user_center() -> UserCenter:
    """获取全局用户中心"""
    global _user_center
    if _user_center is None:
        _user_center = UserCenter()
    return _user_center
