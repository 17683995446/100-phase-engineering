"""
Phase 103 - 类型精确化测试
验证 TypedDict 和类型别名的正确性
"""
import unittest
from src.types.common_types import (
    ConfigValue, MetricValue, Timestamp, Labels,
    CoverageReportDict, PipelineRunDict, SecretInfoDict,
    AlertDict, ConfigItemDict, DataAssetDict, QualityReportDict
)


class TestTypeAliases(unittest.TestCase):
    """类型别名测试"""

    def test_config_value_string(self):
        """测试 ConfigValue 字符串"""
        value: ConfigValue = "test"
        self.assertEqual(value, "test")

    def test_config_value_int(self):
        """测试 ConfigValue 整数"""
        value: ConfigValue = 42
        self.assertEqual(value, 42)

    def test_config_value_list(self):
        """测试 ConfigValue 列表"""
        value: ConfigValue = ["a", "b"]
        self.assertEqual(value, ["a", "b"])

    def test_metric_value(self):
        """测试 MetricValue"""
        value: MetricValue = 3.14
        self.assertEqual(value, 3.14)

    def test_timestamp(self):
        """测试 Timestamp"""
        ts: Timestamp = 1234567890.0
        self.assertEqual(ts, 1234567890.0)

    def test_labels(self):
        """测试 Labels"""
        labels: Labels = {"host": "server1", "env": "prod"}
        self.assertEqual(labels["host"], "server1")


class TestTypedDict(unittest.TestCase):
    """TypedDict 测试"""

    def test_coverage_report_dict(self):
        """测试 CoverageReportDict"""
        report: CoverageReportDict = {
            "report_id": "r1",
            "timestamp": 1234567890.0,
            "overall_coverage": 85.5,
            "passed": True
        }
        self.assertEqual(report["report_id"], "r1")
        self.assertEqual(report["overall_coverage"], 85.5)

    def test_pipeline_run_dict(self):
        """测试 PipelineRunDict"""
        run: PipelineRunDict = {
            "run_id": "run_1",
            "pipeline_id": "deploy",
            "status": "success",
            "duration": 120.5
        }
        self.assertEqual(run["status"], "success")

    def test_secret_info_dict(self):
        """测试 SecretInfoDict"""
        secret: SecretInfoDict = {
            "secret_id": "sec_1",
            "name": "api_key",
            "secret_type": "api_key",
            "status": "active",
            "allowed_services": ["svc1", "svc2"]
        }
        self.assertEqual(secret["name"], "api_key")
        self.assertEqual(secret["allowed_services"], ["svc1", "svc2"])

    def test_alert_dict(self):
        """测试 AlertDict"""
        alert: AlertDict = {
            "alert_id": "a1",
            "name": "CPU High",
            "severity": "critical",
            "value": 95.0,
            "threshold": 80.0
        }
        self.assertEqual(alert["severity"], "critical")

    def test_config_item_dict(self):
        """测试 ConfigItemDict"""
        config: ConfigItemDict = {
            "key": "app.name",
            "value": "MyApp",
            "config_type": "string",
            "version": 1,
            "env": "default"
        }
        self.assertEqual(config["value"], "MyApp")

    def test_data_asset_dict(self):
        """测试 DataAssetDict"""
        asset: DataAssetDict = {
            "asset_id": "users",
            "name": "Users Table",
            "source": "postgres",
            "classification": "confidential",
            "owner": "admin"
        }
        self.assertEqual(asset["classification"], "confidential")

    def test_quality_report_dict(self):
        """测试 QualityReportDict"""
        report: QualityReportDict = {
            "report_id": "qr1",
            "asset_id": "users",
            "status": "pass",
            "score": 0.95,
            "details": "All checks passed"
        }
        self.assertEqual(report["score"], 0.95)

    def test_partial_dict(self):
        """测试部分字段的 TypedDict"""
        report: CoverageReportDict = {
            "report_id": "r1",
            "passed": False
        }
        self.assertIn("report_id", report)
        self.assertNotIn("line_coverage", report)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 103 - 类型精确化测试")
    print("=" * 60)
    unittest.main(verbosity=2)
