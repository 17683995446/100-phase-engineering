"""
增强代码解析与AST处理系统
提供深入的代码结构分析、依赖提取和代码度量
"""

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum, auto
from datetime import datetime
import uuid

from src.utils.logger import logger


class NodeType(Enum):
    """AST节点类型"""
    MODULE = auto()
    CLASS = auto()
    FUNCTION = auto()
    METHOD = auto()
    VARIABLE = auto()
    IMPORT = auto()
    ASSIGNMENT = auto()
    EXPRESSION = auto()
    CONTROL_FLOW = auto()
    DECORATOR = auto()


class ComplexityMetric(Enum):
    """复杂度度量"""
    CYCLOMATIC = auto()    # 圈复杂度
    COGNITIVE = auto()     # 认知复杂度
    NESTING = auto()       # 嵌套深度
    LINES_OF_CODE = auto()  # 代码行数


@dataclass
class ASTNode:
    """AST节点封装"""
    node_id: str
    node_type: NodeType
    name: str
    lineno: int
    end_lineno: Optional[int]
    children: List['ASTNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.name,
            "name": self.name,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "children_count": len(self.children),
            "metadata": self.metadata
        }


@dataclass
class DependencyInfo:
    """依赖信息"""
    module_name: str
    imported_names: List[str]
    import_type: str  # "import" or "from_import"
    line_number: int
    is_builtin: bool = False
    is_third_party: bool = False


@dataclass
class CodeMetrics:
    """代码度量"""
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    cyclomatic_complexity: int
    max_nesting_depth: int
    function_count: int
    class_count: int
    import_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "max_nesting_depth": self.max_nesting_depth,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "import_count": self.import_count
        }


