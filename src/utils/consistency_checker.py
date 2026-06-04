"""
数据一致性校验系统
提供数据校验、差异检测、修复建议和一致性报告功能
"""
import hashlib
import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class ConsistencyLevel(Enum):
    """一致性级别"""
    STRICT = "strict"      # 严格一致
    EVENTUAL = "eventual"  # 最终一致
    WEAK = "weak"          # 弱一致


class CheckStatus(Enum):
    """检查状态"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ConsistencyCheck:
    """一致性检查结果"""
    check_id: str
    name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class DiffResult:
    """差异结果"""
    field: str
    source_value: Any
    target_value: Any
    diff_type: str  # "missing", "mismatch", "extra"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "diff_type": self.diff_type
        }


@dataclass
class ConsistencyReport:
    """一致性报告"""
    report_id: str
    total_checks: int
    passed: int
    failed: int
    warnings: int
    errors: int
    checks: List[ConsistencyCheck]
    generated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "errors": self.errors,
            "checks": [c.to_dict() for c in self.checks],
            "generated_at": self.generated_at
        }


class DataHasher:
    """数据哈希器"""

    def hash_dict(self, data: Dict[str, Any]) -> str:
        """计算字典的哈希值"""
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def hash_list(self, data: List[Any]) -> str:
        """计算列表的哈希值"""
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DiffEngine:
    """差异检测引擎"""

    def compare_dicts(self, source: Dict[str, Any],
                      target: Dict[str, Any],
                      path: str = "") -> List[DiffResult]:
        """比较两个字典的差异"""
        diffs = []
        all_keys = set(source.keys()) | set(target.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in source:
                diffs.append(DiffResult(
                    field=current_path,
                    source_value=None,
                    target_value=target[key],
                    diff_type="extra"
                ))
            elif key not in target:
                diffs.append(DiffResult(
                    field=current_path,
                    source_value=source[key],
                    target_value=None,
                    diff_type="missing"
                ))
            elif isinstance(source[key], dict) and isinstance(target[key], dict):
                diffs.extend(self.compare_dicts(source[key], target[key], current_path))
            elif source[key] != target[key]:
                diffs.append(DiffResult(
                    field=current_path,
                    source_value=source[key],
                    target_value=target[key],
                    diff_type="mismatch"
                ))

        return diffs

    def compare_lists(self, source: List[Any],
                      target: List[Any]) -> List[DiffResult]:
        """比较两个列表的差异"""
        diffs = []
        max_len = max(len(source), len(target))

        for i in range(max_len):
            if i >= len(source):
                diffs.append(DiffResult(
                    field=f"[{i}]",
                    source_value=None,
                    target_value=target[i],
                    diff_type="extra"
                ))
            elif i >= len(target):
                diffs.append(DiffResult(
                    field=f"[{i}]",
                    source_value=source[i],
                    target_value=None,
                    diff_type="missing"
                ))
            elif source[i] != target[i]:
                diffs.append(DiffResult(
                    field=f"[{i}]",
                    source_value=source[i],
                    target_value=target[i],
                    diff_type="mismatch"
                ))

        return diffs


class ConsistencyChecker:
    """一致性校验器"""

    def __init__(self):
        self._checks: Dict[str, Callable[[], ConsistencyCheck]] = {}
        self._hasher = DataHasher()
        self._diff_engine = DiffEngine()
        self._lock = threading.RLock()
        self._logger = get_logger("consistency.checker")

    def register_check(self, check_id: str,
                       name: str,
                       check_func: Callable[[], Tuple[bool, str, Dict[str, Any]]]) -> None:
        """注册一致性检查"""
        def wrapper() -> ConsistencyCheck:
            try:
                passed, message, details = check_func()
                status = CheckStatus.PASSED if passed else CheckStatus.FAILED
                return ConsistencyCheck(
                    check_id=check_id,
                    name=name,
                    status=status,
                    message=message,
                    details=details
                )
            except Exception as e:
                return ConsistencyCheck(
                    check_id=check_id,
                    name=name,
                    status=CheckStatus.ERROR,
                    message=f"Check execution failed: {e}",
                    details={"error": str(e)}
                )

        with self._lock:
            self._checks[check_id] = wrapper

    def unregister_check(self, check_id: str) -> bool:
        """注销一致性检查"""
        with self._lock:
            if check_id in self._checks:
                del self._checks[check_id]
                return True
            return False

    def run_check(self, check_id: str) -> Optional[ConsistencyCheck]:
        """运行单个检查"""
        with self._lock:
            check_func = self._checks.get(check_id)
            if not check_func:
                return None
            return check_func()

    def run_all_checks(self) -> ConsistencyReport:
        """运行所有检查"""
        checks = []
        passed = 0
        failed = 0
        warnings = 0
        errors = 0

        with self._lock:
            check_funcs = list(self._checks.values())

        for check_func in check_funcs:
            result = check_func()
            checks.append(result)
            if result.status == CheckStatus.PASSED:
                passed += 1
            elif result.status == CheckStatus.FAILED:
                failed += 1
            elif result.status == CheckStatus.WARNING:
                warnings += 1
            elif result.status == CheckStatus.ERROR:
                errors += 1

        return ConsistencyReport(
            report_id=f"report_{int(time.time())}",
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            warnings=warnings,
            errors=errors,
            checks=checks,
            generated_at=time.time()
        )

    def compare_data(self, source: Dict[str, Any],
                     target: Dict[str, Any]) -> List[DiffResult]:
        """比较两份数据"""
        return self._diff_engine.compare_dicts(source, target)

    def verify_checksum(self, data: Dict[str, Any],
                        expected_checksum: str) -> bool:
        """验证数据校验和"""
        actual = self._hasher.hash_dict(data)
        return actual == expected_checksum

    def generate_checksum(self, data: Dict[str, Any]) -> str:
        """生成数据校验和"""
        return self._hasher.hash_dict(data)

    def get_registered_checks(self) -> List[str]:
        """获取已注册的检查ID列表"""
        with self._lock:
            return list(self._checks.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "registered_checks": len(self._checks)
            }


class DataReconciler:
    """数据协调器"""

    def __init__(self):
        self._logger = get_logger("consistency.reconciler")

    def reconcile(self, source: Dict[str, Any],
                  target: Dict[str, Any],
                  strategy: str = "merge") -> Dict[str, Any]:
        """协调数据差异"""
        if strategy == "source_wins":
            return dict(source)
        elif strategy == "target_wins":
            return dict(target)
        elif strategy == "merge":
            return self._merge_dicts(source, target)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _merge_dicts(self, source: Dict[str, Any],
                     target: Dict[str, Any]) -> Dict[str, Any]:
        """合并两个字典"""
        result = dict(source)
        for key, value in target.items():
            if key not in result:
                result[key] = value
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
        return result


# 全局实例
_checker: Optional[ConsistencyChecker] = None
_reconciler: Optional[DataReconciler] = None


def get_consistency_checker() -> ConsistencyChecker:
    """获取全局一致性校验器"""
    global _checker
    if _checker is None:
        _checker = ConsistencyChecker()
    return _checker


def get_data_reconciler() -> DataReconciler:
    """获取全局数据协调器"""
    global _reconciler
    if _reconciler is None:
        _reconciler = DataReconciler()
    return _reconciler
