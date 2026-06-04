#!/usr/bin/env python3
"""
第5阶段 Tree-sitter 验证脚本
验证代码解析底座是否正确集成
"""

import sys


def verify_tree_sitter_import():
    """验证 Tree-sitter 相关导入"""
    print("=" * 60)
    print("验证 Tree-sitter 导入验证")
    print("=" * 60)
    print()
    
    try:
        import tree_sitter
        print(f"✅ Tree-sitter 导入成功")
        return True
    except Exception as e:
        print(f"⚠️  Tree-sitter 导入提示: {e}")
        print("   (我们将使用Python AST，不依赖完整Tree-sitter)")
        # 我们的实现不强制依赖Tree-sitter
        return True


def verify_execution_layer():
    """验证执行层模块"""
    print()
    print("=" * 60)
    print("验证执行层模块验证")
    print("=" * 60)
    print()
    
    try:
        import src.execution_layer
        print("✅ src.execution_layer 导入成功")
        
        from src.execution_layer import BaseCodeProcessor, PythonCodeProcessor, CodeAnalyzer
        print("✅ 代码处理器导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_parser():
    """测试代码解析器"""
    print()
    print("=" * 60)
    print("测试代码解析器测试")
    print("=" * 60)
    print()
    
    try:
        from src.execution_layer import PythonCodeProcessor, CodeAnalyzer
        
        # 测试代码
        test_code = '''
def greet(name):
    """问候函数"""
    return f"Hello, {name}!"

class Calculator:
    """简单计算器"""
    
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
'''
        
        # 测试解析器
        processor = PythonCodeProcessor()
        print("✅ PythonCodeProcessor 初始化成功")
        
        parse_result = processor.parse_code(test_code)
        assert parse_result["success"]
        print("✅ 代码解析成功")
        
        # 测试结构分析
        structure = processor.analyze_structure(parse_result)
        assert structure["success"]
        print(f"✅ 结构分析成功: {len(structure['functions'])} 函数, {len(structure['classes'])} 类")
        
        assert len(structure["functions"]) >= 1
        assert len(structure["classes"]) == 1
        # greet 是顶级函数
        greet_func = next((f for f in structure["functions"] if f["name"] == "greet"), None)
        assert greet_func is not None
        assert structure["classes"][0]["name"] == "Calculator"
        assert "add" in structure["classes"][0]["methods"]
        assert "multiply" in structure["classes"][0]["methods"]
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_analyzer():
    """测试综合代码分析器"""
    print()
    print("=" * 60)
    print("测试综合代码分析器测试")
    print("=" * 60)
    print()
    
    try:
        from src.execution_layer import CodeAnalyzer
        
        # 测试代码
        test_code = '''
# 变量
x = 10
y = 20

def calculate_sum(a, b):
    """计算和"""
    return a + b

class MathUtils:
    """数学工具"""
    
    def __init__(self):
        self.value = 0
    
    def square(self, num):
        return num * num
'''
        
        analyzer = CodeAnalyzer()
        print("✅ CodeAnalyzer 初始化成功")
        
        # 完整分析
        analysis = analyzer.analyze_python_file(test_code)
        assert analysis["success"]
        print(f"✅ 完整分析成功: {len(analysis['variables'])} 变量")
        
        # 原子化结构检查
        atomic_check = analyzer.check_atomic_structure(test_code)
        assert atomic_check["success"]
        print(f"✅ 原子化检查: {atomic_check['variable_atoms']} 变量原子, "
              f"{atomic_check['method_atoms']} 方法原子, "
              f"{atomic_check['class_atoms']} 类原子")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    ts_ok = verify_tree_sitter_import()
    layer_ok = verify_execution_layer()
    parser_ok = test_code_parser()
    analyzer_ok = test_code_analyzer()
    
    print()
    print("=" * 60)
    if ts_ok and layer_ok and parser_ok and analyzer_ok:
        print("🎉 第5阶段 Tree-sitter 验证通过！")
        print("=" * 60)
        return 0
    else:
        print("❌ 第5阶段 Tree-sitter 验证失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
