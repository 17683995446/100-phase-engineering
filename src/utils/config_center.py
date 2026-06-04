"""
配置中心
提供配置项管理、多环境支持、版本控制、动态更新和配置推送功能
"""
import time
import threading
import copy
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class ConfigType(Enum):
    """配置类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    YAML = "yaml"
    LIST = "list"


class ConfigStatus(Enum):
    """配置状态"""
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    DELETED = "deleted"


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    config_type: ConfigType = ConfigType.STRING
    description: str = ""
    status: ConfigStatus = ConfigStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    env: str = "default"
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "config_type": self.config_type.value,
            "description": self.description,
            "status": self.status.value,
            "version": self.version,
            "env": self.env,
            "tags": list(self.tags),
            "updated_at": self.updated_at
        }


@dataclass
class ConfigVersion:
    """配置版本"""
    version_id: str
    key: str
    value: Any
    version: int
    updated_at: float
    updated_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "key": self.key,
            "value": self.value,
            "version": self.version,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by
        }


class ConfigCenter:
    """配置中心"""

    def __init__(self):
        self._configs: Dict[str, ConfigItem] = {}
        self._versions: Dict[str, List[ConfigVersion]] = {}
        self._listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("config.center")
        self._version_counter = 0

    def _generate_version_id(self) -> str:
        """生成版本ID"""
        self._version_counter += 1
        return f"v_{self._version_counter}_{int(time.time())}"

    def set_config(self, key: str, value: Any,
                   config_type: ConfigType = ConfigType.STRING,
                   description: str = "",
                   env: str = "default",
                   tags: Optional[List[str]] = None,
                   updated_by: Optional[str] = None) -> ConfigItem:
        """设置配置项"""
        with self._lock:
            old_value = None
            if key in self._configs:
                old_value = self._configs[key].value
                item = self._configs[key]
                item.value = value
                item.config_type = config_type
                item.description = description
                item.env = env
                item.updated_at = time.time()
                item.version += 1
                if tags:
                    item.tags = set(tags)
                item.status = ConfigStatus.ACTIVE
            else:
                item = ConfigItem(
                    key=key,
                    value=value,
                    config_type=config_type,
                    description=description,
                    env=env,
                    tags=set(tags or [])
                )
                self._configs[key] = item

            # 记录版本
            version = ConfigVersion(
                version_id=self._generate_version_id(),
                key=key,
                value=copy.deepcopy(value),
                version=item.version,
                updated_at=item.updated_at,
                updated_by=updated_by
            )
            if key not in self._versions:
                self._versions[key] = []
            self._versions[key].append(version)

            self._logger.info(f"Config set: {key} version={item.version}")

            # 通知监听器
            if old_value is not None and old_value != value:
                self._notify_listeners(key, old_value, value)

            return item

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self._lock:
            item = self._configs.get(key)
            if item and item.status == ConfigStatus.ACTIVE:
                return item.value
            return default

    def get_config_item(self, key: str) -> Optional[ConfigItem]:
        """获取配置项详情"""
        with self._lock:
            return self._configs.get(key)

    def delete_config(self, key: str) -> bool:
        """删除配置项"""
        with self._lock:
            if key in self._configs:
                item = self._configs[key]
                item.status = ConfigStatus.DELETED
                item.updated_at = time.time()
                self._logger.info(f"Config deleted: {key}")
                return True
            return False

    def list_configs(self, env: Optional[str] = None,
                     status: Optional[ConfigStatus] = None,
                     tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出配置项"""
        with self._lock:
            items = self._configs.values()
            if env:
                items = [i for i in items if i.env == env]
            if status:
                items = [i for i in items if i.status == status]
            if tag:
                items = [i for i in items if tag in i.tags]
            return [i.to_dict() for i in items]

    def get_versions(self, key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取配置历史版本"""
        with self._lock:
            versions = self._versions.get(key, [])
            return [v.to_dict() for v in versions[-limit:]]

    def rollback(self, key: str, version: int) -> Optional[ConfigItem]:
        """回滚到指定版本"""
        with self._lock:
            versions = self._versions.get(key, [])
            target = None
            for v in versions:
                if v.version == version:
                    target = v
                    break

            if not target:
                return None

            return self.set_config(
                key=key,
                value=copy.deepcopy(target.value),
                updated_by="rollback"
            )

    def subscribe(self, key: str,
                  callback: Callable[[str, Any, Any], None]) -> None:
        """订阅配置变更"""
        with self._lock:
            if key not in self._listeners:
                self._listeners[key] = []
            self._listeners[key].append(callback)

    def unsubscribe(self, key: str,
                    callback: Callable[[str, Any, Any], None]) -> bool:
        """取消订阅"""
        with self._lock:
            if key in self._listeners and callback in self._listeners[key]:
                self._listeners[key].remove(callback)
                return True
            return False

    def _notify_listeners(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知监听器"""
        listeners = self._listeners.get(key, [])
        for callback in listeners:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                self._logger.error(f"Listener error: {e}")

    def batch_set(self, configs: Dict[str, Any],
                  env: str = "default") -> List[ConfigItem]:
        """批量设置配置"""
        with self._lock:
            results = []
            for key, value in configs.items():
                item = self.set_config(key, value, env=env)
                results.append(item)
            return results

    def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取配置"""
        with self._lock:
            return {
                key: self.get_config(key)
                for key in keys
                if key in self._configs
            }

    def import_configs(self, configs: List[Dict[str, Any]],
                       env: str = "default") -> List[ConfigItem]:
        """导入配置"""
        with self._lock:
            results = []
            for config in configs:
                item = self.set_config(
                    key=config["key"],
                    value=config["value"],
                    config_type=ConfigType(config.get("type", "string")),
                    description=config.get("description", ""),
                    env=env,
                    tags=config.get("tags")
                )
                results.append(item)
            return results

    def export_configs(self, env: Optional[str] = None) -> List[Dict[str, Any]]:
        """导出配置"""
        with self._lock:
            items = self._configs.values()
            if env:
                items = [i for i in items if i.env == env]
            return [i.to_dict() for i in items]

    def clone_env(self, source_env: str, target_env: str) -> List[ConfigItem]:
        """克隆环境配置"""
        with self._lock:
            results = []
            for item in self._configs.values():
                if item.env == source_env and item.status == ConfigStatus.ACTIVE:
                    new_item = self.set_config(
                        key=item.key,
                        value=copy.deepcopy(item.value),
                        config_type=item.config_type,
                        description=item.description,
                        env=target_env,
                        tags=list(item.tags)
                    )
                    results.append(new_item)
            return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            active = sum(1 for c in self._configs.values()
                         if c.status == ConfigStatus.ACTIVE)
            deleted = sum(1 for c in self._configs.values()
                          if c.status == ConfigStatus.DELETED)
            envs = set(c.env for c in self._configs.values())
            return {
                "total_configs": len(self._configs),
                "active": active,
                "deleted": deleted,
                "environments": len(envs),
                "total_versions": sum(len(v) for v in self._versions.values()),
                "subscribers": sum(len(l) for l in self._listeners.values())
            }


# 全局实例
_center: Optional[ConfigCenter] = None


def get_config_center() -> ConfigCenter:
    """获取全局配置中心"""
    global _center
    if _center is None:
        _center = ConfigCenter()
    return _center
