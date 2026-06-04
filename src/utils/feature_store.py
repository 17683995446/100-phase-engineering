"""
特征存储与管理
提供特征定义、存储、检索和版本控制功能
"""
import os
import json
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class FeatureType(Enum):
    """特征类型"""
    NUMERIC = auto()
    CATEGORICAL = auto()
    TEXT = auto()
    BOOLEAN = auto()
    TIMESTAMP = auto()
    EMBEDDING = auto()


@dataclass
class FeatureDefinition:
    """特征定义"""
    name: str
    feature_type: FeatureType
    description: str = ""
    default_value: Any = None
    nullable: bool = True
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "feature_type": self.feature_type.name,
            "description": self.description,
            "default_value": self.default_value,
            "nullable": self.nullable,
            "tags": self.tags
        }


@dataclass
class FeatureVector:
    """特征向量"""
    entity_id: str
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    def get(self, name: str, default: Any = None) -> Any:
        """获取特征值"""
        return self.features.get(name, default)
    
    def set(self, name: str, value: Any) -> None:
        """设置特征值"""
        self.features[name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_id": self.entity_id,
            "features": self.features,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }


class FeatureStore:
    """特征存储"""
    
    def __init__(self, store_dir: str = "feature_store"):
        self.store_dir = store_dir
        self._definitions: Dict[str, FeatureDefinition] = {}
        self._online_store: Dict[str, Dict[str, FeatureVector]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("feature.store")
        
        os.makedirs(store_dir, exist_ok=True)
        self._load_definitions()
    
    def _get_defs_path(self) -> str:
        """获取定义文件路径"""
        return os.path.join(self.store_dir, "definitions.json")
    
    def _load_definitions(self) -> None:
        """加载特征定义"""
        defs_path = self._get_defs_path()
        if os.path.exists(defs_path):
            try:
                with open(defs_path, 'r') as f:
                    data = json.load(f)
                
                for name, def_data in data.items():
                    self._definitions[name] = FeatureDefinition(
                        name=def_data["name"],
                        feature_type=FeatureType[def_data["feature_type"]],
                        description=def_data.get("description", ""),
                        default_value=def_data.get("default_value"),
                        nullable=def_data.get("nullable", True),
                        tags=def_data.get("tags", [])
                    )
                
                self._logger.info(f"Loaded {len(self._definitions)} feature definitions")
            except Exception as e:
                self._logger.error(f"Failed to load definitions: {e}")
    
    def _save_definitions(self) -> None:
        """保存特征定义"""
        with self._lock:
            data = {name: def_.to_dict() for name, def_ in self._definitions.items()}
        
        try:
            with open(self._get_defs_path(), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self._logger.error(f"Failed to save definitions: {e}")
    
    def register_feature(self, definition: FeatureDefinition) -> bool:
        """注册特征"""
        with self._lock:
            self._definitions[definition.name] = definition
        
        self._save_definitions()
        self._logger.info(f"Registered feature: {definition.name}")
        return True
    
    def get_feature_definition(self, name: str) -> Optional[FeatureDefinition]:
        """获取特征定义"""
        with self._lock:
            return self._definitions.get(name)
    
    def get_all_definitions(self) -> List[FeatureDefinition]:
        """获取所有特征定义"""
        with self._lock:
            return list(self._definitions.values())
    
    def get_features_by_tag(self, tag: str) -> List[FeatureDefinition]:
        """按标签获取特征"""
        with self._lock:
            return [
                def_ for def_ in self._definitions.values()
                if tag in def_.tags
            ]
    
    def store_features(self, entity_type: str, vector: FeatureVector) -> bool:
        """存储特征向量"""
        with self._lock:
            if entity_type not in self._online_store:
                self._online_store[entity_type] = {}
            
            self._online_store[entity_type][vector.entity_id] = vector
        
        self._logger.info(f"Stored features for {entity_type}:{vector.entity_id}")
        return True
    
    def get_features(self, entity_type: str, 
                     entity_id: str) -> Optional[FeatureVector]:
        """获取特征向量"""
        with self._lock:
            entity_store = self._online_store.get(entity_type)
            if entity_store:
                return entity_store.get(entity_id)
            return None
    
    def get_feature_value(self, entity_type: str, entity_id: str,
                          feature_name: str) -> Optional[Any]:
        """获取单个特征值"""
        vector = self.get_features(entity_type, entity_id)
        if vector:
            return vector.get(feature_name)
        return None
    
    def get_entity_ids(self, entity_type: str) -> List[str]:
        """获取所有实体ID"""
        with self._lock:
            entity_store = self._online_store.get(entity_type)
            return list(entity_store.keys()) if entity_store else []
    
    def delete_features(self, entity_type: str, entity_id: str) -> bool:
        """删除特征"""
        with self._lock:
            entity_store = self._online_store.get(entity_type)
            if entity_store and entity_id in entity_store:
                del entity_store[entity_id]
                return True
            return False
    
    def get_feature_vector(self, entity_type: str, entity_id: str,
                           feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取特征向量（指定特征）"""
        vector = self.get_features(entity_type, entity_id)
        if not vector:
            return {}
        
        if feature_names:
            return {
                name: vector.get(name)
                for name in feature_names
                if name in vector.features
            }
        
        return dict(vector.features)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_entities = sum(
                len(store) for store in self._online_store.values()
            )
            
            return {
                "feature_definitions": len(self._definitions),
                "entity_types": len(self._online_store),
                "total_entities": total_entities,
                "features": list(self._definitions.keys())
            }
    
    def validate_features(self, entity_type: str, 
                          entity_id: str) -> List[str]:
        """验证特征完整性"""
        vector = self.get_features(entity_type, entity_id)
        if not vector:
            return ["Entity not found"]
        
        errors = []
        for name, def_ in self._definitions.items():
            if name not in vector.features:
                if not def_.nullable and def_.default_value is None:
                    errors.append(f"Missing required feature: {name}")
            elif vector.features[name] is None and not def_.nullable:
                errors.append(f"Null value for non-nullable feature: {name}")
        
        return errors


class FeatureGroup:
    """特征组"""
    
    def __init__(self, name: str, feature_store: FeatureStore):
        self.name = name
        self._store = feature_store
        self._feature_names: Set[str] = set()
        self._lock = threading.Lock()
    
    def add_features(self, feature_names: List[str]) -> None:
        """添加特征到组"""
        with self._lock:
            self._feature_names.update(feature_names)
    
    def get_feature_vector(self, entity_type: str, 
                           entity_id: str) -> Dict[str, Any]:
        """获取特征组向量"""
        with self._lock:
            names = list(self._feature_names)
        
        return self._store.get_feature_vector(entity_type, entity_id, names)
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        with self._lock:
            return list(self._feature_names)


# 全局实例
_feature_store: Optional[FeatureStore] = None


def get_feature_store(store_dir: str = "feature_store") -> FeatureStore:
    """获取特征存储"""
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStore(store_dir)
    return _feature_store
