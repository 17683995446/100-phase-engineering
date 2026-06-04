"""
Phase 46 - 数据迁移与版本控制测试
验证迁移管理和版本控制功能是否正常工作
"""
import os
import tempfile
import unittest
from src.utils.migration import (
    MigrationManager,
    VersionControl,
    MigrationStatus,
    get_migration_manager,
    get_version_control
)


class TestMigrationManager(unittest.TestCase):
    """迁移管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.migrations_dir = os.path.join(self.temp_dir, "migrations")
        self.manager = MigrationManager(self.migrations_dir)
        self.applied_migrations = []
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_register_migration(self):
        """测试注册迁移"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial migration", handler)
        
        self.assertEqual(len(self.manager._migrations), 1)
        self.assertIn("1.0.0", self.manager._migrations)
    
    def test_apply_migration(self):
        """测试应用迁移"""
        def handler():
            self.applied_migrations.append("1.0.0")
        
        self.manager.register_migration("1.0.0", "init", "Initial migration", handler)
        result = self.manager.apply_migration("1.0.0")
        
        self.assertTrue(result)
        self.assertEqual(len(self.applied_migrations), 1)
        self.assertEqual(self.manager.get_migration_status("1.0.0"), MigrationStatus.APPLIED)
    
    def test_apply_all(self):
        """测试应用所有迁移"""
        def handler1():
            self.applied_migrations.append("1.0.0")
        
        def handler2():
            self.applied_migrations.append("1.1.0")
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler1)
        self.manager.register_migration("1.1.0", "update", "Update", handler2)
        
        results = self.manager.apply_all()
        
        self.assertTrue(results["1.0.0"])
        self.assertTrue(results["1.1.0"])
        self.assertEqual(len(self.applied_migrations), 2)
    
    def test_rollback_migration(self):
        """测试回滚迁移"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial migration", handler)
        self.manager.apply_migration("1.0.0")
        
        result = self.manager.rollback_migration("1.0.0")
        
        self.assertTrue(result)
        self.assertEqual(self.manager.get_migration_status("1.0.0"), MigrationStatus.ROLLED_BACK)
    
    def test_migration_order(self):
        """测试迁移顺序"""
        order = []
        
        def handler1():
            order.append("1.0.0")
        
        def handler2():
            order.append("2.0.0")
        
        def handler3():
            order.append("1.5.0")
        
        self.manager.register_migration("2.0.0", "major", "Major", handler2)
        self.manager.register_migration("1.0.0", "init", "Initial", handler1)
        self.manager.register_migration("1.5.0", "mid", "Mid", handler3)
        
        self.manager.apply_all()
        
        # 应该按版本排序执行
        self.assertEqual(order, ["1.0.0", "1.5.0", "2.0.0"])
    
    def test_migration_failure(self):
        """测试迁移失败"""
        def handler():
            raise ValueError("Migration failed")
        
        self.manager.register_migration("1.0.0", "init", "Initial migration", handler)
        result = self.manager.apply_migration("1.0.0")
        
        self.assertFalse(result)
        self.assertEqual(self.manager.get_migration_status("1.0.0"), MigrationStatus.FAILED)
    
    def test_get_pending_migrations(self):
        """测试获取待处理迁移"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler)
        self.manager.register_migration("1.1.0", "update", "Update", handler)
        
        # 应用第一个
        self.manager.apply_migration("1.0.0")
        
        pending = self.manager.get_pending_migrations()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["version"], "1.1.0")
    
    def test_get_applied_migrations(self):
        """测试获取已应用迁移"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler)
        self.manager.apply_migration("1.0.0")
        
        applied = self.manager.get_applied_migrations()
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]["version"], "1.0.0")
    
    def test_stats(self):
        """测试统计"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler)
        self.manager.register_migration("1.1.0", "update", "Update", handler)
        self.manager.apply_migration("1.0.0")
        
        stats = self.manager.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["applied"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["failed"], 0)
    
    def test_history_persistence(self):
        """测试历史记录持久化"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler)
        self.manager.apply_migration("1.0.0")
        
        # 创建新的管理器实例，应该加载历史记录
        new_manager = MigrationManager(self.migrations_dir)
        
        # 新实例应该加载了历史记录中的迁移状态
        self.assertEqual(new_manager.get_migration_status("1.0.0"), MigrationStatus.APPLIED)


class TestVersionControl(unittest.TestCase):
    """版本控制测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.version_file = os.path.join(self.temp_dir, "version.json")
        self.vc = VersionControl(self.version_file)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initial_version(self):
        """测试初始版本"""
        self.assertEqual(self.vc.get_version(), "0.0.0")
    
    def test_set_version(self):
        """测试设置版本"""
        self.vc.set_version("1.2.3")
        self.assertEqual(self.vc.get_version(), "1.2.3")
    
    def test_bump_major(self):
        """测试升级主版本"""
        self.vc.set_version("1.2.3")
        new_version = self.vc.bump_major()
        self.assertEqual(new_version, "2.0.0")
    
    def test_bump_minor(self):
        """测试升级次版本"""
        self.vc.set_version("1.2.3")
        new_version = self.vc.bump_minor()
        self.assertEqual(new_version, "1.3.0")
    
    def test_bump_patch(self):
        """测试升级补丁版本"""
        self.vc.set_version("1.2.3")
        new_version = self.vc.bump_patch()
        self.assertEqual(new_version, "1.2.4")
    
    def test_compare_versions(self):
        """测试版本比较"""
        self.assertEqual(self.vc.compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(self.vc.compare_versions("1.0.0", "2.0.0"), -1)
        self.assertEqual(self.vc.compare_versions("2.0.0", "1.0.0"), 1)
        self.assertEqual(self.vc.compare_versions("1.1.0", "1.0.0"), 1)
        self.assertEqual(self.vc.compare_versions("1.0.1", "1.0.0"), 1)
    
    def test_version_persistence(self):
        """测试版本持久化"""
        self.vc.set_version("1.5.0")
        
        # 创建新的版本控制实例
        new_vc = VersionControl(self.version_file)
        self.assertEqual(new_vc.get_version(), "1.5.0")


class TestMigrationAndVersionIntegration(unittest.TestCase):
    """迁移与版本集成测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.migrations_dir = os.path.join(self.temp_dir, "migrations")
        self.version_file = os.path.join(self.temp_dir, "version.json")
        self.manager = MigrationManager(self.migrations_dir)
        self.vc = VersionControl(self.version_file)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_migration_updates_version(self):
        """测试迁移更新版本"""
        def handler():
            pass
        
        self.manager.register_migration("1.0.0", "init", "Initial", handler)
        self.manager.apply_migration("1.0.0")
        
        # 更新版本
        self.vc.set_version("1.0.0")
        self.assertEqual(self.vc.get_version(), "1.0.0")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 46 - 数据迁移与版本控制测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMigrationManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVersionControl))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMigrationAndVersionIntegration))
    
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
