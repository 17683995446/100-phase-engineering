"""
Phase 99 - 数据治理平台测试
"""
import unittest
from src.utils.data_governance import (
    DataGovernancePlatform, DataClassification, DataQualityStatus,
    RuleType, get_data_governance_platform
)


class TestDataGovernancePlatform(unittest.TestCase):
    """数据治理平台测试"""

    def setUp(self):
        self.platform = DataGovernancePlatform()

    def test_register_asset(self):
        """测试注册数据资产"""
        asset = self.platform.register_asset(
            "users", "Users Table", "postgres",
            classification=DataClassification.CONFIDENTIAL,
            owner="admin"
        )
        self.assertEqual(asset.asset_id, "users")
        self.assertEqual(asset.classification, DataClassification.CONFIDENTIAL)

    def test_register_duplicate_asset(self):
        """测试注册重复资产"""
        self.platform.register_asset("users", "Users", "db")
        with self.assertRaises(ValueError):
            self.platform.register_asset("users", "Users2", "db")

    def test_list_assets(self):
        """测试列出资产"""
        self.platform.register_asset("a1", "A1", "db", tags=["core"])
        self.platform.register_asset("a2", "A2", "db", tags=["core"])
        core_assets = self.platform.list_assets(tag="core")
        self.assertEqual(len(core_assets), 2)

    def test_list_assets_by_classification(self):
        """测试按分类列出资产"""
        self.platform.register_asset("a1", "A1", "db", classification=DataClassification.PUBLIC)
        self.platform.register_asset("a2", "A2", "db", classification=DataClassification.CONFIDENTIAL)
        public = self.platform.list_assets(classification="public")
        self.assertEqual(len(public), 1)

    def test_delete_asset(self):
        """测试删除资产"""
        self.platform.register_asset("users", "Users", "db")
        self.assertTrue(self.platform.delete_asset("users"))
        self.assertIsNone(self.platform.get_asset("users"))

    def test_add_lineage(self):
        """测试添加血缘"""
        lineage = self.platform.add_lineage("raw", "cleaned", "ETL")
        self.assertEqual(lineage.source_asset_id, "raw")
        self.assertEqual(lineage.target_asset_id, "cleaned")

    def test_get_lineage(self):
        """测试获取血缘"""
        self.platform.add_lineage("raw", "cleaned", "ETL")
        self.platform.add_lineage("cleaned", "analytics", "AGG")
        result = self.platform.get_lineage("cleaned")
        self.assertEqual(len(result["upstream"]), 1)
        self.assertEqual(len(result["downstream"]), 1)

    def test_create_rule(self):
        """测试创建质量规则"""
        self.platform.register_asset("users", "Users", "db")
        rule = self.platform.create_rule(
            "not_null", "Not Null",
            RuleType.VALIDITY, "users", "not_null"
        )
        self.assertEqual(rule.rule_id, "not_null")
        self.assertEqual(rule.rule_type, RuleType.VALIDITY)

    def test_create_duplicate_rule(self):
        """测试创建重复规则"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule("r1", "R1", RuleType.VALIDITY, "users", "x")
        with self.assertRaises(ValueError):
            self.platform.create_rule("r1", "R2", RuleType.VALIDITY, "users", "y")

    def test_evaluate_rule_completeness(self):
        """测试评估完整性规则"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule(
            "complete", "Complete",
            RuleType.COMPLETENESS, "users", ""
        )
        report = self.platform.evaluate_rule("complete", [1, 2, 3])
        self.assertEqual(report.status, DataQualityStatus.PASS)
        self.assertEqual(report.score, 1.0)

    def test_evaluate_rule_uniqueness(self):
        """测试评估唯一性规则"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule(
            "unique", "Unique",
            RuleType.UNIQUENESS, "users", "", threshold=1.0
        )
        report = self.platform.evaluate_rule("unique", [1, 1, 2])
        self.assertEqual(report.status, DataQualityStatus.FAIL)
        self.assertLess(report.score, 1.0)

    def test_evaluate_rule_validity(self):
        """测试评估有效性规则"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule(
            "positive", "Positive",
            RuleType.VALIDITY, "users", "positive"
        )
        report = self.platform.evaluate_rule("positive", 5)
        self.assertEqual(report.status, DataQualityStatus.PASS)

        report2 = self.platform.evaluate_rule("positive", -1)
        self.assertEqual(report2.status, DataQualityStatus.FAIL)

    def test_evaluate_asset(self):
        """测试评估资产"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule("r1", "R1", RuleType.COMPLETENESS, "users", "")
        self.platform.create_rule("r2", "R2", RuleType.VALIDITY, "users", "not_null")
        reports = self.platform.evaluate_asset("users", [1, 2, 3])
        self.assertEqual(len(reports), 2)

    def test_get_reports(self):
        """测试获取报告"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule("r1", "R1", RuleType.COMPLETENESS, "users", "")
        self.platform.evaluate_rule("r1", [1, 2])
        reports = self.platform.get_reports("users")
        self.assertEqual(len(reports), 1)

    def test_create_policy(self):
        """测试创建合规策略"""
        policy = self.platform.create_policy(
            "gdpr", "GDPR Policy", "GDPR",
            requirements=["consent", "right_to_deletion"]
        )
        self.assertEqual(policy.policy_id, "gdpr")
        self.assertEqual(len(policy.requirements), 2)

    def test_list_policies(self):
        """测试列出策略"""
        self.platform.create_policy("p1", "P1", "REG1")
        self.platform.create_policy("p2", "P2", "REG2")
        policies = self.platform.list_policies()
        self.assertEqual(len(policies), 2)

    def test_check_compliance_pass(self):
        """测试合规检查通过"""
        self.platform.register_asset(
            "users", "Users", "db",
            classification=DataClassification.CONFIDENTIAL,
            owner="admin"
        )
        result = self.platform.check_compliance("users")
        self.assertTrue(result["compliant"])

    def test_check_compliance_fail_no_owner(self):
        """测试合规检查失败：无所有者"""
        self.platform.register_asset(
            "users", "Users", "db",
            classification=DataClassification.CONFIDENTIAL
        )
        result = self.platform.check_compliance("users")
        self.assertFalse(result["compliant"])
        self.assertIn("High classification asset must have an owner", result["issues"])

    def test_check_compliance_fail_quality(self):
        """测试合规检查失败：质量规则"""
        self.platform.register_asset(
            "users", "Users", "db",
            classification=DataClassification.INTERNAL,
            owner="admin"
        )
        self.platform.create_rule("r1", "R1", RuleType.VALIDITY, "users", "not_null")
        self.platform.evaluate_rule("r1", None)
        result = self.platform.check_compliance("users")
        self.assertFalse(result["compliant"])
        self.assertIn("1 quality rules failed", result["issues"])

    def test_classify_data(self):
        """测试分类数据"""
        self.platform.register_asset("users", "Users", "db")
        self.assertTrue(self.platform.classify_data("users", DataClassification.RESTRICTED))
        asset = self.platform.get_asset("users")
        self.assertEqual(asset.classification, DataClassification.RESTRICTED)

    def test_stats(self):
        """测试统计信息"""
        self.platform.register_asset("users", "Users", "db")
        self.platform.create_rule("r1", "R1", RuleType.COMPLETENESS, "users", "")
        self.platform.create_policy("p1", "P1", "REG")
        stats = self.platform.get_stats()
        self.assertEqual(stats["total_assets"], 1)
        self.assertEqual(stats["total_rules"], 1)
        self.assertEqual(stats["total_policies"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_data_governance_platform(self):
        """测试获取全局数据治理平台"""
        p1 = get_data_governance_platform()
        p2 = get_data_governance_platform()
        self.assertIs(p1, p2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 99 - 数据治理平台测试")
    print("=" * 60)
    unittest.main(verbosity=2)
