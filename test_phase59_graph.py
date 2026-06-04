"""
Phase 59 - 图数据库与图算法测试
验证图存储、遍历和基本图算法功能是否正常工作
"""
import unittest
from src.utils.graph_engine import (
    Graph,
    Node,
    Edge,
    GraphAlgorithms,
    GraphManager,
    get_graph_manager
)


class TestGraph(unittest.TestCase):
    """图测试"""

    def setUp(self):
        """测试前设置"""
        self.graph = Graph("test")
        self.graph.add_node(Node("a", labels=["person"]))
        self.graph.add_node(Node("b", labels=["person"]))
        self.graph.add_node(Node("c", labels=["person"]))
        self.graph.add_node(Node("d", labels=["company"]))

    def test_add_node(self):
        """测试添加节点"""
        self.graph.add_node(Node("e"))
        self.assertIsNotNone(self.graph.get_node("e"))

    def test_add_edge(self):
        """测试添加边"""
        result = self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        self.assertTrue(result)
        self.assertIsNotNone(self.graph.get_edge("e1"))

    def test_add_edge_invalid_node(self):
        """测试添加边到不存在的节点"""
        result = self.graph.add_edge(Edge("e1", "a", "z", "friend"))
        self.assertFalse(result)

    def test_get_neighbors(self):
        """测试获取邻居"""
        self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        self.graph.add_edge(Edge("e2", "a", "c", "friend"))

        neighbors = self.graph.get_neighbors("a")
        self.assertEqual(len(neighbors), 2)
        self.assertIn("b", neighbors)
        self.assertIn("c", neighbors)

    def test_get_predecessors(self):
        """测试获取前驱"""
        self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        self.graph.add_edge(Edge("e2", "c", "b", "friend"))

        predecessors = self.graph.get_predecessors("b")
        self.assertEqual(len(predecessors), 2)

    def test_get_nodes_by_label(self):
        """测试按标签获取节点"""
        nodes = self.graph.get_nodes_by_label("person")
        self.assertEqual(len(nodes), 3)

    def test_get_edges_by_type(self):
        """测试按类型获取边"""
        self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        self.graph.add_edge(Edge("e2", "a", "c", "colleague"))

        edges = self.graph.get_edges_by_type("friend")
        self.assertEqual(len(edges), 1)

    def test_delete_node(self):
        """测试删除节点"""
        self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        result = self.graph.delete_node("a")
        self.assertTrue(result)
        self.assertIsNone(self.graph.get_node("a"))
        self.assertEqual(len(self.graph._edges), 0)

    def test_stats(self):
        """测试统计"""
        self.graph.add_edge(Edge("e1", "a", "b", "friend"))
        stats = self.graph.get_stats()
        self.assertEqual(stats["nodes"], 4)
        self.assertEqual(stats["edges"], 1)


class TestGraphAlgorithms(unittest.TestCase):
    """图算法测试"""

    def setUp(self):
        """测试前设置"""
        self.graph = Graph("algo")
        # 创建图: a -> b -> c, a -> d
        for node_id in ["a", "b", "c", "d"]:
            self.graph.add_node(Node(node_id))
        self.graph.add_edge(Edge("e1", "a", "b"))
        self.graph.add_edge(Edge("e2", "b", "c"))
        self.graph.add_edge(Edge("e3", "a", "d"))

    def test_bfs(self):
        """测试BFS"""
        result = GraphAlgorithms.bfs(self.graph, "a")
        self.assertEqual(result[0], "a")
        self.assertIn("b", result)
        self.assertIn("c", result)
        self.assertIn("d", result)

    def test_dfs(self):
        """测试DFS"""
        result = GraphAlgorithms.dfs(self.graph, "a")
        self.assertEqual(result[0], "a")
        self.assertEqual(len(result), 4)

    def test_shortest_path(self):
        """测试最短路径"""
        path = GraphAlgorithms.shortest_path(self.graph, "a", "c")
        self.assertIsNotNone(path)
        self.assertEqual(path, ["a", "b", "c"])

    def test_shortest_path_no_path(self):
        """测试无路径"""
        # 创建不连通的节点
        self.graph.add_node(Node("e"))
        path = GraphAlgorithms.shortest_path(self.graph, "a", "e")
        self.assertIsNone(path)

    def test_connected_components(self):
        """测试连通分量"""
        # 添加另一个连通分量
        self.graph.add_node(Node("e"))
        self.graph.add_node(Node("f"))
        self.graph.add_edge(Edge("e4", "e", "f"))

        components = GraphAlgorithms.connected_components(self.graph)
        self.assertEqual(len(components), 2)

    def test_degree_centrality(self):
        """测试度中心性"""
        centrality = GraphAlgorithms.degree_centrality(self.graph)
        self.assertEqual(centrality["a"], 2)  # 2 out + 0 in
        self.assertEqual(centrality["b"], 2)  # 1 out + 1 in


class TestGraphManager(unittest.TestCase):
    """图管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = GraphManager()

    def test_create_graph(self):
        """测试创建图"""
        graph = self.manager.create_graph("test")
        self.assertIsNotNone(graph)
        self.assertEqual(graph.name, "test")

    def test_get_graph(self):
        """测试获取图"""
        self.manager.create_graph("test")
        graph = self.manager.get_graph("test")
        self.assertIsNotNone(graph)

    def test_delete_graph(self):
        """测试删除图"""
        self.manager.create_graph("test")
        result = self.manager.delete_graph("test")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_graph("test"))

    def test_get_all_graphs(self):
        """测试获取所有图"""
        self.manager.create_graph("g1")
        self.manager.create_graph("g2")
        graphs = self.manager.get_all_graphs()
        self.assertEqual(len(graphs), 2)

    def test_stats(self):
        """测试统计"""
        self.manager.create_graph("g1")
        stats = self.manager.get_stats()
        self.assertEqual(stats["graphs"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_graph_manager(self):
        """测试获取全局管理器"""
        m1 = get_graph_manager()
        m2 = get_graph_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 59 - 图数据库与图算法测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraph))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphAlgorithms))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphManager))
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
