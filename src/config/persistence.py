"""
持久化与配置管理系统
遵循信息最小熵公理：配置信息显式化、可追溯
"""

import os
import json
import hashlib
import base64
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from enum import Enum, auto
from dataclasses import dataclass, field
import copy
import tempfile


class ConfigFormat(Enum):
    """配置格式"""
    JSON = auto()
    YAML = auto()
    ENV = auto()
    TOML = auto()


class ConfigScope(Enum):
    """配置作用域"""
    GLOBAL = auto()
    SYSTEM = auto()
    AGENT = auto()
    TASK = auto()
    WORKFLOW = auto()


class StorageBackend(Enum):
    """存储后端"""
    FILE = auto()
    MEMORY = auto()
    HYBRID = auto()


@dataclass
class ConfigVersion:
    """配置版本"""
    version_id: str
    timestamp: datetime
    config_data: Dict[str, Any]
    checksum: str
    description: str
    author: str = "system"


@dataclass
class ConfigChange:
    """配置变更记录"""
    change_id: str
    scope: ConfigScope
    key_path: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    reason: str
    reversible: bool


@dataclass
class SecretKey:
    """密钥管理"""
    key_id: str
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None
    description: str = ""


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self._rules: Dict[str, Callable[[Any], bool]] = {}

    def add_rule(self, key_pattern: str, validator: Callable[[Any], bool]):
        """添加验证规则"""
        self._rules[key_pattern] = validator

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        for pattern, validator in self._rules.items():
            value = self._get_value_at_pattern(pattern, config)
            if value is not None:
                try:
                    if not validator(value):
                        errors.append(f"Validation failed for pattern: {pattern}")
                except Exception as e:
                    errors.append(f"Validation error for {pattern}: {str(e)}")
        return errors

    def _get_value_at_pattern(self, pattern: str, data: Dict) -> Optional[Any]:
        """获取模式对应的值"""
        keys = pattern.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


