"""
Phase 54 - 机器学习模型管理测试
验证模型注册、版本控制、加载和预测功能是否正常工作
"""
import os
import tempfile
import pickle
import unittest
from src.utils.ml_model_manager import (
    MLModelManager,
    SimplePredictor,
    ModelStatus,
    get_model_manager
)


class DummyModel:
    """测试用虚拟模型"""
    def predict(self, x):
        return x * 2


class TestMLModelManager(unittest.TestCase):
    """模型管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MLModelManager(self.temp_dir)

    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _save_dummy_model(self, name="model.pkl"):
        """保存虚拟模型"""
        path = os.path.join(self.temp_dir, name)
        with open(path, 'wb') as f:
            pickle.dump(DummyModel(), f)
        return path

    def test_register_model(self):
        """测试注册模型"""
        model_path = self._save_dummy_model()
        result = self.manager.register_model(
            "test-model", "regression", "1.0.0", model_path,
            metrics={"accuracy": 0.95}
        )
        self.assertTrue(result)
        self.assertIn("test-model", self.manager.get_all_models())

    def test_load_model(self):
        """测试加载模型"""
        model_path = self._save_dummy_model()
        self.manager.register_model("load-test", "classifier", "1.0.0", model_path)

        model = self.manager.load_model("load-test")
        self.assertIsNotNone(model)
        self.assertEqual(model.predict(5), 10)

    def test_model_caching(self):
        """测试模型缓存"""
        model_path = self._save_dummy_model()
        self.manager.register_model("cache-test", "classifier", "1.0.0", model_path)

        model1 = self.manager.load_model("cache-test")
        model2 = self.manager.load_model("cache-test")
        self.assertIs(model1, model2)

    def test_unload_model(self):
        """测试卸载模型"""
        model_path = self._save_dummy_model()
        self.manager.register_model("unload-test", "classifier", "1.0.0", model_path)
        self.manager.load_model("unload-test")

        result = self.manager.unload_model("unload-test")
        self.assertTrue(result)

    def test_set_current_version(self):
        """测试设置当前版本"""
        model_path = self._save_dummy_model("v1.pkl")
        self.manager.register_model("version-test", "classifier", "1.0.0", model_path)

        model_path2 = self._save_dummy_model("v2.pkl")
        self.manager.register_model("version-test", "classifier", "2.0.0", model_path2)

        result = self.manager.set_current_version("version-test", "2.0.0")
        self.assertTrue(result)

        info = self.manager.get_model_info("version-test")
        self.assertEqual(info["current_version"], "2.0.0")

    def test_get_model_versions(self):
        """测试获取模型版本"""
        model_path = self._save_dummy_model()
        self.manager.register_model("multi-version", "classifier", "1.0.0", model_path)
        self.manager.register_model("multi-version", "classifier", "1.1.0", model_path)

        versions = self.manager.get_model_versions("multi-version")
        self.assertEqual(len(versions), 2)

    def test_update_metrics(self):
        """测试更新指标"""
        model_path = self._save_dummy_model()
        self.manager.register_model("metrics-test", "classifier", "1.0.0", model_path)

        result = self.manager.update_metrics("metrics-test", "1.0.0", {"f1": 0.88})
        self.assertTrue(result)

        info = self.manager.get_model_info("metrics-test")
        self.assertEqual(info["versions"]["1.0.0"]["metrics"]["f1"], 0.88)

    def test_deprecate_version(self):
        """测试弃用版本"""
        model_path = self._save_dummy_model()
        self.manager.register_model("deprecate-test", "classifier", "1.0.0", model_path)

        result = self.manager.deprecate_version("deprecate-test", "1.0.0")
        self.assertTrue(result)

        info = self.manager.get_model_info("deprecate-test")
        self.assertEqual(info["versions"]["1.0.0"]["status"], ModelStatus.DEPRECATED.name)

    def test_delete_model(self):
        """测试删除模型"""
        model_path = self._save_dummy_model()
        self.manager.register_model("delete-test", "classifier", "1.0.0", model_path)

        result = self.manager.delete_model("delete-test")
        self.assertTrue(result)
        self.assertNotIn("delete-test", self.manager.get_all_models())

    def test_stats(self):
        """测试统计"""
        model_path = self._save_dummy_model()
        self.manager.register_model("stats-test", "classifier", "1.0.0", model_path)

        stats = self.manager.get_stats()
        self.assertEqual(stats["total_models"], 1)
        self.assertEqual(stats["total_versions"], 1)

    def test_persistence(self):
        """测试持久化"""
        model_path = self._save_dummy_model()
        self.manager.register_model("persist-test", "classifier", "1.0.0", model_path)

        # 创建新的管理器实例
        new_manager = MLModelManager(self.temp_dir)
        self.assertIn("persist-test", new_manager.get_all_models())


class TestSimplePredictor(unittest.TestCase):
    """简单预测器测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MLModelManager(self.temp_dir)
        self.predictor = SimplePredictor(self.manager)

    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_predict(self):
        """测试预测"""
        model_path = os.path.join(self.temp_dir, "pred.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(DummyModel(), f)

        self.manager.register_model("pred-model", "regression", "1.0.0", model_path)

        result = self.predictor.predict("pred-model", 5)
        self.assertEqual(result, 10)

    def test_predict_not_found(self):
        """测试模型不存在"""
        result = self.predictor.predict("nonexistent", 5)
        self.assertIsNone(result)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_model_manager(self):
        """测试获取全局管理器"""
        m1 = get_model_manager()
        m2 = get_model_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 54 - 机器学习模型管理测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMLModelManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSimplePredictor))
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
