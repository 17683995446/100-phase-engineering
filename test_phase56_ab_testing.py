"""
Phase 56 - A/B测试框架测试
验证实验创建、分组、指标收集和结果分析功能是否正常工作
"""
import unittest
from src.utils.ab_testing import (
    ABTestingFramework,
    ExperimentStatus,
    get_ab_testing_framework
)


class TestABTestingFramework(unittest.TestCase):
    """A/B测试框架测试"""

    def setUp(self):
        """测试前设置"""
        self.framework = ABTestingFramework()

    def test_create_experiment(self):
        """测试创建实验"""
        experiment = self.framework.create_experiment("exp-1", "Button Color Test")
        self.assertEqual(experiment.experiment_id, "exp-1")
        self.assertEqual(experiment.name, "Button Color Test")
        self.assertEqual(experiment.status, ExperimentStatus.DRAFT)

    def test_add_variant(self):
        """测试添加变体"""
        self.framework.create_experiment("exp-1", "Test")
        result = self.framework.add_variant("exp-1", "control", "Control", 0.5, {"color": "blue"})
        self.assertTrue(result)

        experiment = self.framework.get_experiment("exp-1")
        self.assertEqual(len(experiment.variants), 1)

    def test_start_experiment(self):
        """测试启动实验"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "Variant A", 0.5)
        self.framework.add_variant("exp-1", "b", "Variant B", 0.5)

        result = self.framework.start_experiment("exp-1")
        self.assertTrue(result)
        self.assertEqual(self.framework.get_experiment("exp-1").status, ExperimentStatus.RUNNING)

    def test_stop_experiment(self):
        """测试停止实验"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.start_experiment("exp-1")
        result = self.framework.stop_experiment("exp-1")
        self.assertTrue(result)
        self.assertEqual(self.framework.get_experiment("exp-1").status, ExperimentStatus.COMPLETED)

    def test_assign_variant(self):
        """测试分配变体"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5)
        self.framework.add_variant("exp-1", "b", "B", 0.5)
        self.framework.start_experiment("exp-1")

        variant = self.framework.assign_variant("exp-1", "user-1")
        self.assertIsNotNone(variant)
        self.assertIn(variant, ["a", "b"])

    def test_consistent_assignment(self):
        """测试一致性分配"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5)
        self.framework.add_variant("exp-1", "b", "B", 0.5)
        self.framework.start_experiment("exp-1")

        # 同一用户应该总是分配到同一变体
        variant1 = self.framework.assign_variant("exp-1", "user-1")
        variant2 = self.framework.assign_variant("exp-1", "user-1")
        self.assertEqual(variant1, variant2)

    def test_track_conversion(self):
        """测试跟踪转化"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5)
        self.framework.start_experiment("exp-1")

        self.framework.assign_variant("exp-1", "user-1")
        result = self.framework.track_conversion("exp-1", "user-1")
        self.assertTrue(result)

        experiment = self.framework.get_experiment("exp-1")
        self.assertEqual(experiment.variants["a"].conversions, 1)

    def test_variant_config(self):
        """测试变体配置"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5, {"color": "red"})
        self.framework.start_experiment("exp-1")

        config = self.framework.get_variant_config("exp-1", "user-1")
        self.assertIsNotNone(config)
        self.assertEqual(config["color"], "red")

    def test_experiment_results(self):
        """测试实验结果"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "control", "Control", 0.5)
        self.framework.add_variant("exp-1", "treatment", "Treatment", 0.5)
        self.framework.start_experiment("exp-1")

        # 模拟用户参与
        for i in range(100):
            user_id = f"user-{i}"
            variant = self.framework.assign_variant("exp-1", user_id)
            if i % 2 == 0:
                self.framework.track_conversion("exp-1", user_id)

        results = self.framework.get_experiment_results("exp-1")
        self.assertEqual(results["total_participants"], 100)
        self.assertEqual(results["total_conversions"], 50)
        self.assertIn("control", results["variants"])
        self.assertIn("treatment", results["variants"])

    def test_conversion_rate(self):
        """测试转化率计算"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5)
        self.framework.start_experiment("exp-1")

        for i in range(10):
            self.framework.assign_variant("exp-1", f"user-{i}")
            if i < 3:
                self.framework.track_conversion("exp-1", f"user-{i}")

        results = self.framework.get_experiment_results("exp-1")
        self.assertEqual(results["variants"]["a"]["conversion_rate"], 0.3)

    def test_stats(self):
        """测试统计"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.create_experiment("exp-2", "Test 2")
        self.framework.start_experiment("exp-1")

        stats = self.framework.get_stats()
        self.assertEqual(stats["total_experiments"], 2)
        self.assertEqual(stats["running"], 1)
        self.assertEqual(stats["completed"], 0)

    def test_invalid_experiment(self):
        """测试无效实验"""
        result = self.framework.start_experiment("nonexistent")
        self.assertFalse(result)

    def test_not_running_experiment(self):
        """测试未运行实验"""
        self.framework.create_experiment("exp-1", "Test")
        self.framework.add_variant("exp-1", "a", "A", 0.5)
        # 不启动实验

        variant = self.framework.assign_variant("exp-1", "user-1")
        self.assertIsNone(variant)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_ab_testing_framework(self):
        """测试获取全局框架"""
        f1 = get_ab_testing_framework()
        f2 = get_ab_testing_framework()
        self.assertIs(f1, f2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 56 - A/B测试框架测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestABTestingFramework))
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
