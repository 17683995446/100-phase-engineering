"""
Phase 79 - 地理位置服务测试
验证坐标计算、距离测量、地理围栏和位置查询功能
"""
import unittest
from src.utils.geo_service import (
    GeoPoint,
    GeoFence,
    GeoCalculator,
    DistanceUnit,
    GeoFenceManager,
    GeoSpatialIndex,
    get_geo_fence_manager,
    get_spatial_index
)


class TestGeoPoint(unittest.TestCase):
    """地理坐标点测试"""

    def test_valid_point(self):
        """测试有效坐标"""
        point = GeoPoint(39.9042, 116.4074)
        self.assertEqual(point.latitude, 39.9042)
        self.assertEqual(point.longitude, 116.4074)

    def test_invalid_latitude(self):
        """测试无效纬度"""
        with self.assertRaises(ValueError):
            GeoPoint(91, 0)

    def test_invalid_longitude(self):
        """测试无效经度"""
        with self.assertRaises(ValueError):
            GeoPoint(0, 181)

    def test_to_dict(self):
        """测试转字典"""
        point = GeoPoint(39.9042, 116.4074, metadata={"city": "Beijing"})
        d = point.to_dict()
        self.assertEqual(d["latitude"], 39.9042)
        self.assertEqual(d["metadata"]["city"], "Beijing")


class TestGeoCalculator(unittest.TestCase):
    """地理计算器测试"""

    def test_haversine_distance(self):
        """测试哈弗辛距离"""
        beijing = GeoPoint(39.9042, 116.4074)
        shanghai = GeoPoint(31.2304, 121.4737)
        distance = GeoCalculator.haversine_distance(beijing, shanghai)
        # 北京到上海约1067公里
        self.assertAlmostEqual(distance, 1067, delta=50)

    def test_distance_meters(self):
        """测试米为单位"""
        p1 = GeoPoint(0, 0)
        p2 = GeoPoint(0, 0.01)
        distance = GeoCalculator.haversine_distance(p1, p2, DistanceUnit.METERS)
        # 约1113米
        self.assertAlmostEqual(distance, 1113, delta=50)

    def test_bearing(self):
        """测试方位角"""
        p1 = GeoPoint(0, 0)
        p2 = GeoPoint(1, 0)
        bearing = GeoCalculator.bearing(p1, p2)
        self.assertAlmostEqual(bearing, 0, delta=1)

    def test_destination_point(self):
        """测试目标点计算"""
        start = GeoPoint(0, 0)
        dest = GeoCalculator.destination_point(start, 90, 111.32)
        self.assertAlmostEqual(dest.latitude, 0, delta=0.1)
        self.assertAlmostEqual(dest.longitude, 1, delta=0.1)

    def test_midpoint(self):
        """测试中点计算"""
        p1 = GeoPoint(0, 0)
        p2 = GeoPoint(2, 0)
        mid = GeoCalculator.midpoint(p1, p2)
        self.assertAlmostEqual(mid.latitude, 1, delta=0.1)


class TestGeoFence(unittest.TestCase):
    """地理围栏测试"""

    def test_contains(self):
        """测试包含"""
        center = GeoPoint(0, 0)
        fence = GeoFence("f1", center, 1000)
        inside = GeoPoint(0, 0.005)
        self.assertTrue(fence.contains(inside))

    def test_not_contains(self):
        """测试不包含"""
        center = GeoPoint(0, 0)
        fence = GeoFence("f1", center, 100)
        outside = GeoPoint(1, 1)
        self.assertFalse(fence.contains(outside))


class TestGeoFenceManager(unittest.TestCase):
    """地理围栏管理器测试"""

    def setUp(self):
        self.manager = GeoFenceManager()

    def test_create_fence(self):
        """测试创建围栏"""
        center = GeoPoint(39.9042, 116.4074)
        fence = self.manager.create_fence("f1", center, 1000, "Beijing")
        self.assertEqual(fence.fence_id, "f1")
        self.assertEqual(fence.name, "Beijing")

    def test_get_fence(self):
        """测试获取围栏"""
        center = GeoPoint(0, 0)
        self.manager.create_fence("f1", center, 100)
        fence = self.manager.get_fence("f1")
        self.assertIsNotNone(fence)

    def test_delete_fence(self):
        """测试删除围栏"""
        center = GeoPoint(0, 0)
        self.manager.create_fence("f1", center, 100)
        self.assertTrue(self.manager.delete_fence("f1"))
        self.assertIsNone(self.manager.get_fence("f1"))

    def test_check_point(self):
        """测试检查点"""
        self.manager.create_fence("f1", GeoPoint(0, 0), 1000)
        self.manager.create_fence("f2", GeoPoint(1, 1), 100)
        inside = GeoPoint(0, 0.005)
        fences = self.manager.check_point(inside)
        self.assertIn("f1", fences)
        self.assertNotIn("f2", fences)

    def test_list_fences(self):
        """测试列出围栏"""
        self.manager.create_fence("f1", GeoPoint(0, 0), 100)
        self.manager.create_fence("f2", GeoPoint(1, 1), 100)
        fences = self.manager.list_fences()
        self.assertEqual(len(fences), 2)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_fence("f1", GeoPoint(0, 0), 100)
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_fences"], 1)


class TestGeoSpatialIndex(unittest.TestCase):
    """地理空间索引测试"""

    def setUp(self):
        self.index = GeoSpatialIndex()

    def test_add_remove_point(self):
        """测试添加和移除点"""
        self.index.add_point("p1", GeoPoint(0, 0))
        self.assertTrue(self.index.remove_point("p1"))
        self.assertFalse(self.index.remove_point("p1"))

    def test_find_nearby(self):
        """测试查找附近"""
        self.index.add_point("p1", GeoPoint(0, 0))
        self.index.add_point("p2", GeoPoint(0, 0.01))
        self.index.add_point("p3", GeoPoint(1, 1))
        results = self.index.find_nearby(GeoPoint(0, 0), 2000)
        self.assertEqual(len(results), 2)

    def test_find_nearest(self):
        """测试查找最近"""
        self.index.add_point("p1", GeoPoint(0, 0))
        self.index.add_point("p2", GeoPoint(0, 0.1))
        self.index.add_point("p3", GeoPoint(0, 1))
        results = self.index.find_nearest(GeoPoint(0, 0), limit=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "p1")

    def test_stats(self):
        """测试统计信息"""
        self.index.add_point("p1", GeoPoint(0, 0))
        stats = self.index.get_stats()
        self.assertEqual(stats["total_points"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_geo_fence_manager(self):
        """测试获取全局围栏管理器"""
        m1 = get_geo_fence_manager()
        m2 = get_geo_fence_manager()
        self.assertIs(m1, m2)

    def test_get_spatial_index(self):
        """测试获取全局空间索引"""
        i1 = get_spatial_index()
        i2 = get_spatial_index()
        self.assertIs(i1, i2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 79 - 地理位置服务测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGeoPoint))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGeoCalculator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGeoFence))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGeoFenceManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGeoSpatialIndex))
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
