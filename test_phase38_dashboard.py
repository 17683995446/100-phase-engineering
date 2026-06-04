"""
Phase 38 - 可观测性仪表板与可视化测试
验证仪表板功能是否正常工作
"""
import time
import unittest

from src.utils.observability_dashboard import (
    ObservabilityDashboard,
    get_observability_dashboard
)
from src.utils.health import (
    HealthMonitor,
    get_health_monitor
)

# 创建组件检查的辅助函数
def create_component_check(name, check_fn, check_type=None, **kwargs):
    """创建组件健康检查的辅助函数"""
    from src.utils.health import ComponentHealthCheck, HealthCheckType
    return ComponentHealthCheck(
        component_name=name,
        check_fn=check_fn,
        check_type=check_type or HealthCheckType.LIVENESS,
        **kwargs
    )
from src.utils.alerts import (
    AlertManager,
    AlertRule,
    ThresholdCondition,
    AlertSeverity,
    get_alert_manager
)
from src.api_layer.core import APIApp, HTTPMethod, APIRequest


class TestObservabilityDashboard(unittest.TestCase):
    """可观测性仪表板测试"""
    
    def setUp(self):
        """测试前设置"""
        # 创建独立实例用于测试
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.dashboard = ObservabilityDashboard()
        
        # 替换全局实例以进行隔离测试
        from src.utils.observability_dashboard import set_observability_dashboard
        from src.utils.health import set_health_monitor
        from src.utils.alerts import set_alert_manager
        
        set_health_monitor(self.health_monitor)
        set_alert_manager(self.alert_manager)
        set_observability_dashboard(self.dashboard)
    
    def test_dashboard_overview(self):
        """测试仪表板总览"""
        overview = self.dashboard.get_dashboard_overview()
        
        self.assertIn("overall_health", overview)
        self.assertIn("active_alerts_count", overview)
        self.assertIn("critical_alerts_count", overview)
        self.assertIn("uptime_seconds", overview)
        self.assertIn("last_updated", overview)
        self.assertIsInstance(overview["uptime_seconds"], float)
    
    def test_health_widgets(self):
        """测试健康状态组件"""
        # 添加测试健康检查
        test_check = create_component_check(
            name="test.component",
            check_fn=lambda: True
        )
        self.health_monitor.register_check(test_check)
        
        widgets = self.dashboard.get_health_widgets()
        
        self.assertIn("widgets", widgets)
        self.assertIn("summary", widgets)
        self.assertIn("last_updated", widgets)
        
        summary = widgets["summary"]
        self.assertIn("total", summary)
        self.assertIn("healthy", summary)
    
    def test_alert_widgets(self):
        """测试告警组件"""
        # 添加测试告警规则
        condition = ThresholdCondition(
            metric_name="test_metric",
            threshold=5.0,
            operator="gt"
        )
        rule = AlertRule(
            rule_id="test.rule",
            name="Test Rule",
            condition=condition,
            severity=AlertSeverity.WARNING
        )
        self.alert_manager.add_rule(rule)
        
        # 触发告警
        self.alert_manager.evaluate_rules({"test_metric": 10.0})
        
        widgets = self.dashboard.get_alert_widgets()
        
        self.assertIn("widgets", widgets)
        self.assertIn("summary", widgets)
        self.assertIn("last_updated", widgets)
    
    def test_trace_widgets(self):
        """测试追踪组件"""
        widgets = self.dashboard.get_trace_widgets()
        
        self.assertIn("widgets", widgets)
        self.assertIn("summary", widgets)
        self.assertIn("last_updated", widgets)
        
        summary = widgets["summary"]
        self.assertIn("total", summary)
        self.assertIn("error_count", summary)
        self.assertIn("avg_duration_ms", summary)
    
    def test_alert_operations(self):
        """测试告警操作"""
        # 创建并触发告警
        condition = ThresholdCondition(
            metric_name="test_metric",
            threshold=5.0,
            operator="gt"
        )
        rule = AlertRule(
            rule_id="test.op.rule",
            name="Test Operation Rule",
            condition=condition,
            severity=AlertSeverity.WARNING
        )
        self.alert_manager.add_rule(rule)
        
        alerts = self.alert_manager.evaluate_rules({"test_metric": 10.0})
        self.assertGreater(len(alerts), 0)
        
        alert_id = alerts[0]["alert_id"] if isinstance(alerts[0], dict) else alerts[0].alert_id
        
        # 测试确认告警
        acknowledged = self.dashboard.acknowledge_alert(alert_id, "test_user")
        self.assertTrue(acknowledged)
        
        # 测试解决告警
        resolved = self.dashboard.resolve_alert(alert_id, "test_user", "Fixed issue")
        self.assertTrue(resolved)
        
        # 测试关闭告警
        closed = self.dashboard.close_alert(alert_id)
        self.assertTrue(closed)
    
    def test_run_health_checks(self):
        """测试运行健康检查"""
        # 添加测试检查
        test_check = create_component_check(
            name="test.run.check",
            check_fn=lambda: True
        )
        self.health_monitor.register_check(test_check)
        
        result = self.dashboard.run_health_checks()
        
        self.assertIn("status", result)
        self.assertIn("components", result)
    
    def test_auto_update(self):
        """测试自动更新"""
        # 启动自动更新
        self.dashboard.start_auto_update(interval_seconds=1)
        
        # 等待一段时间
        time.sleep(2)
        
        # 停止自动更新
        self.dashboard.stop_auto_update()
        
        # 测试数据应该被更新
        overview = self.dashboard.get_dashboard_overview()
        self.assertIn("last_updated", overview)


class TestDashboardAPI(unittest.TestCase):
    """仪表板API测试"""
    
    def setUp(self):
        """测试前设置"""
        self.app = APIApp("test.dashboard.api")
        
        # 确保初始化健康检查系统
        pass
    
    def test_dashboard_overview_api(self):
        """测试仪表板总览API"""
        request = APIRequest(HTTPMethod.GET, "/observability/dashboard/overview")
        response = self.app.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.body)
        self.assertEqual(response.body["success"], True)
        self.assertIn("data", response.body)
    
    def test_health_widgets_api(self):
        """测试健康组件API"""
        request = APIRequest(HTTPMethod.GET, "/observability/dashboard/health")
        response = self.app.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.body)
        self.assertEqual(response.body["success"], True)
        self.assertIn("data", response.body)
    
    def test_alert_widgets_api(self):
        """测试告警组件API"""
        request = APIRequest(
            HTTPMethod.GET,
            "/observability/dashboard/alerts",
            params={"limit": "20"}
        )
        response = self.app.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.body)
        self.assertEqual(response.body["success"], True)
        self.assertIn("data", response.body)
    
    def test_trace_widgets_api(self):
        """测试追踪组件API"""
        request = APIRequest(
            HTTPMethod.GET,
            "/observability/dashboard/traces",
            params={"limit": "20"}
        )
        response = self.app.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.body)
        self.assertEqual(response.body["success"], True)
        self.assertIn("data", response.body)
    
    def test_run_health_checks_api(self):
        """测试运行健康检查API"""
        request = APIRequest(HTTPMethod.POST, "/observability/dashboard/health/run")
        response = self.app.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.body)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 38 - 可观测性仪表板与可视化测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestObservabilityDashboard))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDashboardAPI))
    
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
