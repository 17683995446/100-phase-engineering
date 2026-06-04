"""
Phase 97 - 监控告警系统测试
"""
import unittest
from src.utils.monitoring_alert import (
    MonitoringAlertSystem, AlertSeverity, AlertStatus,
    ComparisonOperator, get_monitoring_alert_system
)


class TestMonitoringAlertSystem(unittest.TestCase):
    """监控告警系统测试"""

    def setUp(self):
        self.system = MonitoringAlertSystem()

    def test_create_rule(self):
        """测试创建告警规则"""
        rule = self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0,
            severity=AlertSeverity.HIGH
        )
        self.assertEqual(rule.rule_id, "cpu_high")
        self.assertEqual(rule.threshold, 80.0)
        self.assertEqual(rule.severity, AlertSeverity.HIGH)

    def test_create_duplicate_rule(self):
        """测试创建重复规则"""
        self.system.create_rule("cpu_high", "CPU High", "cpu", ComparisonOperator.GREATER_THAN, 80)
        with self.assertRaises(ValueError):
            self.system.create_rule("cpu_high", "CPU", "cpu", ComparisonOperator.LESS_THAN, 20)

    def test_enable_disable_rule(self):
        """测试启用禁用规则"""
        self.system.create_rule("cpu_high", "CPU High", "cpu", ComparisonOperator.GREATER_THAN, 80)
        self.assertTrue(self.system.disable_rule("cpu_high"))
        self.assertFalse(self.system.get_rule("cpu_high").enabled)
        self.assertTrue(self.system.enable_rule("cpu_high"))
        self.assertTrue(self.system.get_rule("cpu_high").enabled)

    def test_record_metric_trigger_alert(self):
        """测试记录指标触发告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        alerts = self.system.list_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["status"], "firing")

    def test_record_metric_resolve_alert(self):
        """测试记录指标解决告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        self.system.record_metric("cpu_usage", 50.0)
        alerts = self.system.list_alerts(status="resolved")
        self.assertEqual(len(alerts), 1)

    def test_alert_not_retriggered(self):
        """测试告警不重复触发"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        self.system.record_metric("cpu_usage", 95.0)
        alerts = self.system.list_alerts()
        self.assertEqual(len(alerts), 1)

    def test_alert_with_labels(self):
        """测试带标签的告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0,
            labels={"host": "server1"}
        )
        self.system.record_metric("cpu_usage", 90.0, labels={"host": "server1"})
        self.system.record_metric("cpu_usage", 90.0, labels={"host": "server2"})
        alerts = self.system.list_alerts()
        self.assertEqual(len(alerts), 1)

    def test_acknowledge_alert(self):
        """测试确认告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        alert = self.system.list_alerts()[0]
        self.assertTrue(self.system.acknowledge_alert(alert["alert_id"], "admin"))
        updated = self.system.get_alert(alert["alert_id"])
        self.assertEqual(updated.status, AlertStatus.ACKNOWLEDGED)
        self.assertEqual(updated.acknowledged_by, "admin")

    def test_suppress_alert(self):
        """测试抑制告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        alert = self.system.list_alerts()[0]
        self.assertTrue(self.system.suppress_alert(alert["alert_id"]))
        updated = self.system.get_alert(alert["alert_id"])
        self.assertEqual(updated.status, AlertStatus.SUPPRESSED)

    def test_list_alerts_by_status(self):
        """测试按状态列出告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        self.system.record_metric("cpu_usage", 50.0)
        firing = self.system.list_alerts(status="firing")
        resolved = self.system.list_alerts(status="resolved")
        self.assertEqual(len(firing), 0)
        self.assertEqual(len(resolved), 1)

    def test_list_alerts_by_severity(self):
        """测试按级别列出告警"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0,
            severity=AlertSeverity.CRITICAL
        )
        self.system.record_metric("cpu_usage", 90.0)
        critical = self.system.list_alerts(severity="critical")
        self.assertEqual(len(critical), 1)

    def test_get_metrics(self):
        """测试获取指标"""
        self.system.record_metric("cpu_usage", 50.0)
        self.system.record_metric("cpu_usage", 60.0)
        metrics = self.system.get_metrics("cpu_usage")
        self.assertEqual(len(metrics), 2)

    def test_get_metrics_with_labels(self):
        """测试获取带标签的指标"""
        self.system.record_metric("cpu_usage", 50.0, labels={"host": "a"})
        self.system.record_metric("cpu_usage", 60.0, labels={"host": "b"})
        metrics_a = self.system.get_metrics("cpu_usage", labels={"host": "a"})
        self.assertEqual(len(metrics_a), 1)
        self.assertEqual(metrics_a[0]["value"], 50.0)

    def test_delete_rule(self):
        """测试删除规则"""
        self.system.create_rule("cpu_high", "CPU High", "cpu", ComparisonOperator.GREATER_THAN, 80)
        self.assertTrue(self.system.delete_rule("cpu_high"))
        self.assertIsNone(self.system.get_rule("cpu_high"))

    def test_comparison_operators(self):
        """测试比较操作符"""
        self.system.create_rule(
            "cpu_low", "CPU Low",
            "cpu_usage", ComparisonOperator.LESS_THAN, 20.0
        )
        self.system.record_metric("cpu_usage", 10.0)
        self.assertEqual(len(self.system.list_alerts()), 1)

        self.system.create_rule(
            "cpu_equal", "CPU Equal",
            "cpu_usage", ComparisonOperator.EQUAL, 50.0
        )
        self.system.record_metric("cpu_usage", 50.0)
        self.assertEqual(len(self.system.list_alerts()), 2)

    def test_history(self):
        """测试告警历史"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        self.system.record_metric("cpu_usage", 50.0)
        history = self.system.get_history()
        self.assertEqual(len(history), 2)

    def test_stats(self):
        """测试统计信息"""
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        stats = self.system.get_stats()
        self.assertEqual(stats["total_rules"], 1)
        self.assertEqual(stats["firing"], 1)

    def test_notifier(self):
        """测试通知器"""
        notified = []
        def handler(alert):
            notified.append(alert.alert_id)

        self.system.register_notifier("test", handler)
        self.system.create_rule(
            "cpu_high", "CPU High",
            "cpu_usage", ComparisonOperator.GREATER_THAN, 80.0
        )
        self.system.record_metric("cpu_usage", 90.0)
        self.assertEqual(len(notified), 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_monitoring_alert_system(self):
        """测试获取全局监控告警系统"""
        s1 = get_monitoring_alert_system()
        s2 = get_monitoring_alert_system()
        self.assertIs(s1, s2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 97 - 监控告警系统测试")
    print("=" * 60)
    unittest.main(verbosity=2)
