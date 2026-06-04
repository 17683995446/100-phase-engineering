"""
Phase 92 - 代码质量分析器测试
验证代码度量、复杂度分析、风格检查和质量报告功能
"""
import unittest
from src.utils.code_quality import (
    CodeQualityAnalyzer,
    ComplexityAnalyzer,
    StyleChecker,
    Severity,
    get_code_quality_analyzer
)


class TestComplexityAnalyzer(unittest.TestCase):
    """复杂度分析器测试"""

    def test_calculate_cyclomatic_complexity(self):
        """测试圈复杂度"""
        analyzer = ComplexityAnalyzer()
        code = "def test():\n    if True:\n        pass\n    for i in range(10):\n        pass"
        complexity = analyzer.calculate_cyclomatic_complexity(code)
        self.assertGreater(complexity, 1)

    def test_calculate_function_length(self):
        """测试函数长度"""
        analyzer = ComplexityAnalyzer()
        code = "line1\nline2\n\nline3"
        length = analyzer.calculate_function_length(code)
        self.assertEqual(length, 3)


class TestStyleChecker(unittest.TestCase):
    """风格检查器测试"""

    def test_check_line_length(self):
        """测试行长度检查"""
        checker = StyleChecker()
        code = "a" * 130
        issues = checker.check_line_length(code, max_length=120)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule_id, "E501")

    def test_check_trailing_whitespace(self):
        """测试尾部空白检查"""
        checker = StyleChecker()
        code = "line  \n"
        issues = checker.check_trailing_whitespace(code)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule_id, "W291")

    def test_check_import_order(self):
        """测试导入顺序检查"""
        checker = StyleChecker()
        code = "import z\nimport a"
        issues = checker.check_import_order(code)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule_id, "I100")


class TestCodeQualityAnalyzer(unittest.TestCase):
    """代码质量分析器测试"""

    def setUp(self):
        self.analyzer = CodeQualityAnalyzer()

    def test_analyze(self):
        """测试分析"""
        code = "class Test:\n    def method(self):\n        pass\n"
        report = self.analyzer.analyze("test.py", code)
        self.assertEqual(report.file_path, "test.py")
        self.assertEqual(report.metrics.classes, 1)
        self.assertEqual(report.metrics.functions, 1)
        self.assertGreaterEqual(report.score, 0)
        self.assertLessEqual(report.score, 100)

    def test_analyze_complexity(self):
        """测试复杂度分析"""
        code = "def test():\n    if True:\n        pass\n    elif False:\n        pass\n    else:\n        pass\n"
        report = self.analyzer.analyze("test.py", code)
        self.assertGreater(report.metrics.complexity, 1)

    def test_get_report(self):
        """测试获取报告"""
        code = "def test(): pass\n"
        self.analyzer.analyze("test.py", code)
        report = self.analyzer.get_report("test.py")
        self.assertIsNotNone(report)

    def test_get_all_reports(self):
        """测试获取所有报告"""
        self.analyzer.analyze("a.py", "def a(): pass")
        self.analyzer.analyze("b.py", "def b(): pass")
        reports = self.analyzer.get_all_reports()
        self.assertEqual(len(reports), 2)

    def test_get_summary(self):
        """测试获取汇总"""
        self.analyzer.analyze("test.py", "def test(): pass\n")
        summary = self.analyzer.get_summary()
        self.assertEqual(summary["total_files"], 1)
        self.assertIn("average_score", summary)

    def test_stats(self):
        """测试统计信息"""
        self.analyzer.analyze("test.py", "def test(): pass\n")
        stats = self.analyzer.get_stats()
        self.assertEqual(stats["total_files"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_code_quality_analyzer(self):
        """测试获取全局代码质量分析器"""
        a1 = get_code_quality_analyzer()
        a2 = get_code_quality_analyzer()
        self.assertIs(a1, a2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 92 - 代码质量分析器测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestComplexityAnalyzer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStyleChecker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCodeQualityAnalyzer))
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
