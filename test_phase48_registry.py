"""
Phase 48 - 服务发现与注册中心测试
验证服务注册、发现、健康检查功能是否正常工作
"""
import time
import unittest
from src.utils.service_registry import (
    ServiceRegistry,
    ServiceInstance,
    ServiceStatus,
    ServiceDiscoveryClient,
    ServiceRegistrar,
    get_service_registry,
    get_discovery_client,
    get_registrar
)


class TestServiceInstance(unittest.TestCase):
    """服务实例测试"""
    
    def test_instance_creation(self):
        """测试实例创建"""
        instance = ServiceInstance(
            service_id="user-1",
            service_name="user-service",
            host="localhost",
            port=8080,
            metadata={"version": "1.0"}
        )
        self.assertEqual(instance.service_id, "user-1")
        self.assertEqual(instance.service_name, "user-service")
        self.assertEqual(instance.address, "localhost:8080")
        self.assertEqual(instance.instance_id, "user-service@localhost:8080")
    
    def test_instance_to_dict(self):
        """测试转换为字典"""
        instance = ServiceInstance(
            service_id="user-1",
            service_name="user-service",
            host="localhost",
            port=8080
        )
        d = instance.to_dict()
        self.assertEqual(d["service_id"], "user-1")
        self.assertEqual(d["status"], "HEALTHY")


class TestServiceRegistry(unittest.TestCase):
    """服务注册中心测试"""
    
    def setUp(self):
        """测试前设置"""
        self.registry = ServiceRegistry()
        self.instance1 = ServiceInstance(
            service_id="user-1",
            service_name="user-service",
            host="localhost",
            port=8081
        )
        self.instance2 = ServiceInstance(
            service_id="user-2",
            service_name="user-service",
            host="localhost",
            port=8082
        )
    
    def test_register(self):
        """测试注册"""
        result = self.registry.register(self.instance1)
        self.assertTrue(result)
        
        services = self.registry.get_all_services()
        self.assertIn("user-service", services)
    
    def test_deregister(self):
        """测试注销"""
        self.registry.register(self.instance1)
        result = self.registry.deregister("user-service", "user-1")
        self.assertTrue(result)
        
        instances = self.registry.discover("user-service")
        self.assertEqual(len(instances), 0)
    
    def test_discover(self):
        """测试发现"""
        self.registry.register(self.instance1)
        self.registry.register(self.instance2)
        
        instances = self.registry.discover("user-service")
        self.assertEqual(len(instances), 2)
    
    def test_discover_nonexistent(self):
        """测试发现不存在的服务"""
        instances = self.registry.discover("nonexistent")
        self.assertEqual(len(instances), 0)
    
    def test_heartbeat(self):
        """测试心跳"""
        self.registry.register(self.instance1)
        result = self.registry.heartbeat("user-service", "user-1")
        self.assertTrue(result)
    
    def test_heartbeat_nonexistent(self):
        """测试不存在服务的心跳"""
        result = self.registry.heartbeat("nonexistent", "id")
        self.assertFalse(result)
    
    def test_get_instance(self):
        """测试获取实例"""
        self.registry.register(self.instance1)
        instance = self.registry.get_instance("user-service", "user-1")
        self.assertIsNotNone(instance)
        self.assertEqual(instance.service_id, "user-1")
    
    def test_update_status(self):
        """测试更新状态"""
        self.registry.register(self.instance1)
        self.registry.update_status("user-service", "user-1", ServiceStatus.UNHEALTHY)
        
        instances = self.registry.discover("user-service")
        self.assertEqual(len(instances), 0)  # 不健康的不返回
    
    def test_get_all_instances(self):
        """测试获取所有实例"""
        self.registry.register(self.instance1)
        self.registry.register(self.instance2)
        
        all_instances = self.registry.get_all_instances()
        self.assertEqual(len(all_instances), 2)
    
    def test_watcher(self):
        """测试监听器"""
        events = []
        
        def watcher(event, instance):
            events.append((event, instance.service_id))
        
        self.registry.add_watcher(watcher)
        self.registry.register(self.instance1)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "REGISTER")
    
    def test_stats(self):
        """测试统计"""
        self.registry.register(self.instance1)
        self.registry.register(self.instance2)
        
        stats = self.registry.get_stats()
        self.assertEqual(stats["total_services"], 1)
        self.assertEqual(stats["total_instances"], 2)
        self.assertEqual(stats["healthy_instances"], 2)


