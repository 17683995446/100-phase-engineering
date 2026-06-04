"""
监控与告警系统验证测试
"""

import pytest
from datetime import datetime, timedelta
from src.scheduling_layer.monitoring import (
    MetricsRegistry,
    AlertManager,
    MonitoringSystem,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    MetricType,
    MetricsCollector,
    get_monitoring_system
)


class TestMetricsRegistry:
    """测试指标注册表"""
    
    def test_registry_creation(self):
        """测试创建指标注册表"""
        registry = MetricsRegistry()
        assert registry is not None
        assert len(registry.metrics) == 0
        assert len(registry.collectors) == 0
    
    def test_record_metric(self):
        """测试记录指标"""
        registry = MetricsRegistry()
        
        registry.record("test_metric", 10.0)
        
        assert "test_metric" in registry.metrics
        assert len(registry.metrics["test_metric"]) == 1
        assert registry.metrics["test_metric"][0].value == 10.0
    
    def test_increment_counter(self):
        """测试递增计数器"""
        registry = MetricsRegistry()
        
        registry.increment("counter_metric", by=1.0)
        assert registry.metrics["counter_metric"][0].value == 1.0
        
        registry.increment("counter_metric", by=2.0)
        assert registry.metrics["counter_metric"][1].value == 3.0
    
    def test_decrement_counter(self):
        """测试递减计数器"""
        registry = MetricsRegistry()
        
        registry.increment("counter_metric", by=5.0)
        registry.decrement("counter_metric", by=2.0)
        
        assert registry.metrics["counter_metric"][1].value == 3.0
    
    def test_gauge(self):
        """测试设置仪表盘值"""
        registry = MetricsRegistry()
        
        registry.gauge("gauge_metric", 10.0)
        assert registry.metrics["gauge_metric"][0].value == 10.0
        
        registry.gauge("gauge_metric", 20.0)
        assert registry.metrics["gauge_metric"][1].value == 20.0
    
    def test_get_latest(self):
        """测试获取最新值"""
        registry = MetricsRegistry()
        
        registry.record("test_metric", 10.0)
        registry.record("test_metric", 20.0)
        
        latest = registry.get_latest("test_metric")
        assert latest is not None
        assert latest.value == 20.0
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        registry = MetricsRegistry()
        
        registry.record("test_metric", 10.0)
        registry.record("test_metric", 20.0)
        registry.record("test_metric", 30.0)
        
        stats = registry.get_statistics("test_metric", window=3600)
        
        assert stats is not None
        assert stats["count"] == 3
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0
        assert stats["latest"] == 30.0
    
    def test_register_collector(self):
        """测试注册收集器"""
        registry = MetricsRegistry()
        
        def test_collector() -> float:
            return 42.0
        
        collector = MetricsCollector(
            name="test_collector",
            metric_type=MetricType.GAUGE,
            collect_function=test_collector
        )
        
        registry.register_collector(collector)
        assert "test_collector" in registry.collectors


class TestAlertManager:
    """测试告警管理器"""
    
    def test_manager_creation(self):
        """测试创建告警管理器"""
        manager = AlertManager()
        assert manager is not None
        assert len(manager.alerts) == 0
        assert len(manager.rules) == 0
    
    def test_create_alert(self):
        """测试创建告警"""
        manager = AlertManager()
        
        alert = manager.create_alert(
            rule_id="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert"
        )
        
        assert alert is not None
        assert alert.alert_id is not None
        assert alert.status == AlertStatus.ACTIVE
        assert len(manager.alerts) == 1
    
    def test_acknowledge_alert(self):
        """测试确认告警"""
        manager = AlertManager()
        
        alert = manager.create_alert(
            rule_id="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert"
        )
        
        manager.acknowledge_alert(alert.alert_id)
        
        updated_alert = manager.alerts[alert.alert_id]
        assert updated_alert.status == AlertStatus.ACKNOWLEDGED
        assert updated_alert.acknowledged_at is not None
    
    def test_resolve_alert(self):
        """测试解决告警"""
        manager = AlertManager()
        
        alert = manager.create_alert(
            rule_id="test_rule",
            severity=AlertSeverity.WARNING,
            message="Test alert"
        )
        
        manager.resolve_alert(alert.alert_id)
        
        updated_alert = manager.alerts[alert.alert_id]
        assert updated_alert.status == AlertStatus.RESOLVED
        assert updated_alert.resolved_at is not None
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        manager = AlertManager()
        
        # 创建活跃告警
        manager.create_alert(
            rule_id="rule1",
            severity=AlertSeverity.WARNING,
            message="Active alert"
        )
        
        # 创建已解决告警
        resolved = manager.create_alert(
            rule_id="rule2",
            severity=AlertSeverity.WARNING,
            message="Resolved alert"
        )
        manager.resolve_alert(resolved.alert_id)
        
        active = manager.get_active_alerts()
        assert len(active) == 1
    
    def test_register_rule(self):
        """测试注册规则"""
        manager = AlertManager()
        
        def test_condition(data: dict) -> bool:
            return False
        
        rule = AlertRule(
            rule_id="test_rule",
            name="Test rule",
            description="Test rule description",
            severity=AlertSeverity.WARNING,
            condition=test_condition
        )
        
        manager.register_rule(rule)
        assert "test_rule" in manager.rules


class TestMonitoringSystem:
    """测试监控系统"""
    
    def test_system_creation(self):
        """测试创建监控系统"""
        system = MonitoringSystem()
        assert system is not None
        assert system.metrics_registry is not None
        assert system.alert_manager is not None
    
    def test_get_status(self):
        """测试获取状态"""
        system = MonitoringSystem()
        
        status = system.get_status()
        
        assert "running" in status
        assert "metrics" in status
        assert "alerts" in status
    
    def test_start_stop(self):
        """测试启动与停止"""
        system = MonitoringSystem()
        
        system.start()
        assert system._running is True
        
        system.stop()
        assert system._running is False


def test_global_monitoring_system():
    """测试全局监控系统"""
    system1 = get_monitoring_system()
    system2 = get_monitoring_system()
    
    assert system1 is system2


def test_alert_rule_evaluation():
    """测试告警规则评估"""
    registry = MetricsRegistry()
    manager = AlertManager(registry)
    
    # 创建一个总是触发的规则
    def always_true_condition(data: dict) -> bool:
        return True
    
    rule = AlertRule(
        rule_id="always_true",
        name="Always true",
        description="Always triggers",
        severity=AlertSeverity.WARNING,
        condition=always_true_condition
    )
    
    manager.register_rule(rule)
    
    # 评估规则
    manager.evaluate_rules()
    
    # 应该创建一个告警
    assert len(manager.alerts) == 1


def test_alert_statistics():
    """测试告警统计"""
    manager = AlertManager()
    
    manager.create_alert(
        rule_id="rule1",
        severity=AlertSeverity.ERROR,
        message="Error alert"
    )
    
    manager.create_alert(
        rule_id="rule2",
        severity=AlertSeverity.WARNING,
        message="Warning alert"
    )
    
    stats = manager.get_statistics()
    
    assert stats["total_alerts"] == 2
    assert stats["alerts_by_severity"]["ERROR"] == 1
    assert stats["alerts_by_severity"]["WARNING"] == 1
