"""
核心协调模块
四层架构整合和工作流驱动
"""

from .orchestrator import FourLayerOrchestrator
from .atomic_entities import (
    AtomicEntityRegistry,
    EntityDefinition,
    EntityCategory,
    TaskAtomicEntity,
    CodeAtomicEntity,
    MessageAtomicEntity,
    StateAtomicEntity,
    AgentAtomicEntity,
    EventAtomicEntity
)
from .system_coordinator import (
    SystemCoordinator,
    SystemComponent,
    SystemStatus,
    ComponentHealth,
    SystemVerificationResult,
    get_system_coordinator,
    set_system_coordinator
)

__all__ = [
    "FourLayerOrchestrator",
    "AtomicEntityRegistry",
    "EntityDefinition",
    "EntityCategory",
    "TaskAtomicEntity",
    "CodeAtomicEntity",
    "MessageAtomicEntity",
    "StateAtomicEntity",
    "AgentAtomicEntity",
    "EventAtomicEntity",
    "SystemCoordinator",
    "SystemComponent",
    "SystemStatus",
    "ComponentHealth",
    "SystemVerificationResult",
    "get_system_coordinator",
    "set_system_coordinator"
]
