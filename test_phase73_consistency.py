"""
Phase 73 - 数据一致性校验系统测试
验证数据校验、差异检测、修复建议和一致性报告功能
"""
import unittest
from src.utils.consistency_checker import (
    ConsistencyChecker,
    DataReconciler,
    DataHasher,
    DiffEngine,
    CheckStatus,
    get_consistency_checker,
    get_data_reconciler
)


class TestDataHasher(unittest.TestCase):
    """数据哈希器测试"""

    def test_hash_dict(self):
        """测试字典哈希"""
        hasher = DataHasher()
        hash1 = hasher.hash_dict({"a": 1, "b": 2})
        hash2 = hasher.hash_dict({"b": 2, "a": 1})
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_hash_list(self):
        """测试列表哈希"""
        hasher = DataHasher()
        hash1 = hasher.hash_list([1, 2, 3])
        hash2 = hasher.hash_list([1, 2, 3])
        self.assertEqual(hash1, hash2)


class TestDiffEngine(unittest.TestCase):
    """差异检测引擎测试"""

    def test_compare_identical_dicts(self):
        """测试相同字典"""
        engine = DiffEngine()
        diffs = engine.compare_dicts({"a": 1}, {"a": 1})
        self.assertEqual(len(diffs), 0)

    def test_compare_missing_key(self):
        """测试缺失键"""
        engine = DiffEngine()
        diffs = engine.compare_dicts({"a": 1}, {"a": 1, "b": 2})
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].diff_type, "extra")

    def test_compare_mismatch(self):
        """测试值不匹配"""
        engine = DiffEngine()
        diffs = engine.compare_dicts({"a": 1}, {"a": 2})
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].diff_type, "mismatch")

    def test_compare_nested(self):
        """测试嵌套字典"""
        engine = DiffEngine()
        diffs = engine.compare_dicts(
            {"a": {"b": 1}},
            {"a": {"b": 2}}
        )
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].field, "a.b")

    def test_compare_lists(self):
        """测试列表比较"""
        engine = DiffEngine()
        diffs = engine.compare_lists([1, 2], [1, 3])
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].diff_type, "mismatch")


class TestConsistencyChecker(unittest.TestCase):
    """一致性校验器测试"""

    def setUp(self):
        self.checker = ConsistencyChecker()

    def test_register_and_run_check(self):
        """测试注册和运行检查"""
        self.checker.register_check("check1", "Test Check", lambda: (True, "OK", {}))
        result = self.checker.run_check("check1")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, CheckStatus.PASSED)

    def test_run_failed_check(self):
        """测试失败检查"""
        self.checker.register_check("check2", "Fail Check", lambda: (False, "Failed", {}))
        result = self.checker.run_check("check2")
        self.assertEqual(result.status, CheckStatus.FAILED)

    def test_run_all_checks(self):
        """测试运行所有检查"""
        self.checker.register_check("c1", "Check 1", lambda: (True, "OK", {}))
        self.checker.register_check("c2", "Check 2", lambda: (False, "Fail", {}))
        report = self.checker.run_all_checks()
        self.assertEqual(report.total_checks, 2)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)

    def test_unregister_check(self):
        """测试注销检查"""
        self.checker.register_check("c3", "Check 3", lambda: (True, "OK", {}))
        self.assertTrue(self.checker.unregister_check("c3"))
        self.assertIsNone(self.checker.run_check("c3"))

    def test_compare_data(self):
        """测试数据比较"""
        diffs = self.checker.compare_data({"a": 1}, {"a": 2})
        self.assertEqual(len(diffs), 1)

    def test_verify_checksum(self):
        """测试校验和验证"""
        data = {"a": 1, "b": 2}
        checksum = self.checker.generate_checksum(data)
        self.assertTrue(self.checker.verify_checksum(data, checksum))
        self.assertFalse(self.checker.verify_checksum({"a": 2}, checksum))

    def test_get_registered_checks(self):
        """测试获取已注册检查"""
        self.checker.register_check("c4", "Check 4", lambda: (True, "OK", {}))
        checks = self.checker.get_registered_checks()
        self.assertIn("c4", checks)

    def test_stats(self):
        """测试统计信息"""
        self.checker.register_check("c5", "Check 5", lambda: (True, "OK", {}))
        stats = self.checker.get_stats()
        self.assertEqual(stats["registered_checks"], 1)


class TestDataReconciler(unittest.TestCase):
    """数据协调器测试"""

    def setUp(self):
        self.reconciler = DataReconciler()

    def test_reconcile_source_wins(self):
        """测试源优先策略"""
        result = self.reconciler.reconcile(
            {"a": 1, "b": 2},
            {"a": 2, "c": 3},
            strategy="source_wins"
        )
        self.assertEqual(result["a"], 1)
        self.assertNotIn("c", result)

    def test_reconcile_target_wins(self):
        """测试目标优先策略"""
        result = self.reconciler.reconcile(
            {"a": 1, "b": 2},
            {"a": 2, "c": 3},
            strategy="target_wins"
        )
        self.assertEqual(result["a"], 2)
        self.assertEqual(result["c"], 3)

    def test_reconcile_merge(self):
        """测试合并策略"""
        result = self.reconciler.reconcile(
            {"a": 1, "b": 2},
            {"c": 3},
            strategy="merge"
        )
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["c"], 3)

    def test_reconcile_nested_merge(self):
        """测试嵌套合并"""
        result = self.reconciler.reconcile(
            {"a": {"x": 1}},
            {"a": {"y": 2}},
            strategy="merge"
        )
        self.assertEqual(result["a"]["x"], 1)
        self.assertEqual(result["a"]["y"], 2)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_consistency_checker(self):
        """测试获取全局校验器"""
        c1 = get_consistency_checker()
        c2 = get_consistency_checker()
        self.assertIs(c1, c2)

    def test_get_data_reconciler(self):
        """测试获取全局协调器"""
        r1 = get_data_reconciler()
        r2 = get_data_reconciler()
        self.assertIs(r1, r2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 73 - 数据一致性校验系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataHasher))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDiffEngine))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConsistencyChecker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataReconciler))
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
