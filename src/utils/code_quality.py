"""
代码质量分析器
提供代码度量、复杂度分析、风格检查和质量报告功能
"""
import re
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class Severity(Enum):
    """严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """代码问题"""
    rule_id: str
    message: str
    severity: Severity
    line: int = 0
    column: int = 0
    file_path: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.line,
            "column": self.column,
            "file_path": self.file_path,
            "suggestion": self.suggestion
        }


@dataclass
class CodeMetrics:
    """代码度量"""
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    functions: int = 0
    classes: int = 0
    complexity: int = 0
    max_function_length: int = 0
    avg_function_length: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lines_of_code": self.lines_of_code,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "functions": self.functions,
            "classes": self.classes,
            "complexity": self.complexity,
            "max_function_length": self.max_function_length,
            "avg_function_length": round(self.avg_function_length, 2)
        }


@dataclass
class QualityReport:
    """质量报告"""
    file_path: str
    metrics: CodeMetrics
    issues: List[CodeIssue]
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "metrics": self.metrics.to_dict(),
            "issues": [i.to_dict() for i in self.issues],
            "score": round(self.score, 2),
            "timestamp": self.timestamp
        }


class ComplexityAnalyzer:
    """复杂度分析器"""

    def __init__(self):
        self._logger = get_logger("quality.complexity")

    def calculate_cyclomatic_complexity(self, code: str) -> int:
        """计算圈复杂度"""
        complexity = 1
        # 简单的分支计数
        branch_keywords = ['if', 'elif', 'for', 'while', 'except',
                          'with', 'assert', 'and', 'or']
        for keyword in branch_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', code))
        return complexity

    def calculate_function_length(self, code: str) -> int:
        """计算函数长度"""
        lines = code.split('\n')
        return len([l for l in lines if l.strip()])


class StyleChecker:
    """风格检查器"""

    def __init__(self):
        self._logger = get_logger("quality.style")

    def check_line_length(self, code: str, max_length: int = 120) -> List[CodeIssue]:
        """检查行长度"""
        issues = []
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > max_length:
                issues.append(CodeIssue(
                    rule_id="E501",
                    message=f"Line too long ({len(line)} > {max_length})",
                    severity=Severity.WARNING,
                    line=i
                ))
        return issues

    def check_trailing_whitespace(self, code: str) -> List[CodeIssue]:
        """检查尾部空白"""
        issues = []
        for i, line in enumerate(code.split('\n'), 1):
            if line.rstrip() != line:
                issues.append(CodeIssue(
                    rule_id="W291",
                    message="Trailing whitespace",
                    severity=Severity.INFO,
                    line=i
                ))
        return issues

    def check_import_order(self, code: str) -> List[CodeIssue]:
        """检查导入顺序"""
        issues = []
        lines = code.split('\n')
        import_lines = []
        for i, line in enumerate(lines, 1):
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append((i, line))

        if len(import_lines) > 1:
            for i in range(1, len(import_lines)):
                prev = import_lines[i - 1][1].lower()
                curr = import_lines[i][1].lower()
                if curr < prev:
                    issues.append(CodeIssue(
                        rule_id="I100",
                        message="Import statements are not sorted",
                        severity=Severity.WARNING,
                        line=import_lines[i][0]
                    ))
        return issues


class CodeQualityAnalyzer:
    """代码质量分析器"""

    def __init__(self):
        self._complexity = ComplexityAnalyzer()
        self._style = StyleChecker()
        self._reports: Dict[str, QualityReport] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("quality.analyzer")

    def analyze(self, file_path: str, code: str) -> QualityReport:
        """分析代码"""
        metrics = self._calculate_metrics(code)
        issues = self._check_issues(code)
        score = self._calculate_score(metrics, issues)

        report = QualityReport(
            file_path=file_path,
            metrics=metrics,
            issues=issues,
            score=score
        )

        with self._lock:
            self._reports[file_path] = report

        return report

    def _calculate_metrics(self, code: str) -> CodeMetrics:
        """计算度量"""
        lines = code.split('\n')
        metrics = CodeMetrics()
        metrics.lines_of_code = len(lines)
        metrics.blank_lines = sum(1 for l in lines if not l.strip())
        metrics.comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        metrics.classes = len(re.findall(r'\bclass\b', code))
        metrics.functions = len(re.findall(r'\bdef\b', code))
        metrics.complexity = self._complexity.calculate_cyclomatic_complexity(code)

        # 计算函数长度
        func_lengths = []
        for match in re.finditer(r'def\s+\w+\s*\([^)]*\):', code):
            start = match.end()
            # 简化：计算到下一个def或class
            end_match = re.search(r'\n(def|class)\s', code[start:])
            if end_match:
                func_code = code[start:start + end_match.start()]
            else:
                func_code = code[start:]
            length = self._complexity.calculate_function_length(func_code)
            func_lengths.append(length)

        if func_lengths:
            metrics.max_function_length = max(func_lengths)
            metrics.avg_function_length = sum(func_lengths) / len(func_lengths)

        return metrics

    def _check_issues(self, code: str) -> List[CodeIssue]:
        """检查问题"""
        issues = []
        issues.extend(self._style.check_line_length(code))
        issues.extend(self._style.check_trailing_whitespace(code))
        issues.extend(self._style.check_import_order(code))

        # 检查复杂度
        complexity = self._complexity.calculate_cyclomatic_complexity(code)
        if complexity > 10:
            issues.append(CodeIssue(
                rule_id="C901",
                message=f"Function is too complex ({complexity})",
                severity=Severity.WARNING,
                suggestion="Consider refactoring into smaller functions"
            ))

        return issues

    def _calculate_score(self, metrics: CodeMetrics,
                         issues: List[CodeIssue]) -> float:
        """计算质量分数"""
        score = 100.0

        # 根据复杂度扣分
        if metrics.complexity > 10:
            score -= (metrics.complexity - 10) * 2

        # 根据问题扣分
        for issue in issues:
            if issue.severity == Severity.INFO:
                score -= 1
            elif issue.severity == Severity.WARNING:
                score -= 3
            elif issue.severity == Severity.ERROR:
                score -= 5
            elif issue.severity == Severity.CRITICAL:
                score -= 10

        return max(0.0, min(100.0, score))

    def get_report(self, file_path: str) -> Optional[QualityReport]:
        """获取报告"""
        with self._lock:
            return self._reports.get(file_path)

    def get_all_reports(self) -> List[QualityReport]:
        """获取所有报告"""
        with self._lock:
            return list(self._reports.values())

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总"""
        with self._lock:
            if not self._reports:
                return {"total_files": 0, "average_score": 0.0}

            total_score = sum(r.score for r in self._reports.values())
            total_issues = sum(len(r.issues) for r in self._reports.values())
            by_severity = {}
            for report in self._reports.values():
                for issue in report.issues:
                    s = issue.severity.value
                    by_severity[s] = by_severity.get(s, 0) + 1

            return {
                "total_files": len(self._reports),
                "average_score": round(total_score / len(self._reports), 2),
                "total_issues": total_issues,
                "by_severity": by_severity
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.get_summary()


# 全局实例
_analyzer: Optional[CodeQualityAnalyzer] = None


def get_code_quality_analyzer() -> CodeQualityAnalyzer:
    """获取全局代码质量分析器"""
    global _analyzer
    if _analyzer is None:
        _analyzer = CodeQualityAnalyzer()
    return _analyzer
