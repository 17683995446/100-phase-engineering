"""
Phase 76 - 多租户架构系统测试
验证租户隔离、资源配额、数据隔离和租户管理功能
"""
import unittest
from src.utils.multi_tenant import (
    TenantManager,
    TenantAwareStorage,
    TenantContext,
    TenantStatus,
    TenantQuota,
    get_tenant_manager,
    get_tenant_storage,
    get_tenant_context
)


class TestTenantManager(unittest.TestCase):
    """租户管理器测试"""

    def setUp(self):
        self.manager = TenantManager()

    def test_create_tenant(self):
        """测试创建租户"""
        tenant = self.manager.create_tenant("t1", "Tenant 1")
        self.assertEqual(tenant.tenant_id, "t1")
        self.assertEqual(tenant.name, "Tenant 1")
        self.assertEqual(tenant.status, TenantStatus.ACTIVE)

    def test_create_duplicate_tenant(self):
        """测试创建重复租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        with self.assertRaises(ValueError):
            self.manager.create_tenant("t1", "Tenant 1")

    def test_get_tenant(self):
        """测试获取租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        tenant = self.manager.get_tenant("t1")
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.name, "Tenant 1")

    def test_update_tenant(self):
        """测试更新租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        result = self.manager.update_tenant("t1", name="Updated")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_tenant("t1").name, "Updated")

    def test_suspend_activate(self):
        """测试暂停和激活"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.suspend_tenant("t1")
        self.assertEqual(self.manager.get_tenant("t1").status, TenantStatus.SUSPENDED)

        self.manager.activate_tenant("t1")
        self.assertEqual(self.manager.get_tenant("t1").status, TenantStatus.ACTIVE)

    def test_delete_tenant(self):
        """测试删除租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.delete_tenant("t1")
        self.assertEqual(self.manager.get_tenant("t1").status, TenantStatus.DELETED)

    def test_list_tenants(self):
        """测试列出租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.create_tenant("t2", "Tenant 2")
        tenants = self.manager.list_tenants()
        self.assertEqual(len(tenants), 2)

    def test_list_by_status(self):
        """测试按状态列出租户"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.create_tenant("t2", "Tenant 2")
        self.manager.suspend_tenant("t2")
        active = self.manager.list_tenants(TenantStatus.ACTIVE)
        self.assertEqual(len(active), 1)

    def test_check_quota(self):
        """测试配额检查"""
        self.manager.create_tenant("t1", "Tenant 1", quota=TenantQuota(max_users=5))
        self.assertTrue(self.manager.check_quota("t1", "users", 3))
        self.assertFalse(self.manager.check_quota("t1", "users", 5))

    def test_check_quota_suspended(self):
        """测试暂停租户配额检查"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.suspend_tenant("t1")
        self.assertFalse(self.manager.check_quota("t1", "users", 1))

    def test_custom_quota(self):
        """测试自定义配额"""
        self.manager.create_tenant("t1", "Tenant 1",
            quota=TenantQuota(custom_limits={"api_calls": 100}))
        self.assertTrue(self.manager.check_quota("t1", "api_calls", 50))
        self.assertFalse(self.manager.check_quota("t1", "api_calls", 100))

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_tenant("t1", "Tenant 1")
        self.manager.create_tenant("t2", "Tenant 2")
        self.manager.suspend_tenant("t2")
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_tenants"], 2)
        self.assertEqual(stats["active"], 1)
        self.assertEqual(stats["suspended"], 1)


class TestTenantAwareStorage(unittest.TestCase):
    """租户感知存储测试"""

    def setUp(self):
        self.storage = TenantAwareStorage()

    def test_set_get(self):
        """测试设置和获取"""
        self.storage.set("t1", "key1", "value1")
        self.assertEqual(self.storage.get("t1", "key1"), "value1")

    def test_tenant_isolation(self):
        """测试租户隔离"""
        self.storage.set("t1", "key1", "value1")
        self.storage.set("t2", "key1", "value2")
        self.assertEqual(self.storage.get("t1", "key1"), "value1")
        self.assertEqual(self.storage.get("t2", "key1"), "value2")

    def test_delete(self):
        """测试删除"""
        self.storage.set("t1", "key1", "value1")
        self.assertTrue(self.storage.delete("t1", "key1"))
        self.assertIsNone(self.storage.get("t1", "key1"))

    def test_get_all(self):
        """测试获取所有数据"""
        self.storage.set("t1", "key1", "value1")
        self.storage.set("t1", "key2", "value2")
        data = self.storage.get_all("t1")
        self.assertEqual(len(data), 2)

    def test_clear_tenant(self):
        """测试清除租户"""
        self.storage.set("t1", "key1", "value1")
        self.storage.clear_tenant("t1")
        self.assertEqual(len(self.storage.get_all("t1")), 0)

    def test_stats(self):
        """测试统计信息"""
        self.storage.set("t1", "key1", "value1")
        self.storage.set("t2", "key1", "value1")
        stats = self.storage.get_stats()
        self.assertEqual(stats["total_tenants"], 2)
        self.assertEqual(stats["total_keys"], 2)


class TestTenantContext(unittest.TestCase):
    """租户上下文测试"""

    def setUp(self):
        self.context = TenantContext()

    def test_set_get(self):
        """测试设置和获取"""
        self.context.set_tenant("t1")
        self.assertEqual(self.context.get_tenant(), "t1")

    def test_clear(self):
        """测试清除"""
        self.context.set_tenant("t1")
        self.context.clear()
        self.assertIsNone(self.context.get_tenant())


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_tenant_manager(self):
        """测试获取全局租户管理器"""
        m1 = get_tenant_manager()
        m2 = get_tenant_manager()
        self.assertIs(m1, m2)

    def test_get_tenant_storage(self):
        """测试获取全局租户存储"""
        s1 = get_tenant_storage()
        s2 = get_tenant_storage()
        self.assertIs(s1, s2)

    def test_get_tenant_context(self):
        """测试获取全局租户上下文"""
        c1 = get_tenant_context()
        c2 = get_tenant_context()
        self.assertIs(c1, c2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 76 - 多租户架构系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTenantManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTenantAwareStorage))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTenantContext))
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
