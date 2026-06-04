"""
Phase 90 - 机器学习平台测试
验证模型训练、评估、部署和实验管理功能
"""
import unittest
from src.utils.ml_platform import (
    MLPlatform,
    ExperimentTracker,
    ModelRegistry,
    ExperimentStatus,
    ModelStatus,
    get_ml_platform
)


class TestExperimentTracker(unittest.TestCase):
    """实验追踪器测试"""

    def setUp(self):
        self.tracker = ExperimentTracker()

    def test_create_experiment(self):
        """测试创建实验"""
        exp = self.tracker.create_experiment("exp1", "Test Experiment", {"lr": 0.01})
        self.assertEqual(exp.experiment_id, "exp1")
        self.assertEqual(exp.status, ExperimentStatus.PENDING)
        self.assertEqual(exp.parameters["lr"], 0.01)

    def test_create_duplicate(self):
        """测试创建重复实验"""
        self.tracker.create_experiment("exp1", "Test")
        with self.assertRaises(ValueError):
            self.tracker.create_experiment("exp1", "Test2")

    def test_start_experiment(self):
        """测试开始实验"""
        self.tracker.create_experiment("exp1", "Test")
        result = self.tracker.start_experiment("exp1")
        self.assertTrue(result)
        self.assertEqual(self.tracker.get_experiment("exp1").status, ExperimentStatus.RUNNING)

    def test_log_metric(self):
        """测试记录指标"""
        self.tracker.create_experiment("exp1", "Test")
        result = self.tracker.log_metric("exp1", "accuracy", 0.95)
        self.assertTrue(result)
        self.assertEqual(self.tracker.get_experiment("exp1").metrics["accuracy"], 0.95)

    def test_log_parameters(self):
        """测试记录参数"""
        self.tracker.create_experiment("exp1", "Test")
        result = self.tracker.log_parameters("exp1", {"batch_size": 32})
        self.assertTrue(result)
        self.assertEqual(self.tracker.get_experiment("exp1").parameters["batch_size"], 32)

    def test_complete_experiment(self):
        """测试完成实验"""
        self.tracker.create_experiment("exp1", "Test")
        self.tracker.start_experiment("exp1")
        result = self.tracker.complete_experiment("exp1")
        self.assertTrue(result)
        self.assertEqual(self.tracker.get_experiment("exp1").status, ExperimentStatus.COMPLETED)

    def test_list_experiments(self):
        """测试列出实验"""
        self.tracker.create_experiment("exp1", "Test1")
        self.tracker.create_experiment("exp2", "Test2")
        exps = self.tracker.list_experiments()
        self.assertEqual(len(exps), 2)

    def test_list_by_status(self):
        """测试按状态列出"""
        self.tracker.create_experiment("exp1", "Test1")
        self.tracker.create_experiment("exp2", "Test2")
        self.tracker.start_experiment("exp2")
        exps = self.tracker.list_experiments(status=ExperimentStatus.RUNNING)
        self.assertEqual(len(exps), 1)

    def test_get_best_experiment(self):
        """测试获取最佳实验"""
        self.tracker.create_experiment("exp1", "Test1")
        self.tracker.start_experiment("exp1")
        self.tracker.log_metric("exp1", "accuracy", 0.90)
        self.tracker.complete_experiment("exp1")

        self.tracker.create_experiment("exp2", "Test2")
        self.tracker.start_experiment("exp2")
        self.tracker.log_metric("exp2", "accuracy", 0.95)
        self.tracker.complete_experiment("exp2")

        best = self.tracker.get_best_experiment("accuracy")
        self.assertEqual(best.experiment_id, "exp2")

    def test_stats(self):
        """测试统计信息"""
        self.tracker.create_experiment("exp1", "Test")
        stats = self.tracker.get_stats()
        self.assertEqual(stats["total_experiments"], 1)


class TestModelRegistry(unittest.TestCase):
    """模型注册表测试"""

    def setUp(self):
        self.registry = ModelRegistry()

    def test_register_model(self):
        """测试注册模型"""
        model = self.registry.register_model("model1", "Classifier", "1.0.0")
        self.assertEqual(model.model_id, "model1")
        self.assertEqual(model.status, ModelStatus.TRAINED)

    def test_register_duplicate(self):
        """测试注册重复模型"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        with self.assertRaises(ValueError):
            self.registry.register_model("model1", "Classifier", "2.0.0")

    def test_update_status(self):
        """测试更新状态"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        result = self.registry.update_model_status("model1", ModelStatus.DEPLOYED)
        self.assertTrue(result)
        self.assertEqual(self.registry.get_model("model1").status, ModelStatus.DEPLOYED)

    def test_update_metrics(self):
        """测试更新指标"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        result = self.registry.update_model_metrics("model1", {"accuracy": 0.95})
        self.assertTrue(result)
        self.assertEqual(self.registry.get_model("model1").metrics["accuracy"], 0.95)

    def test_list_models(self):
        """测试列出模型"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        self.registry.register_model("model2", "Regressor", "1.0.0")
        models = self.registry.list_models()
        self.assertEqual(len(models), 2)

    def test_list_by_status(self):
        """测试按状态列出"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        self.registry.update_model_status("model1", ModelStatus.DEPLOYED)
        models = self.registry.list_models(status=ModelStatus.DEPLOYED)
        self.assertEqual(len(models), 1)

    def test_get_model_versions(self):
        """测试获取模型版本"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        self.registry.register_model("model2", "Classifier", "2.0.0")
        versions = self.registry.get_model_versions("Classifier")
        self.assertEqual(len(versions), 2)

    def test_delete_model(self):
        """测试删除模型"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        result = self.registry.delete_model("model1")
        self.assertTrue(result)
        self.assertIsNone(self.registry.get_model("model1"))

    def test_stats(self):
        """测试统计信息"""
        self.registry.register_model("model1", "Classifier", "1.0.0")
        stats = self.registry.get_stats()
        self.assertEqual(stats["total_models"], 1)


class TestMLPlatform(unittest.TestCase):
    """机器学习平台测试"""

    def setUp(self):
        self.platform = MLPlatform()

    def test_create_experiment(self):
        """测试创建实验"""
        exp = self.platform.create_experiment("exp1", "Test")
        self.assertEqual(exp.experiment_id, "exp1")

    def test_register_model(self):
        """测试注册模型"""
        model = self.platform.register_model("model1", "Classifier", "1.0.0")
        self.assertEqual(model.model_id, "model1")

    def test_get_experiment_tracker(self):
        """测试获取实验追踪器"""
        tracker = self.platform.get_experiment_tracker()
        self.assertIsInstance(tracker, ExperimentTracker)

    def test_get_model_registry(self):
        """测试获取模型注册表"""
        registry = self.platform.get_model_registry()
        self.assertIsInstance(registry, ModelRegistry)

    def test_stats(self):
        """测试统计信息"""
        self.platform.create_experiment("exp1", "Test")
        self.platform.register_model("model1", "Classifier", "1.0.0")
        stats = self.platform.get_stats()
        self.assertEqual(stats["experiments"]["total_experiments"], 1)
        self.assertEqual(stats["models"]["total_models"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_ml_platform(self):
        """测试获取全局ML平台"""
        p1 = get_ml_platform()
        p2 = get_ml_platform()
        self.assertIs(p1, p2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 90 - 机器学习平台测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExperimentTracker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestModelRegistry))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMLPlatform))
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
