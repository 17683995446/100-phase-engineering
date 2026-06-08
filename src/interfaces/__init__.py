"""
抽象接口层
定义所有管理器的 Protocol/ABC，实现模块间解耦
"""
from .manager_protocols import (
    ICoverageAnalyzer,
    ICICDPipelineManager,
    IContainerOrchestrator,
    ISecretManager,
    IMonitoringAlertSystem,
    IConfigCenter,
    IDataGovernancePlatform,
)

__all__ = [
    "ICoverageAnalyzer",
    "ICICDPipelineManager",
    "IContainerOrchestrator",
    "ISecretManager",
    "IMonitoringAlertSystem",
    "IConfigCenter",
    "IDataGovernancePlatform",
]
