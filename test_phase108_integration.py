"""
Phase 108 - 集成测试与端到端验证
验证多个模块协同工作的场景
"""
import unittest
import time
import sys
import importlib.util

# 直接加载模块避免循环导入
spec = importlib.util.spec_from_file_location("di_container", "/workspace/src/core/di_container.py")
di_mod = importlib.util.module_from_spec(spec)
sys.modules["di_container"] = di_mod
spec.loader.exec_module(di_mod)
DIContainer = di_mod.DIContainer
Lifecycle = di_mod.Lifecycle

spec2 = importlib.util.spec_from_file_location("degradation", "/workspace/src/core/degradation.py")
deg_mod = importlib.util.module_from_spec(spec2)
sys.modules["degradation"] = deg_mod
spec2.loader.exec_module(deg_mod)
DegradationManager = deg_mod.DegradationManager
DegradationPolicy = deg_mod.DegradationPolicy
DegradationLevel = deg_mod.DegradationLevel

from src.utils.config_center import ConfigCenter, ConfigType
from src.utils.secret_manager import SecretManager, SecretType
from src.utils.monitoring_alert import MonitoringAlertSystem, ComparisonOperator, AlertSeverity
from src.interfaces.manager_protocols import IConfigCenter, ISecretManager, IMonitoringAlertSystem


class TestEndToEndScenario(unittest.TestCase):
    """端到端场景测试"""

    def test_full_service_lifecycle(self):
        """测试完整服务生命周期"""
        # 1. 配置中心设置数据库配置
        config = ConfigCenter()
        config.set_config("db.host", "localhost", config_type=ConfigType.STRING)
        config.set_config("db.port", 5432, config_type=ConfigType.NUMBER)

        # 2. 密钥管理创建数据库密码
        secrets = SecretManager()
        secret, password = secrets.generate_password("db_password")
        secrets.grant_access(secret.secret_id, "payment_service")

        # 3. 监控告警设置规则
        monitor = MonitoringAlertSystem()
        monitor.create_rule(
            "db_slow", "DB Slow Query",
            "query_time", ComparisonOperator.GREATER_THAN, 1.0,
            severity=AlertSeverity.HIGH
        )

        # 4. 模拟服务启动读取配置
        db_host = config.get_config("db.host")
        db_port = config.get_config("db.port")
        db_pass = secrets.get_secret_value(secret.secret_id, "payment_service")

        self.assertEqual(db_host, "localhost")
        self.assertEqual(db_port, 5432)
        self.assertIsNotNone(db_pass)

        # 5. 模拟慢查询触发告警
        monitor.record_metric("query_time", 2.5)
        alerts = monitor.list_alerts(status="firing")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["name"], "DB Slow Query")

    def test_di_container_integration(self):
        """测试依赖注入容器集成"""
        container = DIContainer()
        container.register(IConfigCenter, ConfigCenter, lifecycle=Lifecycle.SINGLETON)
        container.register(ISecretManager, SecretManager, lifecycle=Lifecycle.SINGLETON)
        container.register(IMonitoringAlertSystem, MonitoringAlertSystem, lifecycle=Lifecycle.SINGLETON)

        config = container.resolve(IConfigCenter)
        secrets = container.resolve(ISecretManager)
        monitor = container.resolve(IMonitoringAlertSystem)

        # 验证单例
        config2 = container.resolve(IConfigCenter)
        self.assertIs(config, config2)

        # 跨模块协作
        config.set_config("api.key", "secret123")
        secret = secrets.create_secret("api_key", SecretType.API_KEY, "secret123")
        monitor.create_rule(
            "api_error", "API Error Rate",
            "error_rate", ComparisonOperator.GREATER_THAN, 0.05
        )

        self.assertEqual(config.get_config("api.key"), "secret123")
        self.assertTrue(secrets.verify_secret(secret.secret_id, "secret123"))

    def test_degradation_with_config(self):
        """测试降级策略与配置中心集成"""
        config = ConfigCenter()
        config.set_config("feature_flag", True, config_type=ConfigType.BOOLEAN)

        deg_mgr = DegradationManager()
        policy = DegradationPolicy(
            "p1", "feature_service",
            fallback=lambda: config.get_config("feature_flag", False)
        )
        deg_mgr.register_policy(policy)

        def unstable_service():
            raise RuntimeError("Service down")

        result = deg_mgr.execute("feature_service", unstable_service)
        self.assertEqual(result, True)

    def test_monitoring_with_secrets(self):
        """测试监控与密钥管理集成"""
        secrets = SecretManager()
        monitor = MonitoringAlertSystem()

        secret, api_key = secrets.generate_api_key("monitoring_key")
        secrets.grant_access(secret.secret_id, "monitoring_service")

        monitor.create_rule(
            "auth_fail", "Auth Failure",
            "auth_failures", ComparisonOperator.GREATER_THAN, 5.0,
            severity=AlertSeverity.CRITICAL
        )

        # 验证密钥可用
        key = secrets.get_secret_value(secret.secret_id, "monitoring_service")
        self.assertEqual(key, api_key)

        # 触发告警
        monitor.record_metric("auth_failures", 10.0)
        alerts = monitor.list_alerts(severity="critical")
        self.assertEqual(len(alerts), 1)

    def test_config_subscription_with_monitoring(self):
        """测试配置订阅与监控集成"""
        config = ConfigCenter()
        monitor = MonitoringAlertSystem()

        changes = []
        def on_config_change(key, old, new):
            changes.append((key, old, new))
            if key == "threshold":
                monitor.record_metric("config_change", 1.0)

        config.set_config("threshold", 80)
        config.subscribe("threshold", on_config_change)
        config.set_config("threshold", 90)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0], ("threshold", 80, 90))

    def test_multi_module_stats(self):
        """测试多模块统计信息"""
        config = ConfigCenter()
        secrets = SecretManager()
        monitor = MonitoringAlertSystem()

        config.set_config("k1", "v1")
        config.set_config("k2", "v2")
        secrets.create_secret("s1", SecretType.TOKEN, "v1")
        secrets.create_secret("s2", SecretType.TOKEN, "v2")
        monitor.create_rule("r1", "R1", "m1", ComparisonOperator.GREATER_THAN, 1.0)

        self.assertEqual(config.get_stats()["total_configs"], 2)
        self.assertEqual(secrets.get_stats()["total_secrets"], 2)
        self.assertEqual(monitor.get_stats()["total_rules"], 1)


