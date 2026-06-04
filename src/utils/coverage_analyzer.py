"""
测试覆盖率分析器
提供覆盖率收集、报告生成、趋势分析和阈值检查功能
"""
import time
import threading
import copy
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class CoverageLevel(Enum):
    """覆盖级别"""
    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"


@dataclass
class FileCoverage:
    """文件覆盖率"""
    file_path: str
    total_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    total_functions: int = 0
    covered_functions: int = 0

    @property
    def line_coverage(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return (self.covered_lines / self.total_lines) * 100

    @property
    def branch_coverage(self) -> float:
        if self.total_branches == 0:
            return 100.0
        return (self.covered_branches / self.total_branches) * 100

    @property
    def function_coverage(self) -> float:
        if self.total_functions == 0:
            return 100.0
        return (self.covered_functions / self.total_functions) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "line_coverage": round(self.line_coverage, 2),
            "total_branches": self.total_branches,
            "covered_branches": self.covered_branches,
            "branch_coverage": round(self.branch_coverage, 2),
            "total_functions": self.total_functions,
            "covered_functions": self.covered_functions,
            "function_coverage": round(self.function_coverage, 2)
        }


@dataclass
class CoverageReport:
    """覆盖率报告"""
    report_id: str
    timestamp: float
    files: Dict[str, FileCoverage]
    threshold: float = 80.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_lines(self) -> int:
        return sum(f.total_lines for f in self.files.values())

    @property
    def covered_lines(self) -> int:
        return sum(f.covered_lines for f in self.files.values())

    @property
    def overall_coverage(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return (self.covered_lines / self.total_lines) * 100

    @property
    def passed_threshold(self) -> bool:
        return self.overall_coverage >= self.threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "overall_coverage": round(self.overall_coverage, 2),
            "threshold": self.threshold,
            "passed": self.passed_threshold,
            "total_files": len(self.files),
            "files": {k: v.to_dict() for k, v in self.files.items()}
        }


class CoverageCollector:
    """覆盖率收集器"""

    def __init__(self):
        self._file_coverage: Dict[str, FileCoverage] = {}
        self._covered_lines: Dict[str, Set[int]] = {}
        self._lock = threading.RLock()
        self._logger = get_logger("coverage.collector")

    def register_file(self, file_path: str, total_lines: int,
                      total_branches: int = 0,
                      total_functions: int = 0) -> None:
        """注册文件"""
        with self._lock:
            self._file_coverage[file_path] = FileCoverage(
                file_path=file_path,
                total_lines=total_lines,
                total_branches=total_branches,
                total_functions=total_functions
            )
            self._covered_lines[file_path] = set()

    def cover_line(self, file_path: str, line_number: int) -> None:
        """覆盖行"""
        with self._lock:
            if file_path not in self._file_coverage:
                self.register_file(file_path, line_number)

            self._covered_lines[file_path].add(line_number)
            self._file_coverage[file_path].covered_lines = len(self._covered_lines[file_path])

    def cover_branch(self, file_path: str) -> None:
        """覆盖分支"""
        with self._lock:
            if file_path in self._file_coverage:
                self._file_coverage[file_path].covered_branches += 1

    def cover_function(self, file_path: str) -> None:
        """覆盖函数"""
        with self._lock:
            if file_path in self._file_coverage:
                self._file_coverage[file_path].covered_functions += 1

    def get_file_coverage(self, file_path: str) -> Optional[FileCoverage]:
        """获取文件覆盖率"""
        with self._lock:
            return self._file_coverage.get(file_path)

    def get_all_coverage(self) -> Dict[str, FileCoverage]:
        """获取所有覆盖率"""
        with self._lock:
            return dict(self._file_coverage)

    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._file_coverage.clear()
            self._covered_lines.clear()


class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(self):
        self._collector = CoverageCollector()
        self._reports: Dict[str, CoverageReport] = {}
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._counter = 0
        self._logger = get_logger("coverage.analyzer")

    def _generate_id(self) -> str:
        """生成ID"""
        with self._lock:
            self._counter += 1
            return f"COV_{int(time.time())}_{self._counter}"

    def get_collector(self) -> CoverageCollector:
        """获取收集器"""
        return self._collector

    def generate_report(self, threshold: float = 80.0) -> CoverageReport:
        """生成报告"""
        with self._lock:
            report = CoverageReport(
                report_id=self._generate_id(),
                timestamp=time.time(),
                files=copy.deepcopy(self._collector.get_all_coverage()),
                threshold=threshold
            )
            self._reports[report.report_id] = report

            # 记录历史
            self._history.append({
                "timestamp": report.timestamp,
                "coverage": report.overall_coverage
            })

            return report

    def get_report(self, report_id: str) -> Optional[CoverageReport]:
        """获取报告"""
        with self._lock:
            return self._reports.get(report_id)

    def check_threshold(self, report_id: str) -> bool:
        """检查阈值"""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return False
            return report.passed_threshold

    def get_trend(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取趋势"""
        with self._lock:
            return self._history[-limit:]

    def get_uncovered_files(self, report_id: str) -> List[str]:
        """获取未覆盖文件"""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return []

            return [
                path for path, coverage in report.files.items()
                if coverage.line_coverage == 0
            ]

    def get_low_coverage_files(self, report_id: str,
                               min_coverage: float = 50.0) -> List[Dict[str, Any]]:
        """获取低覆盖率文件"""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return []

            return [
                {
                    "file_path": path,
                    "coverage": coverage.line_coverage
                }
                for path, coverage in report.files.items()
                if coverage.line_coverage < min_coverage
            ]

    def compare_reports(self, report_id1: str,
                        report_id2: str) -> Dict[str, Any]:
        """比较报告"""
        with self._lock:
            r1 = self._reports.get(report_id1)
            r2 = self._reports.get(report_id2)
            if not r1 or not r2:
                return {}

            return {
                "coverage_diff": round(r2.overall_coverage - r1.overall_coverage, 2),
                "before": round(r1.overall_coverage, 2),
                "after": round(r2.overall_coverage, 2),
                "file_count_diff": len(r2.files) - len(r1.files)
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_reports": len(self._reports),
                "total_history_points": len(self._history)
            }


# 全局实例
_analyzer: Optional[CoverageAnalyzer] = None


def get_coverage_analyzer() -> CoverageAnalyzer:
    """获取全局覆盖率分析器"""
    global _analyzer
    if _analyzer is None:
        _analyzer = CoverageAnalyzer()
    return _analyzer
