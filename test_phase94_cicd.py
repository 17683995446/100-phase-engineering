"""
Phase 94 - CI/CD流水线管理器测试
"""
import unittest
import time
from src.utils.cicd_pipeline import (
    CICDPipelineManager, PipelineDefinition, PipelineRun,
    PipelineStage, PipelineStatus, StageStatus,
    get_cicd_pipeline_manager
)


class TestCICDPipelineManager(unittest.TestCase):
    """CI/CD流水线管理器测试"""

    def setUp(self):
        self.manager = CICDPipelineManager()

    def test_create_pipeline(self):
        """测试创建流水线"""
        pipeline = self.manager.create_pipeline(
            "deploy", "Deploy Pipeline",
            stages=[
                {"stage_id": "build", "name": "Build", "steps": [{"type": "shell", "command": "make"}]},
                {"stage_id": "test", "name": "Test", "steps": [{"type": "shell", "command": "pytest"}]}
            ]
        )
        self.assertEqual(pipeline.pipeline_id, "deploy")
        self.assertEqual(pipeline.name, "Deploy Pipeline")
        self.assertEqual(len(pipeline.stages), 2)

    def test_create_duplicate(self):
        """测试创建重复流水线"""
        self.manager.create_pipeline("deploy", "Deploy")
        with self.assertRaises(ValueError):
            self.manager.create_pipeline("deploy", "Deploy2")

    def test_get_pipeline(self):
        """测试获取流水线"""
        self.manager.create_pipeline("deploy", "Deploy")
        p = self.manager.get_pipeline("deploy")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Deploy")

    def test_list_pipelines(self):
        """测试列出流水线"""
        self.manager.create_pipeline("p1", "P1")
        self.manager.create_pipeline("p2", "P2")
        pipelines = self.manager.list_pipelines()
        self.assertEqual(len(pipelines), 2)

    def test_delete_pipeline(self):
        """测试删除流水线"""
        self.manager.create_pipeline("deploy", "Deploy")
        self.assertTrue(self.manager.delete_pipeline("deploy"))
        self.assertIsNone(self.manager.get_pipeline("deploy"))

    def test_trigger_pipeline(self):
        """测试触发流水线"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[{"stage_id": "build", "name": "Build", "steps": []}]
        )
        run = self.manager.trigger_pipeline("deploy", trigger="git_push")
        self.assertEqual(run.pipeline_id, "deploy")
        self.assertEqual(run.trigger, "git_push")
        self.assertEqual(run.status, PipelineStatus.PENDING)

    def test_run_pipeline_success(self):
        """测试执行流水线成功"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[
                {"stage_id": "build", "name": "Build", "steps": [{"type": "shell", "command": "echo build"}]},
                {"stage_id": "deploy", "name": "Deploy", "steps": [{"type": "shell", "command": "echo deploy"}]}
            ]
        )
        run = self.manager.trigger_pipeline("deploy")
        result = self.manager.run_pipeline(run.run_id)
        self.assertEqual(result.status, PipelineStatus.SUCCESS)
        self.assertGreater(result.duration, 0)

    def test_run_pipeline_with_dependencies(self):
        """测试带依赖的流水线"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[
                {"stage_id": "build", "name": "Build", "steps": []},
                {"stage_id": "test", "name": "Test", "steps": [], "depends_on": ["build"]},
                {"stage_id": "deploy", "name": "Deploy", "steps": [], "depends_on": ["test"]}
            ]
        )
        run = self.manager.trigger_pipeline("deploy")
        result = self.manager.run_pipeline(run.run_id)
        self.assertEqual(result.status, PipelineStatus.SUCCESS)
        # 验证执行顺序
        build_stage = result.stages["build"]
        test_stage = result.stages["test"]
        deploy_stage = result.stages["deploy"]
        self.assertEqual(build_stage.status, StageStatus.SUCCESS)
        self.assertEqual(test_stage.status, StageStatus.SUCCESS)
        self.assertEqual(deploy_stage.status, StageStatus.SUCCESS)

    def test_run_pipeline_skip_dependency_failed(self):
        """测试依赖失败时跳过阶段"""
        def failing_handler(stage, step):
            return False

        self.manager.register_step_handler("fail", failing_handler)
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[
                {"stage_id": "build", "name": "Build", "steps": [{"type": "fail", "command": "x"}]},
                {"stage_id": "deploy", "name": "Deploy", "steps": [], "depends_on": ["build"]}
            ]
        )
        run = self.manager.trigger_pipeline("deploy")
        result = self.manager.run_pipeline(run.run_id)
        self.assertEqual(result.status, PipelineStatus.FAILED)
        self.assertEqual(result.stages["build"].status, StageStatus.FAILED)
        self.assertEqual(result.stages["deploy"].status, StageStatus.SKIPPED)

    def test_run_pipeline_allow_failure(self):
        """测试允许失败的阶段"""
        def failing_handler(stage, step):
            return False

        self.manager.register_step_handler("fail", failing_handler)
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[
                {"stage_id": "lint", "name": "Lint", "steps": [{"type": "fail", "command": "x"}], "allow_failure": True},
                {"stage_id": "deploy", "name": "Deploy", "steps": []}
            ]
        )
        run = self.manager.trigger_pipeline("deploy")
        result = self.manager.run_pipeline(run.run_id)
        self.assertEqual(result.status, PipelineStatus.SUCCESS)
        self.assertEqual(result.stages["lint"].status, StageStatus.FAILED)
        self.assertEqual(result.stages["deploy"].status, StageStatus.SUCCESS)

    def test_cancel_run(self):
        """测试取消运行"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[{"stage_id": "build", "name": "Build", "steps": []}]
        )
        run = self.manager.trigger_pipeline("deploy")
        run.status = PipelineStatus.RUNNING
        run.stages["build"].status = StageStatus.RUNNING
        self.assertTrue(self.manager.cancel_run(run.run_id))
        self.assertEqual(run.status, PipelineStatus.CANCELLED)

    def test_get_run(self):
        """测试获取运行实例"""
        self.manager.create_pipeline("deploy", "Deploy", stages=[])
        run = self.manager.trigger_pipeline("deploy")
        fetched = self.manager.get_run(run.run_id)
        self.assertEqual(fetched.run_id, run.run_id)

    def test_list_runs(self):
        """测试列出运行"""
        self.manager.create_pipeline("deploy", "Deploy", stages=[])
        self.manager.trigger_pipeline("deploy")
        runs = self.manager.list_runs()
        self.assertEqual(len(runs), 1)

    def test_list_runs_by_status(self):
        """测试按状态列出运行"""
        self.manager.create_pipeline("deploy", "Deploy", stages=[])
        run = self.manager.trigger_pipeline("deploy")
        run.status = PipelineStatus.SUCCESS
        runs = self.manager.list_runs(status="success")
        self.assertEqual(len(runs), 1)

    def test_history(self):
        """测试历史记录"""
        self.manager.create_pipeline("deploy", "Deploy", stages=[])
        run = self.manager.trigger_pipeline("deploy")
        self.manager.run_pipeline(run.run_id)
        history = self.manager.get_history()
        self.assertEqual(len(history), 1)

    def test_stats(self):
        """测试统计信息"""
        self.manager.create_pipeline("deploy", "Deploy", stages=[])
        run = self.manager.trigger_pipeline("deploy")
        self.manager.run_pipeline(run.run_id)
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_pipelines"], 1)
        self.assertEqual(stats["total_runs"], 1)
        self.assertEqual(stats["success_count"], 1)

    def test_circular_dependency(self):
        """测试循环依赖检测"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[
                {"stage_id": "a", "name": "A", "depends_on": ["b"]},
                {"stage_id": "b", "name": "B", "depends_on": ["a"]}
            ]
        )
        run = self.manager.trigger_pipeline("deploy")
        with self.assertRaises(ValueError):
            self.manager.run_pipeline(run.run_id)

    def test_variables(self):
        """测试变量传递"""
        self.manager.create_pipeline(
            "deploy", "Deploy",
            stages=[],
            variables={"ENV": "prod"}
        )
        run = self.manager.trigger_pipeline("deploy", variables={"VERSION": "1.0"})
        self.assertEqual(run.variables["ENV"], "prod")
        self.assertEqual(run.variables["VERSION"], "1.0")


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_cicd_pipeline_manager(self):
        """测试获取全局CI/CD流水线管理器"""
        m1 = get_cicd_pipeline_manager()
        m2 = get_cicd_pipeline_manager()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 94 - CI/CD流水线管理器测试")
    print("=" * 60)
    unittest.main(verbosity=2)
