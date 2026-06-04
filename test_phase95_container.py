"""
Phase 95 - 容器编排管理器测试
"""
import unittest
import time
from src.utils.container_orchestrator import (
    ContainerOrchestrator, ContainerStatus, ServiceStatus,
    get_container_orchestrator
)


class TestContainerOrchestrator(unittest.TestCase):
    """容器编排管理器测试"""

    def setUp(self):
        self.orch = ContainerOrchestrator()

    def test_register_service(self):
        """测试注册服务"""
        svc = self.orch.register_service(
            "web", "Web Service", "nginx:latest",
            replicas=2, ports=[80], env={"ENV": "prod"}
        )
        self.assertEqual(svc.service_id, "web")
        self.assertEqual(svc.replicas, 2)
        self.assertEqual(svc.image, "nginx:latest")

    def test_register_duplicate(self):
        """测试注册重复服务"""
        self.orch.register_service("web", "Web", "nginx")
        with self.assertRaises(ValueError):
            self.orch.register_service("web", "Web2", "nginx")

    def test_deploy_service(self):
        """测试部署服务"""
        self.orch.register_service("web", "Web", "nginx", replicas=2, ports=[80])
        instance = self.orch.deploy_service("web")
        self.assertEqual(instance.status, ServiceStatus.ACTIVE)
        self.assertEqual(instance.current_replicas, 2)
        self.assertEqual(len(instance.containers), 2)

    def test_deploy_not_found(self):
        """测试部署不存在的服务"""
        with self.assertRaises(ValueError):
            self.orch.deploy_service("web")

    def test_scale_up(self):
        """测试扩容"""
        self.orch.register_service("web", "Web", "nginx", replicas=1, ports=[80])
        self.orch.deploy_service("web")
        instance = self.orch.scale_service("web", 3)
        self.assertEqual(instance.current_replicas, 3)
        self.assertEqual(instance.target_replicas, 3)

    def test_scale_down(self):
        """测试缩容"""
        self.orch.register_service("web", "Web", "nginx", replicas=3, ports=[80])
        self.orch.deploy_service("web")
        instance = self.orch.scale_service("web", 1)
        self.assertEqual(instance.current_replicas, 1)

    def test_stop_service(self):
        """测试停止服务"""
        self.orch.register_service("web", "Web", "nginx", replicas=2, ports=[80])
        self.orch.deploy_service("web")
        self.assertTrue(self.orch.stop_service("web"))
        instance = self.orch.get_service("web")
        self.assertEqual(instance.status, ServiceStatus.DOWN)
        self.assertEqual(instance.current_replicas, 0)

    def test_remove_service(self):
        """测试移除服务"""
        self.orch.register_service("web", "Web", "nginx", replicas=1)
        self.orch.deploy_service("web")
        self.assertTrue(self.orch.remove_service("web"))
        self.assertIsNone(self.orch.get_service("web"))

    def test_get_service(self):
        """测试获取服务"""
        self.orch.register_service("web", "Web", "nginx", replicas=1)
        self.orch.deploy_service("web")
        svc = self.orch.get_service("web")
        self.assertIsNotNone(svc)
        self.assertEqual(svc.service_id, "web")

    def test_list_services(self):
        """测试列出服务"""
        self.orch.register_service("web", "Web", "nginx", replicas=1)
        self.orch.register_service("api", "API", "python", replicas=1)
        self.orch.deploy_service("web")
        self.orch.deploy_service("api")
        services = self.orch.list_services()
        self.assertEqual(len(services), 2)

    def test_get_container(self):
        """测试获取容器"""
        self.orch.register_service("web", "Web", "nginx", replicas=1)
        self.orch.deploy_service("web")
        instance = self.orch.get_service("web")
        container_id = list(instance.containers.keys())[0]
        container = self.orch.get_container(container_id)
        self.assertIsNotNone(container)
        self.assertEqual(container.status, ContainerStatus.RUNNING)

    def test_restart_container(self):
        """测试重启容器"""
        self.orch.register_service("web", "Web", "nginx", replicas=1, ports=[80])
        self.orch.deploy_service("web")
        instance = self.orch.get_service("web")
        old_id = list(instance.containers.keys())[0]
        old_port = instance.containers[old_id].port

        new_container = self.orch.restart_container_by_id(old_id)
        self.assertIsNotNone(new_container)
        self.assertNotEqual(new_container.container_id, old_id)
        self.assertEqual(new_container.restart_count, 1)

    def test_port_allocation(self):
        """测试端口分配"""
        self.orch.register_service("web", "Web", "nginx", replicas=2, ports=[80])
        self.orch.deploy_service("web")
        instance = self.orch.get_service("web")
        ports = [c.port for c in instance.containers.values()]
        self.assertEqual(len(ports), 2)
        self.assertNotEqual(ports[0], ports[1])
        self.assertIsNotNone(ports[0])
        self.assertIsNotNone(ports[1])

    def test_stats(self):
        """测试统计信息"""
        self.orch.register_service("web", "Web", "nginx", replicas=2, ports=[80])
        self.orch.deploy_service("web")
        stats = self.orch.get_stats()
        self.assertEqual(stats["total_services"], 1)
        self.assertEqual(stats["total_containers"], 2)
        self.assertEqual(stats["running_containers"], 2)
        self.assertEqual(stats["allocated_ports"], 2)

    def test_container_uptime(self):
        """测试容器运行时间"""
        self.orch.register_service("web", "Web", "nginx", replicas=1)
        self.orch.deploy_service("web")
        instance = self.orch.get_service("web")
        container = list(instance.containers.values())[0]
        self.assertGreaterEqual(container.uptime, 0)

    def test_env_variables(self):
        """测试环境变量"""
        self.orch.register_service("web", "Web", "nginx", env={"KEY": "VALUE"})
        self.orch.deploy_service("web")
        instance = self.orch.get_service("web")
        container = list(instance.containers.values())[0]
        self.assertEqual(container.env["KEY"], "VALUE")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_container_orchestrator(self):
        """测试获取全局容器编排管理器"""
        o1 = get_container_orchestrator()
        o2 = get_container_orchestrator()
        self.assertIs(o1, o2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 95 - 容器编排管理器测试")
    print("=" * 60)
    unittest.main(verbosity=2)
