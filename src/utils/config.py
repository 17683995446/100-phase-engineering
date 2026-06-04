"""
系统配置管理与热更新
提供配置管理、持久化和热更新功能
"""
import os
import json
import threading
import copy
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class ConfigChangeType(Enum):
    """配置变更类型"""
    ADD = auto()
    UPDATE = auto()
    DELETE = auto()


@dataclass
class ConfigChange:
    """配置变更事件"""
    key: str
    old_value: Any
    new_value: Any
    change_type: ConfigChangeType
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type.name,
            "timestamp": self.timestamp.isoformat()
        }


class ConfigScope(Enum):
    """配置作用域"""
    GLOBAL = auto()
    API = auto()
    SCHEDULING = auto()
    HEALTH = auto()
    ALERT = auto()
    CUSTOM = auto()


@dataclass
class ConfigValue:
    """配置值"""
    key: str
    value: Any
    scope: ConfigScope = ConfigScope.GLOBAL
    description: str = ""
    editable: bool = True
    default_value: Any = None
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.name,
            "description": self.description,
            "editable": self.editable,
            "default_value": self.default_value,
            "last_updated": self.last_updated.isoformat(),
            "version": self.version
        }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._config: Dict[str, ConfigValue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._all_subscribers: List[Callable] = []
        self._lock = threading.RLock()
        self._history: List[ConfigChange] = []
        self._max_history = 1000
        self._auto_save = False
        self._save_path: Optional[str] = None
        self.logger = get_logger(f"config.{name}")
    
    def set_config(self, key: str, value: Any, scope: ConfigScope = ConfigScope.GLOBAL,
                  description: str = "", editable: bool = True) -> Optional[ConfigChange]:
        """设置配置"""
        with self._lock:
            old_config = self._config.get(key)
            old_value = old_config.value if old_config else None
            
            if old_config is not None:
                old_config.value = value
                old_config.scope = scope
                old_config.description = description
                old_config.editable = editable
                old_config.last_updated = datetime.now()
                old_config.version += 1
                change_type = ConfigChangeType.UPDATE
            else:
                new_config = ConfigValue(
                    key=key,
                    value=value,
                    scope=scope,
                    description=description,
                    editable=editable,
                    default_value=value
                )
                self._config[key] = new_config
                change_type = ConfigChangeType.ADD
            
            change = ConfigChange(
                key=key,
                old_value=old_value,
                new_value=value,
                change_type=change_type
            )
            
            self._history.append(change)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            self.logger.info(f"Config {change_type.name}: {key} = {value}")
            
            # 自动保存
            if self._auto_save and self._save_path:
                self._save()
            
            # 通知订阅者
            self._notify_subscribers(change)
            
            return change
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        with self._lock:
            config_value = self._config.get(key)
            if config_value:
                return config_value.value
            return default
    
    def get_config_value(self, key: str) -> Optional[ConfigValue]:
        """获取完整的配置值对象"""
        with self._lock:
            return copy.deepcopy(self._config.get(key))
    
    def delete_config(self, key: str) -> Optional[ConfigChange]:
        """删除配置"""
        with self._lock:
            config = self._config.get(key)
            if config and config.editable:
                old_value = config.value
                del self._config[key]
                
                change = ConfigChange(
                    key=key,
                    old_value=old_value,
                    new_value=None,
                    change_type=ConfigChangeType.DELETE
                )
                
                self._history.append(change)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
                
                self.logger.info(f"Config DELETE: {key}")
                
                if self._auto_save and self._save_path:
                    self._save()
                
                self._notify_subscribers(change)
                
                return change
            
            return None
    
    def get_all_configs(self, scope: Optional[ConfigScope] = None) -> Dict[str, ConfigValue]:
        """获取所有配置"""
        with self._lock:
            if scope is None:
                return copy.deepcopy(self._config)
            else:
                return {
                    k: copy.deepcopy(v)
                    for k, v in self._config.items()
                    if v.scope == scope
                }
    
    def get_config_dict(self, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """获取所有配置的字典形式"""
        configs = self.get_all_configs(scope)
        return {k: v.value for k, v in configs.items()}
    
    def subscribe(self, key: str, callback: Callable[[ConfigChange], None]) -> None:
        """订阅配置变更"""
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)
            self.logger.debug(f"Subscribed to config: {key}")
    
    def subscribe_all(self, callback: Callable[[ConfigChange], None]) -> None:
        """订阅所有配置变更"""
        with self._lock:
            self._all_subscribers.append(callback)
            self.logger.debug("Subscribed to all config changes")
    
    def unsubscribe(self, key: str, callback: Callable[[ConfigChange], None]) -> bool:
        """取消订阅"""
        with self._lock:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)
                self.logger.debug(f"Unsubscribed from config: {key}")
                return True
            return False
    
    def unsubscribe_all(self, callback: Callable[[ConfigChange], None]) -> bool:
        """取消全局订阅"""
        with self._lock:
            if callback in self._all_subscribers:
                self._all_subscribers.remove(callback)
                self.logger.debug("Unsubscribed from all config changes")
                return True
            return False
    
    def _notify_subscribers(self, change: ConfigChange) -> None:
        """通知订阅者"""
        # 首先通知特定键的订阅者
        if change.key in self._subscribers:
            for callback in self._subscribers[change.key]:
                try:
                    callback(change)
                except Exception as e:
                    self.logger.error(f"Error in subscriber callback: {e}", exc_info=True)
        
        # 然后通知所有订阅者
        for callback in self._all_subscribers:
            try:
                callback(change)
            except Exception as e:
                self.logger.error(f"Error in global subscriber callback: {e}", exc_info=True)
    
    def enable_auto_save(self, path: str) -> None:
        """启用自动保存"""
        with self._lock:
            self._save_path = path
            self._auto_save = True
            self.logger.info(f"Auto-save enabled: {path}")
            self._save()
    
    def disable_auto_save(self) -> None:
        """禁用自动保存"""
        with self._lock:
            self._auto_save = False
            self.logger.info("Auto-save disabled")
    
    def save(self, path: str) -> bool:
        """保存配置到文件"""
        try:
            with self._lock:
                self._save_path = path
                self._save()
                return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}", exc_info=True)
            return False
    
    def _save(self) -> None:
        """实际保存（内部方法）"""
        if not self._save_path:
            return
        
        save_data = {
            "name": self.name,
            "configs": [v.to_dict() for v in self._config.values()]
        }
        
        dir_path = os.path.dirname(self._save_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        with open(self._save_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str) -> bool:
        """从文件加载配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self._lock:
                self._save_path = path
                self._config.clear()
                
                for config_dict in data.get("configs", []):
                    config_value = ConfigValue(
                        key=config_dict["key"],
                        value=config_dict["value"],
                        scope=ConfigScope[config_dict["scope"]],
                        description=config_dict.get("description", ""),
                        editable=config_dict.get("editable", True),
                        default_value=config_dict.get("default_value"),
                        version=config_dict.get("version", 1)
                    )
                    # 解析时间
                    if "last_updated" in config_dict:
                        config_value.last_updated = datetime.fromisoformat(
                            config_dict["last_updated"]
                        )
                    
                    self._config[config_dict["key"]] = config_value
            
            self.logger.info(f"Config loaded from: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}", exc_info=True)
            return False
    
    def get_history(self, key: Optional[str] = None, limit: int = 100) -> List[ConfigChange]:
        """获取配置变更历史"""
        with self._lock:
            history = self._history[-limit:]
            if key:
                history = [c for c in history if c.key == key]
            return copy.deepcopy(history)
    
    def reset_config(self, key: str) -> Optional[ConfigChange]:
        """重置配置到默认值"""
        with self._lock:
            config = self._config.get(key)
            if config and config.default_value is not None:
                old_value = config.value
                config.value = config.default_value
                config.last_updated = datetime.now()
                config.version += 1
                
                change = ConfigChange(
                    key=key,
                    old_value=old_value,
                    new_value=config.default_value,
                    change_type=ConfigChangeType.UPDATE
                )
                
                self._history.append(change)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
                
                if self._auto_save and self._save_path:
                    self._save()
                
                self._notify_subscribers(change)
                
                self.logger.info(f"Config RESET: {key}")
                
                return change
            
            return None
    
    def batch_update(self, updates: Dict[str, Any]) -> List[ConfigChange]:
        """批量更新配置"""
        changes: List[ConfigChange] = []
        with self._lock:
            for key, value in updates.items():
                change = self.set_config(key, value)
                if change:
                    changes.append(change)
        return changes


# 全局实例
_default_manager: Optional[ConfigManager] = None


def get_config_manager(name: str = "default") -> ConfigManager:
    """获取配置管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ConfigManager(name)
    return _default_manager


def set_config_manager(manager: ConfigManager) -> None:
    """设置配置管理器"""
    global _default_manager
    _default_manager = manager


# 便捷函数
def set_config(key: str, value: Any, **kwargs) -> Optional[ConfigChange]:
    """设置配置"""
    manager = get_config_manager()
    return manager.set_config(key, value, **kwargs)


def get_config(key: str, default: Any = None) -> Any:
    """获取配置"""
    manager = get_config_manager()
    return manager.get_config(key, default)
