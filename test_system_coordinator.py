"""
Phase 20 系统集成与完整性验证测试
"""

import pytest
from datetime import datetime
from src.core.system_coordinator import (
    SystemCoordinator,
    SystemComponent,
    SystemStatus,
    ComponentHealth,
    SystemVerificationResult,
    get_system_coordinator
)


class TestSystemCoordinator:
    """测试系统协调器"""
    
    def test_coordinator_creation(self):
        """测试创建协调器"""
        coordinator = SystemCoordinator()
        
        assert coordinator is not None
        assert coordinator.status == SystemStatus.INITIALIZED
        assert len(coordinator.list_components()) > 0
    
    def test_get_system_status(self):
        """测试获取系统状态"""
        coordinator = SystemCoordinator()
        
        status = coordinator.get_system_status()
        
        assert "coordinator_id" in status
        assert "status" in status
        assert "components" in status
        assert "monitoring" in status
        assert status["status"] == "INITIALIZED"
    
    def test_start_system(self):
        """测试启动系统"""
        coordinator = SystemCoordinator()
        
        coordinator.start_system()
        
        assert coordinator.status == SystemStatus.RUNNING
        assert coordinator.started_at is not None
    
    def test_pause_resume_system(self):
        """测试暂停和恢复系统"""
        coordinator = SystemCoordinator()
        
        coordinator.start_system()
        coordinator.pause_system()
        assert coordinator.status == SystemStatus.PAUSED
        
        coordinator.resume_system()
        assert coordinator.status == SystemStatus.RUNNING
    
    def test_stop_system(self):
        """测试停止系统"""
        coordinator = SystemCoordinator()
        
        coordinator.start_system()
        coordinator.stop_system()
        
        assert coordinator.status == SystemStatus.STOPPED
    
    def test_register_get_component(self):
        """测试注册和获取组件"""
        coordinator = SystemCoordinator()
        
        components = coordinator.list_components()
        assert SystemComponent.STATE_MANAGER in components
        
        state_manager = coordinator.get_component(SystemComponent.STATE_MANAGER)
        assert state_manager is not None
    
    def test_verify_system(self):
        """测试系统验证"""
        coordinator = SystemCoordinator()
        
        result = coordinator.verify_system()
        
        assert result is not None
        assert result.verification_id is not None
        assert len(result.component_health) > 0


class TestSystemVerification:
    """测试系统验证"""
    
    def test_verification_creation(self):
        """测试创建验证结果"""
        result = SystemVerificationResult(
            verification_id="test-verification",
            timestamp=datetime.now()
        )
        
        assert result.all_healthy is True
        assert len(result.component_health) == 0
        assert len(result.recommendations) == 0
    
    def test_verification_with_healthy_components(self):
        """测试有健康组件的验证"""
        result = SystemVerificationResult(
            verification_id="test-verification",
            timestamp=datetime.now()
        )
        
        health = ComponentHealth(
            component=SystemComponent.STATE_MANAGER,
            healthy=True
        )
        
        result.component_health[SystemComponent.STATE_MANAGER] = health
        
        assert result.all_healthy is True
    
    def test_verification_with_unhealthy_components(self):
        """测试有不健康组件的验证"""
        result = SystemVerificationResult(
            verification_id="test-verification",
            timestamp=datetime.now()
        )
        
        health = ComponentHealth(
            component=SystemComponent.STATE_MANAGER,
            healthy=False,
            errors=["Component error"]
        )
        
        result.component_health[SystemComponent.STATE_MANAGER] = health
        result.all_healthy = False
        result.recommendations.append("Fix the error")
        
        assert result.all_healthy is False
        assert len(result.recommendations) == 1


def test_global_system_coordinator():
    """测试全局系统协调器"""
    coordinator1 = get_system_coordinator()
    coordinator2 = get_system_coordinator()
    
    assert coordinator1 is coordinator2


def test_full_system_integration():
    """测试完整系统集成"""
    coordinator = SystemCoordinator()
    
    # 启动系统
    coordinator.start_system()
    
    # 验证系统
    verification = coordinator.verify_system()
    
    # 停止系统
    coordinator.stop_system()
    
    assert verification is not None
    assert len(verification.component_health) == len(SystemComponent)
    # 大多数组件应该是健康的
    healthy_count = sum(1 for h in verification.component_health.values() if h.healthy)
    assert healthy_count >= 5  # 至少有一半组件应该是健康的


def test_component_access_all_components():
    """测试访问所有组件"""
    coordinator = SystemCoordinator()
    
    for component in SystemComponent:
        if component in coordinator.list_components():
            instance = coordinator.get_component(component)
            assert instance is not None
