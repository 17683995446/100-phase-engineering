"""
图数据库与图算法
提供图存储、遍历和基本图算法功能
"""
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class Node:
    """图节点"""
    node_id: str
    labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "labels": self.labels,
            "properties": self.properties
        }


@dataclass
class Edge:
    """图边"""
    edge_id: str
    from_node: str
    to_node: str
    relation_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "relation_type": self.relation_type,
            "properties": self.properties
        }


class Graph:
    """图"""
    
    def __init__(self, name: str):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()
        self._logger = get_logger(f"graph.{name}")
    
    def add_node(self, node: Node) -> bool:
        """添加节点"""
        with self._lock:
            self._nodes[node.node_id] = node
        return True
    
    def add_edge(self, edge: Edge) -> bool:
        """添加边"""
        with self._lock:
            if edge.from_node not in self._nodes or edge.to_node not in self._nodes:
                return False
            
            self._edges[edge.edge_id] = edge
            self._adjacency[edge.from_node].append(edge.to_node)
            self._reverse_adjacency[edge.to_node].append(edge.from_node)
        return True
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        with self._lock:
            return self._nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """获取边"""
        with self._lock:
            return self._edges.get(edge_id)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """获取邻居节点"""
        with self._lock:
            return list(self._adjacency.get(node_id, []))
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """获取前驱节点"""
        with self._lock:
            return list(self._reverse_adjacency.get(node_id, []))
    
    def get_nodes_by_label(self, label: str) -> List[Node]:
        """按标签获取节点"""
        with self._lock:
            return [
                node for node in self._nodes.values()
                if label in node.labels
            ]
    
    def get_edges_by_type(self, relation_type: str) -> List[Edge]:
        """按类型获取边"""
        with self._lock:
            return [
                edge for edge in self._edges.values()
                if edge.relation_type == relation_type
            ]
    
    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        with self._lock:
            if node_id not in self._nodes:
                return False
            
            del self._nodes[node_id]
            
            # 删除相关边
            edges_to_remove = [
                edge_id for edge_id, edge in self._edges.items()
                if edge.from_node == node_id or edge.to_node == node_id
            ]
            
            for edge_id in edges_to_remove:
                edge = self._edges[edge_id]
                self._adjacency[edge.from_node].remove(edge.to_node)
                self._reverse_adjacency[edge.to_node].remove(edge.from_node)
                del self._edges[edge_id]
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "nodes": len(self._nodes),
                "edges": len(self._edges),
                "name": self.name
            }


class GraphAlgorithms:
    """图算法"""
    
    @staticmethod
    def bfs(graph: Graph, start_node: str, 
            target_node: Optional[str] = None) -> List[str]:
        """广度优先搜索"""
        if start_node not in [n.node_id for n in graph._nodes.values()]:
            return []
        
        visited = set()
        queue = deque([start_node])
        visited.add(start_node)
        result = [start_node]
        
        while queue:
            current = queue.popleft()
            
            if target_node and current == target_node:
                return result
            
            for neighbor in graph.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    result.append(neighbor)
        
        return result
    
    @staticmethod
    def dfs(graph: Graph, start_node: str) -> List[str]:
        """深度优先搜索"""
        if start_node not in [n.node_id for n in graph._nodes.values()]:
            return []
        
        visited = set()
        result = []
        
        def _dfs(node_id: str):
            visited.add(node_id)
            result.append(node_id)
            
            for neighbor in graph.get_neighbors(node_id):
                if neighbor not in visited:
                    _dfs(neighbor)
        
        _dfs(start_node)
        return result
    
    @staticmethod
    def shortest_path(graph: Graph, start: str, 
                      end: str) -> Optional[List[str]]:
        """最短路径（BFS）"""
        if start not in [n.node_id for n in graph._nodes.values()]:
            return None
        if end not in [n.node_id for n in graph._nodes.values()]:
            return None
        
        visited = {start: None}
        queue = deque([start])
        
        while queue:
            current = queue.popleft()
            
            if current == end:
                # 重建路径
                path = []
                while current is not None:
                    path.append(current)
                    current = visited[current]
                return path[::-1]
            
            for neighbor in graph.get_neighbors(current):
                if neighbor not in visited:
                    visited[neighbor] = current
                    queue.append(neighbor)
        
        return None
    
    @staticmethod
    def connected_components(graph: Graph) -> List[List[str]]:
        """连通分量"""
        visited = set()
        components = []
        
        for node_id in [n.node_id for n in graph._nodes.values()]:
            if node_id not in visited:
                component = GraphAlgorithms.dfs(graph, node_id)
                visited.update(component)
                components.append(component)
        
        return components
    
    @staticmethod
    def degree_centrality(graph: Graph) -> Dict[str, int]:
        """度中心性"""
        centrality = {}
        for node_id in [n.node_id for n in graph._nodes.values()]:
            out_degree = len(graph.get_neighbors(node_id))
            in_degree = len(graph.get_predecessors(node_id))
            centrality[node_id] = out_degree + in_degree
        return centrality


class GraphManager:
    """图管理器"""
    
    def __init__(self):
        self._graphs: Dict[str, Graph] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("graph.manager")
    
    def create_graph(self, name: str) -> Graph:
        """创建图"""
        with self._lock:
            if name not in self._graphs:
                self._graphs[name] = Graph(name)
        return self._graphs[name]
    
    def get_graph(self, name: str) -> Optional[Graph]:
        """获取图"""
        with self._lock:
            return self._graphs.get(name)
    
    def delete_graph(self, name: str) -> bool:
        """删除图"""
        with self._lock:
            if name in self._graphs:
                del self._graphs[name]
                return True
            return False
    
    def get_all_graphs(self) -> List[str]:
        """获取所有图名称"""
        with self._lock:
            return list(self._graphs.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "graphs": len(self._graphs),
                "graph_names": list(self._graphs.keys())
            }


# 全局实例
_manager: Optional[GraphManager] = None


def get_graph_manager() -> GraphManager:
    """获取图管理器"""
    global _manager
    if _manager is None:
        _manager = GraphManager()
    return _manager
