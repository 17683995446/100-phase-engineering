"""
Phase 84 - 用户中心系统测试
验证用户注册、认证、资料管理和账户安全功能
"""
import unittest
from src.utils.user_center import (
    UserCenter,
    UserProfile,
    UserStatus,
    AccountType,
    PasswordHasher,
    get_user_center
)


class TestPasswordHasher(unittest.TestCase):
    """密码哈希器测试"""

    def test_hash(self):
        """测试哈希"""
        hash1 = PasswordHasher.hash("password123")
        self.assertEqual(len(hash1), 64)

    def test_verify(self):
        """测试验证"""
        hash_value = PasswordHasher.hash("password123")
        self.assertTrue(PasswordHasher.verify("password123", hash_value))


class TestUserCenter(unittest.TestCase):
    """用户中心测试"""

    def setUp(self):
        self.center = UserCenter()

    def test_register(self):
        """测试注册"""
        user = self.center.register("u1", "alice", "alice@example.com", "pass123")
        self.assertEqual(user.user_id, "u1")
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.status, UserStatus.ACTIVE)

    def test_register_duplicate_user_id(self):
        """测试重复用户ID"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        with self.assertRaises(ValueError):
            self.center.register("u1", "bob", "bob@example.com", "pass123")

    def test_register_duplicate_username(self):
        """测试重复用户名"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        with self.assertRaises(ValueError):
            self.center.register("u2", "alice", "bob@example.com", "pass123")

    def test_register_duplicate_email(self):
        """测试重复邮箱"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        with self.assertRaises(ValueError):
            self.center.register("u2", "bob", "alice@example.com", "pass123")

    def test_authenticate(self):
        """测试认证"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        user = self.center.authenticate("alice", "pass123")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "u1")
        self.assertIsNotNone(user.last_login)

    def test_authenticate_wrong_password(self):
        """测试错误密码"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        user = self.center.authenticate("alice", "wrong")
        self.assertIsNone(user)

    def test_authenticate_inactive(self):
        """测试非活跃用户"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        self.center.update_status("u1", UserStatus.SUSPENDED)
        user = self.center.authenticate("alice", "pass123")
        self.assertIsNone(user)

    def test_get_user(self):
        """测试获取用户"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        user = self.center.get_user("u1")
        self.assertIsNotNone(user)

    def test_get_user_by_username(self):
        """测试通过用户名获取"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        user = self.center.get_user_by_username("alice")
        self.assertIsNotNone(user)

    def test_get_user_by_email(self):
        """测试通过邮箱获取"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        user = self.center.get_user_by_email("alice@example.com")
        self.assertIsNotNone(user)

    def test_update_profile(self):
        """测试更新资料"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        profile = UserProfile(display_name="Alice Smith", bio="Hello")
        result = self.center.update_profile("u1", profile)
        self.assertTrue(result)
        self.assertEqual(self.center.get_user("u1").profile.display_name, "Alice Smith")

    def test_update_status(self):
        """测试更新状态"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        result = self.center.update_status("u1", UserStatus.SUSPENDED)
        self.assertTrue(result)
        self.assertEqual(self.center.get_user("u1").status, UserStatus.SUSPENDED)

    def test_change_password(self):
        """测试修改密码"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        result = self.center.change_password("u1", "pass123", "newpass")
        self.assertTrue(result)

    def test_change_password_wrong_old(self):
        """测试修改密码错误旧密码"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        result = self.center.change_password("u1", "wrong", "newpass")
        self.assertFalse(result)

    def test_upgrade_account(self):
        """测试升级账户"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        result = self.center.upgrade_account("u1", AccountType.PREMIUM)
        self.assertTrue(result)
        self.assertEqual(self.center.get_user("u1").account_type, AccountType.PREMIUM)

    def test_list_users(self):
        """测试列出用户"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        self.center.register("u2", "bob", "bob@example.com", "pass123")
        users = self.center.list_users()
        self.assertEqual(len(users), 2)

    def test_list_by_status(self):
        """测试按状态列出"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        self.center.update_status("u1", UserStatus.SUSPENDED)
        users = self.center.list_users(status=UserStatus.ACTIVE)
        self.assertEqual(len(users), 0)

    def test_list_by_account_type(self):
        """测试按账户类型列出"""
        self.center.register("u1", "alice", "alice@example.com", "pass123",
                             account_type=AccountType.PREMIUM)
        users = self.center.list_users(account_type=AccountType.PREMIUM)
        self.assertEqual(len(users), 1)

    def test_delete_user(self):
        """测试删除用户"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        result = self.center.delete_user("u1")
        self.assertTrue(result)
        self.assertIsNone(self.center.get_user("u1"))

    def test_stats(self):
        """测试统计信息"""
        self.center.register("u1", "alice", "alice@example.com", "pass123")
        self.center.register("u2", "bob", "bob@example.com", "pass123",
                             account_type=AccountType.PREMIUM)
        stats = self.center.get_stats()
        self.assertEqual(stats["total_users"], 2)
        self.assertEqual(stats["active_users"], 2)
        self.assertEqual(stats["by_account_type"]["premium"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_user_center(self):
        """测试获取全局用户中心"""
        c1 = get_user_center()
        c2 = get_user_center()
        self.assertIs(c1, c2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 84 - 用户中心系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPasswordHasher))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestUserCenter))
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
