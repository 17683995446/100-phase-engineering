"""
Phase 88 - 报表生成系统测试
验证数据汇总、报表模板、多种格式导出和定时生成功能
"""
import unittest
from src.utils.report_generator import (
    ReportGenerator,
    ReportColumn,
    ReportTemplate,
    ReportFormat,
    get_report_generator
)


class TestReportGenerator(unittest.TestCase):
    """报表生成器测试"""

    def setUp(self):
        self.generator = ReportGenerator()

    def test_create_template(self):
        """测试创建模板"""
        columns = [
            ReportColumn("Name", "name"),
            ReportColumn("Amount", "amount")
        ]
        template = self.generator.create_template("sales", "Sales Report", columns)
        self.assertEqual(template.template_id, "sales")
        self.assertEqual(len(template.columns), 2)

    def test_create_duplicate_template(self):
        """测试创建重复模板"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        with self.assertRaises(ValueError):
            self.generator.create_template("sales", "Sales2", columns)

    def test_generate_report(self):
        """测试生成报表"""
        columns = [
            ReportColumn("Name", "name"),
            ReportColumn("Amount", "amount")
        ]
        self.generator.create_template("sales", "Sales Report", columns,
                                       aggregations={"amount": "sum"})
        data = [
            {"name": "Product A", "amount": 100},
            {"name": "Product B", "amount": 200}
        ]
        report = self.generator.generate_report("sales", data)
        self.assertIsNotNone(report)
        self.assertEqual(report.summary["amount"], 300)

    def test_generate_report_no_template(self):
        """测试无模板生成"""
        report = self.generator.generate_report("nonexistent", [])
        self.assertIsNone(report)

    def test_export_csv(self):
        """测试导出CSV"""
        columns = [
            ReportColumn("Name", "name"),
            ReportColumn("Amount", "amount")
        ]
        self.generator.create_template("sales", "Sales", columns)
        data = [{"name": "Product A", "amount": 100}]
        report = self.generator.generate_report("sales", data)
        csv = self.generator.export_report(report.report_id, ReportFormat.CSV)
        self.assertIn("Name,Amount", csv)
        self.assertIn("Product A,100", csv)

    def test_export_table(self):
        """测试导出表格"""
        columns = [
            ReportColumn("Name", "name"),
            ReportColumn("Amount", "amount")
        ]
        self.generator.create_template("sales", "Sales", columns)
        data = [{"name": "Product A", "amount": 100}]
        report = self.generator.generate_report("sales", data)
        table = self.generator.export_report(report.report_id, ReportFormat.TABLE)
        self.assertIn("Name", table)
        self.assertIn("Product A", table)

    def test_export_json(self):
        """测试导出JSON"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        data = [{"name": "Product A"}]
        report = self.generator.generate_report("sales", data)
        json_str = self.generator.export_report(report.report_id, ReportFormat.JSON)
        self.assertIn("Product A", json_str)

    def test_list_templates(self):
        """测试列出模板"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("t1", "T1", columns)
        self.generator.create_template("t2", "T2", columns)
        templates = self.generator.list_templates()
        self.assertEqual(len(templates), 2)

    def test_list_reports(self):
        """测试列出报表"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        self.generator.generate_report("sales", [{"name": "A"}])
        reports = self.generator.list_reports()
        self.assertEqual(len(reports), 1)

    def test_delete_template(self):
        """测试删除模板"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        self.assertTrue(self.generator.delete_template("sales"))
        self.assertIsNone(self.generator.get_template("sales"))

    def test_delete_report(self):
        """测试删除报表"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        report = self.generator.generate_report("sales", [{"name": "A"}])
        self.assertTrue(self.generator.delete_report(report.report_id))

    def test_stats(self):
        """测试统计信息"""
        columns = [ReportColumn("Name", "name")]
        self.generator.create_template("sales", "Sales", columns)
        self.generator.generate_report("sales", [{"name": "A"}])
        stats = self.generator.get_stats()
        self.assertEqual(stats["total_templates"], 1)
        self.assertEqual(stats["total_reports"], 1)


class TestReportColumn(unittest.TestCase):
    """报表列测试"""

    def test_format(self):
        """测试格式化"""
        col = ReportColumn("Amount", "amount")
        self.assertEqual(col.format(100), "100")

    def test_format_with_formatter(self):
        """测试自定义格式化"""
        col = ReportColumn("Amount", "amount", formatter=lambda x: f"${x}")
        self.assertEqual(col.format(100), "$100")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_report_generator(self):
        """测试获取全局报表生成器"""
        g1 = get_report_generator()
        g2 = get_report_generator()
        self.assertIs(g1, g2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 88 - 报表生成系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestReportGenerator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestReportColumn))
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
