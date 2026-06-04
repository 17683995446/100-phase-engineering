"""
DAG (有向无环图) 验证器
遵循依赖单向性公理：整体架构与代码结构保持有向无环DAG，规避循环依赖
"""

from typing import Dict, List, Set, Optional, Any, Callable
from collections import defaultdict, deque
from src.utils.logger import logger


class DAGNode:
    """
    DAG节点
    表示依赖图中的一个节点
    """
    
    def __init__(self, node_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.metadata = metadata or {}
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
    
    def add_dependency(self, node_id: str):
        """添加依赖（指向依赖节点）"""
        self.dependencies.add(node_id)
    
    def add_dependent(self, node_id: str):
        """添加依赖者"""
        self.dependents.add(node_id)
    
    def __repr__(self) -> str:
        return f"DAGNode({self.node_id}, deps={len(self.dependencies)}, dependents={len(self.dependents)})"


class DAG:
    """
    有向无环图
    用于验证系统架构和代码依赖关系
    
    依赖关系：A 依赖 B = 必须先完成 B，再完成 A
    """
    
    def __init__(self, name: str = "DAG"):
        self.name = name
        self.nodes: Dict[str, DAGNode] = {}
        logger.info(f"初始化DAG: {name}")
    
    def add_node(self, node_id: str, metadata: Optional[Dict[str, Any]] = None) -> DAGNode:
        """
        添加节点
        
        Args:
            node_id: 节点ID
            metadata: 节点元数据
            
        Returns:
            创建的节点
        """
        if node_id in self.nodes:
            logger.warning(f"节点已存在: {node_id}")
            return self.nodes[node_id]
        
        node = DAGNode(node_id, metadata)
        self.nodes[node_id] = node
        logger.debug(f"添加节点: {node_id}")
        return node
    
    def add_edge(self, from_node: str, to_node: str):
        """
        添加边 (from_node -> to_node)
        表示 from_node 依赖 to_node（必须先完成 to_node，再完成 from_node）
        
        Args:
            from_node: 起点节点ID（依赖者）
            to_node: 终点节点ID（被依赖者）
        """
        if from_node not in self.nodes:
            self.add_node(from_node)
        if to_node not in self.nodes:
            self.add_node(to_node)
        
        self.nodes[from_node].add_dependency(to_node)
        self.nodes[to_node].add_dependent(from_node)
        
        logger.debug(f"添加边: {from_node} 依赖 {to_node}")
    
    def get_dependencies(self, node_id: str) -> Set[str]:
        """获取节点的直接依赖"""
        if node_id not in self.nodes:
            return set()
        return self.nodes[node_id].dependencies.copy()
    
    def get_dependents(self, node_id: str) -> Set[str]:
        """获取依赖该节点的节点"""
        if node_id not in self.nodes:
            return set()
        return self.nodes[node_id].dependents.copy()
    
    def get_all_dependencies(self, node_id: str) -> Set[str]:
        """
        获取节点的所有传递依赖
        
        Args:
            node_id: 节点ID
            
        Returns:
            所有依赖节点集合
        """
        if node_id not in self.nodes:
            return set()
        
        all_deps = set()
        stack = list(self.nodes[node_id].dependencies)
        
        while stack:
            dep = stack.pop()
            if dep not in all_deps:
                all_deps.add(dep)
                if dep in self.nodes:
                    stack.extend(self.nodes[dep].dependencies - all_deps)
        
        return all_deps
    
    def get_all_dependents(self, node_id: str) -> Set[str]:
        """
        获取节点的所有传递依赖者
        
        Args:
            node_id: 节点ID
            
        Returns:
            所有依赖节点集合
        """
        if node_id not in self.nodes:
            return set()
        
        all_deps = set()
        stack = list(self.nodes[node_id].dependents)
        
        while stack:
            dep = stack.pop()
            if dep not in all_deps:
                all_deps.add(dep)
                if dep in self.nodes:
                    stack.extend(self.nodes[dep].dependents - all_deps)
        
        return all_deps
    
    def topological_sort(self) -> Optional[List[str]]:
        """
        拓扑排序（Kahn算法）
        
        由于 A 依赖 B 时 in_degree[A] += 1，
        排序结果中依赖者会在被依赖者之后，
        这符合"必须先完成被依赖者，再完成依赖者"的语义。
        
        Returns:
            排序后的节点列表，如果存在环则返回None
        """
        in_degree = defaultdict(int)
        for node_id in self.nodes:
            in_degree[node_id] = 0
        
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                in_degree[node_id] += 1
        
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            for dependent in self.nodes[node_id].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.nodes):
            logger.error(f"检测到循环依赖")
            return None
        
        return result
    
    def detect_cycles(self) -> List[List[str]]:
        """
        检测所有循环依赖
        
        Returns:
            循环列表，每个循环是一个节点ID列表
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            if node_id in self.nodes:
                for dep in self.nodes[node_id].dependencies:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        cycle_start = path.index(dep)
                        cycle = path[cycle_start:] + [dep]
                        cycles.append(cycle)
                        return True
            
            path.pop()
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles
    
    def validate(self) -> Dict[str, Any]:
        """
        验证DAG是否有效
        
        Returns:
            验证结果
        """
        result = {
            "valid": True,
            "node_count": len(self.nodes),
            "edge_count": sum(len(n.dependencies) for n in self.nodes.values()),
            "cycles": [],
            "issues": []
        }
        
        if len(self.nodes) == 0:
            result["issues"].append("DAG为空")
            return result
        
        cycles = self.detect_cycles()
        if cycles:
            result["valid"] = False
            result["cycles"] = cycles
            result["issues"].append(f"检测到 {len(cycles)} 个循环依赖")
        
        return result
    
    def __repr__(self) -> str:
        return f"DAG({self.name}, nodes={len(self.nodes)})"


class DAGValidator:
    """
    DAG验证器
    提供系统架构和代码依赖的验证功能
    """
    
    def __init__(self):
        self.dags: Dict[str, DAG] = {}
        logger.info("初始化DAG验证器")
    
    def create_dag(self, name: str) -> DAG:
        """
        创建新的DAG
        
        Args:
            name: DAG名称
            
        Returns:
            创建的DAG实例
        """
        dag = DAG(name)
        self.dags[name] = dag
        logger.info(f"创建DAG: {name}")
        return dag
    
    def get_dag(self, name: str) -> Optional[DAG]:
        """获取DAG"""
        return self.dags.get(name)
    
    def validate_architecture(self) -> Dict[str, Any]:
        """
        验证整体架构的DAG约束
        
        Returns:
            验证结果
        """
        logger.info("验证架构DAG约束")
        
        result = {
            "valid": True,
            "dag_count": len(self.dags),
            "dag_results": {},
            "global_issues": []
        }
        
        for name, dag in self.dags.items():
            dag_result = dag.validate()
            result["dag_results"][name] = dag_result
            if not dag_result["valid"]:
                result["valid"] = False
                result["global_issues"].extend([
                    f"{name}: {issue}" for issue in dag_result["issues"]
                ])
        
        return result
    
    def build_from_dependencies(
        self,
        name: str,
        dependencies: Dict[str, List[str]]
    ) -> DAG:
        """
        从依赖关系构建DAG
        
        Args:
            name: DAG名称
            dependencies: 依赖关系字典，格式: {node: [dep1, dep2, ...]}
            
        Returns:
            构建的DAG
        """
        dag = self.create_dag(name)
        
        for node_id, deps in dependencies.items():
            dag.add_node(node_id)
            for dep in deps:
                dag.add_node(dep)
                dag.add_edge(node_id, dep)
        
        logger.info(f"从依赖关系构建DAG: {name}")
        return dag
    
    def check_circular_import(self, module_dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        检查模块间的循环导入
        
        Args:
            module_dependencies: 模块依赖关系
            
        Returns:
            检查结果
        """
        logger.info("检查循环导入")
        
        dag = self.build_from_dependencies("circular_check", module_dependencies)
        validation = dag.validate()
        
        result = {
            "has_circular": not validation["valid"],
            "circular_modules": validation.get("cycles", []),
            "message": ""
        }
        
        if result["has_circular"]:
            result["message"] = f"检测到循环依赖，涉及模块: {result['circular_modules']}"
            logger.error(result["message"])
        else:
            result["message"] = "未检测到循环依赖"
            logger.info(result["message"])
        
        return result
