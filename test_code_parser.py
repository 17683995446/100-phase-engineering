"""
增强代码解析与AST处理验证测试
"""

import pytest
from src.execution_layer.code_parser import (
    NodeType,
    ComplexityMetric,
    ASTNode,
    DependencyInfo,
    CodeMetrics,
    EnhancedASTProcessor,
    CodeStructureAnalyzer,
    DependencyExtractor
)


SAMPLE_CODE = '''
"""
Sample module for testing
"""

import os
from typing import List, Dict
import json

class MyClass:
    """A sample class"""
    
    def __init__(self):
        self.value = 0
    
    def method_a(self, x: int) -> int:
        """Method A"""
        if x > 0:
            return x * 2
        else:
            return x
    
    async def async_method(self):
        """Async method"""
        pass

def standalone_function(a: int, b: int) -> int:
    """A standalone function"""
    result = a + b
    for i in range(10):
        if i > 5:
            result += i
    return result
'''


class TestEnhancedASTProcessor:
    """测试增强AST处理器"""
    
    def test_processor_creation(self):
        """测试创建处理器"""
        processor = EnhancedASTProcessor()
        assert processor is not None
        assert len(processor.builtin_modules) > 0
    
    def test_process_valid_code(self):
        """测试处理有效代码"""
        processor = EnhancedASTProcessor()
        result = processor.process_code(SAMPLE_CODE)
        
        assert result["success"] is True
        assert "tree" in result
        assert "nodes" in result
        assert "metrics" in result
        assert "dependencies" in result
    
    def test_process_invalid_code(self):
        """测试处理无效代码"""
        processor = EnhancedASTProcessor()
        result = processor.process_code("def broken(:")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_extract_nodes(self):
        """测试提取节点"""
        processor = EnhancedASTProcessor()
        result = processor.process_code(SAMPLE_CODE)
        
        nodes = result["nodes"]
        node_types = [n.node_type for n in nodes]
        
        assert NodeType.MODULE in node_types
        assert NodeType.CLASS in node_types
        assert NodeType.FUNCTION in node_types
    
    def test_calculate_metrics(self):
        """测试计算度量"""
        processor = EnhancedASTProcessor()
        result = processor.process_code(SAMPLE_CODE)
        
        metrics = result["metrics"]
        
        assert metrics.total_lines > 0
        assert metrics.code_lines > 0
        assert metrics.function_count > 0
        assert metrics.class_count > 0
    
    def test_extract_dependencies(self):
        """测试提取依赖"""
        processor = EnhancedASTProcessor()
        result = processor.process_code(SAMPLE_CODE)
        
        dependencies = result["dependencies"]
        
        assert len(dependencies) > 0
        
        # 检查内置模块
        os_dep = next((d for d in dependencies if d.module_name == "os"), None)
        assert os_dep is not None
        assert os_dep.is_builtin is True


class TestCodeStructureAnalyzer:
    """测试代码结构分析器"""
    
    def test_analyzer_creation(self):
        """测试创建分析器"""
        analyzer = CodeStructureAnalyzer()
        assert analyzer is not None
    
    def test_analyze_structure(self):
        """测试分析结构"""
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_structure(SAMPLE_CODE)
        
        assert result["success"] is True
        assert "metrics" in result
        assert "classes" in result
        assert "functions" in result
        assert "dependencies" in result
    
    def test_analyze_inheritance(self):
        """测试分析继承"""
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_structure(SAMPLE_CODE)
        
        inheritance = result["inheritance"]
        assert len(inheritance) > 0
        
        my_class = next((i for i in inheritance if i["class"] == "MyClass"), None)
        assert my_class is not None
    
    def test_analyze_calls(self):
        """测试分析调用"""
        analyzer = CodeStructureAnalyzer()
        result = analyzer.analyze_structure(SAMPLE_CODE)
        
        calls = result["calls"]
        assert len(calls) > 0


