"""
Phase 75 - 灰度发布系统测试
验证流量分配、版本切换、回滚和渐进式发布功能
"""
import unittest
from src.utils.canary_release import (
    CanaryReleaseManager,
    ReleaseStrategy,
    ReleaseStatus,
    TrafficRouter,
    ReleaseVersion,
    get_canary_manager
)


class TestTrafficRouter(unittest.TestCase):
    """流量路由器测试"""

    def setUp(self):
        self.router = TrafficRouter()
        self.versions = [
            ReleaseVersion("v1", weight=0.7),
            ReleaseVersion("v2", weight=0.3)
        ]

    def test_route_hash(self):
        """测试哈希路由"""
        result = self.router.route("user1", self.versions, ReleaseStrategy.HASH)
        self.assertIn(result, ["v1", "v2"])

    def test_route_user_id(self):
        """测试用户ID路由"""
        result1 = self.router.route("user1", self.versions, ReleaseStrategy.USER_ID)
        result2 = self.router.route("user1", self.versions, ReleaseStrategy.USER_ID)
        self.assertEqual(result1, result2)

    def test_route_empty_versions(self):
        """测试空版本列表"""
        result = self.router.route("key", [], ReleaseStrategy.HASH)
        self.assertIsNone(result)

    def test_route_inactive_versions(self):
        """测试非活动版本"""
        versions = [ReleaseVersion("v1", weight=1.0, status=ReleaseStatus.ROLLED_BACK)]
        result = self.router.route("key", versions, ReleaseStrategy.HASH)
        self.assertIsNone(result)


class TestCanaryReleaseManager(unittest.TestCase):
    """灰度发布管理器测试"""

    def setUp(self):
        self.manager = CanaryReleaseManager()

    def test_create_plan(self):
        """测试创建计划"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        self.assertIsNotNone(plan.plan_id)
        self.assertEqual(plan.name, "test")
        self.assertEqual(len(plan.versions), 2)
        self.assertEqual(plan.status, ReleaseStatus.PENDING)

    def test_start_plan(self):
        """测试开始计划"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        result = self.manager.start_plan(plan.plan_id)
        self.assertTrue(result)

        plan = self.manager.get_plan(plan.plan_id)
        self.assertEqual(plan.status, ReleaseStatus.RUNNING)

    def test_advance_step(self):
        """测试推进步骤"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        self.manager.start_plan(plan.plan_id)

        result = self.manager.advance_step(plan.plan_id)
        self.assertTrue(result)

        plan = self.manager.get_plan(plan.plan_id)
        self.assertEqual(plan.current_step, 1)
        self.assertEqual(plan.versions[1].weight, 0.1)

    def test_rollback(self):
        """测试回滚"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        self.manager.start_plan(plan.plan_id)
        self.manager.advance_step(plan.plan_id)

        result = self.manager.rollback(plan.plan_id)
        self.assertTrue(result)

        plan = self.manager.get_plan(plan.plan_id)
        self.assertEqual(plan.status, ReleaseStatus.ROLLED_BACK)
        self.assertEqual(plan.versions[0].weight, 1.0)

    def test_route(self):
        """测试路由"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        self.manager.start_plan(plan.plan_id)

        version = self.manager.route(plan.plan_id, "user1")
        self.assertIn(version, ["v1", "v2"])

    def test_route_not_running(self):
        """测试未运行计划的路由"""
        plan = self.manager.create_plan("test", ["v1", "v2"])
        result = self.manager.route(plan.plan_id, "user1")
        self.assertIsNone(result)

    def test_delete_plan(self):
        """测试删除计划"""
        plan = self.manager.create_plan("test", ["v1"])
        result = self.manager.delete_plan(plan.plan_id)
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_plan(plan.plan_id))

    def test_list_plans(self):
        """测试列出计划"""
        self.manager.create_plan("test1", ["v1"])
        self.manager.create_plan("test2", ["v2"])
        plans = self.manager.list_plans()
        self.assertEqual(len(plans), 2)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_plan("test", ["v1"])
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_plans"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_canary_manager(self):
        """测试获取全局管理器"""
        m1 = get_canary_manager()
        m2 = get_canary_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 75 - 灰度发布系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTrafficRouter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCanaryReleaseManager))
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
