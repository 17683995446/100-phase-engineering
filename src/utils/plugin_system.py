"""
插件系统
提供插件加载、注册、管理和生命周期管理功能
"""
import os
import sys
import importlib
import importlib.util
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class PluginStatus(Enum):
    """插件状态"""
    REGISTERED = auto()
    LOADED = auto()
    ENABLED = auto()
    DISABLED = auto()
    ERROR = auto()


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point
        }


class Plugin:
    """插件基类"""
    
    def __init__(self, info: PluginInfo):
        self.info = info
        self.status = PluginStatus.REGISTERED
        self._logger = get_logger(f"plugin.{info.name}")
    
    def load(self) -> bool:
        """加载插件"""
        try:
            self.status = PluginStatus.LOADED
            self._logger.info(f"Plugin loaded: {self.info.name}")
            return True
        except Exception as e:
            self.status = PluginStatus.ERROR
            self._logger.error(f"Plugin load failed: {e}")
            return False
    
    def enable(self) -> bool:
        """启用插件"""
        if self.status != PluginStatus.LOADED:
            return False
        self.status = PluginStatus.ENABLED
        self._logger.info(f"Plugin enabled: {self.info.name}")
        return True
    
    def disable(self) -> bool:
        """禁用插件"""
        if self.status == PluginStatus.ENABLED:
            self.status = PluginStatus.DISABLED
            self._logger.info(f"Plugin disabled: {self.info.name}")
            return True
        return False
    
    def execute(self, *args, **kwargs) -> Any:
        """执行插件功能"""
        if self.status != PluginStatus.ENABLED:
            return None
        return self._execute(*args, **kwargs)
    
    def _execute(self, *args, **kwargs) -> Any:
        """子类实现"""
        raise NotImplementedError


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("plugin.manager")
        
        os.makedirs(plugin_dir, exist_ok=True)
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """注册插件"""
        with self._lock:
            if plugin.info.name in self._plugins:
                return False
            
            self._plugins[plugin.info.name] = plugin
        
        self._logger.info(f"Plugin registered: {plugin.info.name}")
        return True
    
    def load_plugin(self, name: str) -> bool:
        """加载插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            
            return plugin.load()
    
    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            
            if plugin.status == PluginStatus.REGISTERED:
                if not plugin.load():
                    return False
            
            return plugin.enable()
    
    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            
            return plugin.disable()
    
    def unregister_plugin(self, name: str) -> bool:
        """注销插件"""
        with self._lock:
            if name in self._plugins:
                del self._plugins[name]
                return True
            return False
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        with self._lock:
            return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        with self._lock:
            return [plugin.info for plugin in self._plugins.values()]
    
    def get_plugins_by_status(self, status: PluginStatus) -> List[Plugin]:
        """按状态获取插件"""
        with self._lock:
            return [
                plugin for plugin in self._plugins.values()
                if plugin.status == status
            ]
    
    def add_hook(self, event: str, callback: Callable) -> None:
        """添加钩子"""
        with self._lock:
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].append(callback)
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        
        with self._lock:
            callbacks = self._hooks.get(event, [])
        
        for callback in callbacks:
            try:
                result = callback(*args, **kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                self._logger.error(f"Hook error: {e}")
        
        return results
    
    def execute_plugin(self, name: str, *args, **kwargs) -> Any:
        """执行插件"""
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.execute(*args, **kwargs)
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._plugins)
            enabled = sum(1 for p in self._plugins.values() if p.status == PluginStatus.ENABLED)
            
            return {
                "total": total,
                "enabled": enabled,
                "hooks": len(self._hooks)
            }


# 全局实例
_manager: Optional[PluginManager] = None


def get_plugin_manager(plugin_dir: str = "plugins") -> PluginManager:
    """获取插件管理器"""
    global _manager
    if _manager is None:
        _manager = PluginManager(plugin_dir)
    return _manager
