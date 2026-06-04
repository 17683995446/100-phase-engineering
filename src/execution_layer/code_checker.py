"""
代码质量检查器
集成Ruff静态代码检查
"""

import subprocess
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.utils.logger import logger


class CodeChecker:
    """
    代码质量检查器
    使用Ruff进行静态代码检查
    """
    
    def __init__(self):
        logger.info("初始化代码检查器")
    
    def check_with_ruff(self, code: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        使用Ruff检查代码
        
        Args:
            code: 源代码字符串
            file_path: 可选的文件路径（用于临时文件）
            
        Returns:
            检查结果
        """
        logger.info("使用Ruff检查代码")
        
        temp_file = None
        try:
            if file_path:
                file_to_check = Path(file_path)
                if not file_to_check.exists():
                    file_to_check.write_text(code, encoding='utf-8')
            else:
                temp_file = Path("temp_check.py")
                temp_file.write_text(code, encoding='utf-8')
                file_to_check = temp_file
            
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", str(file_to_check)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = self._parse_ruff_output(result.stdout, result.stderr)
            
            return {
                "success": True,
                "return_code": result.returncode,
                "issues": issues,
                "total_issues": len(issues),
                "has_errors": any(issue.get("severity") in ["error", "E"] for issue in issues),
                "has_warnings": any(issue.get("severity") in ["warning", "W"] for issue in issues)
            }
            
        except Exception as e:
            logger.error(f"检查失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": [],
                "total_issues": 0
            }
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()
    
    def _parse_ruff_output(self, stdout: str, stderr: str) -> List[Dict[str, Any]]:
        """
        解析Ruff输出
        
        Args:
            stdout: 标准输出
            stderr: 标准错误
            
        Returns:
            问题列表
        """
        issues = []
        
        for line in stdout.splitlines():
            if not line.strip():
                continue
                
            # 简单解析，Ruff输出格式: filename:line:col: EXXX message
            parts = line.split(':', 3)
            if len(parts) >= 4:
                try:
                    line_num = int(parts[1].strip())
                    col = int(parts[2].strip())
                    message_part = parts[3].strip()
                    
                    # 提取错误代码
                    error_code = None
                    message = message_part
                    if ' ' in message_part:
                        first_word = message_part.split(' ', 1)[0]
                        if len(first_word) > 1 and first_word[0] in ['E', 'W', 'F', 'I', 'N', 'UP']:
                            error_code = first_word
                            message = message_part.split(' ', 1)[1]
                    
                    issues.append({
                        "line": line_num,
                        "column": col,
                        "code": error_code,
                        "message": message,
                        "severity": "error" if error_code and error_code.startswith(('E', 'F')) else "warning"
                    })
                except (ValueError, IndexError):
                    continue
        
        return issues
    
    def format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """
        格式化问题输出
        
        Args:
            issues: 问题列表
            
        Returns:
            格式化的字符串
        """
        if not issues:
            return "✅ 未发现问题"
        
        result = []
        for issue in issues:
            result.append(f"  - [{issue.get('code', 'N/A')}] Line {issue['line']}: {issue['message']}")
        
        return "\n".join(result)
    
    def check_atomic_compliance(self, code: str) -> Dict[str, Any]:
        """
        检查四级原子化规范合规性
        
        Args:
            code: 源代码
            
        Returns:
            合规性检查结果
        """
        from src.execution_layer.python_parser import CodeAnalyzer
        
        logger.info("检查四级原子化规范合规性")
        
        analyzer = CodeAnalyzer()
        atomic_result = analyzer.check_atomic_structure(code)
        
        if not atomic_result["success"]:
            return atomic_result
        
        # 运行Ruff检查
        ruff_result = self.check_with_ruff(code)
        
        return {
            "success": True,
            "atomic_check": atomic_result,
            "ruff_check": ruff_result,
            "recommendations": atomic_result.get("recommendations", []) + self._generate_recommendations(ruff_result)
        }
    
    def _generate_recommendations(self, ruff_result: Dict[str, Any]) -> List[str]:
        """
        根据Ruff结果生成建议
        
        Args:
            ruff_result: Ruff检查结果
            
        Returns:
            建议列表
        """
        recommendations = []
        if ruff_result.get("total_issues", 0) > 5:
            recommendations.append("建议分批修复代码问题")
        if ruff_result.get("has_errors", False):
            recommendations.append("优先修复错误级问题")
        return recommendations
