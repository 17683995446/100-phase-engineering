"""
Phase 64 - 插件系统测试
验证插件加载、注册、管理和生命周期管理功能是否正常工作
"""
import unittest
from src.utils.plugin_system import (
    PluginManager,
    Plugin,
    PluginInfo,
    PluginStatus,
    get_plugin_manager
)


class TestPlugin(Plugin):
    """测试插件"""

    def __init__(self, name="test"):
        super().__init__(PluginInfo(name=name, version="1.0.0"))
        self.executed = False
        self.result = None

    def _execute(self, *args, **kwargs):
        self.executed = True
        self.result = args[0] if args else None
        return self.result


class TestPluginManager(unittest.TestCase):
    """插件管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = PluginManager()

    def test_register_plugin(self):
        """测试注册插件"""
        plugin = TestPlugin("plugin1")
        result = self.manager.register_plugin(plugin)
        self.assertTrue(result)
        self.assertIsNotNone(self.manager.get_plugin("plugin1"))

    def test_register_duplicate(self):
        """测试重复注册"""
        self.manager.register_plugin(TestPlugin("plugin1"))
        result = self.manager.register_plugin(TestPlugin("plugin1"))
        self.assertFalse(result)

    def test_load_plugin(self):
        """测试加载插件"""
        self.manager.register_plugin(TestPlugin("plugin1"))
        result = self.manager.load_plugin("plugin1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_plugin("plugin1").status, PluginStatus.LOADED)

    def test_enable_plugin(self):
        """测试启用插件"""
        self.manager.register_plugin(TestPlugin("plugin1"))
        result = self.manager.enable_plugin("plugin1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_plugin("plugin1").status, PluginStatus.ENABLED)

    def test_disable_plugin(self):
        """测试禁用插件"""
        self.manager.register_plugin(TestPlugin("plugin1"))
        self.manager.enable_plugin("plugin1")
        result = self.manager.disable_plugin("plugin1")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_plugin("plugin1").status, PluginStatus.DISABLED)

    def test_unregister_plugin(self):
        """测试注销插件"""
        self.manager.register_plugin(TestPlugin("plugin1"))
        result = self.manager.unregister_plugin("plugin1")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_plugin("plugin1"))

    def test_execute_plugin(self):
        """测试执行插件"""
        plugin = TestPlugin("plugin1")
        self.manager.register_plugin(plugin)
        self.manager.enable_plugin("plugin1")

        result = self.manager.execute_plugin("plugin1", "hello")
        self.assertEqual(result, "hello")
        self.assertTrue(plugin.executed)

    def test_execute_disabled(self):
        """测试执行禁用插件"""
        plugin = TestPlugin("plugin1")
        self.manager.register_plugin(plugin)
        # 不启用

        result = self.manager.execute_plugin("plugin1", "hello")
        self.assertIsNone(result)
        self.assertFalse(plugin.executed)

    def test_get_all_plugins(self):
        """测试获取所有插件"""
        self.manager.register_plugin(TestPlugin("p1"))
        self.manager.register_plugin(TestPlugin("p2"))

        plugins = self.manager.get_all_plugins()
        self.assertEqual(len(plugins), 2)

    def test_get_plugins_by_status(self):
        """测试按状态获取插件"""
        self.manager.register_plugin(TestPlugin("p1"))
        self.manager.register_plugin(TestPlugin("p2"))
        self.manager.enable_plugin("p1")

        enabled = self.manager.get_plugins_by_status(PluginStatus.ENABLED)
        self.assertEqual(len(enabled), 1)

    def test_hooks(self):
        """测试钩子"""
        results = []

        def callback(data):
            results.append(data)
            return data * 2

        self.manager.add_hook("test_event", callback)
        hook_results = self.manager.trigger_hook("test_event", "hello")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "hello")
        self.assertEqual(hook_results, ["hellohello"])

    def test_stats(self):
        """测试统计"""
        self.manager.register_plugin(TestPlugin("p1"))
        self.manager.register_plugin(TestPlugin("p2"))
        self.manager.enable_plugin("p1")

        stats = self.manager.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["enabled"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_plugin_manager(self):
        """测试获取全局管理器"""
        m1 = get_plugin_manager()
        m2 = get_plugin_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 64 - 插件系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPluginManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstance))

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
