"""
Phase 55 - 特征存储与管理测试
验证特征定义、存储、检索和版本控制功能是否正常工作
"""
import os
import tempfile
import unittest
from src.utils.feature_store import (
    FeatureStore,
    FeatureDefinition,
    FeatureVector,
    FeatureType,
    FeatureGroup,
    get_feature_store
)


class TestFeatureDefinition(unittest.TestCase):
    """特征定义测试"""

    def test_definition_creation(self):
        """测试定义创建"""
        def_ = FeatureDefinition(
            name="age",
            feature_type=FeatureType.NUMERIC,
            description="User age",
            default_value=0,
            nullable=False,
            tags=["user", "demographic"]
        )
        self.assertEqual(def_.name, "age")
        self.assertEqual(def_.feature_type, FeatureType.NUMERIC)
        self.assertFalse(def_.nullable)

    def test_definition_to_dict(self):
        """测试转换为字典"""
        def_ = FeatureDefinition(name="score", feature_type=FeatureType.NUMERIC)
        d = def_.to_dict()
        self.assertEqual(d["name"], "score")
        self.assertEqual(d["feature_type"], "NUMERIC")


class TestFeatureVector(unittest.TestCase):
    """特征向量测试"""

    def test_vector_operations(self):
        """测试向量操作"""
        vector = FeatureVector(entity_id="user_1")
        vector.set("age", 25)
        vector.set("city", "Beijing")

        self.assertEqual(vector.get("age"), 25)
        self.assertEqual(vector.get("city"), "Beijing")
        self.assertIsNone(vector.get("nonexistent"))


class TestFeatureStore(unittest.TestCase):
    """特征存储测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.store = FeatureStore(self.temp_dir)

    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_register_feature(self):
        """测试注册特征"""
        def_ = FeatureDefinition(name="income", feature_type=FeatureType.NUMERIC)
        result = self.store.register_feature(def_)
        self.assertTrue(result)
        self.assertIsNotNone(self.store.get_feature_definition("income"))

    def test_get_all_definitions(self):
        """测试获取所有定义"""
        self.store.register_feature(FeatureDefinition("f1", FeatureType.NUMERIC))
        self.store.register_feature(FeatureDefinition("f2", FeatureType.CATEGORICAL))

        defs = self.store.get_all_definitions()
        self.assertEqual(len(defs), 2)

    def test_get_features_by_tag(self):
        """测试按标签获取特征"""
        self.store.register_feature(
            FeatureDefinition("f1", FeatureType.NUMERIC, tags=["group-a"])
        )
        self.store.register_feature(
            FeatureDefinition("f2", FeatureType.NUMERIC, tags=["group-b"])
        )

        features = self.store.get_features_by_tag("group-a")
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].name, "f1")

    def test_store_and_get_features(self):
        """测试存储和获取特征"""
        vector = FeatureVector(entity_id="user_1")
        vector.set("age", 25)
        vector.set("score", 100)

        self.store.store_features("user", vector)
        retrieved = self.store.get_features("user", "user_1")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.get("age"), 25)
        self.assertEqual(retrieved.get("score"), 100)

    def test_get_feature_value(self):
        """测试获取单个特征值"""
        vector = FeatureVector(entity_id="user_1")
        vector.set("age", 25)

        self.store.store_features("user", vector)
        value = self.store.get_feature_value("user", "user_1", "age")

        self.assertEqual(value, 25)

    def test_get_entity_ids(self):
        """测试获取实体ID"""
        self.store.store_features("user", FeatureVector("user_1", {"age": 25}))
        self.store.store_features("user", FeatureVector("user_2", {"age": 30}))

        ids = self.store.get_entity_ids("user")
        self.assertEqual(len(ids), 2)
        self.assertIn("user_1", ids)
        self.assertIn("user_2", ids)

    def test_delete_features(self):
        """测试删除特征"""
        self.store.store_features("user", FeatureVector("user_1", {"age": 25}))
        result = self.store.delete_features("user", "user_1")
        self.assertTrue(result)
        self.assertIsNone(self.store.get_features("user", "user_1"))

    def test_get_feature_vector_subset(self):
        """测试获取特征子集"""
        vector = FeatureVector(entity_id="user_1")
        vector.set("age", 25)
        vector.set("score", 100)
        vector.set("city", "Beijing")

        self.store.store_features("user", vector)
        subset = self.store.get_feature_vector("user", "user_1", ["age", "score"])

        self.assertEqual(len(subset), 2)
        self.assertEqual(subset["age"], 25)
        self.assertEqual(subset["score"], 100)
        self.assertNotIn("city", subset)

    def test_validate_features(self):
        """测试特征验证"""
        self.store.register_feature(
            FeatureDefinition("required_field", FeatureType.NUMERIC, nullable=False)
        )
        self.store.register_feature(
            FeatureDefinition("optional_field", FeatureType.NUMERIC, nullable=True)
        )

        # 缺少必需字段
        vector = FeatureVector("user_1", {"optional_field": 10})
        self.store.store_features("user", vector)
        errors = self.store.validate_features("user", "user_1")
        self.assertTrue(any("required_field" in e for e in errors))

        # 完整特征
        vector2 = FeatureVector("user_2", {"required_field": 10, "optional_field": 20})
        self.store.store_features("user", vector2)
        errors2 = self.store.validate_features("user", "user_2")
        self.assertEqual(len(errors2), 0)

    def test_stats(self):
        """测试统计"""
        self.store.register_feature(FeatureDefinition("f1", FeatureType.NUMERIC))
        self.store.store_features("user", FeatureVector("user_1", {"f1": 1}))

        stats = self.store.get_stats()
        self.assertEqual(stats["feature_definitions"], 1)
        self.assertEqual(stats["entity_types"], 1)
        self.assertEqual(stats["total_entities"], 1)

    def test_persistence(self):
        """测试持久化"""
        self.store.register_feature(FeatureDefinition("persist", FeatureType.NUMERIC))

        # 创建新实例
        new_store = FeatureStore(self.temp_dir)
        self.assertIsNotNone(new_store.get_feature_definition("persist"))


class TestFeatureGroup(unittest.TestCase):
    """特征组测试"""

    def setUp(self):
        """测试前设置"""
        self.store = FeatureStore()
        self.group = FeatureGroup("user_profile", self.store)

    def test_add_features(self):
        """测试添加特征"""
        self.group.add_features(["age", "gender", "city"])
        self.assertEqual(len(self.group.get_feature_names()), 3)

    def test_get_feature_vector(self):
        """测试获取特征组向量"""
        self.group.add_features(["age", "score"])

        vector = FeatureVector("user_1")
        vector.set("age", 25)
        vector.set("score", 100)
        vector.set("city", "Beijing")

        self.store.store_features("user", vector)
        result = self.group.get_feature_vector("user", "user_1")

        self.assertEqual(len(result), 2)
        self.assertEqual(result["age"], 25)
        self.assertEqual(result["score"], 100)
        self.assertNotIn("city", result)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_feature_store(self):
        """测试获取全局存储"""
        s1 = get_feature_store()
        s2 = get_feature_store()
        self.assertIs(s1, s2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 55 - 特征存储与管理测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFeatureDefinition))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFeatureVector))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFeatureStore))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFeatureGroup))
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
