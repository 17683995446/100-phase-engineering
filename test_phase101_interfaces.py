"""
Phase 101 - 抽象接口层测试
验证所有管理器实现是否符合 Protocol 定义
"""
import unittest
from typing import Protocol
from src.interfaces.manager_protocols import (
    ICoverageAnalyzer,
    ICICDPipelineManager,
    IContainerOrchestrator,
    ISecretManager,
    IMonitoringAlertSystem,
    IConfigCenter,
    IDataGovernancePlatform,
)
from src.utils.coverage_analyzer import CoverageAnalyzer
from src.utils.cicd_pipeline import CICDPipelineManager
from src.utils.container_orchestrator import ContainerOrchestrator
from src.utils.secret_manager import SecretManager
from src.utils.monitoring_alert import MonitoringAlertSystem
from src.utils.config_center import ConfigCenter
from src.utils.data_governance import DataGovernancePlatform


class TestInterfaceCompliance(unittest.TestCase):
    """接口合规性测试"""

    def test_coverage_analyzer_implements_protocol(self):
        """测试 CoverageAnalyzer 实现 ICoverageAnalyzer"""
        instance = CoverageAnalyzer()
        self.assertIsInstance(instance, ICoverageAnalyzer)

    def test_cicd_pipeline_implements_protocol(self):
        """测试 CICDPipelineManager 实现 ICICDPipelineManager"""
        instance = CICDPipelineManager()
        self.assertIsInstance(instance, ICICDPipelineManager)

    def test_container_orchestrator_implements_protocol(self):
        """测试 ContainerOrchestrator 实现 IContainerOrchestrator"""
        instance = ContainerOrchestrator()
        self.assertIsInstance(instance, IContainerOrchestrator)

    def test_secret_manager_implements_protocol(self):
        """测试 SecretManager 实现 ISecretManager"""
        instance = SecretManager()
        self.assertIsInstance(instance, ISecretManager)

    def test_monitoring_alert_implements_protocol(self):
        """测试 MonitoringAlertSystem 实现 IMonitoringAlertSystem"""
        instance = MonitoringAlertSystem()
        self.assertIsInstance(instance, IMonitoringAlertSystem)

    def test_config_center_implements_protocol(self):
        """测试 ConfigCenter 实现 IConfigCenter"""
        instance = ConfigCenter()
        self.assertIsInstance(instance, IConfigCenter)

    def test_data_governance_implements_protocol(self):
        """测试 DataGovernancePlatform 实现 IDataGovernancePlatform"""
        instance = DataGovernancePlatform()
        self.assertIsInstance(instance, IDataGovernancePlatform)


class TestProtocolRuntimeCheck(unittest.TestCase):
    """Protocol 运行时检查测试"""

    def test_protocol_is_runtime_checkable(self):
        """测试 Protocol 可运行时检查"""
        from typing import runtime_checkable
        self.assertTrue(hasattr(ICoverageAnalyzer, "_is_protocol"))

    def test_non_compliant_object_fails(self):
        """测试不符合协议的对象检查失败"""
        class FakeManager:
            pass

        fake = FakeManager()
        self.assertNotIsInstance(fake, ICoverageAnalyzer)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 101 - 抽象接口层测试")
    print("=" * 60)
    unittest.main(verbosity=2)
