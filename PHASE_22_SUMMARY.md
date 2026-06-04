# Phase 22: 执行层增强：代码解析与AST处理

## 阶段目标

增强执行层代码解析功能，实现深入的AST处理、代码结构分析和依赖关系提取，遵循信息完整公理。

## 核心成果

### 1. 核心类型定义

**文件**: `/workspace/src/execution_layer/code_parser.py`

#### AST节点类型 (NodeType)
```python
class NodeType(Enum):
    MODULE = auto()         # 模块
    CLASS = auto()          # 类
    FUNCTION = auto()       # 函数
    METHOD = auto()         # 方法
    VARIABLE = auto()        # 变量
    IMPORT = auto()          # 导入
    ASSIGNMENT = auto()      # 赋值
    EXPRESSION = auto()      # 表达式
    CONTROL_FLOW = auto()    # 控制流
    DECORATOR = auto()       # 装饰器
```

#### 复杂度度量 (ComplexityMetric)
```python
class ComplexityMetric(Enum):
    CYCLOMATIC = auto()     # 圈复杂度
    COGNITIVE = auto()       # 认知复杂度
    NESTING = auto()         # 嵌套深度
    LINES_OF_CODE = auto()   # 代码行数
```

### 2. 增强AST处理器 (EnhancedASTProcessor)

核心功能：
- `process_code(code)` - 处理代码，返回完整分析
- `_extract_nodes(tree)` - 提取AST节点
- `_calculate_metrics(code, tree)` - 计算代码度量
- `_calculate_cyclomatic_complexity(tree)` - 计算圈复杂度
- `_calculate_max_nesting(tree)` - 计算最大嵌套深度
- `_extract_dependencies(tree)` - 提取依赖信息

### 3. 代码结构分析器 (CodeStructureAnalyzer)

核心功能：
- `analyze_structure(code)` - 分析代码结构
- `_analyze_inheritance(tree)` - 分析继承关系
- `_analyze_calls(tree)` - 分析函数调用

### 4. 依赖关系提取器 (DependencyExtractor)

核心功能：
- `extract_dependencies(code)` - 提取依赖
- `detect_circular_dependencies(codes)` - 检测循环依赖

### 5. 代码度量 (CodeMetrics)

```python
@dataclass
class CodeMetrics:
    total_lines: int              # 总行数
    code_lines: int               # 代码行数
    comment_lines: int            # 注释行数
    blank_lines: int             # 空白行数
    cyclomatic_complexity: int   # 圈复杂度
    max_nesting_depth: int       # 最大嵌套深度
    function_count: int           # 函数数量
    class_count: int             # 类数量
    import_count: int             # 导入数量
```

## 技术特性

### 1. 完整的代码度量

自动计算多种代码质量指标：
```python
metrics = processor.process_code(code)
print(f"圈复杂度: {metrics.cyclomatic_complexity}")
print(f"最大嵌套: {metrics.max_nesting_depth}")
print(f"代码行数: {metrics.code_lines}")
```

### 2. AST节点提取

提取完整的AST结构：
```python
nodes = processor.process_code(code)["nodes"]
for node in nodes:
    print(f"{node.node_type}: {node.name} @ line {node.lineno}")
```

### 3. 依赖分析

分析模块依赖关系：
```python
extractor = DependencyExtractor()
result = extractor.extract_dependencies(code)

print(f"内置模块: {result['builtin']}")
print(f"第三方: {result['third_party']}")
print(f"本地: {result['local']}")
print(f"依赖图: {result['dependency_graph']}")
```

### 4. 继承关系分析

分析类的继承结构：
```python
analyzer = CodeStructureAnalyzer()
result = analyzer.analyze_structure(code)

for inh in result["inheritance"]:
    print(f"{inh['class']} extends {inh['bases']}")
```

### 5. 函数调用分析

分析函数间的调用关系：
```python
calls = result["calls"]
for call in calls:
    print(f"{call['function']} @ line {call['lineno']}")
```

## 验证测试

**文件**: `/workspace/test_code_parser.py`

**测试覆盖**:
- EnhancedASTProcessor (6个测试)
- CodeStructureAnalyzer (4个测试)
- DependencyExtractor (4个测试)
- ASTNode (2个测试)
- CodeMetrics (2个测试)
- 集成测试 (2个测试)

**测试结果**: 20个测试全部通过 ✓

**整体系统测试**: 所有311个测试通过 ✓

## 与现有系统集成

### 1. 执行层导出

已将增强解析器导出到执行层：
```python
# src/execution_layer/__init__.py
from .code_parser import (
    NodeType,
    ComplexityMetric,
    ASTNode,
    DependencyInfo,
    CodeMetrics,
    EnhancedASTProcessor,
    CodeStructureAnalyzer,
    DependencyExtractor
)
```

### 2. 与Phase 12 原子实体集成

- ASTNode对应代码原子实体
- CodeMetrics提供量化分析
- 支持四级原子化结构验证

## 使用示例

### 1. 基本代码分析

```python
from src.execution_layer.code_parser import (
    EnhancedASTProcessor,
    CodeStructureAnalyzer
)

code = '''
class MyClass:
    def method(self):
        pass

def function():
    pass
'''

processor = EnhancedASTProcessor()
result = processor.process_code(code)

print(f"圈复杂度: {result['metrics'].cyclomatic_complexity}")
print(f"类数量: {result['metrics'].class_count}")
```

### 2. 完整结构分析

```python
analyzer = CodeStructureAnalyzer()
result = analyzer.analyze_structure(code)

print(f"类: {result['classes']}")
print(f"函数: {result['functions']}")
print(f"依赖: {result['dependencies']}")
print(f"继承: {result['inheritance']}")
```

### 3. 依赖提取

```python
extractor = DependencyExtractor()
result = extractor.extract_dependencies(code)

for dep in result["all_dependencies"]:
    print(f"{dep['module_name']}: {dep['imported_names']}")
```

## 架构位置

**执行层 (execution_layer)** 核心组件：
- 位置: `src/execution_layer/code_parser.py`
- 导出: `src/execution_layer/__init__.py`
- 依赖: 无外部依赖（使用Python标准库ast）

## 设计原则

1. **信息完整性**: 提取所有有意义的代码结构信息
2. **量化分析**: 提供可量化的代码质量指标
3. **依赖追踪**: 完整追踪模块间的依赖关系
4. **结构分析**: 深入分析代码的继承和调用关系
5. **标准库实现**: 使用Python标准库ast，无需外部依赖

## 统计

- **代码行数**: ~470行
- **测试用例**: 20个
- **测试通过率**: 100%
- **AST节点类型**: 10种
- **代码度量指标**: 9种
- **导出API**: 9个

## 下一步

Phase 23-100 将继续完善系统，增加更多高级功能和特性。
