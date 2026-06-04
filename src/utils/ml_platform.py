"""
机器学习平台
提供模型训练、评估、部署和实验管理功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class ExperimentStatus(Enum):
    """实验状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelStatus(Enum):
    """模型状态"""
    TRAINING = "training"
    TRAINED = "trained"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


@dataclass
class Experiment:
    """实验"""
    experiment_id: str
    name: str
    status: ExperimentStatus
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.value,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }


@dataclass
class MLModel:
    """ML模型"""
    model_id: str
    name: str
    version: str
    status: ModelStatus
    experiment_id: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "experiment_id": self.experiment_id,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


class ExperimentTracker:
    """实验追踪器"""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("ml.experiment")

    def create_experiment(self, experiment_id: str, name: str,
                          parameters: Optional[Dict[str, Any]] = None) -> Experiment:
        """创建实验"""
        with self._lock:
            if experiment_id in self._experiments:
                raise ValueError(f"Experiment {experiment_id} already exists")

            experiment = Experiment(
                experiment_id=experiment_id,
                name=name,
                status=ExperimentStatus.PENDING,
                parameters=parameters or {}
            )
            self._experiments[experiment_id] = experiment
            self._logger.info(f"Experiment created: {experiment_id}")
            return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """开始实验"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment or experiment.status != ExperimentStatus.PENDING:
                return False

            experiment.status = ExperimentStatus.RUNNING
            self._logger.info(f"Experiment started: {experiment_id}")
            return True

    def log_metric(self, experiment_id: str, metric_name: str,
                   value: float) -> bool:
        """记录指标"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False

            experiment.metrics[metric_name] = value
            return True

    def log_parameters(self, experiment_id: str,
                       parameters: Dict[str, Any]) -> bool:
        """记录参数"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                return False

            experiment.parameters.update(parameters)
            return True

    def complete_experiment(self, experiment_id: str,
                            status: ExperimentStatus = ExperimentStatus.COMPLETED) -> bool:
        """完成实验"""
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment or experiment.status != ExperimentStatus.RUNNING:
                return False

            experiment.status = status
            experiment.completed_at = time.time()
            self._logger.info(f"Experiment completed: {experiment_id}")
            return True

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """获取实验"""
        with self._lock:
            return self._experiments.get(experiment_id)

    def list_experiments(self, status: Optional[ExperimentStatus] = None) -> List[Experiment]:
        """列出实验"""
        with self._lock:
            experiments = list(self._experiments.values())
            if status:
                experiments = [e for e in experiments if e.status == status]
            return experiments

    def get_best_experiment(self, metric: str,
                            maximize: bool = True) -> Optional[Experiment]:
        """获取最佳实验"""
        with self._lock:
            completed = [
                e for e in self._experiments.values()
                if e.status == ExperimentStatus.COMPLETED and metric in e.metrics
            ]
            if not completed:
                return None

            if maximize:
                return max(completed, key=lambda e: e.metrics[metric])
            else:
                return min(completed, key=lambda e: e.metrics[metric])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._experiments)
            by_status = {}
            for exp in self._experiments.values():
                s = exp.status.value
                by_status[s] = by_status.get(s, 0) + 1
            return {
                "total_experiments": total,
                "by_status": by_status
            }


class ModelRegistry:
    """模型注册表"""

    def __init__(self):
        self._models: Dict[str, MLModel] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("ml.registry")

    def register_model(self, model_id: str, name: str, version: str,
                       experiment_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> MLModel:
        """注册模型"""
        with self._lock:
            if model_id in self._models:
                raise ValueError(f"Model {model_id} already exists")

            model = MLModel(
                model_id=model_id,
                name=name,
                version=version,
                status=ModelStatus.TRAINED,
                experiment_id=experiment_id,
                metadata=metadata or {}
            )
            self._models[model_id] = model
            self._logger.info(f"Model registered: {model_id}")
            return model

    def get_model(self, model_id: str) -> Optional[MLModel]:
        """获取模型"""
        with self._lock:
            return self._models.get(model_id)

    def update_model_status(self, model_id: str,
                            status: ModelStatus) -> bool:
        """更新模型状态"""
        with self._lock:
            model = self._models.get(model_id)
            if not model:
                return False

            model.status = status
            return True

    def update_model_metrics(self, model_id: str,
                             metrics: Dict[str, float]) -> bool:
        """更新模型指标"""
        with self._lock:
            model = self._models.get(model_id)
            if not model:
                return False

            model.metrics.update(metrics)
            return True

    def list_models(self, status: Optional[ModelStatus] = None) -> List[MLModel]:
        """列出模型"""
        with self._lock:
            models = list(self._models.values())
            if status:
                models = [m for m in models if m.status == status]
            return models

    def get_model_versions(self, name: str) -> List[MLModel]:
        """获取模型的所有版本"""
        with self._lock:
            return [
                m for m in self._models.values()
                if m.name == name
            ]

    def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        with self._lock:
            if model_id in self._models:
                del self._models[model_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._models)
            by_status = {}
            for model in self._models.values():
                s = model.status.value
                by_status[s] = by_status.get(s, 0) + 1
            return {
                "total_models": total,
                "by_status": by_status
            }


class MLPlatform:
    """机器学习平台"""

    def __init__(self):
        self._experiment_tracker = ExperimentTracker()
        self._model_registry = ModelRegistry()
        self._logger = get_logger("ml.platform")

    def create_experiment(self, experiment_id: str, name: str,
                          parameters: Optional[Dict[str, Any]] = None) -> Experiment:
        """创建实验"""
        return self._experiment_tracker.create_experiment(experiment_id, name, parameters)

    def register_model(self, model_id: str, name: str, version: str,
                       experiment_id: Optional[str] = None) -> MLModel:
        """注册模型"""
        return self._model_registry.register_model(model_id, name, version, experiment_id)

    def get_experiment_tracker(self) -> ExperimentTracker:
        """获取实验追踪器"""
        return self._experiment_tracker

    def get_model_registry(self) -> ModelRegistry:
        """获取模型注册表"""
        return self._model_registry

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "experiments": self._experiment_tracker.get_stats(),
            "models": self._model_registry.get_stats()
        }


# 全局实例
_platform: Optional[MLPlatform] = None


def get_ml_platform() -> MLPlatform:
    """获取全局机器学习平台"""
    global _platform
    if _platform is None:
        _platform = MLPlatform()
    return _platform
