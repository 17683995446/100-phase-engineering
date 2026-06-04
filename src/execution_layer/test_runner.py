"""
测试运行器
集成Pytest自动化测试
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.utils.logger import logger


class TestRunner:
    """
    测试运行器
    使用Pytest执行测试
    """
    
    def __init__(self):
        logger.info("初始化测试运行器")
    
    def run_tests(
        self,
        test_dir: Optional[str] = None,
        test_file: Optional[str] = None,
        test_pattern: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行测试
        
        Args:
            test_dir: 测试目录
            test_file: 测试文件
            test_pattern: 测试匹配模式
            extra_args: 额外的Pytest参数
            
        Returns:
            测试结果
        """
        logger.info("开始运行测试")
        
        cmd = [sys.executable, "-m", "pytest"]
        
        if test_file:
            cmd.append(test_file)
        elif test_dir:
            cmd.append(test_dir)
        else:
            cmd.append("tests/")
        
        if test_pattern:
            cmd.extend(["-k", test_pattern])
        
        if extra_args:
            cmd.extend(extra_args)
        
        # 确保一些默认参数
        if "-v" not in cmd:
            cmd.append("-v")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": True,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": result.returncode == 0,
                "summary": self._parse_pytest_output(result.stdout)
            }
        except Exception as e:
            logger.error(f"测试运行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "passed": False,
                "summary": None
            }
    
    def _parse_pytest_output(self, stdout: str) -> Dict[str, Any]:
        """
        解析Pytest输出
        
        Args:
            stdout: Pytest标准输出
            
        Returns:
            解析后的摘要
        """
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "warnings": 0
        }
        
        for line in stdout.splitlines():
            line = line.strip()
            
            if line.startswith("======") and "test session starts" in line:
                continue
            
            if line.startswith("======") and any(keyword in line for keyword in ["failed", "passed", "error", "warning"]):
                # 统计通过/失败
                if "passed" in line:
                    try:
                        pass_str = line.split("passed")[0].strip().split()[-1]
                        summary["passed"] = int(pass_str)
                    except (ValueError, IndexError):
                        pass
                
                if "failed" in line:
                    try:
                        fail_str = line.split("failed")[0].strip().split()[-1]
                        summary["failed"] = int(fail_str)
                    except (ValueError, IndexError):
                        pass
                
                if "error" in line:
                    try:
                        err_str = line.split("error")[0].strip().split()[-1]
                        summary["errors"] = int(err_str)
                    except (ValueError, IndexError):
                        pass
                
                if "warning" in line:
                    try:
                        warn_str = line.split("warning")[0].strip().split()[-1]
                        summary["warnings"] = int(warn_str)
                    except (ValueError, IndexError):
                        pass
        
        summary["total"] = summary["passed"] + summary["failed"] + summary["errors"] + summary["skipped"]
        
        return summary
    
    def run_tests_from_code(
        self,
        code: str,
        test_code: str,
        module_name: str = "test_module"
    ) -> Dict[str, Any]:
        """
        从代码字符串运行测试
        
        Args:
            code: 待测试的代码
            test_code: 测试代码
            module_name: 模块名称
            
        Returns:
            测试结果
        """
        logger.info("从代码字符串运行测试")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建源代码文件
            src_file = temp_path / f"{module_name}.py"
            src_file.write_text(code, encoding='utf-8')
            
            # 创建测试文件
            test_file = temp_path / f"test_{module_name}.py"
            test_file.write_text(test_code, encoding='utf-8')
            
            # 运行测试
            return self.run_tests(test_file=str(test_file), extra_args=["-v"])
    
    def generate_simple_test(self, func_name: str, test_cases: List[Dict[str, Any]]) -> str:
        """
        生成简单的测试代码
        
        Args:
            func_name: 函数名
            test_cases: 测试用例列表
            
        Returns:
            测试代码字符串
        """
        test_code_lines = [
            f"import pytest",
            f"",
            f"def test_{func_name}_basic():",
            f"    # 基本测试",
        ]
        
        for i, case in enumerate(test_cases):
            test_code_lines.append(f"    # 测试用例 {i + 1}")
            if "args" in case:
                args_str = ", ".join(repr(a) for a in case["args"])
                if "kwargs" in case:
                    kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in case["kwargs"].items())
                    test_code_lines.append(f"    result = {func_name}({args_str}, {kwargs_str})")
                else:
                    test_code_lines.append(f"    result = {func_name}({args_str})")
            elif "kwargs" in case:
                kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in case["kwargs"].items())
                test_code_lines.append(f"    result = {func_name}({kwargs_str})")
            
            if "expected" in case:
                test_code_lines.append(f"    assert result == {repr(case['expected'])}")
        
        return "\n".join(test_code_lines)
