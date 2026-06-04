"""
Phase 42 - 数据库连接池与ORM集成测试
验证数据库功能是否正常工作
"""
import os
import tempfile
import unittest
from typing import Optional
from datetime import datetime

from src.utils.database import (
    ConnectionPool,
    ConnectionPoolConfig,
    Model,
    DatabaseManager,
    get_database_manager
)


class TestUser(Model):
    """测试用户模型"""
    _table_name = "test_users"
    
    id: Optional[int] = None
    name: str = ""
    email: str = ""
    age: int = 0
    created_at: Optional[str] = None


class TestConnectionPool(unittest.TestCase):
    """连接池测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.pool = ConnectionPool(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        self.pool.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_execute_query(self):
        """测试执行查询"""
        # 创建表
        self.pool.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # 插入数据
        self.pool.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))
        
        # 查询数据
        results = self.pool.execute("SELECT * FROM test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "test_name")
    
    def test_pool_stats(self):
        """测试连接池统计"""
        stats = self.pool.get_stats()
        self.assertEqual(stats["database_path"], self.db_path)
        self.assertFalse(stats["closed"])
    
    def test_multiple_connections(self):
        """测试多个连接"""
        # 创建多个连接
        conn1 = self.pool._acquire_connection()
        conn2 = self.pool._acquire_connection()
        
        # 验证连接有效
        conn1.execute("SELECT 1")
        conn2.execute("SELECT 1")
        
        # 释放连接
        self.pool._release_connection(conn1)
        self.pool._release_connection(conn2)


class TestORM(unittest.TestCase):
    """ORM测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_orm.db")
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.register_model(TestUser)
        self.db_manager.create_all_tables()
    
    def tearDown(self):
        """测试后清理"""
        self.db_manager.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_create_table(self):
        """测试创建表"""
        # 表应该已经创建
        results = self.db_manager.pool.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_users'"
        )
        self.assertEqual(len(results), 1)
    
    def test_save(self):
        """测试保存记录"""
        user = TestUser(name="John", email="john@example.com", age=25)
        user.save()
        
        self.assertIsNotNone(user.id)
        self.assertGreater(user.id, 0)
    
    def test_find_by_id(self):
        """测试根据ID查找"""
        # 先保存一个用户
        user = TestUser(name="Jane", email="jane@example.com", age=30)
        user.save()
        
        # 查找
        found = TestUser.find_by_id(user.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Jane")
        self.assertEqual(found.email, "jane@example.com")
    
    def test_find_all(self):
        """测试查找所有记录"""
        # 保存多个用户
        for i in range(5):
            user = TestUser(name=f"User{i}", email=f"user{i}@example.com", age=20 + i)
            user.save()
        
        # 查找所有
        users = TestUser.find_all()
        self.assertEqual(len(users), 5)
    
    def test_find_by(self):
        """测试条件查找"""
        # 保存用户
        user1 = TestUser(name="Alice", email="alice@example.com", age=25)
        user1.save()
        user2 = TestUser(name="Bob", email="bob@example.com", age=30)
        user2.save()
        
        # 按条件查找
        results = TestUser.find_by(age=25)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")
    
    def test_update(self):
        """测试更新记录"""
        # 保存用户
        user = TestUser(name="Original", email="original@example.com", age=20)
        user.save()
        
        # 更新
        user.name = "Updated"
        user.update()
        
        # 验证更新
        updated = TestUser.find_by_id(user.id)
        self.assertEqual(updated.name, "Updated")
    
    def test_delete(self):
        """测试删除记录"""
        # 保存用户
        user = TestUser(name="ToDelete", email="delete@example.com", age=20)
        user.save()
        
        # 删除
        user.delete()
        
        # 验证删除
        found = TestUser.find_by_id(user.id)
        self.assertIsNone(found)
    
    def test_count(self):
        """测试记录数"""
        # 保存多个用户
        for i in range(3):
            user = TestUser(name=f"User{i}", email=f"user{i}@example.com", age=20)
            user.save()
        
        # 获取记录数
        count = TestUser.count()
        self.assertEqual(count, 3)
    
    def test_to_dict(self):
        """测试转换为字典"""
        user = TestUser(name="DictTest", email="dict@example.com", age=25)
        user.save()
        
        user_dict = user.to_dict()
        self.assertEqual(user_dict["name"], "DictTest")
        self.assertEqual(user_dict["email"], "dict@example.com")


class TestDatabaseManager(unittest.TestCase):
    """数据库管理器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_manager.db")
        self.db_manager = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        self.db_manager.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_register_model(self):
        """测试注册模型"""
        self.db_manager.register_model(TestUser)
        self.assertEqual(len(self.db_manager._models), 1)
    
    def test_get_stats(self):
        """测试获取统计"""
        self.db_manager.register_model(TestUser)
        stats = self.db_manager.get_stats()
        
        self.assertEqual(stats["database_path"], self.db_path)
        self.assertEqual(stats["registered_models"], 1)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 42 - 数据库连接池与ORM集成测试")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionPool))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestORM))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDatabaseManager))
    
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