class TestCrossModuleErrorHandling(unittest.TestCase):
    """跨模块错误处理测试"""

    def test_secret_expires_during_monitoring(self):
        """测试密钥过期时监控继续工作"""
        secrets = SecretManager()
        monitor = MonitoringAlertSystem()

        secret = secrets.create_secret(
            "temp", SecretType.TOKEN, "temp_value",
            expires_in_seconds=1
        )
        secrets.grant_access(secret.secret_id, "svc")

        monitor.create_rule("cpu", "CPU", "cpu", ComparisonOperator.GREATER_THAN, 80.0)

        time.sleep(1.1)
        value = secrets.get_secret_value(secret.secret_id, "svc")
        self.assertIsNone(value)

        # 监控不受影响
        monitor.record_metric("cpu", 90.0)
        alerts = monitor.list_alerts()
        self.assertEqual(len(alerts), 1)

    def test_config_delete_does_not_affect_secrets(self):
        """测试配置删除不影响密钥"""
        config = ConfigCenter()
        secrets = SecretManager()

        config.set_config("api_key", "config_value")
        secret = secrets.create_secret("api_key", SecretType.API_KEY, "secret_value")

        config.delete_config("api_key")
        self.assertIsNone(config.get_config("api_key"))
        self.assertTrue(secrets.verify_secret(secret.secret_id, "secret_value"))


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 108 - 集成测试与端到端验证")
    print("=" * 60)
    unittest.main(verbosity=2)
