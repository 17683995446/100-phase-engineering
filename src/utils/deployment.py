"""
容器化与部署管理
提供部署配置、环境管理和发布策略功能
"""
import os
import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class DeploymentStrategy(Enum):
    """部署策略"""
    ROLLING = auto()      # 滚动部署
    BLUE_GREEN = auto()   # 蓝绿部署
    CANARY = auto()       # 金丝雀部署
    RECREATE = auto()     # 重建部署


class DeploymentStatus(Enum):
    """部署状态"""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    ROLLING_BACK = auto()
    ROLLED_BACK = auto()


class EnvironmentType(Enum):
    """环境类型"""
    DEVELOPMENT = auto()
    TESTING = auto()
    STAGING = auto()
    PRODUCTION = auto()


@dataclass
class ContainerConfig:
    """容器配置"""
    name: str
    image: str
    tag: str = "latest"
    ports: Dict[int, int] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    volumes: Dict[str, str] = field(default_factory=dict)
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    replicas: int = 1
    health_check_path: str = "/health"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "image": self.image,
            "tag": self.tag,
            "ports": self.ports,
            "env_vars": self.env_vars,
            "volumes": self.volumes,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "replicas": self.replicas,
            "health_check_path": self.health_check_path
        }


@dataclass
class DeploymentConfig:
    """部署配置"""
    name: str
    version: str
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    containers: List[ContainerConfig] = field(default_factory=list)
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    namespace: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "strategy": self.strategy.name,
            "containers": [c.to_dict() for c in self.containers],
            "environment": self.environment.name,
            "namespace": self.namespace
        }


