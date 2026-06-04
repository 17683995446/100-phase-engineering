"""
Phase 86 - 角色管理系统测试
验证角色定义、继承、层级和动态权限功能
"""
import unittest
from src.utils.role_manager import (
    RoleManager,
    RoleDefinition,
    get_role_manager
)
from src.utils.permission_manager import Permission, PermissionType


class TestRoleManager(unittest.TestCase):
    """角色管理器测试"""

    def setUp(self):
        self.manager = RoleManager()

    def test_create_role(self):
        """测试创建角色"""
        role = self.manager.create_role("admin", "Administrator")
        self.assertEqual(role.role_id, "admin")
        self.assertEqual(role.name, "Administrator")

    def test_create_role_with_parent(self):
        """测试创建带父角色"""
        self.manager.create_role("base", "Base Role")
        role = self.manager.create_role("derived", "Derived", parent_roles=["base"])
        self.assertEqual(role.parent_roles, ["base"])

    def test_create_role_nonexistent_parent(self):
        """测试创建不存在的父角色"""
        with self.assertRaises(ValueError):
            self.manager.create_role("derived", "Derived", parent_roles=["nonexistent"])

    def test_create_duplicate(self):
        """测试创建重复角色"""
        self.manager.create_role("admin", "Administrator")
        with self.assertRaises(ValueError):
            self.manager.create_role("admin", "Admin")

    def test_update_role(self):
        """测试更新角色"""
        self.manager.create_role("admin", "Administrator")
        result = self.manager.update_role("admin", description="Updated")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_role("admin").description, "Updated")

    def test_delete_role(self):
        """测试删除角色"""
        self.manager.create_role("temp", "Temp")
        result = self.manager.delete_role("temp")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_role("temp"))

    def test_delete_role_with_children(self):
        """测试删除有子角色的角色"""
        self.manager.create_role("base", "Base")
        self.manager.create_role("derived", "Derived", parent_roles=["base"])
        with self.assertRaises(ValueError):
            self.manager.delete_role("base")

    def test_add_parent_role(self):
        """测试添加父角色"""
        self.manager.create_role("base", "Base")
        self.manager.create_role("derived", "Derived")
        result = self.manager.add_parent_role("derived", "base")
        self.assertTrue(result)

    def test_add_parent_cycle(self):
        """测试添加父角色循环"""
        self.manager.create_role("a", "A")
        self.manager.create_role("b", "B")
        self.manager.add_parent_role("b", "a")
        with self.assertRaises(ValueError):
            self.manager.add_parent_role("a", "b")

    def test_remove_parent_role(self):
        """测试移除父角色"""
        self.manager.create_role("base", "Base")
        self.manager.create_role("derived", "Derived", parent_roles=["base"])
        result = self.manager.remove_parent_role("derived", "base")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_role("derived").parent_roles, [])

    def test_add_permission(self):
        """测试添加权限"""
        self.manager.create_role("editor", "Editor")
        perm = Permission("articles", PermissionType.CREATE)
        result = self.manager.add_permission("editor", perm)
        self.assertTrue(result)
        self.assertIn(perm, self.manager.get_role("editor").permissions)

    def test_get_effective_permissions(self):
        """测试获取有效权限"""
        self.manager.create_role("base", "Base",
            permissions=[Permission("articles", PermissionType.READ)])
        self.manager.create_role("editor", "Editor",
            parent_roles=["base"],
            permissions=[Permission("articles", PermissionType.CREATE)])
        perms = self.manager.get_effective_permissions("editor")
        self.assertEqual(len(perms), 2)

    def test_get_role_hierarchy(self):
        """测试获取角色层级"""
        self.manager.create_role("grandparent", "Grandparent")
        self.manager.create_role("parent", "Parent", parent_roles=["grandparent"])
        self.manager.create_role("child", "Child", parent_roles=["parent"])
        hierarchy = self.manager.get_role_hierarchy("child")
        self.assertEqual(len(hierarchy), 3)
        self.assertEqual(hierarchy[0], "child")

    def test_get_child_roles(self):
        """测试获取子角色"""
        self.manager.create_role("base", "Base")
        self.manager.create_role("derived1", "Derived1", parent_roles=["base"])
        self.manager.create_role("derived2", "Derived2", parent_roles=["base"])
        children = self.manager.get_child_roles("base")
        self.assertEqual(len(children), 2)

    def test_list_roles(self):
        """测试列出角色"""
        self.manager.create_role("admin", "Admin")
        self.manager.create_role("user", "User")
        roles = self.manager.list_roles()
        self.assertEqual(len(roles), 2)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_role("base", "Base")
        self.manager.create_role("derived", "Derived", parent_roles=["base"])
        self.manager.add_permission("derived", Permission("res", PermissionType.READ))
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_roles"], 2)
        self.assertEqual(stats["roles_with_parents"], 1)
        self.assertEqual(stats["total_permissions"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_role_manager(self):
        """测试获取全局角色管理器"""
        m1 = get_role_manager()
        m2 = get_role_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 86 - 角色管理系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRoleManager))
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
