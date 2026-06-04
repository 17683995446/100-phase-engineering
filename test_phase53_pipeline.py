"""
Phase 53 - 数据管道与ETL测试
验证数据提取、转换、加载功能是否正常工作
"""
import unittest
from src.utils.data_pipeline import (
    Pipeline,
    PipelineManager,
    MemorySource,
    MemorySink,
    FilterTransformer,
    MapTransformer,
    DataRecord,
    PipelineStatus,
    get_pipeline_manager
)


class TestDataRecord(unittest.TestCase):
    """数据记录测试"""

    def test_record_creation(self):
        """测试记录创建"""
        record = DataRecord(data={"name": "test", "value": 100})
        self.assertEqual(record.get("name"), "test")
        self.assertEqual(record.get("value"), 100)

    def test_record_set(self):
        """测试记录设置"""
        record = DataRecord(data={})
        record.set("key", "value")
        self.assertEqual(record.get("key"), "value")


class TestMemorySource(unittest.TestCase):
    """内存数据源测试"""

    def test_extract(self):
        """测试提取"""
        data = [{"id": 1}, {"id": 2}]
        source = MemorySource("test", data)
        records = list(source.extract())
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].get("id"), 1)


class TestMemorySink(unittest.TestCase):
    """内存数据目标测试"""

    def test_load(self):
        """测试加载"""
        sink = MemorySink("test")
        record = DataRecord(data={"id": 1})
        self.assertTrue(sink.load(record))
        self.assertEqual(len(sink.get_records()), 1)

    def test_clear(self):
        """测试清空"""
        sink = MemorySink("test")
        sink.load(DataRecord(data={"id": 1}))
        sink.clear()
        self.assertEqual(len(sink.get_records()), 0)


class TestFilterTransformer(unittest.TestCase):
    """过滤转换器测试"""

    def test_filter_pass(self):
        """测试通过"""
        transformer = FilterTransformer("pass", lambda r: r.get("value", 0) > 5)
        record = DataRecord(data={"value": 10})
        result = transformer.transform(record)
        self.assertIsNotNone(result)

    def test_filter_block(self):
        """测试阻止"""
        transformer = FilterTransformer("block", lambda r: r.get("value", 0) > 5)
        record = DataRecord(data={"value": 3})
        result = transformer.transform(record)
        self.assertIsNone(result)


class TestMapTransformer(unittest.TestCase):
    """映射转换器测试"""

    def test_map(self):
        """测试映射"""
        def double_value(record):
            record.set("value", record.get("value", 0) * 2)
            return record

        transformer = MapTransformer("double", double_value)
        record = DataRecord(data={"value": 5})
        result = transformer.transform(record)
        self.assertEqual(result.get("value"), 10)


class TestPipeline(unittest.TestCase):
    """管道测试"""

    def test_simple_pipeline(self):
        """测试简单管道"""
        data = [{"id": i, "value": i * 10} for i in range(5)]
        source = MemorySource("input", data)
        sink = MemorySink("output")

        pipeline = Pipeline("simple")
        pipeline.set_source(source).set_sink(sink)
        stats = pipeline.run()

        self.assertEqual(stats["status"], PipelineStatus.COMPLETED.name)
        self.assertEqual(stats["records_processed"], 5)
        self.assertEqual(stats["records_loaded"], 5)
        self.assertEqual(len(sink.get_records()), 5)

    def test_pipeline_with_filter(self):
        """测试带过滤的管道"""
        data = [{"value": i} for i in range(10)]
        source = MemorySource("input", data)
        sink = MemorySink("output")
        filter_transformer = FilterTransformer("even", lambda r: r.get("value", 0) % 2 == 0)

        pipeline = Pipeline("filtered")
        pipeline.set_source(source).add_transformer(filter_transformer).set_sink(sink)
        stats = pipeline.run()

        self.assertEqual(stats["records_processed"], 10)
        self.assertEqual(stats["records_filtered"], 5)
        self.assertEqual(stats["records_loaded"], 5)

    def test_pipeline_with_map(self):
        """测试带映射的管道"""
        data = [{"value": i} for i in range(3)]
        source = MemorySource("input", data)
        sink = MemorySink("output")

        def double(record):
            record.set("value", record.get("value", 0) * 2)
            return record

        map_transformer = MapTransformer("double", double)

        pipeline = Pipeline("mapped")
        pipeline.set_source(source).add_transformer(map_transformer).set_sink(sink)
        pipeline.run()

        records = sink.get_records()
        self.assertEqual(records[0].get("value"), 0)
        self.assertEqual(records[1].get("value"), 2)
        self.assertEqual(records[2].get("value"), 4)

    def test_pipeline_chained_transformers(self):
        """测试链式转换器"""
        data = [{"value": i} for i in range(10)]
        source = MemorySource("input", data)
        sink = MemorySink("output")

        filter_even = FilterTransformer("even", lambda r: r.get("value", 0) % 2 == 0)

        def double(record):
            record.set("value", record.get("value", 0) * 2)
            return record

        map_double = MapTransformer("double", double)

        pipeline = Pipeline("chained")
        pipeline.set_source(source).add_transformer(filter_even).add_transformer(map_double).set_sink(sink)
        stats = pipeline.run()

        self.assertEqual(stats["records_loaded"], 5)
        records = sink.get_records()
        self.assertEqual(records[0].get("value"), 0)
        self.assertEqual(records[1].get("value"), 4)

    def test_pipeline_no_source_sink(self):
        """测试缺少源或目标"""
        pipeline = Pipeline("incomplete")
        with self.assertRaises(ValueError):
            pipeline.run()

    def test_pipeline_status(self):
        """测试管道状态"""
        pipeline = Pipeline("status-test")
        self.assertEqual(pipeline.get_status(), PipelineStatus.IDLE)


class TestPipelineManager(unittest.TestCase):
    """管道管理器测试"""

    def test_register_pipeline(self):
        """测试注册管道"""
        manager = PipelineManager()
        pipeline = Pipeline("test")
        manager.register_pipeline(pipeline)
        self.assertIsNotNone(manager.get_pipeline("test"))

    def test_run_pipeline(self):
        """测试运行管道"""
        manager = PipelineManager()
        data = [{"id": 1}]
        source = MemorySource("input", data)
        sink = MemorySink("output")

        pipeline = Pipeline("run-test")
        pipeline.set_source(source).set_sink(sink)
        manager.register_pipeline(pipeline)

        stats = manager.run_pipeline("run-test")
        self.assertIsNotNone(stats)
        self.assertEqual(stats["records_loaded"], 1)

    def test_get_all_stats(self):
        """测试获取所有统计"""
        manager = PipelineManager()
        pipeline = Pipeline("stats-test")
        manager.register_pipeline(pipeline)

        stats = manager.get_all_stats()
        self.assertIn("stats-test", stats)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_pipeline_manager(self):
        """测试获取全局管理器"""
        m1 = get_pipeline_manager()
        m2 = get_pipeline_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 53 - 数据管道与ETL测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataRecord))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMemorySource))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMemorySink))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFilterTransformer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMapTransformer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPipeline))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPipelineManager))
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