class ConfigPersistence:
    """配置持久化管理器"""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        backend: StorageBackend = StorageBackend.HYBRID,
        max_versions: int = 50
    ):
        self._storage_path = storage_path or Path.home() / ".agent_system" / "config"
        self._backend = backend
        self._max_versions = max_versions
        self._memory_cache: Dict[str, Any] = {}
        self._versions: Dict[str, List[ConfigVersion]] = {}
        self._change_history: List[ConfigChange] = []
        self._validator = ConfigValidator()
        self._secret_keys: Dict[str, SecretKey] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_save": [],
            "post_save": [],
            "pre_load": [],
            "post_load": [],
            "on_change": []
        }

        if backend != StorageBackend.MEMORY:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            self._init_storage_structure()

    def _init_storage_structure(self):
        """初始化存储结构"""
        dirs = [
            "global",
            "system",
            "agent",
            "task",
            "workflow",
            "secrets",
            "versions"
        ]
        for dir_name in dirs:
            (self._storage_path / dir_name).mkdir(parents=True, exist_ok=True)

    def register_hook(self, event: str, callback: Callable):
        """注册钩子函数"""
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _execute_hooks(self, event: str, *args, **kwargs):
        """执行钩子函数"""
        for callback in self._hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                pass

    def save(
        self,
        scope: ConfigScope,
        config_data: Dict[str, Any],
        name: str = "default",
        description: str = "",
        author: str = "system",
        validate: bool = True
    ) -> bool:
        """保存配置"""
        self._execute_hooks("pre_save", scope, config_data)

        if validate:
            errors = self._validator.validate(config_data)
            if errors:
                return False

        config_key = self._get_config_key(scope, name)

        if scope == ConfigScope.GLOBAL:
            cache_data = copy.deepcopy(config_data)
        else:
            cache_data = config_data

        self._memory_cache[config_key] = copy.deepcopy(cache_data)

        if self._backend != StorageBackend.MEMORY:
            file_path = self._get_config_file_path(scope, name)
            metadata = {
                "scope": scope.name,
                "name": name,
                "saved_at": datetime.now().isoformat(),
                "author": author,
                "description": description,
                "checksum": self._calculate_checksum(cache_data)
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"metadata": metadata, "data": cache_data}, f, indent=2, ensure_ascii=False)

            self._create_version(config_key, cache_data, description, author)

        self._execute_hooks("post_save", scope, config_data)
        return True

    def load(
        self,
        scope: ConfigScope,
        name: str = "default",
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """加载配置"""
        config_key = self._get_config_key(scope, name)
        self._execute_hooks("pre_load", scope, name)

        if version:
            return self._load_version(config_key, version)

        if config_key in self._memory_cache:
            self._execute_hooks("post_load", scope, self._memory_cache[config_key])
            return copy.deepcopy(self._memory_cache[config_key])

        if self._backend != StorageBackend.MEMORY:
            file_path = self._get_config_file_path(scope, name)
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    config_data = loaded.get("data", {})
                    self._memory_cache[config_key] = copy.deepcopy(config_data)
                    self._execute_hooks("post_load", scope, config_data)
                    return config_data

        return None

    def delete(self, scope: ConfigScope, name: str = "default") -> bool:
        """删除配置"""
        config_key = self._get_config_key(scope, name)

        if config_key in self._memory_cache:
            del self._memory_cache[config_key]

        if self._backend != StorageBackend.MEMORY:
            file_path = self._get_config_file_path(scope, name)
            if file_path.exists():
                backup_path = file_path.with_suffix(".backup")
                shutil.move(str(file_path), str(backup_path))
                return True

        return False

    def list_configs(self, scope: Optional[ConfigScope] = None) -> List[str]:
        """列出配置"""
        configs = []

        if self._backend != StorageBackend.MEMORY:
            base_path = self._storage_path
            if scope:
                base_path = base_path / scope.name.lower()

            if base_path.exists():
                for file_path in base_path.glob("*.json"):
                    configs.append(file_path.stem)

        for key in self._memory_cache.keys():
            if scope:
                key_scope = self._parse_config_key(key)[0]
                if key_scope == scope:
                    configs.append(self._parse_config_key(key)[1])
            else:
                configs.append(key)

        return list(set(configs))

    def get_versions(self, scope: ConfigScope, name: str = "default") -> List[ConfigVersion]:
        """获取配置版本历史"""
        config_key = self._get_config_key(scope, name)
        return self._versions.get(config_key, [])

    def rollback(self, scope: ConfigScope, name: str = "default", version_id: Optional[str] = None) -> bool:
        """回滚配置到指定版本"""
        config_key = self._get_config_key(scope, name)
        versions = self._versions.get(config_key, [])

        if not versions:
            return False

        target_version = None
        if version_id:
            for v in versions:
                if v.version_id == version_id:
                    target_version = v
                    break
        else:
            if len(versions) > 1:
                target_version = versions[-2]

        if target_version:
            self.save(
                scope,
                copy.deepcopy(target_version.config_data),
                name,
                f"Rollback to version {target_version.version_id}",
                "system",
                validate=False
            )
            return True

        return False

    def merge(
        self,
        scope: ConfigScope,
        configs: List[str],
        strategy: str = "override"
    ) -> Dict[str, Any]:
        """合并多个配置"""
        merged: Dict[str, Any] = {}

        for config_name in configs:
            config_data = self.load(scope, config_name)
            if config_data:
                if strategy == "override":
                    merged.update(config_data)
                elif strategy == "deep_merge":
                    merged = self._deep_merge(merged, config_data)

        return merged

    def export(
        self,
        scope: ConfigScope,
        name: str = "default",
        format: ConfigFormat = ConfigFormat.JSON,
        target_path: Optional[Path] = None
    ) -> Optional[Path]:
        """导出配置"""
        config_data = self.load(scope, name)
        if not config_data:
            return None

        if target_path is None:
            target_path = self._storage_path / f"{scope.name.lower()}_{name}.{format.name.lower()}"

        if format == ConfigFormat.JSON:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        elif format == ConfigFormat.ENV:
            self._export_as_env(config_data, target_path)

        return target_path

    def import_config(
        self,
        source_path: Path,
        scope: ConfigScope,
        name: str = "default",
        format: ConfigFormat = ConfigFormat.JSON
    ) -> bool:
        """导入配置"""
        try:
            if format == ConfigFormat.JSON:
                with open(source_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            elif format == ConfigFormat.ENV:
                config_data = self._import_from_env(source_path)
            else:
                return False

            return self.save(scope, config_data, name)
        except Exception:
            return False

    def watch_changes(self, scope: ConfigScope, name: str = "default") -> bool:
        """监视配置变化"""
        if self._backend == StorageBackend.MEMORY:
            return False

        file_path = self._get_config_file_path(scope, name)
        return file_path.exists()

    def _get_config_key(self, scope: ConfigScope, name: str) -> str:
        """获取配置键"""
        return f"{scope.name}:{name}"

    def _parse_config_key(self, key: str) -> tuple:
        """解析配置键"""
        parts = key.split(":")
        return ConfigScope[parts[0]], parts[1] if len(parts) > 1 else "default"

    def _get_config_file_path(self, scope: ConfigScope, name: str) -> Path:
        """获取配置文件路径"""
        return self._storage_path / scope.name.lower() / f"{name}.json"

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算校验和"""
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _create_version(
        self,
        config_key: str,
        config_data: Dict[str, Any],
        description: str,
        author: str
    ):
        """创建配置版本"""
        if config_key not in self._versions:
            self._versions[config_key] = []

        version = ConfigVersion(
            version_id=f"v{len(self._versions[config_key]) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            config_data=copy.deepcopy(config_data),
            checksum=self._calculate_checksum(config_data),
            description=description,
            author=author
        )

        self._versions[config_key].append(version)

        if len(self._versions[config_key]) > self._max_versions:
            self._versions[config_key] = self._versions[config_key][-self._max_versions:]

    def _load_version(self, config_key: str, version_id: str) -> Optional[Dict[str, Any]]:
        """加载指定版本"""
        versions = self._versions.get(config_key, [])
        for v in versions:
            if v.version_id == version_id:
                return copy.deepcopy(v.config_data)
        return None

    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """深度合并配置"""
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _export_as_env(self, data: Dict, target_path: Path):
        """导出为环境变量格式"""
        def flatten(d: Dict, prefix: str = "") -> Dict:
            items = {}
            for key, value in d.items():
                new_key = f"{prefix}{key}".upper().replace(".", "_")
                if isinstance(value, dict):
                    items.update(flatten(value, f"{new_key}_"))
                else:
                    items[new_key] = str(value)
            return items

        flat_data = flatten(data)
        with open(target_path, "w", encoding="utf-8") as f:
            for key, value in flat_data.items():
                f.write(f"{key}={value}\n")

    def _import_from_env(self, source_path: Path) -> Dict:
        """从环境变量文件导入"""
        data = {}
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    keys = key.lower().split("_")
                    self._set_nested(data, keys, value)
        return data

    def _set_nested(self, data: Dict, keys: List[str], value: Any):
        """设置嵌套值"""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


class SecretManager:
    """敏感信息管理器"""

    def __init__(self, persistence: ConfigPersistence):
        self._persistence = persistence
        self._memory_secrets: Dict[str, bytes] = {}
        self._encryption_key = self._get_or_create_encryption_key()

    def _get_or_create_encryption_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = self._persistence._storage_path / "secrets" / ".key"
        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = os.urandom(32)
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)
            return key

    def store_secret(
        self,
        key_id: str,
        value: str,
        description: str = "",
        expires_at: Optional[datetime] = None
    ) -> bool:
        """存储敏感信息"""
        try:
            encoded = base64.b64encode(value.encode()).decode()
            secret_key = SecretKey(
                key_id=key_id,
                key_data=encoded.encode(),
                created_at=datetime.now(),
                expires_at=expires_at,
                description=description
            )
            self._persistence._secret_keys[key_id] = secret_key
            self._memory_secrets[key_id] = value.encode()
            return True
        except Exception:
            return False

    def get_secret(self, key_id: str) -> Optional[str]:
        """获取敏感信息"""
        if key_id in self._persistence._secret_keys:
            secret_key = self._persistence._secret_keys[key_id]
            if secret_key.expires_at and secret_key.expires_at < datetime.now():
                return None
            return base64.b64decode(secret_key.key_data).decode()

        if key_id in self._memory_secrets:
            return self._memory_secrets[key_id].decode()

        return None

    def delete_secret(self, key_id: str) -> bool:
        """删除敏感信息"""
        if key_id in self._memory_secrets:
            del self._memory_secrets[key_id]
        if key_id in self._persistence._secret_keys:
            del self._persistence._secret_keys[key_id]
        return True

    def list_secrets(self) -> List[str]:
        """列出所有敏感信息键"""
        keys = list(self._persistence._secret_keys.keys())
        keys.extend(list(self._memory_secrets.keys()))
        return list(set(keys))


class EnvironmentConfig:
    """环境配置管理"""

    def __init__(self, persistence: ConfigPersistence):
        self._persistence = persistence
        self._env_overrides: Dict[str, str] = {}

    def sync_from_env(self, prefix: str = "AGENT_") -> int:
        """从环境变量同步配置"""
        count = 0
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._env_overrides[config_key] = value
                count += 1
        return count

    def sync_to_env(self, scope: ConfigScope, name: str = "default", prefix: str = "AGENT_") -> bool:
        """将配置同步到环境变量"""
        config_data = self._persistence.load(scope, name)
        if not config_data:
            return False

        def flatten_and_set(d: Dict, prefix: str = ""):
            for key, value in d.items():
                env_key = f"{prefix}{key}".upper()
                if isinstance(value, dict):
                    flatten_and_set(value, f"{env_key}_")
                else:
                    os.environ[env_key] = str(value)

        flatten_and_set(config_data, prefix)
        return True

    def get_override(self, key: str) -> Optional[str]:
        """获取环境变量覆盖值"""
        return self._env_overrides.get(key)

    def set_override(self, key: str, value: str):
        """设置环境变量覆盖值"""
        self._env_overrides[key] = value

    def clear_overrides(self):
        """清除所有覆盖值"""
        self._env_overrides.clear()

    def get_effective_value(self, key: str, default: Any = None) -> Any:
        """获取有效值（优先环境变量覆盖）"""
        if key in self._env_overrides:
            return self._env_overrides[key]
        return os.environ.get(key, default)


class HotReloadConfig:
    """配置热加载"""

    def __init__(self, persistence: ConfigPersistence):
        self._persistence = persistence
        self._last_modified: Dict[str, datetime] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def register_callback(self, scope: ConfigScope, name: str, callback: Callable):
        """注册配置变更回调"""
        key = f"{scope.name}:{name}"
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def check_and_reload(self, scope: ConfigScope, name: str = "default") -> bool:
        """检查并热加载配置"""
        if not self._persistence.watch_changes(scope, name):
            return False

        file_path = self._persistence._get_config_file_path(scope, name)
        if not file_path.exists():
            return False

        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        key = f"{scope.name}:{name}"

        if key in self._last_modified and mtime <= self._last_modified[key]:
            return False

        self._last_modified[key] = mtime
        self._persistence.load(scope, name)

        for callback in self._callbacks.get(key, []):
            try:
                callback()
            except Exception:
                pass

        return True

    def watch_all(self) -> List[str]:
        """监视所有已注册的配置"""
        reloaded = []
        for key in self._callbacks.keys():
            scope, name = self._persistence._parse_config_key(key)
            if self.check_and_reload(scope, name):
                reloaded.append(key)
        return reloaded


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, storage_path: Optional[Path] = None):
        self._persistence = ConfigPersistence(
            storage_path=storage_path,
            backend=StorageBackend.HYBRID
        )
        self._secret_manager = SecretManager(self._persistence)
        self._env_config = EnvironmentConfig(self._persistence)
        self._hot_reload = HotReloadConfig(self._persistence)
        self._validators: Dict[ConfigScope, ConfigValidator] = {}

    def get_persistence(self) -> ConfigPersistence:
        """获取持久化管理器"""
        return self._persistence

    def get_secret_manager(self) -> SecretManager:
        """获取敏感信息管理器"""
        return self._secret_manager

    def get_env_config(self) -> EnvironmentConfig:
        """获取环境配置"""
        return self._env_config

    def get_hot_reload(self) -> HotReloadConfig:
        """获取热加载配置"""
        return self._hot_reload

    def add_validator(self, scope: ConfigScope, validator: ConfigValidator):
        """添加作用域验证器"""
        self._validators[scope] = validator

    def validate_config(self, scope: ConfigScope, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        if scope in self._validators:
            return self._validators[scope].validate(config)
        return self._persistence._validator.validate(config)

    def reset(self, scope: Optional[ConfigScope] = None):
        """重置配置"""
        if scope:
            self._persistence._memory_cache = {
                k: v for k, v in self._persistence._memory_cache.items()
                if not k.startswith(scope.name)
            }
        else:
            self._persistence._memory_cache.clear()
            self._persistence._versions.clear()
            self._secret_manager._memory_secrets.clear()

    def backup(self, target_path: Optional[Path] = None) -> Path:
        """备份所有配置"""
        if target_path is None:
            target_path = Path(tempfile.mkdtemp()) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        target_path.mkdir(parents=True, exist_ok=True)

        if self._persistence._storage_path.exists():
            shutil.copytree(
                self._persistence._storage_path,
                target_path / "config",
                dirs_exist_ok=True
            )

        return target_path

    def restore(self, backup_path: Path) -> bool:
        """恢复配置"""
        try:
            config_backup = backup_path / "config"
            if not config_backup.exists():
                return False

            shutil.copytree(config_backup, self._persistence._storage_path, dirs_exist_ok=True)
            self._persistence._memory_cache.clear()
            return True
        except Exception:
            return False
