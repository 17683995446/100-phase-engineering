"""
Phase 62 - 实时数据处理测试
验证流数据接收、处理和窗口计算功能是否正常工作
"""
import time
import unittest
from src.utils.stream_processor import (
    StreamProcessor,
    StreamWindow,
    StreamRecord,
    StreamAggregator,
    WindowType,
    get_stream_processor
)


class TestStreamWindow(unittest.TestCase):
    """流窗口测试"""

    def test_add_and_count(self):
        """测试添加和计数"""
        window = StreamWindow(WindowType.TUMBLING, size_seconds=10)
        window.add(StreamRecord("temp", 25.0))
        window.add(StreamRecord("temp", 30.0))
        self.assertEqual(window.count(), 2)

    def test_cleanup(self):
        """测试清理过期记录"""
        window = StreamWindow(WindowType.TUMBLING, size_seconds=0.1)
        window.add(StreamRecord("temp", 25.0, timestamp=time.time() - 1))
        window.add(StreamRecord("temp", 30.0))
        self.assertEqual(window.count(), 1)

    def test_sum_values(self):
        """测试求和"""
        window = StreamWindow(WindowType.TUMBLING, size_seconds=10)
        window.add(StreamRecord("temp", 10.0))
        window.add(StreamRecord("temp", 20.0))
        window.add(StreamRecord("temp", 30.0))
        self.assertEqual(window.sum_values(), 60.0)

    def test_average(self):
        """测试平均值"""
        window = StreamWindow(WindowType.TUMBLING, size_seconds=10)
        window.add(StreamRecord("temp", 10.0))
        window.add(StreamRecord("temp", 20.0))
        self.assertEqual(window.average(), 15.0)


class TestStreamProcessor(unittest.TestCase):
    """流处理器测试"""

    def setUp(self):
        """测试前设置"""
        self.processor = StreamProcessor()
        self.received = []

    def test_add_handler(self):
        """测试添加处理器"""
        def handler(record):
            self.received.append(record)

        self.processor.add_handler("temp", handler)
        self.processor.process(StreamRecord("temp", 25.0))
        self.assertEqual(len(self.received), 1)

    def test_create_window(self):
        """测试创建窗口"""
        window = self.processor.create_window("temp", WindowType.TUMBLING, 10)
        self.assertIsNotNone(window)

    def test_process_with_window(self):
        """测试带窗口的处理"""
        self.processor.create_window("temp", WindowType.TUMBLING, 10)
        self.processor.process(StreamRecord("temp", 10.0))
        self.processor.process(StreamRecord("temp", 20.0))

        stats = self.processor.get_window_stats("temp")
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["sum"], 30.0)

    def test_window_stats_nonexistent(self):
        """测试不存在的窗口统计"""
        stats = self.processor.get_window_stats("nonexistent")
        self.assertEqual(stats, {})

    def test_stats(self):
        """测试统计"""
        self.processor.process(StreamRecord("temp", 25.0))
        stats = self.processor.get_stats()
        self.assertEqual(stats["processed"], 1)


class TestStreamAggregator(unittest.TestCase):
    """流聚合器测试"""

    def setUp(self):
        """测试前设置"""
        self.aggregator = StreamAggregator()

    def test_sum(self):
        """测试求和"""
        self.aggregator.aggregate("sales", StreamRecord("sales", 100), "sum")
        self.aggregator.aggregate("sales", StreamRecord("sales", 200), "sum")
        result = self.aggregator.aggregate("sales", StreamRecord("sales", 300), "sum")
        self.assertEqual(result, 600)

    def test_count(self):
        """测试计数"""
        self.aggregator.aggregate("clicks", StreamRecord("clicks", 1), "count")
        self.aggregator.aggregate("clicks", StreamRecord("clicks", 1), "count")
        result = self.aggregator.aggregate("clicks", StreamRecord("clicks", 1), "count")
        self.assertEqual(result, 3)

    def test_avg(self):
        """测试平均值"""
        self.aggregator.aggregate("temp", StreamRecord("temp", 10), "avg")
        self.aggregator.aggregate("temp", StreamRecord("temp", 20), "avg")
        result = self.aggregator.aggregate("temp", StreamRecord("temp", 30), "avg")
        self.assertEqual(result, 20.0)

    def test_min_max(self):
        """测试最小最大值"""
        self.aggregator.aggregate("temp", StreamRecord("temp", 10), "min")
        self.aggregator.aggregate("temp", StreamRecord("temp", 5), "min")
        self.aggregator.aggregate("temp", StreamRecord("temp", 20), "max")

        agg = self.aggregator.get_aggregate("temp")
        self.assertEqual(agg["min"], 5)
        self.assertEqual(agg["max"], 20)

    def test_get_aggregate(self):
        """测试获取聚合结果"""
        self.aggregator.aggregate("test", StreamRecord("test", 100))
        agg = self.aggregator.get_aggregate("test")
        self.assertIsNotNone(agg)
        self.assertEqual(agg["count"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_stream_processor(self):
        """测试获取全局处理器"""
        p1 = get_stream_processor()
        p2 = get_stream_processor()
        self.assertIs(p1, p2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 62 - 实时数据处理测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStreamWindow))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStreamProcessor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStreamAggregator))
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
