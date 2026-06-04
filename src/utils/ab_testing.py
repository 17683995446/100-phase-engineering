"""
A/B测试框架
提供实验创建、分组、指标收集和结果分析功能
"""
import random
import hashlib
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class ExperimentStatus(Enum):
    """实验状态"""
    DRAFT = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()


@dataclass
class Variant:
    """实验变体"""
    variant_id: str
    name: str
    weight: float = 0.5
    config: Dict[str, Any] = field(default_factory=dict)
    participants: int = 0
    conversions: int = 0
    
    @property
    def conversion_rate(self) -> float:
        """转化率"""
        return self.conversions / self.participants if self.participants > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "weight": self.weight,
            "participants": self.participants,
            "conversions": self.conversions,
            "conversion_rate": self.conversion_rate
        }


@dataclass
class Experiment:
    """实验"""
    experiment_id: str
    name: str
    variants: Dict[str, Variant] = field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.name,
            "variants": {k: v.to_dict() for k, v in self.variants.items()},
            "created_at": self.created_at.isoformat()
        }


class ABTestingFramework:
    """A/B测试框架"""
    
    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._user_assignments: Dict[str, Dict[str, str]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("ab.testing")
    
    def create_experiment(self, experiment_id: str, name: str) -> Experiment:
        """创建实验"""
        experiment = Experiment(experiment_id=experiment_id, name=name)
        
        with self._lock:
            self._experiments[experiment_id] = experiment
        
        self._logger.info(f"Created experiment: {name}")
        return experiment
    
    def add_variant(self, experiment_id: str, variant_id: str,
                    name: str, weight: float = 0.5,
                    config: Optional[Dict[str, Any]] = None) -> bool:
        """添加变体"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False
            
            experiment.variants[variant_id] = Variant(
                variant_id=variant_id,
                name=name,
                weight=weight,
                config=config or {}
            )
        
        self._logger.info(f"Added variant {name} to experiment {experiment_id}")
        return True
    
    def start_experiment(self, experiment_id: str) -> bool:
        """启动实验"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False
            
            experiment.status = ExperimentStatus.RUNNING
        
        self._logger.info(f"Started experiment: {experiment_id}")
        return True
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """停止实验"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False
            
            experiment.status = ExperimentStatus.COMPLETED
        
        self._logger.info(f"Stopped experiment: {experiment_id}")
        return True
    
    def assign_variant(self, experiment_id: str, user_id: str) -> Optional[str]:
        """为用户分配变体"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment or experiment.status != ExperimentStatus.RUNNING:
                return None
            
            # 检查用户是否已有分配
            if user_id in self._user_assignments:
                if experiment_id in self._user_assignments[user_id]:
                    return self._user_assignments[user_id][experiment_id]
            
            # 基于哈希的一致性分配
            hash_input = f"{experiment_id}:{user_id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            
            total_weight = sum(v.weight for v in experiment.variants.values())
            if total_weight == 0:
                return None
            
            point = (hash_value % 10000) / 10000 * total_weight
            current = 0.0
            
            for variant_id, variant in experiment.variants.items():
                current += variant.weight
                if point <= current:
                    if user_id not in self._user_assignments:
                        self._user_assignments[user_id] = {}
                    self._user_assignments[user_id][experiment_id] = variant_id
                    variant.participants += 1
                    return variant_id
            
            # 默认返回最后一个
            last_variant = list(experiment.variants.keys())[-1]
            if user_id not in self._user_assignments:
                self._user_assignments[user_id] = {}
            self._user_assignments[user_id][experiment_id] = last_variant
            experiment.variants[last_variant].participants += 1
            return last_variant
    
    def track_conversion(self, experiment_id: str, user_id: str,
                         value: float = 1.0) -> bool:
        """跟踪转化"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False
            
            user_assignments = self._user_assignments.get(user_id, {})
            variant_id = user_assignments.get(experiment_id)
            
            if not variant_id or variant_id not in experiment.variants:
                return False
            
            experiment.variants[variant_id].conversions += 1
            
            if "conversion_value" not in experiment.metrics:
                experiment.metrics["conversion_value"] = []
            experiment.metrics["conversion_value"].append(value)
        
        return True
    
    def get_variant_config(self, experiment_id: str, 
                           user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户变体配置"""
        variant_id = self.assign_variant(experiment_id, user_id)
        if not variant_id:
            return None
        
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment and variant_id in experiment.variants:
                return experiment.variants[variant_id].config
        return None
    
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """获取实验结果"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return None
            
            results = {
                "experiment_id": experiment_id,
                "name": experiment.name,
                "status": experiment.status.name,
                "total_participants": sum(v.participants for v in experiment.variants.values()),
                "total_conversions": sum(v.conversions for v in experiment.variants.values()),
                "variants": {}
            }
            
            for variant_id, variant in experiment.variants.items():
                results["variants"][variant_id] = variant.to_dict()
            
            return results
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """获取实验"""
        with self._lock:
            return self._experiments.get(experiment_id)
    
    def get_all_experiments(self) -> List[Dict[str, Any]]:
        """获取所有实验"""
        with self._lock:
            return [exp.to_dict() for exp in self._experiments.values()]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total_experiments = len(self._experiments)
            running = sum(1 for e in self._experiments.values() 
                        if e.status == ExperimentStatus.RUNNING)
            
            return {
                "total_experiments": total_experiments,
                "running": running,
                "completed": sum(1 for e in self._experiments.values() 
                               if e.status == ExperimentStatus.COMPLETED)
            }


# 全局实例
_ab_framework: Optional[ABTestingFramework] = None


def get_ab_testing_framework() -> ABTestingFramework:
    """获取A/B测试框架"""
    global _ab_framework
    if _ab_framework is None:
        _ab_framework = ABTestingFramework()
    return _ab_framework
