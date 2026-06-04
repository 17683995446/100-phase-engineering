"""
Phase 52 - 工作流引擎测试
验证工作流定义、执行和节点编排功能是否正常工作
"""
import unittest
from src.utils.workflow import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowNode,
    NodeStatus,
    WorkflowStatus,
    get_workflow_engine
)


class TestWorkflowEngine(unittest.TestCase):
    """工作流引擎测试"""

    def setUp(self):
        """测试前设置"""
        self.engine = WorkflowEngine()

    def test_register_workflow(self):
        """测试注册工作流"""
        workflow = WorkflowDefinition(workflow_id="wf1", name="test-workflow")
        self.engine.register_workflow(workflow)
        self.assertEqual(self.engine.get_stats()["workflows"], 1)

    def test_simple_workflow(self):
        """测试简单工作流"""
        results = {}

        def step1(**kwargs):
            results["step1"] = "done"
            return "step1-result"

        def step2(**kwargs):
            results["step2"] = "done"
            return "step2-result"

        workflow = WorkflowDefinition(workflow_id="simple", name="simple-wf")
        workflow.add_node(WorkflowNode("n1", "step1", step1))
        workflow.add_node(WorkflowNode("n2", "step2", step2, dependencies=["n1"]))

        self.engine.register_workflow(workflow)
        execution = self.engine.execute_workflow("simple")

        self.assertEqual(execution["status"], WorkflowStatus.COMPLETED)
        self.assertEqual(results["step1"], "done")
        self.assertEqual(results["step2"], "done")

    def test_parallel_execution(self):
        """测试并行执行"""
        results = []

        def task1(**kwargs):
            results.append("task1")
            return "r1"

        def task2(**kwargs):
            results.append("task2")
            return "r2"

        workflow = WorkflowDefinition(workflow_id="parallel", name="parallel-wf")
        workflow.add_node(WorkflowNode("a", "task1", task1))
        workflow.add_node(WorkflowNode("b", "task2", task2))

        self.engine.register_workflow(workflow)
        execution = self.engine.execute_workflow("parallel")

        self.assertEqual(execution["status"], WorkflowStatus.COMPLETED)
        self.assertEqual(len(results), 2)

    def test_workflow_failure(self):
        """测试工作流失败"""
        def fail_step(**kwargs):
            raise ValueError("Step failed")

        workflow = WorkflowDefinition(workflow_id="fail", name="fail-wf")
        workflow.add_node(WorkflowNode("f1", "fail", fail_step))

        self.engine.register_workflow(workflow)
        execution = self.engine.execute_workflow("fail")

        self.assertEqual(execution["status"], WorkflowStatus.FAILED)

    def test_node_results(self):
        """测试节点结果传递"""
        def step1(**kwargs):
            return {"data": "value1"}

        def step2(_results=None, **kwargs):
            prev = _results.get("n1", {})
            return {"data": prev.get("data", "") + "-extended"}

        workflow = WorkflowDefinition(workflow_id="results", name="results-wf")
        workflow.add_node(WorkflowNode("n1", "step1", step1))
        workflow.add_node(WorkflowNode("n2", "step2", step2, dependencies=["n1"]))

        self.engine.register_workflow(workflow)
        execution = self.engine.execute_workflow("results")

        self.assertEqual(execution["status"], WorkflowStatus.COMPLETED)
        self.assertEqual(execution["node_results"]["n2"]["data"], "value1-extended")

    def test_circular_dependency(self):
        """测试循环依赖检测"""
        workflow = WorkflowDefinition(workflow_id="circular", name="circular-wf")
        workflow.add_node(WorkflowNode("a", "node-a", lambda **k: None, dependencies=["b"]))
        workflow.add_node(WorkflowNode("b", "node-b", lambda **k: None, dependencies=["a"]))

        with self.assertRaises(ValueError):
            workflow.get_execution_order()

    def test_context_passing(self):
        """测试上下文传递"""
        received_context = {}

        def step(**kwargs):
            received_context.update(kwargs.get("_context", {}))
            return "ok"

        workflow = WorkflowDefinition(workflow_id="ctx", name="context-wf")
        workflow.add_node(WorkflowNode("n1", "step", step))

        self.engine.register_workflow(workflow)
        self.engine.execute_workflow("ctx", context={"user": "admin"})

        self.assertEqual(received_context["user"], "admin")

    def test_get_execution(self):
        """测试获取执行记录"""
        workflow = WorkflowDefinition(workflow_id="exec", name="exec-wf")
        workflow.add_node(WorkflowNode("n1", "step", lambda **k: "result"))

        self.engine.register_workflow(workflow)
        execution = self.engine.execute_workflow("exec")

        fetched = self.engine.get_execution(execution["execution_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["status"], WorkflowStatus.COMPLETED)

    def test_stats(self):
        """测试统计"""
        workflow = WorkflowDefinition(workflow_id="stats", name="stats-wf")
        workflow.add_node(WorkflowNode("n1", "step", lambda **k: None))

        self.engine.register_workflow(workflow)
        self.engine.execute_workflow("stats")

        stats = self.engine.get_stats()
        self.assertEqual(stats["workflows"], 1)
        self.assertEqual(stats["executions"], 1)
        self.assertEqual(stats["completed"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_workflow_engine(self):
        """测试获取全局引擎"""
        e1 = get_workflow_engine()
        e2 = get_workflow_engine()
        self.assertIs(e1, e2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 52 - 工作流引擎测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWorkflowEngine))
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
