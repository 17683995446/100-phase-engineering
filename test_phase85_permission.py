"""
Phase 85 - 权限管理系统测试
验证权限定义、角色分配、资源访问控制和权限校验功能
"""
import unittest
from src.utils.permission_manager import (
    PermissionManager,
    Permission,
    PermissionType,
    Role,
    get_permission_manager
)


class TestPermissionManager(unittest.TestCase):
    """权限管理器测试"""

    def setUp(self):
        self.manager = PermissionManager()

    def test_create_role(self):
        """测试创建角色"""
        role = self.manager.create_role("admin", "Administrator")
        self.assertEqual(role.role_id, "admin")
        self.assertEqual(role.name, "Administrator")

    def test_create_duplicate_role(self):
        """测试创建重复角色"""
        self.manager.create_role("admin", "Administrator")
        with self.assertRaises(ValueError):
            self.manager.create_role("admin", "Admin")

    def test_add_permission(self):
        """测试添加权限"""
        self.manager.create_role("editor", "Editor")
        perm = Permission("articles", PermissionType.CREATE)
        result = self.manager.add_permission_to_role("editor", perm)
        self.assertTrue(result)
        role = self.manager.get_role("editor")
        self.assertIn(perm, role.permissions)

    def test_remove_permission(self):
        """测试移除权限"""
        self.manager.create_role("editor", "Editor")
        perm = Permission("articles", PermissionType.CREATE)
        self.manager.add_permission_to_role("editor", perm)
        result = self.manager.remove_permission_from_role("editor", perm)
        self.assertTrue(result)
        role = self.manager.get_role("editor")
        self.assertNotIn(perm, role.permissions)

    def test_assign_role(self):
        """测试分配角色"""
        self.manager.create_role("viewer", "Viewer")
        result = self.manager.assign_role_to_user("user1", "viewer")
        self.assertTrue(result)
        roles = self.manager.get_user_roles("user1")
        self.assertEqual(len(roles), 1)

    def test_assign_nonexistent_role(self):
        """测试分配不存在的角色"""
        result = self.manager.assign_role_to_user("user1", "nonexistent")
        self.assertFalse(result)

    def test_revoke_role(self):
        """测试撤销角色"""
        self.manager.create_role("viewer", "Viewer")
        self.manager.assign_role_to_user("user1", "viewer")
        result = self.manager.revoke_role_from_user("user1", "viewer")
        self.assertTrue(result)
        roles = self.manager.get_user_roles("user1")
        self.assertEqual(len(roles), 0)

    def test_check_permission(self):
        """测试权限检查"""
        self.manager.create_role("editor", "Editor")
        self.manager.add_permission_to_role("editor", Permission("articles", PermissionType.CREATE))
        self.manager.assign_role_to_user("user1", "editor")
        self.assertTrue(self.manager.check_permission("user1", "articles", PermissionType.CREATE))
        self.assertFalse(self.manager.check_permission("user1", "articles", PermissionType.DELETE))

    def test_admin_permission(self):
        """测试管理员权限"""
        self.manager.create_role("super", "Super Admin")
        self.manager.add_permission_to_role("super", Permission("*", PermissionType.ADMIN))
        self.manager.assign_role_to_user("admin1", "super")
        self.assertTrue(self.manager.check_permission("admin1", "anything", PermissionType.DELETE))

    def test_check_any_permission(self):
        """测试任意权限检查"""
        self.manager.create_role("editor", "Editor")
        self.manager.add_permission_to_role("editor", Permission("articles", PermissionType.CREATE))
        self.manager.assign_role_to_user("user1", "editor")
        perms = [Permission("articles", PermissionType.CREATE), Permission("articles", PermissionType.DELETE)]
        self.assertTrue(self.manager.check_any_permission("user1", perms))

    def test_check_all_permissions(self):
        """测试所有权限检查"""
        self.manager.create_role("editor", "Editor")
        self.manager.add_permission_to_role("editor", Permission("articles", PermissionType.CREATE))
        self.manager.add_permission_to_role("editor", Permission("articles", PermissionType.UPDATE))
        self.manager.assign_role_to_user("user1", "editor")
        perms = [Permission("articles", PermissionType.CREATE), Permission("articles", PermissionType.UPDATE)]
        self.assertTrue(self.manager.check_all_permissions("user1", perms))

    def test_delete_role(self):
        """测试删除角色"""
        self.manager.create_role("temp", "Temp")
        self.manager.assign_role_to_user("user1", "temp")
        result = self.manager.delete_role("temp")
        self.assertTrue(result)
        self.assertEqual(len(self.manager.get_user_roles("user1")), 0)

    def test_list_roles(self):
        """测试列出角色"""
        self.manager.create_role("admin", "Admin")
        self.manager.create_role("user", "User")
        roles = self.manager.list_roles()
        self.assertEqual(len(roles), 2)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_role("admin", "Admin")
        self.manager.assign_role_to_user("user1", "admin")
        self.manager.assign_role_to_user("user2", "admin")
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_roles"], 1)
        self.assertEqual(stats["total_user_assignments"], 2)


class TestPermission(unittest.TestCase):
    """权限测试"""

    def test_equality(self):
        """测试相等性"""
        p1 = Permission("articles", PermissionType.CREATE)
        p2 = Permission("articles", PermissionType.CREATE)
        self.assertEqual(p1, p2)

    def test_hash(self):
        """测试哈希"""
        p1 = Permission("articles", PermissionType.CREATE)
        p2 = Permission("articles", PermissionType.CREATE)
        self.assertEqual(hash(p1), hash(p2))


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_permission_manager(self):
        """测试获取全局权限管理器"""
        m1 = get_permission_manager()
        m2 = get_permission_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 85 - 权限管理系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissionManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermission))
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
