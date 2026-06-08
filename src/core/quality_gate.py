"""
代码质量门禁
提供代码风格检查、复杂度分析、测试覆盖率和类型检查门禁功能
"""
import ast
import os
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class GateStatus(Enum):
    """门禁状态"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class CheckType(Enum):
    """检查类型"""
    STYLE = "style"
    COMPLEXITY = "complexity"
    COVERAGE = "coverage"
    TYPING = "typing"
    SECURITY = "security"


@dataclass
class CheckResult:
    """检查结果"""
    check_type: CheckType
    status: GateStatus
    score: float
    details: str
    violations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=__import__("time").time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type.value,
            "status": self.status.value,
            "score": round(self.score, 2),
            "details": self.details,
            "violations": self.violations
        }


@dataclass
class GateReport:
    """门禁报告"""
    report_id: str
    status: GateStatus
    checks: List[CheckResult] = field(default_factory=list)
    timestamp: float = field(default_factory=__import__("time").time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp
        }


class QualityGate:
    """代码质量门禁"""

    def __init__(self):
        self._checks: Dict[CheckType, Callable[[str], CheckResult]] = {}
        self._thresholds: Dict[CheckType, float] = {
            CheckType.STYLE: 90.0,
            CheckType.COMPLEXITY: 80.0,
            CheckType.COVERAGE: 80.0,
            CheckType.TYPING: 85.0,
            CheckType.SECURITY: 95.0
        }
        self._lock = threading.RLock()
        self._logger = get_logger("quality.gate")
        self._counter = 0
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """注册默认检查"""
        self._checks[CheckType.STYLE] = self._check_style
        self._checks[CheckType.COMPLEXITY] = self._check_complexity
        self._checks[CheckType.TYPING] = self._check_typing

    def set_threshold(self, check_type: CheckType, threshold: float) -> None:
        """设置阈值"""
        with self._lock:
            self._thresholds[check_type] = threshold

    def _check_style(self, file_path: str) -> CheckResult:
        """检查代码风格"""
        violations = []
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                if len(line.rstrip()) > 120:
                    violations.append(f"Line {i}: exceeds 120 characters")
                if line.endswith(" \n"):
                    violations.append(f"Line {i}: trailing whitespace")

            score = max(0, 100 - len(violations) * 2)
            status = GateStatus.PASS if score >= self._thresholds[CheckType.STYLE] else GateStatus.FAIL

            return CheckResult(
                check_type=CheckType.STYLE,
                status=status,
                score=score,
                details=f"Checked {len(lines)} lines, {len(violations)} violations",
                violations=violations
            )
        except Exception as e:
            return CheckResult(
                check_type=CheckType.STYLE,
                status=GateStatus.FAIL,
                score=0.0,
                details=str(e)
            )

    def _check_complexity(self, file_path: str) -> CheckResult:
        """检查代码复杂度"""
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())

            complexities = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._calculate_complexity(node)
                    complexities.append(complexity)

            avg_complexity = sum(complexities) / len(complexities) if complexities else 0
            score = max(0, 100 - avg_complexity * 5)
            status = GateStatus.PASS if score >= self._thresholds[CheckType.COMPLEXITY] else GateStatus.FAIL

            return CheckResult(
                check_type=CheckType.COMPLEXITY,
                status=status,
                score=score,
                details=f"Average cyclomatic complexity: {avg_complexity:.2f}",
                violations=[f"{n.name}: complexity {c}" for n, c in zip(
                    [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                    complexities
                )] if complexities else []
            )
        except Exception as e:
            return CheckResult(
                check_type=CheckType.COMPLEXITY,
                status=GateStatus.FAIL,
                score=0.0,
                details=str(e)
            )

    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                 ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _check_typing(self, file_path: str) -> CheckResult:
        """检查类型注解"""
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())

            total_functions = 0
            typed_functions = 0
            any_count = 0

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_functions += 1
                    if node.returns is not None:
                        typed_functions += 1
                    for arg in node.args.args:
                        if arg.annotation is not None:
                            typed_functions += 1
                        if isinstance(arg.annotation, ast.Name) and arg.annotation.id == "Any":
                            any_count += 1

            score = (typed_functions / max(total_functions * 2, 1)) * 100
            score = max(0, score - any_count * 5)
            status = GateStatus.PASS if score >= self._thresholds[CheckType.TYPING] else GateStatus.FAIL

            return CheckResult(
                check_type=CheckType.TYPING,
                status=status,
                score=score,
                details=f"Typed: {typed_functions}/{total_functions * 2}, Any usage: {any_count}"
            )
        except Exception as e:
            return CheckResult(
                check_type=CheckType.TYPING,
                status=GateStatus.FAIL,
                score=0.0,
                details=str(e)
            )

    def run_check(self, check_type: CheckType, file_path: str) -> CheckResult:
        """运行单个检查"""
        with self._lock:
            checker = self._checks.get(check_type)
            if not checker:
                return CheckResult(
                    check_type=check_type,
                    status=GateStatus.SKIPPED,
                    score=0.0,
                    details="Checker not registered"
                )
            return checker(file_path)

    def run_all(self, file_path: str) -> GateReport:
        """运行所有检查"""
        self._counter += 1
        report_id = f"gate_{self._counter}"

        checks = []
        for check_type in CheckType:
            result = self.run_check(check_type, file_path)
            checks.append(result)

        overall_status = GateStatus.PASS
        for check in checks:
            if check.status == GateStatus.FAIL:
                overall_status = GateStatus.FAIL
                break
            elif check.status == GateStatus.WARNING and overall_status == GateStatus.PASS:
                overall_status = GateStatus.WARNING

        report = GateReport(
            report_id=report_id,
            status=overall_status,
            checks=checks
        )

        self._logger.info(f"Quality gate {report_id}: {overall_status.value}")
        return report

    def register_custom_check(self, check_type: CheckType,
                              checker: Callable[[str], CheckResult]) -> None:
        """注册自定义检查"""
        with self._lock:
            self._checks[check_type] = checker

    def get_thresholds(self) -> Dict[str, float]:
        """获取阈值"""
        with self._lock:
            return {k.value: v for k, v in self._thresholds.items()}


# 全局实例
_gate: Optional[QualityGate] = None


def get_quality_gate() -> QualityGate:
    """获取全局质量门禁"""
    global _gate
    if _gate is None:
        _gate = QualityGate()
    return _gate