class TestDependencyExtractor:
    """测试依赖提取器"""
    
    def test_extractor_creation(self):
        """测试创建提取器"""
        extractor = DependencyExtractor()
        assert extractor is not None
    
    def test_extract_dependencies(self):
        """测试提取依赖"""
        extractor = DependencyExtractor()
        result = extractor.extract_dependencies(SAMPLE_CODE)
        
        assert result["success"] is True
        assert "all_dependencies" in result
        assert "builtin" in result
        assert "third_party" in result
        assert "local" in result
        
        assert len(result["all_dependencies"]) > 0
    
    def test_dependency_statistics(self):
        """测试依赖统计"""
        extractor = DependencyExtractor()
        result = extractor.extract_dependencies(SAMPLE_CODE)
        
        stats = result["statistics"]
        assert "total" in stats
        assert "builtin_count" in stats
        
        assert stats["total"] == len(result["all_dependencies"])
    
    def test_dependency_graph(self):
        """测试依赖图"""
        extractor = DependencyExtractor()
        result = extractor.extract_dependencies(SAMPLE_CODE)
        
        graph = result["dependency_graph"]
        assert isinstance(graph, dict)


class TestASTNode:
    """测试AST节点"""
    
    def test_node_creation(self):
        """测试创建节点"""
        node = ASTNode(
            node_id="test-001",
            node_type=NodeType.CLASS,
            name="TestClass",
            lineno=10,
            end_lineno=20
        )
        
        assert node.node_id == "test-001"
        assert node.node_type == NodeType.CLASS
        assert node.name == "TestClass"
        assert node.lineno == 10
    
    def test_node_to_dict(self):
        """测试节点序列化"""
        node = ASTNode(
            node_id="test-002",
            node_type=NodeType.FUNCTION,
            name="test_func",
            lineno=5,
            end_lineno=15,
            metadata={"args": ["a", "b"]}
        )
        
        result = node.to_dict()
        
        assert isinstance(result, dict)
        assert result["node_id"] == "test-002"
        assert result["node_type"] == "FUNCTION"


class TestCodeMetrics:
    """测试代码度量"""
    
    def test_metrics_creation(self):
        """测试创建度量"""
        metrics = CodeMetrics(
            total_lines=100,
            code_lines=80,
            comment_lines=10,
            blank_lines=10,
            cyclomatic_complexity=5,
            max_nesting_depth=3,
            function_count=5,
            class_count=2,
            import_count=3
        )
        
        assert metrics.total_lines == 100
        assert metrics.cyclomatic_complexity == 5
    
    def test_metrics_to_dict(self):
        """测试度量序列化"""
        metrics = CodeMetrics(
            total_lines=100,
            code_lines=80,
            comment_lines=10,
            blank_lines=10,
            cyclomatic_complexity=5,
            max_nesting_depth=3,
            function_count=5,
            class_count=2,
            import_count=3
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result["total_lines"] == 100
        assert result["cyclomatic_complexity"] == 5


def test_complexity_calculation():
    """测试复杂度计算"""
    complex_code = '''
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 100:
                while True:
                    break
    return x
'''
    processor = EnhancedASTProcessor()
    result = processor.process_code(complex_code)
    
    assert result["success"] is True
    assert result["metrics"].cyclomatic_complexity > 1
    assert result["metrics"].max_nesting_depth >= 3


def test_async_function_detection():
    """测试异步函数检测"""
    async_code = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL"""
    pass

def sync_function():
    """Sync function"""
    pass
'''
    processor = EnhancedASTProcessor()
    result = processor.process_code(async_code)
    
    assert result["success"] is True
    
    funcs = [n for n in result["nodes"] if n.node_type == NodeType.FUNCTION]
    async_funcs = [f for f in funcs if f.metadata.get("is_async")]
    
    assert len(async_funcs) == 1
    assert async_funcs[0].name == "fetch_data"