@dataclass
class DeploymentRecord:
    """部署记录"""
    deployment_id: str
    config: DeploymentConfig
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    steps_completed: int = 0
    total_steps: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "deployment_id": self.deployment_id,
            "config": self.config.to_dict(),
            "status": self.status.name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps
        }


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self, deployments_dir: str = "deployments"):
        self.deployments_dir = deployments_dir
        self._deployments: Dict[str, DeploymentRecord] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("deployment.manager")
        self._running_deployments: Dict[str, threading.Thread] = {}
        
        os.makedirs(deployments_dir, exist_ok=True)
    
    def create_deployment(self, config: DeploymentConfig) -> str:
        """创建部署"""
        import uuid
        deployment_id = f"{config.name}-{config.version}-{uuid.uuid4().hex[:8]}"
        
        record = DeploymentRecord(
            deployment_id=deployment_id,
            config=config,
            status=DeploymentStatus.PENDING
        )
        
        with self._lock:
            self._deployments[deployment_id] = record
        
        self._logger.info(f"Deployment created: {deployment_id}")
        return deployment_id
    
    def start_deployment(self, deployment_id: str) -> bool:
        """开始部署"""
        record = self._deployments.get(deployment_id)
        if not record:
            return False
        
        record.status = DeploymentStatus.RUNNING
        record.started_at = datetime.now()
        record.total_steps = self._calculate_total_steps(record.config)
        
        # 启动部署线程
        thread = threading.Thread(
            target=self._execute_deployment,
            args=(deployment_id,),
            daemon=True
        )
        
        with self._lock:
            self._running_deployments[deployment_id] = thread
        
        thread.start()
        self._logger.info(f"Deployment started: {deployment_id}")
        return True
    
    def _calculate_total_steps(self, config: DeploymentConfig) -> int:
        """计算总步骤数"""
        base_steps = 3  # 准备、部署、验证
        container_steps = len(config.containers) * 2  # 每个容器：拉取、启动
        
        if config.strategy == DeploymentStrategy.BLUE_GREEN:
            return base_steps + container_steps + 2  # 切换、清理
        elif config.strategy == DeploymentStrategy.CANARY:
            return base_steps + container_steps + 3  # 金丝雀、验证、全量
        elif config.strategy == DeploymentStrategy.ROLLING:
            return base_steps + container_steps + 1  # 滚动更新
        else:
            return base_steps + container_steps
    
    def _execute_deployment(self, deployment_id: str) -> None:
        """执行部署"""
        record = self._deployments.get(deployment_id)
        if not record:
            return
        
        try:
            config = record.config
            
            # 模拟部署步骤
            self._update_step(record, "Preparing deployment")
            time.sleep(0.1)
            
            for container in config.containers:
                self._update_step(record, f"Pulling image {container.image}:{container.tag}")
                time.sleep(0.1)
                
                self._update_step(record, f"Starting container {container.name}")
                time.sleep(0.1)
            
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                self._update_step(record, "Switching traffic")
                time.sleep(0.1)
                self._update_step(record, "Cleaning up old version")
                time.sleep(0.1)
            elif config.strategy == DeploymentStrategy.CANARY:
                self._update_step(record, "Deploying canary")
                time.sleep(0.1)
                self._update_step(record, "Validating canary")
                time.sleep(0.1)
                self._update_step(record, "Promoting to full deployment")
                time.sleep(0.1)
            elif config.strategy == DeploymentStrategy.ROLLING:
                self._update_step(record, "Rolling update")
                time.sleep(0.1)
            
            self._update_step(record, "Verifying deployment")
            time.sleep(0.1)
            
            record.status = DeploymentStatus.SUCCESS
            record.completed_at = datetime.now()
            self._logger.info(f"Deployment completed: {deployment_id}")
            
        except Exception as e:
            record.status = DeploymentStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now()
            self._logger.error(f"Deployment failed: {deployment_id} - {e}")
        
        finally:
            with self._lock:
                self._running_deployments.pop(deployment_id, None)
    
    def _update_step(self, record: DeploymentRecord, step_name: str) -> None:
        """更新步骤"""
        record.steps_completed += 1
        self._logger.info(f"Deployment {record.deployment_id}: [{record.steps_completed}/{record.total_steps}] {step_name}")
    
    def rollback_deployment(self, deployment_id: str) -> bool:
        """回滚部署"""
        record = self._deployments.get(deployment_id)
        if not record:
            return False
        
        record.status = DeploymentStatus.ROLLING_BACK
        self._logger.info(f"Rolling back deployment: {deployment_id}")
        
        # 模拟回滚
        time.sleep(0.1)
        
        record.status = DeploymentStatus.ROLLED_BACK
        record.completed_at = datetime.now()
        self._logger.info(f"Deployment rolled back: {deployment_id}")
        return True
    
    def get_deployment(self, deployment_id: str) -> Optional[DeploymentRecord]:
        """获取部署记录"""
        return self._deployments.get(deployment_id)
    
    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentStatus]:
        """获取部署状态"""
        record = self._deployments.get(deployment_id)
        return record.status if record else None
    
    def get_all_deployments(self) -> List[Dict[str, Any]]:
        """获取所有部署"""
        with self._lock:
            return [
                record.to_dict()
                for record in sorted(
                    self._deployments.values(),
                    key=lambda r: r.started_at or datetime.min,
                    reverse=True
                )
            ]
    
    def get_deployments_by_status(self, status: DeploymentStatus) -> List[DeploymentRecord]:
        """按状态获取部署"""
        with self._lock:
            return [
                record for record in self._deployments.values()
                if record.status == status
            ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            total = len(self._deployments)
            success = sum(1 for d in self._deployments.values() if d.status == DeploymentStatus.SUCCESS)
            failed = sum(1 for d in self._deployments.values() if d.status == DeploymentStatus.FAILED)
            running = sum(1 for d in self._deployments.values() if d.status == DeploymentStatus.RUNNING)
            
            return {
                "total": total,
                "success": success,
                "failed": failed,
                "running": running,
                "success_rate": success / total if total > 0 else 0
            }
    
    def save_deployment_config(self, deployment_id: str, filepath: str) -> bool:
        """保存部署配置到文件"""
        record = self._deployments.get(deployment_id)
        if not record:
            return False
        
        try:
            with open(filepath, 'w') as f:
                json.dump(record.to_dict(), f, indent=2)
            return True
        except Exception as e:
            self._logger.error(f"Failed to save deployment config: {e}")
            return False


class EnvironmentManager:
    """环境管理器"""
    
    def __init__(self):
        self._environments: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("environment.manager")
    
    def create_environment(self, name: str, env_type: EnvironmentType, 
                          config: Dict[str, Any]) -> bool:
        """创建环境"""
        with self._lock:
            if name in self._environments:
                return False
            
            self._environments[name] = {
                "name": name,
                "type": env_type.name,
                "config": config,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
        
        self._logger.info(f"Environment created: {name} ({env_type.name})")
        return True
    
    def get_environment(self, name: str) -> Optional[Dict[str, Any]]:
        """获取环境"""
        with self._lock:
            return self._environments.get(name)
    
    def update_environment(self, name: str, config: Dict[str, Any]) -> bool:
        """更新环境配置"""
        with self._lock:
            if name not in self._environments:
                return False
            
            self._environments[name]["config"].update(config)
            self._environments[name]["updated_at"] = datetime.now().isoformat()
        
        self._logger.info(f"Environment updated: {name}")
        return True
    
    def delete_environment(self, name: str) -> bool:
        """删除环境"""
        with self._lock:
            if name not in self._environments:
                return False
            
            del self._environments[name]
        
        self._logger.info(f"Environment deleted: {name}")
        return True
    
    def get_all_environments(self) -> List[Dict[str, Any]]:
        """获取所有环境"""
        with self._lock:
            return list(self._environments.values())
    
    def get_environment_variables(self, name: str) -> Dict[str, str]:
        """获取环境变量"""
        env = self.get_environment(name)
        if env:
            return env.get("config", {}).get("env_vars", {})
        return {}


# 全局实例
_deployment_manager: Optional[DeploymentManager] = None
_environment_manager: Optional[EnvironmentManager] = None


def get_deployment_manager(deployments_dir: str = "deployments") -> DeploymentManager:
    """获取部署管理器"""
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = DeploymentManager(deployments_dir)
    return _deployment_manager


def get_environment_manager() -> EnvironmentManager:
    """获取环境管理器"""
    global _environment_manager
    if _environment_manager is None:
        _environment_manager = EnvironmentManager()
    return _environment_manager
