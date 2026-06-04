"""
Phase 37 - 系统告警与通知机制测试
验证告警系统是否正常工作
"""

import time
import unittest
import uuid

from src.utils.alerts import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus,
    ThresholdCondition,
    StatusCondition,
    LogNotificationChannel,
    MemoryNotificationChannel
)
from src.utils.alert_integration import (
    HealthAlertIntegrator,
    HealthAlertConfig,
    get_health_alert_integrator,
    initialize_health_alerts
)
from src.utils.health import (
    HealthMonitor,
    create_component_check,
    HealthStatus,
    HealthCheckType,
    get_health_monitor
)


class TestAlertCore(unittest.TestCase):
    """告警核心功能测试"""
    
    def setUp(self):
        """测试前设置"""
        self.alert_manager = AlertManager()
        self.memory_channel = MemoryNotificationChannel()
        self.alert_manager.add_channel(self.memory_channel)
    
    def tearDown(self):
        """测试后清理"""
        self.memory_channel.clear()
    
    def test_threshold_condition(self):
        """测试阈值条件"""
        condition = ThresholdCondition(
            metric_name="test_metric",
            threshold=50.0,
            operator="gt"
        )
        
        # 应该触发
        result = condition.evaluate({"test_metric": 60.0})
        self.assertTrue(result)
        
        # 不应该触发
        result = condition.evaluate({"test_metric": 40.0})
        self.assertFalse(result)
    
    def test_status_condition(self):
        """测试状态条件"""
        condition = StatusCondition(
            source="database",
            expected_status="HEALTHY"
        )
        
        # 应该触发（状态不匹配）
        result = condition.evaluate({"database_status": "UNHEALTHY"})
        self.assertTrue(result)
        
        # 不应该触发（状态匹配）
        result = condition.evaluate({"database_status": "HEALTHY"})
        self.assertFalse(result)
    
    def test_alert_rule(self):
        """测试告警规则"""
        condition = ThresholdCondition(
            metric_name="cpu_usage",
            threshold=80.0,
            operator="gt"
        )
        
        rule = AlertRule(
            rule_id="test_cpu_rule",
            name="High CPU Usage",
            condition=condition,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=60
        )
        
        # 测试条件评估
        self.assertTrue(rule.should_trigger({"cpu_usage": 90.0}))
        self.assertFalse(rule.should_trigger({"cpu_usage": 70.0}))
        
        # 测试触发告警
        alert = rule.trigger({"cpu_usage": 90.0})
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
    
    def test_alert_manager_basic(self):
        """测试告警管理器基础功能"""
        # 添加规则
        condition = ThresholdCondition(
            metric_name="error_rate",
            threshold=5.0,
            operator="gt"
        )
        rule = AlertRule(
            rule_id="test_error_rule",
            name="High Error Rate",
            condition=condition,
            severity=AlertSeverity.ERROR
        )
        self.alert_manager.add_rule(rule)
        
        # 评估规则
        alerts = self.alert_manager.evaluate_rules({"error_rate": 10.0})
        
        # 检查是否有告警
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].name, "High Error Rate")
        
        # 检查通知是否发送
        notifications = self.memory_channel.get_notifications()
        self.assertEqual(len(notifications), 1)
    
    def test_alert_lifecycle(self):
        """测试告警生命周期"""
        # 创建并触发告警
        condition = ThresholdCondition(
            metric_name="test_metric",
            threshold=10.0,
            operator="gt"
        )
        rule = AlertRule(
            rule_id="test_lifecycle_rule",
            name="Test Rule",
            condition=condition,
            severity=AlertSeverity.WARNING
        )
        self.alert_manager.add_rule(rule)
        
        alerts = self.alert_manager.evaluate_rules({"test_metric": 20.0})
        self.assertEqual(len(alerts), 1)
        alert_id = alerts[0].alert_id
        
        # 确认告警
        acknowledged = self.alert_manager.acknowledge_alert(alert_id, "admin")
        self.assertTrue(acknowledged)
        
        alert = self.alert_manager.get_alert(alert_id)
        self.assertEqual(alert.status, AlertStatus.ACKNOWLEDGED)
        
        # 解决告警
        resolved = self.alert_manager.resolve_alert(alert_id, "admin", "Fixed issue")
        self.assertTrue(resolved)
        
        alert = self.alert_manager.get_alert(alert_id)
        self.assertEqual(alert.status, AlertStatus.RESOLVED)
        
        # 关闭告警
        closed = self.alert_manager.close_alert(alert_id)
        self.assertTrue(closed)
        
        alert = self.alert_manager.get_alert(alert_id)
        self.assertEqual(alert.status, AlertStatus.CLOSED)
    
    def test_alert_summary(self):
        """测试告警摘要"""
        # 添加多个规则和触发多个告警
        for i in range(3):
            condition = ThresholdCondition(
                metric_name=f"metric_{i}",
                threshold=5.0,
                operator="gt"
            )
            rule = AlertRule(
                rule_id=f"test_rule_{i}",
                name=f"Test Rule {i}",
                condition=condition,
                severity=AlertSeverity.ERROR
            )
            self.alert_manager.add_rule(rule)
        
        # 触发告警
        self.alert_manager.evaluate_rules({
            "metric_0": 10.0,
            "metric_1": 10.0,
            "metric_2": 10.0
        })
        
        # 获取摘要
        summary = self.alert_manager.get_alert_summary()
        self.assertEqual(summary["total_alerts"], 3)
        self.assertEqual(summary["active"], 3)
        self.assertEqual(summary["rules_count"], 3)
    
    def test_cooldown_period(self):
        """测试冷却期"""
        condition = ThresholdCondition(
            metric_name="test_metric",
            threshold=5.0,
            operator="gt"
        )
        rule = AlertRule(
            rule_id="test_cooldown_rule",
            name="Test Rule",
            condition=condition,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=2
        )
        self.alert_manager.add_rule(rule)
        
        # 第一次触发
        alerts1 = self.alert_manager.evaluate_rules({"test_metric": 10.0})
        self.assertEqual(len(alerts1), 1)
        
        # 冷却期内，不应该触发
        alerts2 = self.alert_manager.evaluate_rules({"test_metric": 10.0})
        self.assertEqual(len(alerts2), 0)