class TestHealthCheck(unittest.TestCase):
    """健康检查测试"""
    
    def test_expired_service(self):
        """测试过期服务检测"""
        registry = ServiceRegistry(heartbeat_timeout=0.1, check_interval=0.1)
        instance = ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080
        )
        registry.register(instance)
        
        # 启动健康检查
        registry.start_health_check()
        
        # 等待超时
        time.sleep(0.3)
        
        # 停止健康检查
        registry.stop_health_check()
        
        # 服务应该被标记为不健康
        instances = registry.discover("test-service")
        self.assertEqual(len(instances), 0)
    
    def test_heartbeat_keeps_alive(self):
        """测试心跳保持服务存活"""
        registry = ServiceRegistry(heartbeat_timeout=1.0, check_interval=0.1)
        instance = ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080
        )
        registry.register(instance)
        registry.start_health_check()
        
        # 持续发送心跳
        for _ in range(5):
            time.sleep(0.15)
            registry.heartbeat("test-service", "test-1")
        
        registry.stop_health_check()
        
        # 服务应该仍然健康
        instances = registry.discover("test-service")
        self.assertEqual(len(instances), 1)


class TestServiceDiscoveryClient(unittest.TestCase):
    """服务发现客户端测试"""
    
    def setUp(self):
        """测试前设置"""
        self.registry = ServiceRegistry()
        self.client = ServiceDiscoveryClient(self.registry)
        self.instance = ServiceInstance(
            service_id="user-1",
            service_name="user-service",
            host="localhost",
            port=8080
        )
        self.registry.register(self.instance)
    
    def test_discover(self):
        """测试发现"""
        instances = self.client.discover("user-service")
        self.assertEqual(len(instances), 1)
    
    def test_get_one_instance(self):
        """测试获取单个实例"""
        instance = self.client.get_one_instance("user-service")
        self.assertIsNotNone(instance)
        self.assertEqual(instance.service_id, "user-1")
    
    def test_cache(self):
        """测试缓存"""
        # 第一次查询
        instances1 = self.client.discover("user-service", use_cache=True)
        self.assertEqual(len(instances1), 1)
        
        # 第二次应该从缓存获取
        instances2 = self.client.discover("user-service", use_cache=True)
        self.assertEqual(len(instances2), 1)
    
    def test_invalidate_cache(self):
        """测试缓存失效"""
        self.client.discover("user-service", use_cache=True)
        self.client.invalidate_cache("user-service")
        
        cached = self.client._get_cached("user-service")
        self.assertIsNone(cached)


class TestServiceRegistrar(unittest.TestCase):
    """服务注册客户端测试"""
    
    def setUp(self):
        """测试前设置"""
        self.registry = ServiceRegistry()
        self.registrar = ServiceRegistrar(self.registry)
        self.instance = ServiceInstance(
            service_id="user-1",
            service_name="user-service",
            host="localhost",
            port=8080
        )
    
    def test_register(self):
        """测试注册"""
        result = self.registrar.register(self.instance)
        self.assertTrue(result)
    
    def test_deregister(self):
        """测试注销"""
        self.registrar.register(self.instance)
        result = self.registrar.deregister("user-service", "user-1")
        self.assertTrue(result)
    
    def test_heartbeat(self):
        """测试自动心跳"""
        self.registrar.register(self.instance)
        self.registrar.start_heartbeat(interval=0.1)
        
        # 等待心跳发送
        time.sleep(0.25)
        
        self.registrar.stop_heartbeat()
        
        # 验证心跳更新了时间
        instance = self.registry.get_instance("user-service", "user-1")
        self.assertIsNotNone(instance.last_heartbeat)


class TestGlobalInstances(unittest.TestCase):
    """全局实例测试"""
    
    def test_get_service_registry(self):
        """测试获取全局注册中心"""
        registry1 = get_service_registry()
        registry2 = get_service_registry()
        self.assertIs(registry1, registry2)
    
    def test_get_discovery_client(self):
        """测试获取全局发现客户端"""
        client1 = get_discovery_client()
        client2 = get_discovery_client()
        self.assertIs(client1, client2)
    
    def test_get_registrar(self):
        """测试获取全局注册客户端"""
        registrar1 = get_registrar()
        registrar2 = get_registrar()
        self.assertIs(registrar1, registrar2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 48 - 服务发现与注册中心测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestServiceInstance))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestServiceRegistry))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHealthCheck))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestServiceDiscoveryClient))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestServiceRegistrar))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstances))
    
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
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
