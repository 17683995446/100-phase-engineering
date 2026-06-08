"""
Phase 106 - 阶段依赖图与路线图测试
"""
import unittest
import time
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("roadmap", "/workspace/src/core/roadmap.py")
roadmap_module = importlib.util.module_from_spec(spec)
sys.modules["roadmap"] = roadmap_module
spec.loader.exec_module(roadmap_module)
RoadmapManager = roadmap_module.RoadmapManager
PhaseStatus = roadmap_module.PhaseStatus
get_roadmap_manager = roadmap_module.get_roadmap_manager


class TestRoadmapManager(unittest.TestCase):
    """路线图管理器测试"""

    def setUp(self):
        self.roadmap = RoadmapManager()

    def test_add_phase(self):
        """测试添加阶段"""
        phase = self.roadmap.add_phase("p1", "Phase 1", "Description")
        self.assertEqual(phase.phase_id, "p1")
        self.assertEqual(phase.status, PhaseStatus.PENDING)

    def test_add_duplicate_phase(self):
        """测试添加重复阶段"""
        self.roadmap.add_phase("p1", "Phase 1", "Desc")
        with self.assertRaises(ValueError):
            self.roadmap.add_phase("p1", "Phase 1", "Desc")

    def test_start_phase(self):
        """测试开始阶段"""
        self.roadmap.add_phase("p1", "Phase 1", "Desc")
        self.assertTrue(self.roadmap.start_phase("p1"))
        self.assertEqual(self.roadmap.get_phase("p1").status, PhaseStatus.IN_PROGRESS)

    def test_start_phase_with_dependency(self):
        """测试带依赖的阶段"""
        self.roadmap.add_phase("p1", "Phase 1", "Desc")
        self.roadmap.add_phase("p2", "Phase 2", "Desc", depends_on=["p1"])
        self.assertFalse(self.roadmap.start_phase("p2"))
        self.assertEqual(self.roadmap.get_phase("p2").status, PhaseStatus.BLOCKED)

    def test_complete_phase(self):
        """测试完成阶段"""
        self.roadmap.add_phase("p1", "Phase 1", "Desc")
        self.roadmap.start_phase("p1")
        time.sleep(0.01)
        self.assertTrue(self.roadmap.complete_phase("p1"))
        self.assertEqual(self.roadmap.get_phase("p1").status, PhaseStatus.COMPLETED)
        self.assertGreater(self.roadmap.get_phase("p1").duration, 0)

    def test_execution_order(self):
        """测试执行顺序"""
        self.roadmap.add_phase("p3", "Phase 3", "Desc", depends_on=["p2"])
        self.roadmap.add_phase("p1", "Phase 1", "Desc")
        self.roadmap.add_phase("p2", "Phase 2", "Desc", depends_on=["p1"])
        order = self.roadmap.get_execution_order()
        self.assertEqual(order.index("p1"), 0)
        self.assertLess(order.index("p1"), order.index("p2"))
        self.assertLess(order.index("p2"), order.index("p3"))

    def test_circular_dependency(self):
        """测试循环依赖检测"""
        self.roadmap.add_phase("a", "A", "Desc", depends_on=["b"])
        self.roadmap.add_phase("b", "B", "Desc", depends_on=["a"])
        with self.assertRaises(ValueError):
            self.roadmap.get_execution_order()

    def test_critical_path(self):
        """测试关键路径"""
        self.roadmap.add_phase("p1", "P1", "Desc")
        self.roadmap.add_phase("p2", "P2", "Desc", depends_on=["p1"])
        self.roadmap.add_phase("p3", "P3", "Desc", depends_on=["p2"])
        self.roadmap.add_phase("p4", "P4", "Desc", depends_on=["p1"])
        critical = self.roadmap.get_critical_path()
        self.assertIn("p3", critical)

    def test_get_ready_phases(self):
        """测试获取可执行阶段"""
        self.roadmap.add_phase("p1", "P1", "Desc")
        self.roadmap.add_phase("p2", "P2", "Desc", depends_on=["p1"])
        ready = self.roadmap.get_ready_phases()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].phase_id, "p1")

    def test_list_phases(self):
        """测试列出阶段"""
        self.roadmap.add_phase("p1", "P1", "Desc", tags=["core"])
        self.roadmap.add_phase("p2", "P2", "Desc", tags=["core"])
        phases = self.roadmap.list_phases(tag="core")
        self.assertEqual(len(phases), 2)

    def test_generate_mermaid(self):
        """测试生成 Mermaid 图"""
        self.roadmap.add_phase("p1", "P1", "Desc")
        self.roadmap.add_phase("p2", "P2", "Desc", depends_on=["p1"])
        mermaid = self.roadmap.generate_mermaid()
        self.assertIn("graph TD", mermaid)
        self.assertIn("p1 --> p2", mermaid)

    def test_stats(self):
        """测试统计信息"""
        self.roadmap.add_phase("p1", "P1", "Desc")
        self.roadmap.add_phase("p2", "P2", "Desc")
        self.roadmap.start_phase("p1")
        self.roadmap.complete_phase("p1")
        stats = self.roadmap.get_stats()
        self.assertEqual(stats["total_phases"], 2)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["completion_rate"], 50.0)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_roadmap_manager(self):
        """测试获取全局路线图管理器"""
        r1 = get_roadmap_manager()
        r2 = get_roadmap_manager()
        self.assertIs(r1, r2)


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 106 - 阶段依赖图与路线图测试")
    print("=" * 60)
    unittest.main(verbosity=2)