class EnhancedASTProcessor:
    """增强的AST处理器"""
    
    def __init__(self):
        self.builtin_modules = self._get_builtin_modules()
        logger.info("增强AST处理器初始化")
    
    def _get_builtin_modules(self) -> Set[str]:
        """获取内置模块列表"""
        import sys
        return set(sys.stdlib_module_names)
    
    def process_code(self, code: str) -> Dict[str, Any]:
        """处理代码，返回完整分析结果"""
        try:
            tree = ast.parse(code)
            return {
                "success": True,
                "tree": tree,
                "nodes": self._extract_nodes(tree),
                "metrics": self._calculate_metrics(code, tree),
                "dependencies": self._extract_dependencies(tree)
            }
        except SyntaxError as e:
            logger.error(f"语法错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "line": e.lineno
            }
    
    def _extract_nodes(self, tree: ast.AST) -> List[ASTNode]:
        """提取AST节点"""
        nodes = []
        
        for node in ast.walk(tree):
            ast_node = self._create_ast_node(node)
            if ast_node:
                nodes.append(ast_node)
        
        return nodes
    
    def _create_ast_node(self, node: ast.AST) -> Optional[ASTNode]:
        """创建AST节点封装"""
        node_id = str(uuid.uuid4())[:8]
        
        if isinstance(node, ast.Module):
            return ASTNode(
                node_id=node_id,
                node_type=NodeType.MODULE,
                name="<module>",
                lineno=1,
                end_lineno=getattr(node, 'end_lineno', None),
                metadata={"type_comment": getattr(node, 'type_comment', None)}
            )
        
        elif isinstance(node, ast.ClassDef):
            return ASTNode(
                node_id=node_id,
                node_type=NodeType.CLASS,
                name=node.name,
                lineno=node.lineno,
                end_lineno=getattr(node, 'end_lineno', None),
                metadata={
                    "bases": [self._get_name(b) for b in node.bases],
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                    "method_count": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                }
            )
        
        elif isinstance(node, ast.FunctionDef):
            return ASTNode(
                node_id=node_id,
                node_type=NodeType.FUNCTION,
                name=node.name,
                lineno=node.lineno,
                end_lineno=getattr(node, 'end_lineno', None),
                metadata={
                    "args": [arg.arg for arg in node.args.args],
                    "defaults": len(node.args.defaults),
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                    "returns": self._get_name(node.returns)
                }
            )
        
        elif isinstance(node, ast.AsyncFunctionDef):
            return ASTNode(
                node_id=node_id,
                node_type=NodeType.FUNCTION,
                name=node.name,
                lineno=node.lineno,
                end_lineno=getattr(node, 'end_lineno', None),
                metadata={
                    "is_async": True,
                    "args": [arg.arg for arg in node.args.args]
                }
            )
        
        return None
    
    def _get_name(self, node: Optional[ast.AST]) -> Optional[str]:
        """获取节点名称"""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None
    
    def _calculate_metrics(self, code: str, tree: ast.AST) -> CodeMetrics:
        """计算代码度量"""
        lines = code.splitlines()
        
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        code_lines = total_lines - blank_lines - comment_lines
        
        cyclomatic = self._calculate_cyclomatic_complexity(tree)
        max_nesting = self._calculate_max_nesting(tree)
        
        func_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        import_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
        
        return CodeMetrics(
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            cyclomatic_complexity=cyclomatic,
            max_nesting_depth=max_nesting,
            function_count=func_count,
            class_count=class_count,
            import_count=import_count
        )
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.ExceptHandler,)):
                complexity += 1
        
        return complexity
    
    def _calculate_max_nesting(self, tree: ast.AST) -> int:
        """计算最大嵌套深度"""
        max_depth = 0
        
        class NestingVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0
            
            def visit_If(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
        
        visitor = NestingVisitor()
        visitor.visit(tree)
        
        return visitor.max_depth
    
    def _extract_dependencies(self, tree: ast.AST) -> List[DependencyInfo]:
        """提取依赖信息"""
        dependencies = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dep = DependencyInfo(
                        module_name=alias.name,
                        imported_names=[alias.asname or alias.name],
                        import_type="import",
                        line_number=node.lineno,
                        is_builtin=alias.name in self.builtin_modules
                    )
                    dependencies.append(dep)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported = [a.asname or a.name for a in node.names]
                    dep = DependencyInfo(
                        module_name=node.module,
                        imported_names=imported,
                        import_type="from_import",
                        line_number=node.lineno,
                        is_builtin=node.module in self.builtin_modules
                    )
                    dependencies.append(dep)
        
        return dependencies


class CodeStructureAnalyzer:
    """代码结构分析器"""
    
    def __init__(self):
        self.processor = EnhancedASTProcessor()
        logger.info("代码结构分析器初始化")
    
    def analyze_structure(self, code: str) -> Dict[str, Any]:
        """分析代码结构"""
        result = self.processor.process_code(code)
        
        if not result["success"]:
            return result
        
        tree = result["tree"]
        nodes = result["nodes"]
        metrics = result["metrics"]
        dependencies = result["dependencies"]
        
        # 提取类和方法
        classes = []
        functions = []
        
        for node in nodes:
            if node.node_type == NodeType.CLASS:
                classes.append(node)
            elif node.node_type == NodeType.FUNCTION:
                functions.append(node)
        
        # 分析继承关系
        inheritance = self._analyze_inheritance(tree)
        
        # 分析调用关系
        calls = self._analyze_calls(tree)
        
        return {
            "success": True,
            "metrics": metrics.to_dict(),
            "classes": [c.to_dict() for c in classes],
            "functions": [f.to_dict() for f in functions],
            "dependencies": [d.__dict__ for d in dependencies],
            "inheritance": inheritance,
            "calls": calls,
            "statistics": {
                "total_nodes": len(nodes),
                "total_dependencies": len(dependencies)
            }
        }
    
    def _analyze_inheritance(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """分析继承关系"""
        inheritance = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    base_name = self._get_base_name(base)
                    if base_name:
                        bases.append(base_name)
                
                inheritance.append({
                    "class": node.name,
                    "bases": bases,
                    "lineno": node.lineno
                })
        
        return inheritance
    
    def _get_base_name(self, node: ast.AST) -> Optional[str]:
        """获取基类名称"""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._get_base_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return None
    
    def _analyze_calls(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """分析函数调用"""
        calls = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_func_name(node.func)
                if func_name:
                    calls.append({
                        "function": func_name,
                        "lineno": node.lineno,
                        "args_count": len(node.args),
                        "keywords_count": len(node.keywords)
                    })
        
        return calls
    
    def _get_func_name(self, node: ast.AST) -> Optional[str]:
        """获取函数名称"""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._get_func_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return None


class DependencyExtractor:
    """依赖关系提取器"""
    
    def __init__(self):
        self.processor = EnhancedASTProcessor()
        logger.info("依赖提取器初始化")
    
    def extract_dependencies(self, code: str) -> Dict[str, Any]:
        """提取依赖关系"""
        result = self.processor.process_code(code)
        
        if not result["success"]:
            return result
        
        dependencies = result["dependencies"]
        
        # 分类依赖
        builtin = [d for d in dependencies if d.is_builtin]
        third_party = [d for d in dependencies if d.is_third_party]
        local = [d for d in dependencies if not d.is_builtin and not d.is_third_party]
        
        # 构建依赖图
        dependency_graph = {}
        for dep in dependencies:
            if dep.module_name not in dependency_graph:
                dependency_graph[dep.module_name] = []
            dependency_graph[dep.module_name].extend(dep.imported_names)
        
        return {
            "success": True,
            "all_dependencies": [d.__dict__ for d in dependencies],
            "builtin": [d.__dict__ for d in builtin],
            "third_party": [d.__dict__ for d in third_party],
            "local": [d.__dict__ for d in local],
            "dependency_graph": dependency_graph,
            "statistics": {
                "total": len(dependencies),
                "builtin_count": len(builtin),
                "third_party_count": len(third_party),
                "local_count": len(local)
            }
        }
    
    def detect_circular_dependencies(self, codes: Dict[str, str]) -> List[List[str]]:
        """检测循环依赖"""
        dependencies = {}
        
        for module_name, code in codes.items():
            result = self.processor.process_code(code)
            if result["success"]:
                deps = result["dependencies"]
                dependencies[module_name] = [d.module_name for d in deps if not d.is_builtin]
        
        # 检测循环
        cycles = []
        visited = set()
        path = []
        
        def dfs(node: str):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dep in dependencies.get(node, []):
                dfs(dep)
            
            path.pop()
        
        for module in dependencies:
            dfs(module)
        
        return cycles
