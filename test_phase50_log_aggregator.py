"""
Phase 50 - 日志聚合与分析测试
验证日志聚合、查询和分析功能是否正常工作
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from src.utils.log_aggregator import (
    LogAggregator,
    LogAnalyzer,
    LogExporter,
    LogEntry,
    LogLevel,
    get_log_aggregator,
    get_log_analyzer
)


class TestLogEntry(unittest.TestCase):
    """日志条目测试"""

    def test_entry_creation(self):
        """测试条目创建"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            source="test-service",
            message="Test message",
            metadata={"user_id": "123"}
        )
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.source, "test-service")

    def test_entry_to_dict(self):
        """测试转换为字典"""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            level=LogLevel.ERROR,
            source="app",
            message="Error occurred"
        )
        d = entry.to_dict()
        self.assertEqual(d["level"], "ERROR")
        self.assertEqual(d["source"], "app")


class TestLogBuffer(unittest.TestCase):
    """日志缓冲区测试"""

    def test_buffer_append(self):
        """测试添加"""
        from src.utils.log_aggregator import LogBuffer
        buffer = LogBuffer(max_size=5)
        entry = LogEntry(datetime.now(), LogLevel.INFO, "test", "msg")
        buffer.append(entry)
        self.assertEqual(buffer.get_size(), 1)

    def test_buffer_limit(self):
        """测试容量限制"""
        from src.utils.log_aggregator import LogBuffer
        buffer = LogBuffer(max_size=3)
        for i in range(5):
            buffer.append(LogEntry(datetime.now(), LogLevel.INFO, "test", f"msg{i}"))
        self.assertEqual(buffer.get_size(), 3)


class TestLogAggregator(unittest.TestCase):
    """日志聚合器测试"""

    def setUp(self):
        """测试前设置"""
        self.aggregator = LogAggregator(buffer_size=100)

    def test_collect(self):
        """测试收集"""
        entry = LogEntry(datetime.now(), LogLevel.INFO, "service1", "Test message")
        self.aggregator.collect(entry)
        self.assertEqual(self.aggregator.get_stats()["total_entries"], 1)

    def test_collect_from_dict(self):
        """测试从字典收集"""
        log_dict = {
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "source": "api",
            "message": "Slow response",
            "metadata": {"duration_ms": 5000}
        }
        self.aggregator.collect_from_dict(log_dict)
        self.assertEqual(self.aggregator.get_stats()["total_entries"], 1)

    def test_query_by_level(self):
        """测试按级别查询"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "info msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", "error msg"))

        results = self.aggregator.query(level=LogLevel.ERROR)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].level, LogLevel.ERROR)

    def test_query_by_source(self):
        """测试按来源查询"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "service-a", "msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "service-b", "msg"))

        results = self.aggregator.query(source="service-a")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "service-a")

    def test_query_by_pattern(self):
        """测试按模式查询"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "user login success"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "user logout"))

        results = self.aggregator.query(message_pattern="login")
        self.assertEqual(len(results), 1)
        self.assertIn("login", results[0].message)

    def test_query_by_time(self):
        """测试按时间查询"""
        now = datetime.now()
        self.aggregator.collect(LogEntry(now - timedelta(hours=2), LogLevel.INFO, "s", "old"))
        self.aggregator.collect(LogEntry(now, LogLevel.INFO, "s", "new"))

        results = self.aggregator.query(start_time=now - timedelta(minutes=30))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].message, "new")

    def test_level_distribution(self):
        """测试级别分布"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", "msg"))

        dist = self.aggregator.get_level_distribution()
        self.assertEqual(dist["INFO"], 2)
        self.assertEqual(dist["ERROR"], 1)

    def test_source_distribution(self):
        """测试来源分布"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "svc1", "msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "svc1", "msg"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "svc2", "msg"))

        dist = self.aggregator.get_source_distribution()
        self.assertEqual(dist["svc1"], 2)
        self.assertEqual(dist["svc2"], 1)

    def test_top_errors(self):
        """测试常见错误"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", "Connection timeout"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", "Connection timeout"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", "Database error"))

        errors = self.aggregator.get_top_errors(2)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0][1], 2)  # Connection timeout 出现2次

    def test_clear(self):
        """测试清空"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "msg"))
        self.aggregator.clear()
        self.assertEqual(self.aggregator.get_stats()["total_entries"], 0)


class TestLogAnalyzer(unittest.TestCase):
    """日志分析器测试"""

    def setUp(self):
        """测试前设置"""
        self.aggregator = LogAggregator()
        self.analyzer = LogAnalyzer(self.aggregator)

    def test_analyze_trends(self):
        """测试趋势分析"""
        now = datetime.now()
        for i in range(5):
            self.aggregator.collect(LogEntry(
                now - timedelta(hours=i),
                LogLevel.ERROR,
                "s",
                f"error {i}"
            ))

        trends = self.analyzer.analyze_trends()
        self.assertIn("error_trend", trends)

    def test_detect_anomalies(self):
        """测试异常检测"""
        now = datetime.now()
        # 正常时段
        for i in range(5):
            self.aggregator.collect(LogEntry(
                now - timedelta(hours=i+1),
                LogLevel.INFO,
                "s",
                "normal"
            ))

        # 异常时段 - 大量错误
        for i in range(50):
            self.aggregator.collect(LogEntry(
                now,
                LogLevel.ERROR,
                "s",
                f"error burst {i}"
            ))

        anomalies = self.analyzer.detect_anomalies(threshold=2)
        self.assertTrue(len(anomalies) > 0)

    def test_generate_report(self):
        """测试生成报告"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "msg"))
        report = self.analyzer.generate_report()

        self.assertIn("generated_at", report)
        self.assertIn("summary", report)
        self.assertIn("recommendations", report)

    def test_recommendations_high_error_rate(self):
        """测试高错误率建议"""
        for i in range(10):
            self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "s", f"error {i}"))
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "info"))

        report = self.analyzer.generate_report()
        recommendations = report["recommendations"]
        self.assertTrue(any("错误率" in r for r in recommendations))


class TestLogExporter(unittest.TestCase):
    """日志导出器测试"""

    def setUp(self):
        """测试前设置"""
        self.aggregator = LogAggregator()
        self.exporter = LogExporter(self.aggregator)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_export_to_json(self):
        """测试导出JSON"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.INFO, "s", "test"))
        filepath = os.path.join(self.temp_dir, "logs.json")

        result = self.exporter.export_to_json(filepath)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))

    def test_export_to_csv(self):
        """测试导出CSV"""
        self.aggregator.collect(LogEntry(datetime.now(), LogLevel.ERROR, "svc", "error msg"))
        filepath = os.path.join(self.temp_dir, "logs.csv")

        result = self.exporter.export_to_csv(filepath)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, 'r') as f:
            content = f.read()
            self.assertIn("timestamp,level,source,message", content)
            self.assertIn("ERROR", content)


class TestGlobalInstances(unittest.TestCase):
    """全局实例测试"""

    def test_get_log_aggregator(self):
        """测试获取全局聚合器"""
        agg1 = get_log_aggregator()
        agg2 = get_log_aggregator()
        self.assertIs(agg1, agg2)

    def test_get_log_analyzer(self):
        """测试获取全局分析器"""
        analyzer1 = get_log_analyzer()
        analyzer2 = get_log_analyzer()
        self.assertIs(analyzer1, analyzer2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 50 - 日志聚合与分析测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogEntry))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogBuffer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogAggregator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogAnalyzer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogExporter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstances))

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
