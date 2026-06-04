"""
机器学习模型管理
提供模型注册、版本控制、加载和预测功能
"""
import os
import json
import time
import pickle
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class ModelStatus(Enum):
    """模型状态"""
    REGISTERED = auto()
    TRAINING = auto()
    READY = auto()
    DEPRECATED = auto()
    FAILED = auto()


@dataclass
class ModelVersion:
    """模型版本"""
    version: str
    model_path: str
    created_at: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, float] = field(default_factory=dict)
    status: ModelStatus = ModelStatus.REGISTERED
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "model_path": self.model_path,
            "created_at": self.created_at.isoformat(),
            "metrics": self.metrics,
            "status": self.status.name,
            "description": self.description
        }


@dataclass
class ModelMetadata:
    """模型元数据"""
    model_name: str
    model_type: str
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    current_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "current_version": self.current_version
        }


class MLModelManager:
    """机器学习模型管理器"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self._models: Dict[str, ModelMetadata] = {}
        self._loaded_models: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("ml.model.manager")
        
        os.makedirs(models_dir, exist_ok=True)
        self._load_registry()
    
    def _get_registry_path(self) -> str:
        """获取注册表路径"""
        return os.path.join(self.models_dir, "registry.json")
    
    def _load_registry(self) -> None:
        """加载注册表"""
        registry_path = self._get_registry_path()
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    data = json.load(f)
                
                for name, meta in data.items():
                    metadata = ModelMetadata(
                        model_name=meta["model_name"],
                        model_type=meta["model_type"],
                        current_version=meta.get("current_version")
                    )
                    
                    for version_str, ver_data in meta.get("versions", {}).items():
                        version = ModelVersion(
                            version=version_str,
                            model_path=ver_data["model_path"],
                            metrics=ver_data.get("metrics", {}),
                            status=ModelStatus[ver_data.get("status", "REGISTERED")],
                            description=ver_data.get("description", "")
                        )
                        metadata.versions[version_str] = version
                    
                    self._models[name] = metadata
                
                self._logger.info(f"Loaded {len(self._models)} models from registry")
            except Exception as e:
                self._logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self) -> None:
        """保存注册表"""
        with self._lock:
            data = {name: meta.to_dict() for name, meta in self._models.items()}
        
        try:
            with open(self._get_registry_path(), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self._logger.error(f"Failed to save registry: {e}")
    
    def register_model(self, model_name: str, model_type: str,
                       version: str, model_path: str,
                       metrics: Optional[Dict[str, float]] = None,
                       description: str = "") -> bool:
        """注册模型"""
        with self._lock:
            if model_name not in self._models:
                self._models[model_name] = ModelMetadata(
                    model_name=model_name,
                    model_type=model_type
                )
            
            model_version = ModelVersion(
                version=version,
                model_path=model_path,
                metrics=metrics or {},
                status=ModelStatus.READY,
                description=description
            )
            
            self._models[model_name].versions[version] = model_version
            
            # 如果是第一个版本，设为当前版本
            if not self._models[model_name].current_version:
                self._models[model_name].current_version = version
        
        self._save_registry()
        self._logger.info(f"Registered model: {model_name} v{version}")
        return True
    
    def load_model(self, model_name: str, 
                   version: Optional[str] = None) -> Optional[Any]:
        """加载模型"""
        with self._lock:
            metadata = self._models.get(model_name)
            if not metadata:
                return None
            
            target_version = version or metadata.current_version
            if not target_version:
                return None
            
            version_info = metadata.versions.get(target_version)
            if not version_info:
                return None
            
            cache_key = f"{model_name}:{target_version}"
            if cache_key in self._loaded_models:
                return self._loaded_models[cache_key]
            
            try:
                if os.path.exists(version_info.model_path):
                    with open(version_info.model_path, 'rb') as f:
                        model = pickle.load(f)
                    self._loaded_models[cache_key] = model
                    self._logger.info(f"Loaded model: {model_name} v{target_version}")
                    return model
                else:
                    self._logger.warning(f"Model file not found: {version_info.model_path}")
                    return None
            except Exception as e:
                self._logger.error(f"Failed to load model: {e}")
                return None
    
    def unload_model(self, model_name: str, version: Optional[str] = None) -> bool:
        """卸载模型"""
        with self._lock:
            metadata = self._models.get(model_name)
            if not metadata:
                return False
            
            target_version = version or metadata.current_version
            cache_key = f"{model_name}:{target_version}"
            
            if cache_key in self._loaded_models:
                del self._loaded_models[cache_key]
                self._logger.info(f"Unloaded model: {cache_key}")
                return True
            return False
    
    def set_current_version(self, model_name: str, version: str) -> bool:
        """设置当前版本"""
        with self._lock:
            metadata = self._models.get(model_name)
            if not metadata or version not in metadata.versions:
                return False
            
            metadata.current_version = version
        
        self._save_registry()
        self._logger.info(f"Set current version: {model_name} -> {version}")
        return True
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        with self._lock:
            metadata = self._models.get(model_name)
            return metadata.to_dict() if metadata else None
    
    def get_all_models(self) -> List[str]:
        """获取所有模型名称"""
        with self._lock:
            return list(self._models.keys())
    
    def get_model_versions(self, model_name: str) -> List[str]:
        """获取模型所有版本"""
        with self._lock:
            metadata = self._models.get(model_name)
            return list(metadata.versions.keys()) if metadata else []
    
    def update_metrics(self, model_name: str, version: str,
                       metrics: Dict[str, float]) -> bool:
        """更新模型指标"""
        with self._lock:
            metadata = self._models.get(model_name)
            if not metadata or version not in metadata.versions:
                return False
            
            metadata.versions[version].metrics.update(metrics)
        
        self._save_registry()
        return True
    
    def deprecate_version(self, model_name: str, version: str) -> bool:
        """弃用版本"""
        with self._lock:
            metadata = self._models.get(model_name)
            if not metadata or version not in metadata.versions:
                return False
            
            metadata.versions[version].status = ModelStatus.DEPRECATED
        
        self._save_registry()
        self._logger.info(f"Deprecated model: {model_name} v{version}")
        return True
    
    def delete_model(self, model_name: str) -> bool:
        """删除模型"""
        with self._lock:
            if model_name not in self._models:
                return False
            
            # 卸载所有版本
            for version in self._models[model_name].versions:
                cache_key = f"{model_name}:{version}"
                self._loaded_models.pop(cache_key, None)
            
            del self._models[model_name]
        
        self._save_registry()
        self._logger.info(f"Deleted model: {model_name}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_models = len(self._models)
            total_versions = sum(len(m.versions) for m in self._models.values())
            loaded_models = len(self._loaded_models)
            
            return {
                "total_models": total_models,
                "total_versions": total_versions,
                "loaded_models": loaded_models,
                "models": {
                    name: {
                        "type": meta.model_type,
                        "versions": len(meta.versions),
                        "current": meta.current_version
                    }
                    for name, meta in self._models.items()
                }
            }


class SimplePredictor:
    """简单预测器"""
    
    def __init__(self, model_manager: MLModelManager):
        self._manager = model_manager
        self._logger = get_logger("simple.predictor")
    
    def predict(self, model_name: str, input_data: Any,
                version: Optional[str] = None) -> Optional[Any]:
        """预测"""
        model = self._manager.load_model(model_name, version)
        if model is None:
            self._logger.error(f"Model not found: {model_name}")
            return None
        
        try:
            if hasattr(model, 'predict'):
                return model.predict(input_data)
            elif callable(model):
                return model(input_data)
            else:
                self._logger.error(f"Model has no predict method: {model_name}")
                return None
        except Exception as e:
            self._logger.error(f"Prediction failed: {e}")
            return None


# 全局实例
_model_manager: Optional[MLModelManager] = None


def get_model_manager(models_dir: str = "models") -> MLModelManager:
    """获取模型管理器"""
    global _model_manager
    if _model_manager is None:
        _model_manager = MLModelManager(models_dir)
    return _model_manager
