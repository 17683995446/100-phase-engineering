"""
Phase 102 - 依赖注入容器测试
"""
import unittest
import sys
import importlib.util
# 绕过 src.core.__init__ 的循环导入，直接从文件加载
spec = importlib.util.spec_from_file_location("di_container", "/workspace/src/core/di_container.py")
di_module = importlib.util.module_from_spec(spec)
sys.modules["di_container"] = di_module
spec.loader.exec_module(di_module)
DIContainer = di_module.DIContainer
ServiceProvider = di_module.ServiceProvider
Lifecycle = di_module.Lifecycle
get_di_container = di_module.get_di_container
get_service_provider = di_module.get_service_provider
from src.interfaces.manager_protocols import IConfigCenter, ISecretManager
from src.utils.config_center import ConfigCenter
from src.utils.secret_manager import SecretManager, SecretType


class TestDIContainer(unittest.TestCase):
    """DI容器测试"""

    def setUp(self):
        self.container = DIContainer()

    def test_register_and_resolve(self):
        """测试注册和解析服务"""
        self.container.register(IConfigCenter, ConfigCenter)
        instance = self.container.resolve(IConfigCenter)
        self.assertIsInstance(instance, ConfigCenter)

    def test_singleton_lifecycle(self):
        """测试单例生命周期"""
        self.container.register(IConfigCenter, ConfigCenter, lifecycle=Lifecycle.SINGLETON)
        instance1 = self.container.resolve(IConfigCenter)
        instance2 = self.container.resolve(IConfigCenter)
        self.assertIs(instance1, instance2)

    def test_transient_lifecycle(self):
        """测试瞬态生命周期"""
        self.container.register(IConfigCenter, ConfigCenter, lifecycle=Lifecycle.TRANSIENT)
        instance1 = self.container.resolve(IConfigCenter)
        instance2 = self.container.resolve(IConfigCenter)
        self.assertIsNot(instance1, instance2)

    def test_register_instance(self):
        """测试注册已有实例"""
        config = ConfigCenter()
        self.container.register_instance(IConfigCenter, config)
        resolved = self.container.resolve(IConfigCenter)
        self.assertIs(resolved, config)

    def test_is_registered(self):
        """测试检查是否已注册"""
        self.assertFalse(self.container.is_registered(IConfigCenter))
        self.container.register(IConfigCenter, ConfigCenter)
        self.assertTrue(self.container.is_registered(IConfigCenter))

    def test_unregister(self):
        """测试注销服务"""
        self.container.register(IConfigCenter, ConfigCenter)
        self.assertTrue(self.container.unregister(IConfigCenter))
        self.assertFalse(self.container.is_registered(IConfigCenter))

    def test_resolve_not_registered(self):
        """测试解析未注册服务"""
        with self.assertRaises(KeyError):
            self.container.resolve(IConfigCenter)

    def test_factory_registration(self):
        """测试工厂注册"""
        def factory():
            return ConfigCenter()

        self.container.register(IConfigCenter, ConfigCenter, factory=factory)
        instance = self.container.resolve(IConfigCenter)
        self.assertIsInstance(instance, ConfigCenter)

    def test_get_registered_services(self):
        """测试获取已注册服务列表"""
        self.container.register(IConfigCenter, ConfigCenter)
        self.container.register(ISecretManager, SecretManager)
        services = self.container.get_registered_services()
        self.assertIn("IConfigCenter", services)
        self.assertIn("ISecretManager", services)


class TestServiceProvider(unittest.TestCase):
    """服务提供者测试"""

    def setUp(self):
        self.container = DIContainer()
        self.provider = self.container.build_provider()

    def test_get_service(self):
        """测试获取服务"""
        self.container.register(IConfigCenter, ConfigCenter)
        instance = self.provider.get_service(IConfigCenter)
        self.assertIsInstance(instance, ConfigCenter)

    def test_get_required_service_registered(self):
        """测试获取已注册的必需服务"""
        self.container.register(IConfigCenter, ConfigCenter)
        instance = self.provider.get_required_service(IConfigCenter)
        self.assertIsInstance(instance, ConfigCenter)

    def test_get_required_service_not_registered(self):
        """测试获取未注册的必需服务"""
        with self.assertRaises(KeyError):
            self.provider.get_required_service(IConfigCenter)

    def test_get_services(self):
        """测试获取所有服务"""
        self.container.register(IConfigCenter, ConfigCenter)
        services = self.provider.get_services()
        self.assertEqual(services["IConfigCenter"], "ConfigCenter")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_di_container(self):
        """测试获取全局DI容器"""
        c1 = get_di_container()
        c2 = get_di_container()
        self.assertIs(c1, c2)

    def test_get_service_provider(self):
        """测试获取全局服务提供者"""
        p1 = get_service_provider()
        p2 = get_service_provider()
        self.assertIsInstance(p1, ServiceProvider)
        self.assertIsInstance(p2, ServiceProvider)


class TestIntegrationWithProtocols(unittest.TestCase):
    """与 Protocol 集成的测试"""

    def test_protocol_based_registration(self):
        """测试基于 Protocol 的注册和解析"""
        container = DIContainer()
        container.register(ISecretManager, SecretManager)
        instance = container.resolve(ISecretManager)
        self.assertIsInstance(instance, SecretManager)

        # 验证接口功能
        secret = instance.create_secret("test", SecretType.PASSWORD, "value")
        self.assertEqual(secret.name, "test")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 102 - 依赖注入容器测试")
    print("=" * 60)
    unittest.main(verbosity=2)
