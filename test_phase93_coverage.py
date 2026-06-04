"""
Phase 93 - 测试覆盖率分析器测试
验证覆盖率收集、报告生成、趋势分析和阈值检查功能
"""
import unittest
from src.utils.coverage_analyzer import (
    CoverageAnalyzer,
    CoverageCollector,
    FileCoverage,
    get_coverage_analyzer
)


class TestCoverageCollector(unittest.TestCase):
    """覆盖率收集器测试"""

    def setUp(self):
        self.collector = CoverageCollector()

    def test_register_file(self):
        """测试注册文件"""
        self.collector.register_file("test.py", 100, 10, 5)
        coverage = self.collector.get_file_coverage("test.py")
        self.assertIsNotNone(coverage)
        self.assertEqual(coverage.total_lines, 100)

    def test_cover_line(self):
        """测试覆盖行"""
        self.collector.register_file("test.py", 100)
        self.collector.cover_line("test.py", 1)
        self.collector.cover_line("test.py", 2)
        coverage = self.collector.get_file_coverage("test.py")
        self.assertEqual(coverage.covered_lines, 2)

    def test_cover_branch(self):
        """测试覆盖分支"""
        self.collector.register_file("test.py", 100, 10)
        self.collector.cover_branch("test.py")
        coverage = self.collector.get_file_coverage("test.py")
        self.assertEqual(coverage.covered_branches, 1)

    def test_cover_function(self):
        """测试覆盖函数"""
        self.collector.register_file("test.py", 100, 0, 5)
        self.collector.cover_function("test.py")
        coverage = self.collector.get_file_coverage("test.py")
        self.assertEqual(coverage.covered_functions, 1)

    def test_get_all_coverage(self):
        """测试获取所有覆盖率"""
        self.collector.register_file("a.py", 100)
        self.collector.register_file("b.py", 200)
        coverage = self.collector.get_all_coverage()
        self.assertEqual(len(coverage), 2)

    def test_reset(self):
        """测试重置"""
        self.collector.register_file("test.py", 100)
        self.collector.reset()
        self.assertEqual(len(self.collector.get_all_coverage()), 0)


class TestCoverageAnalyzer(unittest.TestCase):
    """覆盖率分析器测试"""

    def setUp(self):
        self.analyzer = CoverageAnalyzer()

    def test_generate_report(self):
        """测试生成报告"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 100, 10, 5)
        collector.cover_line("test.py", 1)
        collector.cover_line("test.py", 2)
        report = self.analyzer.generate_report(threshold=80.0)
        self.assertEqual(report.overall_coverage, 2.0)
        self.assertFalse(report.passed_threshold)

    def test_generate_report_passed(self):
        """测试通过阈值的报告"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 10)
        for i in range(1, 9):
            collector.cover_line("test.py", i)
        report = self.analyzer.generate_report(threshold=80.0)
        self.assertEqual(report.overall_coverage, 80.0)
        self.assertTrue(report.passed_threshold)

    def test_get_report(self):
        """测试获取报告"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 100)
        report = self.analyzer.generate_report()
        retrieved = self.analyzer.get_report(report.report_id)
        self.assertIsNotNone(retrieved)

    def test_check_threshold(self):
        """测试检查阈值"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 10)
        for i in range(1, 10):
            collector.cover_line("test.py", i)
        report = self.analyzer.generate_report(threshold=80.0)
        self.assertTrue(self.analyzer.check_threshold(report.report_id))

    def test_get_trend(self):
        """测试获取趋势"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 10)
        collector.cover_line("test.py", 1)
        self.analyzer.generate_report()
        collector.cover_line("test.py", 2)
        self.analyzer.generate_report()
        trend = self.analyzer.get_trend()
        self.assertEqual(len(trend), 2)

    def test_get_uncovered_files(self):
        """测试获取未覆盖文件"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 100)
        report = self.analyzer.generate_report()
        uncovered = self.analyzer.get_uncovered_files(report.report_id)
        self.assertIn("test.py", uncovered)

    def test_get_low_coverage_files(self):
        """测试获取低覆盖率文件"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 100)
        collector.cover_line("test.py", 1)
        report = self.analyzer.generate_report()
        low = self.analyzer.get_low_coverage_files(report.report_id, min_coverage=50.0)
        self.assertEqual(len(low), 1)

    def test_compare_reports(self):
        """测试比较报告"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 10)
        collector.cover_line("test.py", 1)
        report1 = self.analyzer.generate_report()
        collector.cover_line("test.py", 2)
        report2 = self.analyzer.generate_report()
        comparison = self.analyzer.compare_reports(report1.report_id, report2.report_id)
        self.assertGreater(comparison["coverage_diff"], 0)

    def test_stats(self):
        """测试统计信息"""
        collector = self.analyzer.get_collector()
        collector.register_file("test.py", 10)
        self.analyzer.generate_report()
        stats = self.analyzer.get_stats()
        self.assertEqual(stats["total_reports"], 1)


class TestFileCoverage(unittest.TestCase):
    """文件覆盖率测试"""

    def test_line_coverage(self):
        """测试行覆盖率"""
        fc = FileCoverage("test.py", total_lines=100, covered_lines=50)
        self.assertEqual(fc.line_coverage, 50.0)

    def test_line_coverage_zero(self):
        """测试零行覆盖率"""
        fc = FileCoverage("test.py", total_lines=0, covered_lines=0)
        self.assertEqual(fc.line_coverage, 100.0)

    def test_branch_coverage(self):
        """测试分支覆盖率"""
        fc = FileCoverage("test.py", total_branches=10, covered_branches=5)
        self.assertEqual(fc.branch_coverage, 50.0)

    def test_function_coverage(self):
        """测试函数覆盖率"""
        fc = FileCoverage("test.py", total_functions=5, covered_functions=3)
        self.assertEqual(fc.function_coverage, 60.0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_coverage_analyzer(self):
        """测试获取全局覆盖率分析器"""
        a1 = get_coverage_analyzer()
        a2 = get_coverage_analyzer()
        self.assertIs(a1, a2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 93 - 测试覆盖率分析器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCoverageCollector))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCoverageAnalyzer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFileCoverage))
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
