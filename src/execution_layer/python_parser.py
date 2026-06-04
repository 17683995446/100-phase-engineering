"""
Python代码解析器
使用Python内置AST模块，不依赖Tree-sitter的复杂构建
后续可根据需要集成真实Tree-sitter
"""

import ast
from typing import Dict, Any, List, Optional
from src.execution_layer.base import BaseCodeProcessor
from src.utils.logger import logger


class PythonCodeProcessor(BaseCodeProcessor):
    """
    Python代码处理器
    使用Python标准库AST模块
    """
    
    def __init__(self):
        super().__init__("python")
    
    def parse_code(self, code: str) -> Dict[str, Any]:
        """
        解析Python代码
        
        Args:
            code: 源代码字符串
            
        Returns:
            解析结果
        """
        logger.info("解析Python代码")
        
        try:
            tree = ast.parse(code)
            return {
                "success": True,
                "ast": tree,
                "code": code,
                "language": "python"
            }
        except SyntaxError as e:
            logger.error(f"语法错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "code": code
            }
    
    def analyze_structure(self, parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析代码结构
        
        Args:
            parse_result: 解析结果
            
        Returns:
            结构分析结果
        """
        if not parse_result.get("success"):
            return {"success": False, "error": "解析失败"}
        
        tree = parse_result["ast"]
        code = parse_result["code"]
        
        logger.info("分析代码结构")
        
        # 分析结果
        result = {
            "success": True,
            "functions": [],
            "classes": [],
            "imports": [],
            "variables": [],
            "total_lines": len(code.splitlines())
        }
        
        # 遍历AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node)
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                result["classes"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "methods": methods,
                    "docstring": ast.get_docstring(node)
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        result["imports"].append({
                            "type": "import",
                            "name": name.name,
                            "alias": name.asname
                        })
                else:
                    for name in node.names:
                        result["imports"].append({
                            "type": "from_import",
                            "module": node.module,
                            "name": name.name,
                            "alias": name.asname
                        })
        
        logger.info(f"分析完成: {len(result['classes'])} 类, {len(result['functions'])} 函数")
        return result
    
    def get_variables(self, parse_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取变量列表
        
        Args:
            parse_result: 解析结果
            
        Returns:
            变量列表
        """
        if not parse_result.get("success"):
            return []
        
        variables = []
        tree = parse_result["ast"]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append({
                            "name": target.id,
                            "lineno": node.lineno,
                            "type": "assignment"
                        })
        
        return variables
    
    def get_method_atom_info(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """
        获取方法原子信息（用于四级原子化结构）
        
        Args:
            func_node: 函数节点
            
        Returns:
            方法原子信息
        """
        return {
            "name": func_node.name,
            "lineno": func_node.lineno,
            "args_count": len(func_node.args.args),
            "has_docstring": ast.get_docstring(func_node) is not None,
            "body_lines": func_node.end_lineno - func_node.lineno + 1 if hasattr(func_node, 'end_lineno') else 0
        }


class CodeAnalyzer:
    """
    综合代码分析器
    """
    
    def __init__(self):
        self.python_processor = PythonCodeProcessor()
        logger.info("初始化代码分析器")
    
    def analyze_python_file(self, code: str) -> Dict[str, Any]:
        """
        分析Python文件
        
        Args:
            code: 源代码字符串
            
        Returns:
            完整分析结果
        """
        logger.info("开始完整代码分析")
        
        parse_result = self.python_processor.parse_code(code)
        if not parse_result["success"]:
            return parse_result
        
        structure = self.python_processor.analyze_structure(parse_result)
        variables = self.python_processor.get_variables(parse_result)
        
        return {
            "success": True,
            "parse": parse_result,
            "structure": structure,
            "variables": variables
        }
    
    def check_atomic_structure(self, code: str) -> Dict[str, Any]:
        """
        检查四级原子化结构
        
        Returns:
            原子化检查结果
        """
        analysis = self.analyze_python_file(code)
        if not analysis["success"]:
            return analysis
        
        structure = analysis["structure"]
        
        result = {
            "success": True,
            "variable_atoms": len(analysis["variables"]),
            "method_atoms": len(structure["functions"]),
            "class_atoms": len(structure["classes"]),
            "module_atoms": 1,  # 当前文件
            "recommendations": []
        }
        
        # 简单检查
        for func in structure["functions"]:
            if func.get("body_lines", 0) > 50:
                result["recommendations"].append(
                    f"函数 {func['name']} 可能过长，考虑拆分"
                )
        
        return result