class TestHealthAlertIntegration(unittest.TestCase):
    """健康告警集成测试"""
    
    def setUp(self):
        """测试前设置"""
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.memory_channel = MemoryNotificationChannel()
        self.alert_manager.add_channel(self.memory_channel)
        
        self.config = HealthAlertConfig(
            check_interval_seconds=1,
            alert_cooldown_seconds=1
        )
        self.integrator = HealthAlertIntegrator(
            self.health_monitor,
            self.alert_manager,
            self.config
        )
    
    def tearDown(self):
        """测试后清理"""
        self.memory_channel.clear()
        self.integrator.stop()
    
    def test_setup_default_rules(self):
        """测试设置默认规则"""
        self.integrator.setup_default_rules()
        self.assertGreater(len(self.alert_manager.rules), 0)
    
    def test_metric_collection(self):
        """测试指标收集"""
        metrics = self.integrator._collect_metrics()
        self.assertIn("overall_status", metrics)
    
    def test_alert_triggering_via_integration(self):
        """测试通过集成触发告警"""
        # 添加一个简单的组件检查
        check = create_component_check(
            name="test_component",
            check_fn=lambda: False,
            check_type=HealthCheckType.LIVENESS
        )
        self.health_monitor.register_check(check)
        
        # 设置告警规则
        condition = StatusCondition(
            source="component",
            expected_status="HEALTHY"
        )
        rule = AlertRule(
            rule_id="test_component_rule",
            name="Component Issue",
            condition=condition,
            severity=AlertSeverity.ERROR,
            cooldown_seconds=1
        )
        self.alert_manager.add_rule(rule)
        
        # 触发检查
        alerts = self.alert_manager.evaluate_rules({"component_status": "UNHEALTHY"})
        
        self.assertGreater(len(alerts), 0)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 37 - 系统告警与通知机制测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAlertCore))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthAlertIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_tests()
