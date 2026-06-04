"""
Phase 98 - 配置中心测试
"""
import unittest
from src.utils.config_center import (
    ConfigCenter, ConfigType, ConfigStatus,
    get_config_center
)


class TestConfigCenter(unittest.TestCase):
    """配置中心测试"""

    def setUp(self):
        self.center = ConfigCenter()

    def test_set_config(self):
        """测试设置配置"""
        item = self.center.set_config("app.name", "MyApp")
        self.assertEqual(item.key, "app.name")
        self.assertEqual(item.value, "MyApp")
        self.assertEqual(item.version, 1)

    def test_get_config(self):
        """测试获取配置"""
        self.center.set_config("app.name", "MyApp")
        value = self.center.get_config("app.name")
        self.assertEqual(value, "MyApp")

    def test_get_config_default(self):
        """测试获取默认配置"""
        value = self.center.get_config("nonexistent", "default")
        self.assertEqual(value, "default")

    def test_update_config(self):
        """测试更新配置"""
        self.center.set_config("app.name", "MyApp")
        item = self.center.set_config("app.name", "NewApp")
        self.assertEqual(item.value, "NewApp")
        self.assertEqual(item.version, 2)

    def test_delete_config(self):
        """测试删除配置"""
        self.center.set_config("app.name", "MyApp")
        self.assertTrue(self.center.delete_config("app.name"))
        self.assertIsNone(self.center.get_config("app.name"))

    def test_list_configs(self):
        """测试列出配置"""
        self.center.set_config("k1", "v1", env="dev")
        self.center.set_config("k2", "v2", env="prod")
        dev_configs = self.center.list_configs(env="dev")
        self.assertEqual(len(dev_configs), 1)

    def test_list_configs_by_tag(self):
        """测试按标签列出配置"""
        self.center.set_config("k1", "v1", tags=["db"])
        self.center.set_config("k2", "v2", tags=["cache"])
        db_configs = self.center.list_configs(tag="db")
        self.assertEqual(len(db_configs), 1)

    def test_versions(self):
        """测试版本历史"""
        self.center.set_config("app.name", "v1")
        self.center.set_config("app.name", "v2")
        self.center.set_config("app.name", "v3")
        versions = self.center.get_versions("app.name")
        self.assertEqual(len(versions), 3)

    def test_rollback(self):
        """测试回滚"""
        self.center.set_config("app.name", "v1")
        self.center.set_config("app.name", "v2")
        versions = self.center.get_versions("app.name")
        target_version = versions[0]["version"]
        item = self.center.rollback("app.name", target_version)
        self.assertEqual(item.value, "v1")
        self.assertEqual(item.version, 3)

    def test_rollback_not_found(self):
        """测试回滚不存在的版本"""
        self.center.set_config("app.name", "v1")
        result = self.center.rollback("app.name", 999)
        self.assertIsNone(result)

    def test_subscribe(self):
        """测试订阅配置变更"""
        changes = []
        def callback(key, old, new):
            changes.append((key, old, new))

        self.center.set_config("app.name", "v1")
        self.center.subscribe("app.name", callback)
        self.center.set_config("app.name", "v2")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0], ("app.name", "v1", "v2"))

    def test_unsubscribe(self):
        """测试取消订阅"""
        def callback(key, old, new):
            pass

        self.center.set_config("app.name", "v1")
        self.center.subscribe("app.name", callback)
        self.assertTrue(self.center.unsubscribe("app.name", callback))

    def test_batch_set(self):
        """测试批量设置"""
        items = self.center.batch_set({"k1": "v1", "k2": "v2"})
        self.assertEqual(len(items), 2)
        self.assertEqual(self.center.get_config("k1"), "v1")
        self.assertEqual(self.center.get_config("k2"), "v2")

    def test_batch_get(self):
        """测试批量获取"""
        self.center.set_config("k1", "v1")
        self.center.set_config("k2", "v2")
        values = self.center.batch_get(["k1", "k2"])
        self.assertEqual(values, {"k1": "v1", "k2": "v2"})

    def test_import_configs(self):
        """测试导入配置"""
        configs = [
            {"key": "db.host", "value": "localhost", "type": "string"},
            {"key": "db.port", "value": 5432, "type": "number"}
        ]
        items = self.center.import_configs(configs)
        self.assertEqual(len(items), 2)
        self.assertEqual(self.center.get_config("db.host"), "localhost")
        self.assertEqual(self.center.get_config("db.port"), 5432)

    def test_export_configs(self):
        """测试导出配置"""
        self.center.set_config("k1", "v1", env="dev")
        self.center.set_config("k2", "v2", env="prod")
        exported = self.center.export_configs(env="dev")
        self.assertEqual(len(exported), 1)

    def test_clone_env(self):
        """测试克隆环境"""
        self.center.set_config("k1", "v1", env="dev")
        self.center.set_config("k2", "v2", env="dev")
        items = self.center.clone_env("dev", "staging")
        self.assertEqual(len(items), 2)
        self.assertEqual(self.center.get_config("k1"), "v1")

    def test_clone_env_skips_deleted(self):
        """测试克隆环境跳过已删除配置"""
        self.center.set_config("k1", "v1", env="dev")
        self.center.delete_config("k1")
        items = self.center.clone_env("dev", "staging")
        self.assertEqual(len(items), 0)

    def test_config_types(self):
        """测试配置类型"""
        self.center.set_config("num", 42, config_type=ConfigType.NUMBER)
        self.center.set_config("flag", True, config_type=ConfigType.BOOLEAN)
        self.center.set_config("items", [1, 2, 3], config_type=ConfigType.LIST)
        self.assertEqual(self.center.get_config("num"), 42)
        self.assertEqual(self.center.get_config("flag"), True)
        self.assertEqual(self.center.get_config("items"), [1, 2, 3])

    def test_stats(self):
        """测试统计信息"""
        self.center.set_config("k1", "v1")
        self.center.set_config("k2", "v2")
        stats = self.center.get_stats()
        self.assertEqual(stats["total_configs"], 2)
        self.assertEqual(stats["active"], 2)

    def test_deleted_config_not_returned(self):
        """测试已删除配置不返回"""
        self.center.set_config("k1", "v1")
        self.center.delete_config("k1")
        value = self.center.get_config("k1")
        self.assertIsNone(value)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_config_center(self):
        """测试获取全局配置中心"""
        c1 = get_config_center()
        c2 = get_config_center()
        self.assertIs(c1, c2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 98 - 配置中心测试")
    print("=" * 60)
    unittest.main(verbosity=2)
