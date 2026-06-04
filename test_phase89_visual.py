"""
Phase 89 - 数据可视化系统测试
验证图表生成、数据映射、主题配置和实时更新功能
"""
import unittest
from src.utils.data_visualizer import (
    DataVisualizer,
    DataMapper,
    ChartConfig,
    ChartData,
    ChartType,
    DataVisualizationTheme,
    get_visualizer
)


class TestDataMapper(unittest.TestCase):
    """数据映射器测试"""

    def test_map_dict_to_labels_datasets(self):
        """测试映射字典列表"""
        mapper = DataMapper()
        data = [
            {"month": "Jan", "sales": 100},
            {"month": "Feb", "sales": 200}
        ]
        chart_data = mapper.map_dict_to_labels_datasets(data, "month", "sales")
        self.assertEqual(chart_data.labels, ["Feb", "Jan"])
        self.assertEqual(len(chart_data.datasets), 1)
        self.assertEqual(chart_data.datasets[0]["data"], [100, 200])

    def test_map_with_series(self):
        """测试带系列映射"""
        mapper = DataMapper()
        data = [
            {"month": "Jan", "sales": 100, "region": "A"},
            {"month": "Jan", "sales": 150, "region": "B"}
        ]
        chart_data = mapper.map_dict_to_labels_datasets(data, "month", "sales", "region")
        self.assertEqual(len(chart_data.datasets), 2)

    def test_aggregate_by_label(self):
        """测试按标签聚合"""
        mapper = DataMapper()
        data = [
            {"month": "Jan", "sales": 100},
            {"month": "Jan", "sales": 200},
            {"month": "Feb", "sales": 150}
        ]
        result = mapper.aggregate_by_label(data, "month", "sales", "sum")
        self.assertEqual(len(result), 2)
        jan = next(r for r in result if r["month"] == "Jan")
        self.assertEqual(jan["sales"], 300)


class TestDataVisualizer(unittest.TestCase):
    """数据可视化器测试"""

    def setUp(self):
        self.visualizer = DataVisualizer()

    def test_create_chart(self):
        """测试创建图表"""
        config = ChartConfig(
            chart_id="chart1",
            title="Sales",
            chart_type=ChartType.BAR
        )
        data = ChartData(labels=["Jan", "Feb"], datasets=[{"name": "Sales", "data": [100, 200]}])
        chart = self.visualizer.create_chart(config, data)
        self.assertEqual(chart.chart_id, "chart1")

    def test_create_chart_from_config(self):
        """测试从配置创建"""
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        chart = self.visualizer.create_chart_from_config("chart1", "Sales", ChartType.BAR, data)
        self.assertEqual(chart.config.title, "Sales")

    def test_get_chart(self):
        """测试获取图表"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        chart = self.visualizer.get_chart("chart1")
        self.assertIsNotNone(chart)

    def test_update_chart(self):
        """测试更新图表"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        new_data = ChartData(labels=["Jan", "Feb"], datasets=[{"data": [100, 200]}])
        result = self.visualizer.update_chart("chart1", new_data)
        self.assertTrue(result)
        self.assertEqual(len(self.visualizer.get_chart("chart1").data.labels), 2)

    def test_delete_chart(self):
        """测试删除图表"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        result = self.visualizer.delete_chart("chart1")
        self.assertTrue(result)
        self.assertIsNone(self.visualizer.get_chart("chart1"))

    def test_render_chart(self):
        """测试渲染图表"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        svg = self.visualizer.render_chart("chart1")
        self.assertIsNotNone(svg)
        self.assertIn("<svg", svg)

    def test_render_line_chart(self):
        """测试渲染折线图"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.LINE)
        data = ChartData(labels=["Jan", "Feb"], datasets=[{"data": [100, 200]}])
        self.visualizer.create_chart(config, data)
        svg = self.visualizer.render_chart("chart1")
        self.assertIn("<line", svg)

    def test_list_charts(self):
        """测试列出图表"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        charts = self.visualizer.list_charts()
        self.assertEqual(len(charts), 1)

    def test_stats(self):
        """测试统计信息"""
        config = ChartConfig(chart_id="chart1", title="Sales", chart_type=ChartType.BAR)
        data = ChartData(labels=["Jan"], datasets=[{"data": [100]}])
        self.visualizer.create_chart(config, data)
        stats = self.visualizer.get_stats()
        self.assertEqual(stats["total_charts"], 1)
        self.assertEqual(stats["by_type"]["bar"], 1)


class TestChartConfig(unittest.TestCase):
    """图表配置测试"""

    def test_to_dict(self):
        """测试转字典"""
        config = ChartConfig(
            chart_id="c1",
            title="Test",
            chart_type=ChartType.BAR,
            theme=DataVisualizationTheme.DARK
        )
        d = config.to_dict()
        self.assertEqual(d["chart_id"], "c1")
        self.assertEqual(d["theme"], "dark")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_visualizer(self):
        """测试获取全局可视化器"""
        v1 = get_visualizer()
        v2 = get_visualizer()
        self.assertIs(v1, v2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 89 - 数据可视化系统测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataMapper))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataVisualizer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestChartConfig))
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
