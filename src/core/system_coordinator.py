"""
系统集成协调器
Phase 20 里程碑: 整合所有组件，提供完整的系统协调与验证功能
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum, auto
from datetime import datetime
import uuid
import threading

from src.scheduling_layer.state import StateManager
from src.scheduling_layer.event_tracker import EventTracker, get_event_tracker
from src.scheduling_layer.chain_id import ChainTracker, get_chain_tracker
from src.scheduling_layer.task_dispatcher import TaskDispatcher, get_task_dispatcher
from src.scheduling_layer.state_sync import StateSynchronizer, get_state_synchronizer
from src.scheduling_layer.monitoring import MonitoringSystem, get_monitoring_system
from src.agent_layer.agent_roles import AgentFactory, AgentRegistry
from src.agent_layer.workflow import AgentWorkflowEngine
from src.agent_layer.protocol import AgentCollaborationProtocol, get_collaboration_protocol
from src.utils.logger import logger


class SystemComponent(Enum):
    """系统组件枚举"""
    STATE_MANAGER = auto()
    EVENT_TRACKER = auto()
    CHAIN_TRACKER = auto()
    TASK_DISPATCHER = auto()
    STATE_SYNCHRONIZER = auto()
    MONITORING_SYSTEM = auto()
    AGENT_FACTORY = auto()
    AGENT_REGISTRY = auto()
    WORKFLOW_ENGINE = auto()
    COLLABORATION_PROTOCOL = auto()


class SystemStatus(Enum):
    """系统状态"""
    INITIALIZED = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class ComponentHealth:
    """组件健康状态"""
    component: SystemComponent
    healthy: bool = True
    last_check: Optional[datetime] = None
    status_message: str = "OK"
    errors: List[str] = field(default_factory=list)


@dataclass
class SystemVerificationResult:
    """系统验证结果"""
    verification_id: str
    timestamp: datetime
    all_healthy: bool = True
    component_health: Dict[SystemComponent, ComponentHealth] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class SystemCoordinator:
    """系统协调器 - 整合所有组件"""
    
    def __init__(self):
        self.coordinator_id: str = f"coordinator-{uuid.uuid4().hex[:8]}"
        self.status: SystemStatus = SystemStatus.INITIALIZED
        self.started_at: Optional[datetime] = None
        self._lock = threading.RLock()
        
        # 组件存储
        self._components: Dict[SystemComponent, Any] = {}
        
        # 初始化默认组件
        self._initialize_default_components()
        
        logger.info(f"系统协调器初始化完成: {self.coordinator_id}")
    
    def _initialize_default_components(self):
        """初始化默认组件"""
        self.register_component(SystemComponent.STATE_MANAGER, StateManager())
        self.register_component(SystemComponent.EVENT_TRACKER, get_event_tracker())
        self.register_component(SystemComponent.CHAIN_TRACKER, get_chain_tracker())
        self.register_component(SystemComponent.TASK_DISPATCHER, get_task_dispatcher())
        self.register_component(SystemComponent.STATE_SYNCHRONIZER, get_state_synchronizer())
        self.register_component(SystemComponent.MONITORING_SYSTEM, get_monitoring_system())
        self.register_component(SystemComponent.AGENT_FACTORY, AgentFactory())
        self.register_component(SystemComponent.AGENT_REGISTRY, AgentRegistry())
        self.register_component(SystemComponent.WORKFLOW_ENGINE, AgentWorkflowEngine())
        self.register_component(SystemComponent.COLLABORATION_PROTOCOL, get_collaboration_protocol())
    
    def register_component(self, component: SystemComponent, instance: Any):
        """注册组件"""
        with self._lock:
            self._components[component] = instance
            logger.debug(f"组件注册成功: {component.name}")
    
    def get_component(self, component: SystemComponent) -> Optional[Any]:
        """获取组件"""
        return self._components.get(component)
    
    def list_components(self) -> List[SystemComponent]:
        """列出所有注册的组件"""
        return list(self._components.keys())
    
    def start_system(self):
        """启动系统"""
        if self.status != SystemStatus.INITIALIZED and self.status != SystemStatus.STOPPED:
            logger.warning(f"系统不能从当前状态启动: {self.status.name}")
            return
        
        self.status = SystemStatus.STARTING
        self.started_at = datetime.now()
        
        logger.info("正在启动系统...")
        
        # 启动监控系统
        monitoring = self.get_component(SystemComponent.MONITORING_SYSTEM)
        if monitoring:
            monitoring.start()
        
        self.status = SystemStatus.RUNNING
        logger.info("系统已启动并运行")
    
    def pause_system(self):
        """暂停系统"""
        if self.status != SystemStatus.RUNNING:
            logger.warning(f"系统不能从当前状态暂停: {self.status.name}")
            return
        
        self.status = SystemStatus.PAUSING
        
        logger.info("正在暂停系统...")
        
        self.status = SystemStatus.PAUSED
        logger.info("系统已暂停")
    
    def resume_system(self):
        """恢复系统"""
        if self.status != SystemStatus.PAUSED:
            logger.warning(f"系统不能从当前状态恢复: {self.status.name}")
            return
        
        self.status = SystemStatus.RUNNING
        logger.info("系统已恢复运行")
    
    def stop_system(self):
        """停止系统"""
        if self.status in [SystemStatus.STOPPING, SystemStatus.STOPPED]:
            logger.warning(f"系统不能从当前状态停止: {self.status.name}")
            return
        
        self.status = SystemStatus.STOPPING
        
        logger.info("正在停止系统...")
        
        # 停止监控系统
        monitoring = self.get_component(SystemComponent.MONITORING_SYSTEM)
        if monitoring:
            monitoring.stop()
        
        self.status = SystemStatus.STOPPED
        logger.info("系统已停止")
    
    def verify_system(self) -> SystemVerificationResult:
        """验证系统完整性"""
        logger.info("开始系统完整性验证...")
        
        result = SystemVerificationResult(
            verification_id=str(uuid.uuid4()),
            timestamp=datetime.now()
        )
        
        # 验证每个组件
        all_healthy = True
        
        for component in SystemComponent:
            health = self._verify_component(component)
            result.component_health[component] = health
            
            if not health.healthy:
                all_healthy = False
        
        result.all_healthy = all_healthy
        
        # 添加建议
        if not all_healthy:
            result.recommendations.append("检查不健康的组件并修复问题")
        
        logger.info(f"系统验证完成: {'成功' if all_healthy else '发现问题'}")
        return result
    
    def _verify_component(self, component: SystemComponent) -> ComponentHealth:
        """验证单个组件"""
        health = ComponentHealth(
            component=component,
            last_check=datetime.now()
        )
        
        instance = self.get_component(component)
        
        if instance is None:
            health.healthy = False
            health.status_message = "组件未注册"
            health.errors.append("组件未注册或初始化失败")
            return health
        
        # 基本检查
        try:
            if hasattr(instance, 'get_status'):
                status = instance.get_status()
                if isinstance(status, dict) and status.get('healthy', True) is False:
                    health.healthy = False
                    health.status_message = "组件报告不健康"
            
            # 针对特定组件的检查
            if component == SystemComponent.AGENT_REGISTRY:
                # 检查是否有注册的Agent或能力
                if hasattr(instance, 'agents') and len(instance.agents) == 0:
                    health.status_message = "无Agent注册（这是正常的初始状态）"
                if hasattr(instance, 'capabilities') and len(instance.capabilities) == 0:
                    health.status_message = "无Agent能力注册（这是正常的初始状态）"
            
        except Exception as e:
            health.healthy = False
            health.status_message = f"组件验证异常: {e}"
            health.errors.append(str(e))
        
        return health
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self._lock:
            status = {
                "coordinator_id": self.coordinator_id,
                "status": self.status.name,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "uptime_seconds": (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
                "components": {c.name: "registered" for c in self.list_components()},
                "monitoring": {}
            }
            
            # 获取监控系统状态
            monitoring = self.get_component(SystemComponent.MONITORING_SYSTEM)
            if monitoring:
                status["monitoring"] = monitoring.get_status()
            
            return status


# 全局系统协调器
_global_system_coordinator: Optional[SystemCoordinator] = None


def get_system_coordinator() -> SystemCoordinator:
    """获取全局系统协调器"""
    global _global_system_coordinator
    if _global_system_coordinator is None:
        _global_system_coordinator = SystemCoordinator()
    return _global_system_coordinator


def set_system_coordinator(coordinator: SystemCoordinator):
    """设置全局系统协调器"""
    global _global_system_coordinator
    _global_system_coordinator = coordinator
