"""
Phase 36 - 高级健康检查与系统状态监控测试
验证健康检查系统是否正常工作
"""
import time
import unittest
from src.api_layer.core import APIApp, HTTPMethod, APIRequest
from src.utils.health import (
    HealthMonitor,
    ComponentHealthCheck,
    ThresholdHealthCheck,
    HealthStatus,
    HealthCheckType,
    get_health_monitor,
    create_component_check,
)
from src.utils.system_health import (
    setup_system_health_checks,
    get_liveness_status,
    get_readiness_status,
)


class TestHealthChecks(unittest.TestCase):
    """健康检查测试"""

    def setUp(self):
        """测试前设置"""
        self.monitor = HealthMonitor()
    
    def test_component_health_check(self):
        """测试组件健康检查"""
        def check_service():
            return True
        
        check = ComponentHealthCheck(
            component_name="test.service",
            check_fn=check_service,
            check_type=HealthCheckType.LIVENESS,
            tags=["test"]
        )
        
        result = check.check()
        self.assertEqual(result.component, "test.service")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
    
    def test_component_health_check_failure(self):
        """测试组件健康检查失败"""
        def check_service():
            return False
        
        check = ComponentHealthCheck(
            component_name="test.service",
            check_fn=check_service,
            check_type=HealthCheckType.LIVENESS
        )
        
        result = check.check()
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
    
    def test_threshold_health_check(self):
        """测试阈值健康检查"""
        def get_metric():
            return 50.0
        
        check = ThresholdHealthCheck(
            name="test.metric",
            metric_fn=get_metric,
            healthy_threshold=60.0,
            degraded_threshold=40.0,
            higher_is_healthier=True
        )
        
        result = check.check()
        self.assertEqual(result.status, HealthStatus.DEGRADED)
    
    def test_health_monitor_register(self):
        """测试健康监控器注册"""
        def check_service():
            return True
        
        check = create_component_check(
            name="test.service",
            check_fn=check_service
        )
        
        self.monitor.register_check(check)
        self.assertIn("test.service", self.monitor.checks)
    
    def test_health_monitor_run_check(self):
        """测试健康监控器运行检查"""
        def check_service():
            return True
        
        check = create_component_check(
            name="test.service",
            check_fn=check_service
        )
        
        self.monitor.register_check(check)
        result = self.monitor.run_check("test.service")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.component, "test.service")
    
    def test_health_monitor_run_all(self):
        """测试健康监控器运行所有检查"""
        def check_service1():
            return True
        
        def check_service2():
            return False
        
        self.monitor.register_check(create_component_check(
            name="service1",
            check_fn=check_service1
        ))
        self.monitor.register_check(create_component_check(
            name="service2",
            check_fn=check_service2
        ))
        
        result = self.monitor.run_all_checks()
        
        self.assertEqual(result.total_components, 2)
        self.assertEqual(result.healthy_components, 1)
        self.assertEqual(result.unhealthy_components, 1)
    
    def test_aggregated_status(self):
        """测试聚合状态"""
        def check_all():
            return True
        
        self.monitor.register_check(create_component_check(
            name="service1",
            check_fn=check_all
        ))
        self.monitor.register_check(create_component_check(
            name="service2",
            check_fn=check_all
        ))
        
        result = self.monitor.run_all_checks()
        status_dict = result.to_dict()
        
        self.assertIn("status", status_dict)
        self.assertIn("summary", status_dict)
        self.assertIn("components", status_dict)


class TestSystemHealthChecks(unittest.TestCase):
    """系统健康检查测试"""

    def test_setup_system_health_checks(self):
        """测试设置系统健康检查"""
        monitor = setup_system_health_checks()
        self.assertIsNotNone(monitor)
        self.assertGreater(len(monitor.checks), 0)
    
    def test_liveness_status(self):
        """测试存活探针状态"""
        status = get_liveness_status()
        self.assertIn("status", status)
        self.assertIn("summary", status)
        self.assertIn("components", status)
    
    def test_readiness_status(self):
        """测试就绪探针状态"""
        status = get_readiness_status()
        self.assertIn("status", status)


class TestHealthEndpoints(unittest.TestCase):
    """健康检查端点测试"""

    def setUp(self):
        """测试前设置"""
        setup_system_health_checks()
        self.app = APIApp("test_health_api")
    
    def test_health_endpoint(self):
        """测试健康端点"""
        request = APIRequest(HTTPMethod.GET, "/health")
        response = self.app.handle_request(request)
        
        self.assertIn(response.status_code, [200, 503])
        self.assertIsNotNone(response.body)
    
    def test_liveness_endpoint(self):
        """测试存活端点"""
        request = APIRequest(HTTPMethod.GET, "/health/live")
        response = self.app.handle_request(request)
        
        self.assertIn(response.status_code, [200, 503])
        self.assertIn("status", response.body)
    
    def test_readiness_endpoint(self):
        """测试就绪端点"""
        request = APIRequest(HTTPMethod.GET, "/health/ready")
        response = self.app.handle_request(request)
        
        self.assertIn(response.status_code, [200, 503])
        self.assertIn("status", response.body)
    
    def test_startup_endpoint(self):
        """测试启动端点"""
        request = APIRequest(HTTPMethod.GET, "/health/startup")
        response = self.app.handle_request(request)
        
        self.assertIn(response.status_code, [200, 503])
        self.assertIn("status", response.body)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 36 - 高级健康检查与系统状态监控测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthChecks))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSystemHealthChecks))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthEndpoints))
    
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
