"""
报表生成系统
提供数据汇总、报表模板、多种格式导出和定时生成功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.utils.structured_logging import get_logger


class ReportFormat(Enum):
    """报表格式"""
    JSON = "json"
    CSV = "csv"
    TABLE = "table"
    SUMMARY = "summary"


@dataclass
class ReportColumn:
    """报表列"""
    name: str
    key: str
    formatter: Optional[Callable[[Any], str]] = None
    align: str = "left"

    def format(self, value: Any) -> str:
        if self.formatter:
            return self.formatter(value)
        return str(value)


@dataclass
class ReportTemplate:
    """报表模板"""
    template_id: str
    name: str
    columns: List[ReportColumn]
    aggregations: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "columns": [{"name": c.name, "key": c.key} for c in self.columns],
            "aggregations": self.aggregations,
            "filters": self.filters
        }


@dataclass
class Report:
    """报表"""
    report_id: str
    template_id: str
    name: str
    data: List[Dict[str, Any]]
    columns: List[ReportColumn]
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "template_id": self.template_id,
            "name": self.name,
            "data": self.data,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "row_count": len(self.data)
        }

    def to_csv(self) -> str:
        """导出为CSV"""
        lines = []
        # 表头
        lines.append(",".join(c.name for c in self.columns))
        # 数据
        for row in self.data:
            values = []
            for col in self.columns:
                val = row.get(col.key, "")
                val_str = str(val).replace(",", ";")
                values.append(val_str)
            lines.append(",".join(values))
        return "\n".join(lines)

    def to_table(self) -> str:
        """导出为表格"""
        if not self.data:
            return "No data"

        # 计算列宽
        widths = {}
        for col in self.columns:
            widths[col.key] = max(
                len(col.name),
                max(len(str(row.get(col.key, ""))) for row in self.data)
            )

        lines = []
        # 表头
        header = " | ".join(
            col.name.ljust(widths[col.key]) for col in self.columns
        )
        lines.append(header)
        lines.append("-" * len(header))

        # 数据
        for row in self.data:
            line = " | ".join(
                str(row.get(col.key, "")).ljust(widths[col.key])
                for col in self.columns
            )
            lines.append(line)

        return "\n".join(lines)


class ReportGenerator:
    """报表生成器"""

    def __init__(self):
        self._templates: Dict[str, ReportTemplate] = {}
        self._reports: Dict[str, Report] = {}
        self._lock = threading.RLock()
        self._counter = 0
        self._logger = get_logger("report.generator")

    def _generate_id(self) -> str:
        """生成ID"""
        with self._lock:
            self._counter += 1
            return f"RPT_{int(time.time())}_{self._counter}"

    def create_template(self, template_id: str, name: str,
                        columns: List[ReportColumn],
                        aggregations: Optional[Dict[str, str]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> ReportTemplate:
        """创建报表模板"""
        with self._lock:
            if template_id in self._templates:
                raise ValueError(f"Template {template_id} already exists")

            template = ReportTemplate(
                template_id=template_id,
                name=name,
                columns=columns,
                aggregations=aggregations or {},
                metadata=metadata or {}
            )
            self._templates[template_id] = template
            return template

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """获取模板"""
        with self._lock:
            return self._templates.get(template_id)

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        with self._lock:
            if template_id in self._templates:
                del self._templates[template_id]
                return True
            return False

    def generate_report(self, template_id: str, data: List[Dict[str, Any]],
                        name: Optional[str] = None) -> Optional[Report]:
        """生成报表"""
        with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return None

            # 计算汇总
            summary = {}
            for key, agg_type in template.aggregations.items():
                values = [row.get(key, 0) for row in data if isinstance(row.get(key), (int, float))]
                if values:
                    if agg_type == "sum":
                        summary[key] = sum(values)
                    elif agg_type == "avg":
                        summary[key] = sum(values) / len(values)
                    elif agg_type == "max":
                        summary[key] = max(values)
                    elif agg_type == "min":
                        summary[key] = min(values)
                    elif agg_type == "count":
                        summary[key] = len(values)

            report = Report(
                report_id=self._generate_id(),
                template_id=template_id,
                name=name or template.name,
                data=data,
                columns=template.columns,
                summary=summary
            )

            self._reports[report.report_id] = report
            self._logger.info(f"Report generated: {report.report_id}")
            return report

    def get_report(self, report_id: str) -> Optional[Report]:
        """获取报表"""
        with self._lock:
            return self._reports.get(report_id)

    def delete_report(self, report_id: str) -> bool:
        """删除报表"""
        with self._lock:
            if report_id in self._reports:
                del self._reports[report_id]
                return True
            return False

    def list_templates(self) -> List[ReportTemplate]:
        """列出模板"""
        with self._lock:
            return list(self._templates.values())

    def list_reports(self) -> List[Report]:
        """列出报表"""
        with self._lock:
            return list(self._reports.values())

    def export_report(self, report_id: str,
                      format: ReportFormat) -> Optional[str]:
        """导出报表"""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return None

            if format == ReportFormat.JSON:
                import json
                return json.dumps(report.to_dict(), indent=2)
            elif format == ReportFormat.CSV:
                return report.to_csv()
            elif format == ReportFormat.TABLE:
                return report.to_table()
            elif format == ReportFormat.SUMMARY:
                return str(report.summary)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_templates": len(self._templates),
                "total_reports": len(self._reports)
            }


# 全局实例
_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """获取全局报表生成器"""
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator
