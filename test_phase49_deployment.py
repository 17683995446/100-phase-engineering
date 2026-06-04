"""
Phase 49 - 容器化与部署测试
验证部署管理和环境管理功能是否正常工作
"""
import os
import tempfile
import time
import unittest
from src.utils.deployment import (
    DeploymentManager,
    DeploymentConfig,
    ContainerConfig,
    DeploymentStrategy,
    DeploymentStatus,
    EnvironmentType,
    EnvironmentManager,
)


class TestContainerConfig(unittest.TestCase):
    """容器配置测试"""

    def test_container_creation(self):
        """测试容器配置创建"""
        container = ContainerConfig(
            name="web-app",
            image="myapp",
            tag="v1.0",
            ports={8080: 80},
            env_vars={"DB_HOST": "localhost"},
            replicas=3
        )
        self.assertEqual(container.name, "web-app")
        self.assertEqual(container.image, "myapp")
        self.assertEqual(container.tag, "v1.0")
        self.assertEqual(container.replicas, 3)

    def test_container_to_dict(self):
        """测试转换为字典"""
        container = ContainerConfig(name="app", image="test")
        d = container.to_dict()
        self.assertEqual(d["name"], "app")
        self.assertEqual(d["image"], "test")


class TestDeploymentConfig(unittest.TestCase):
    """部署配置测试"""

    def test_deployment_config(self):
        """测试部署配置"""
        container = ContainerConfig(name="app", image="test")
        config = DeploymentConfig(
            name="my-app",
            version="1.0.0",
            strategy=DeploymentStrategy.ROLLING,
            containers=[container],
            environment=EnvironmentType.PRODUCTION
        )
        self.assertEqual(config.name, "my-app")
        self.assertEqual(config.strategy, DeploymentStrategy.ROLLING)
        self.assertEqual(config.environment, EnvironmentType.PRODUCTION)


class TestDeploymentManager(unittest.TestCase):
    """部署管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        # 每个测试使用独立的 DeploymentManager，避免全局单例污染
        self.manager = DeploymentManager(self.temp_dir)

        self.container = ContainerConfig(
            name="web-app",
            image="myapp",
            tag="v1.0"
        )
        self.config = DeploymentConfig(
            name="my-app",
            version="1.0.0",
            strategy=DeploymentStrategy.ROLLING,
            containers=[self.container]
        )

    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _wait_for_deployment(self, deployment_id, timeout=2.0):
        """等待部署完成"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.manager.get_deployment_status(deployment_id)
            if status in (DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, DeploymentStatus.ROLLED_BACK):
                return status
            time.sleep(0.05)
        return self.manager.get_deployment_status(deployment_id)

    def test_create_deployment(self):
        """测试创建部署"""
        deployment_id = self.manager.create_deployment(self.config)
        self.assertIsNotNone(deployment_id)
        self.assertIn("my-app", deployment_id)

    def test_start_deployment(self):
        """测试开始部署"""
        deployment_id = self.manager.create_deployment(self.config)
        result = self.manager.start_deployment(deployment_id)
        self.assertTrue(result)

        status = self._wait_for_deployment(deployment_id)
        self.assertEqual(status, DeploymentStatus.SUCCESS)

    def test_rollback_deployment(self):
        """测试回滚部署"""
        deployment_id = self.manager.create_deployment(self.config)
        self.manager.start_deployment(deployment_id)
        self._wait_for_deployment(deployment_id)

        result = self.manager.rollback_deployment(deployment_id)
        self.assertTrue(result)

        status = self.manager.get_deployment_status(deployment_id)
        self.assertEqual(status, DeploymentStatus.ROLLED_BACK)

    def test_get_deployment(self):
        """测试获取部署"""
        deployment_id = self.manager.create_deployment(self.config)
        record = self.manager.get_deployment(deployment_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.config.name, "my-app")

    def test_get_all_deployments(self):
        """测试获取所有部署"""
        self.manager.create_deployment(self.config)
        self.manager.create_deployment(self.config)

        deployments = self.manager.get_all_deployments()
        self.assertEqual(len(deployments), 2)

    def test_get_deployments_by_status(self):
        """测试按状态获取部署"""
        deployment_id = self.manager.create_deployment(self.config)
        self.manager.start_deployment(deployment_id)
        self._wait_for_deployment(deployment_id)

        success_deployments = self.manager.get_deployments_by_status(DeploymentStatus.SUCCESS)
        self.assertEqual(len(success_deployments), 1)

    def test_stats(self):
        """测试统计"""
        deployment_id = self.manager.create_deployment(self.config)
        self.manager.start_deployment(deployment_id)
        self._wait_for_deployment(deployment_id)

        stats = self.manager.get_stats()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["success"], 1)
        self.assertEqual(stats["success_rate"], 1.0)

    def test_blue_green_deployment(self):
        """测试蓝绿部署"""
        config = DeploymentConfig(
            name="bg-app",
            version="1.0.0",
            strategy=DeploymentStrategy.BLUE_GREEN,
            containers=[self.container]
        )
        deployment_id = self.manager.create_deployment(config)
        self.manager.start_deployment(deployment_id)
        status = self._wait_for_deployment(deployment_id)
        self.assertEqual(status, DeploymentStatus.SUCCESS)

    def test_canary_deployment(self):
        """测试金丝雀部署"""
        config = DeploymentConfig(
            name="canary-app",
            version="1.0.0",
            strategy=DeploymentStrategy.CANARY,
            containers=[self.container]
        )
        deployment_id = self.manager.create_deployment(config)
        self.manager.start_deployment(deployment_id)
        status = self._wait_for_deployment(deployment_id)
        self.assertEqual(status, DeploymentStatus.SUCCESS)

    def test_save_deployment_config(self):
        """测试保存部署配置"""
        deployment_id = self.manager.create_deployment(self.config)
        self.manager.start_deployment(deployment_id)
        self._wait_for_deployment(deployment_id)

        filepath = os.path.join(self.temp_dir, "deployment.json")
        result = self.manager.save_deployment_config(deployment_id, filepath)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))


class TestEnvironmentManager(unittest.TestCase):
    """环境管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = EnvironmentManager()

    def test_create_environment(self):
        """测试创建环境"""
        result = self.manager.create_environment(
            "prod",
            EnvironmentType.PRODUCTION,
            {"env_vars": {"DB_HOST": "prod.db"}}
        )
        self.assertTrue(result)

    def test_create_duplicate_environment(self):
        """测试创建重复环境"""
        self.manager.create_environment("dev", EnvironmentType.DEVELOPMENT, {})
        result = self.manager.create_environment("dev", EnvironmentType.DEVELOPMENT, {})
        self.assertFalse(result)

    def test_get_environment(self):
        """测试获取环境"""
        self.manager.create_environment("test", EnvironmentType.TESTING, {"key": "value"})
        env = self.manager.get_environment("test")
        self.assertIsNotNone(env)
        self.assertEqual(env["name"], "test")

    def test_update_environment(self):
        """测试更新环境"""
        self.manager.create_environment("staging", EnvironmentType.STAGING, {"old": "value"})
        result = self.manager.update_environment("staging", {"new": "value"})
        self.assertTrue(result)

        env = self.manager.get_environment("staging")
        self.assertIn("new", env["config"])

    def test_delete_environment(self):
        """测试删除环境"""
        self.manager.create_environment("temp", EnvironmentType.DEVELOPMENT, {})
        result = self.manager.delete_environment("temp")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_environment("temp"))

    def test_get_all_environments(self):
        """测试获取所有环境"""
        self.manager.create_environment("dev", EnvironmentType.DEVELOPMENT, {})
        self.manager.create_environment("prod", EnvironmentType.PRODUCTION, {})
        envs = self.manager.get_all_environments()
        self.assertEqual(len(envs), 2)

    def test_get_environment_variables(self):
        """测试获取环境变量"""
        self.manager.create_environment(
            "app",
            EnvironmentType.PRODUCTION,
            {"env_vars": {"KEY1": "VALUE1", "KEY2": "VALUE2"}}
        )
        env_vars = self.manager.get_environment_variables("app")
        self.assertEqual(env_vars["KEY1"], "VALUE1")
        self.assertEqual(env_vars["KEY2"], "VALUE2")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 49 - 容器化与部署测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestContainerConfig))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDeploymentConfig))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDeploymentManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEnvironmentManager))

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
