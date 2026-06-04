"""
Phase 40 - 系统配置管理与热更新测试
验证配置管理功能是否正常工作
"""
import os
import json
import tempfile
import unittest
from src.utils.config import (
    ConfigManager,
    ConfigScope,
    ConfigChangeType,
    get_config_manager,
    set_config,
    get_config
)


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = ConfigManager("test_manager")
    
    def test_set_and_get_config(self):
        """测试设置和获取配置"""
        # 设置配置
        change = self.manager.set_config(
            "test_key",
            "test_value",
            scope=ConfigScope.GLOBAL,
            description="Test configuration"
        )
        
        self.assertIsNotNone(change)
        self.assertEqual(change.key, "test_key")
        self.assertEqual(change.change_type, ConfigChangeType.ADD)
        
        # 获取配置
        value = self.manager.get_config("test_key")
        self.assertEqual(value, "test_value")
    
    def test_update_config(self):
        """测试更新配置"""
        # 首先设置
        self.manager.set_config("update_key", "old_value")
        
        # 然后更新
        change = self.manager.set_config("update_key", "new_value")
        
        self.assertEqual(change.change_type, ConfigChangeType.UPDATE)
        self.assertEqual(change.old_value, "old_value")
        self.assertEqual(change.new_value, "new_value")
        
        value = self.manager.get_config("update_key")
        self.assertEqual(value, "new_value")
    
    def test_delete_config(self):
        """测试删除配置"""
        self.manager.set_config("delete_key", "value")
        
        change = self.manager.delete_config("delete_key")
        self.assertEqual(change.change_type, ConfigChangeType.DELETE)
        
        value = self.manager.get_config("delete_key")
        self.assertIsNone(value)
    
    def test_get_all_configs(self):
        """测试获取所有配置"""
        self.manager.set_config("key1", "value1", scope=ConfigScope.GLOBAL)
        self.manager.set_config("key2", "value2", scope=ConfigScope.API)
        
        all_configs = self.manager.get_config_dict()
        self.assertEqual(len(all_configs), 2)
        
        global_configs = self.manager.get_config_dict(ConfigScope.GLOBAL)
        self.assertEqual(len(global_configs), 1)
    
    def test_batch_update(self):
        """测试批量更新"""
        updates = {
            "batch1": "value1",
            "batch2": "value2",
            "batch3": "value3"
        }
        
        changes = self.manager.batch_update(updates)
        
        self.assertEqual(len(changes), 3)
        self.assertEqual(self.manager.get_config("batch1"), "value1")
    
    def test_reset_config(self):
        """测试重置配置"""
        self.manager.set_config("reset_key", "initial_value")
        self.manager.set_config("reset_key", "updated_value")
        
        change = self.manager.reset_config("reset_key")
        
        self.assertIsNotNone(change)
        self.assertEqual(self.manager.get_config("reset_key"), "initial_value")
    
    def test_config_history(self):
        """测试配置历史"""
        self.manager.set_config("history_key", "v1")
        self.manager.set_config("history_key", "v2")
        self.manager.set_config("history_key", "v3")
        
        history = self.manager.get_history("history_key")
        self.assertEqual(len(history), 3)


class TestConfigPersistence(unittest.TestCase):
    """配置持久化测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = ConfigManager("test_persistence")
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        # 设置配置
        self.manager.set_config("save_key", "save_value")
        self.manager.set_config("save_key2", "save_value2")
        
        # 保存
        success = self.manager.save(self.config_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.config_path))
        
        # 创建新的管理器并加载
        new_manager = ConfigManager("loaded_manager")
        load_success = new_manager.load(self.config_path)
        self.assertTrue(load_success)
        
        self.assertEqual(new_manager.get_config("save_key"), "save_value")
    
    def test_auto_save(self):
        """测试自动保存"""
        self.manager.enable_auto_save(self.config_path)
        
        # 设置配置应该自动保存
        self.manager.set_config("auto_key", "auto_value")
        
        # 验证文件存在
        self.assertTrue(os.path.exists(self.config_path))
        
        # 验证内容
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        self.assertTrue(any(c['key'] == 'auto_key' for c in data['configs']))


class TestConfigSubscription(unittest.TestCase):
    """配置订阅测试"""
    
    def setUp(self):
        """测试前设置"""
        self.manager = ConfigManager("test_subscription")
        self.notifications = []
    
    def callback(self, change):
        """测试回调函数"""
        self.notifications.append(change)
    
    def test_specific_key_subscription(self):
        """测试特定键订阅"""
        self.manager.subscribe("sub_key", self.callback)
        
        # 触发变更
        self.manager.set_config("sub_key", "sub_value")
        
        # 验证收到通知
        self.assertEqual(len(self.notifications), 1)
        self.assertEqual(self.notifications[0].key, "sub_key")
    
    def test_all_subscription(self):
        """测试全局订阅"""
        self.manager.subscribe_all(self.callback)
        
        # 触发多个变更
        self.manager.set_config("key1", "value1")
        self.manager.set_config("key2", "value2")
        
        # 验证收到所有通知
        self.assertEqual(len(self.notifications), 2)
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        self.manager.subscribe("unsub_key", self.callback)
        
        # 第一次应该触发
        self.manager.set_config("unsub_key", "v1")
        self.assertEqual(len(self.notifications), 1)
        
        # 取消订阅
        self.manager.unsubscribe("unsub_key", self.callback)
        
        # 第二次不应该触发
        self.manager.set_config("unsub_key", "v2")
        self.assertEqual(len(self.notifications), 1)


class TestConfigAPI(unittest.TestCase):
    """配置API测试"""
    
    def setUp(self):
        """测试前设置"""
        from src.api_layer.core import APIApp, APIRequest, HTTPMethod
        self.app = APIApp("test_config_api")
        self.app_instance = self.app
    
    def test_get_configs_api(self):
        """测试获取配置API"""
        from src.api_layer.core import APIRequest, HTTPMethod
        
        # 先设置一些配置
        set_config("api_key", "api_value")
        
        # 调用API
        request = APIRequest(HTTPMethod.GET, "/configs")
        response = self.app_instance.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.body["success"])
    
    def test_update_config_api(self):
        """测试更新配置API"""
        from src.api_layer.core import APIRequest, HTTPMethod
        
        request = APIRequest(
            HTTPMethod.PUT,
            "/configs/test_api_key",
            body={"value": "test_api_value", "description": "Test config"}
        )
        response = self.app_instance.handle_request(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.body["success"])
        
        # 验证配置真的更新了
        self.assertEqual(get_config("test_api_key"), "test_api_value")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 40 - 系统配置管理与热更新测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigPersistence))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigSubscription))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigAPI))
    
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
