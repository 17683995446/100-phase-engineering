"""
数据可视化系统
提供图表生成、数据映射、主题配置和实时更新功能
"""
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.structured_logging import get_logger


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"


class DataVisualizationTheme(Enum):
    """可视化主题"""
    LIGHT = "light"
    DARK = "dark"
    CORPORATE = "corporate"
    COLORFUL = "colorful"


@dataclass
class ChartData:
    """图表数据"""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "labels": self.labels,
            "datasets": self.datasets,
            "metadata": self.metadata
        }


@dataclass
class ChartConfig:
    """图表配置"""
    chart_id: str
    title: str
    chart_type: ChartType
    width: int = 800
    height: int = 600
    theme: DataVisualizationTheme = DataVisualizationTheme.LIGHT
    show_legend: bool = True
    show_grid: bool = True
    x_label: str = ""
    y_label: str = ""
    colors: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "title": self.title,
            "chart_type": self.chart_type.value,
            "width": self.width,
            "height": self.height,
            "theme": self.theme.value,
            "show_legend": self.show_legend,
            "show_grid": self.show_grid,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "colors": self.colors,
            "options": self.options
        }


@dataclass
class Chart:
    """图表"""
    chart_id: str
    config: ChartConfig
    data: ChartData
    rendered_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "config": self.config.to_dict(),
            "data": self.data.to_dict(),
            "rendered_at": self.rendered_at,
            "metadata": self.metadata
        }


class DataMapper:
    """数据映射器"""

    def __init__(self):
        self._logger = get_logger("viz.mapper")

    def map_dict_to_labels_datasets(self, data: List[Dict[str, Any]],
                                   label_key: str,
                                   value_key: str,
                                   series_key: Optional[str] = None) -> ChartData:
        """将字典列表映射为图表数据"""
        if not data:
            return ChartData(labels=[], datasets=[])

        labels = sorted(set(str(row.get(label_key, "")) for row in data))
        datasets_map: Dict[str, List[Any]] = {}

        if series_key:
            for row in data:
                series = str(row.get(series_key, "default"))
                if series not in datasets_map:
                    datasets_map[series] = []
                datasets_map[series].append(row.get(value_key, 0))
        else:
            datasets_map["default"] = [row.get(value_key, 0) for row in data]

        datasets = [
            {"name": series, "data": values}
            for series, values in datasets_map.items()
        ]

        return ChartData(labels=labels, datasets=datasets)

    def aggregate_by_label(self, data: List[Dict[str, Any]],
                          label_key: str,
                          value_key: str,
                          agg_type: str = "sum") -> List[Dict[str, Any]]:
        """按标签聚合数据"""
        aggregated: Dict[str, float] = {}

        for row in data:
            label = str(row.get(label_key, ""))
            value = row.get(value_key, 0)
            if not isinstance(value, (int, float)):
                value = 0

            if label not in aggregated:
                aggregated[label] = 0

            if agg_type == "sum":
                aggregated[label] += value
            elif agg_type == "avg" and label in aggregated:
                aggregated[label] = (aggregated[label] + value) / 2
            elif agg_type == "max":
                aggregated[label] = max(aggregated.get(label, value), value)
            elif agg_type == "min":
                aggregated[label] = min(aggregated.get(label, value), value)

        return [
            {label_key: label, value_key: value}
            for label, value in aggregated.items()
        ]


class ChartRenderer:
    """图表渲染器"""

    def __init__(self):
        self._logger = get_logger("viz.renderer")

    def render(self, chart: Chart) -> str:
        """渲染图表（返回SVG格式）"""
        config = chart.config
        data = chart.data

        # 生成简单的SVG
        svg_parts = [
            f'<svg width="{config.width}" height="{config.height}" xmlns="http://www.w3.org/2000/svg">',
            f'<title>{config.title}</title>',
            f'<rect width="100%" height="100%" fill="white"/>'
        ]

        if config.show_grid:
            svg_parts.append('<g class="grid">')
            for i in range(5):
                y = 100 + i * 80
                svg_parts.append(f'<line x1="50" y1="{y}" x2="{config.width - 20}" y2="{y}" stroke="#ddd"/>')
            svg_parts.append('</g>')

        if data.labels:
            max_val = max(
                max(ds.get("data", [0])) for ds in data.datasets
            ) if data.datasets else 1
            bar_width = (config.width - 100) / max(len(data.labels), 1)

            for i, label in enumerate(data.labels):
                x = 60 + i * bar_width
                svg_parts.append(f'<text x="{x}" y="{config.height - 10}" font-size="12">{label}</text>')

            colors = config.colors or ["#3498db", "#e74c3c", "#2ecc71", "#f1c40f"]
            for di, dataset in enumerate(data.datasets):
                values = dataset.get("data", [])
                for i, val in enumerate(values):
                    x = 60 + i * bar_width
                    height = (val / max_val) * (config.height - 150)
                    y = config.height - 50 - height
                    color = colors[di % len(colors)]

                    if config.chart_type == ChartType.BAR:
                        svg_parts.append(
                            f'<rect x="{x}" y="{y}" width="{bar_width - 5}" height="{height}" fill="{color}"/>'
                        )
                    elif config.chart_type == ChartType.LINE:
                        if i > 0:
                            prev_val = values[i - 1]
                            prev_height = (prev_val / max_val) * (config.height - 150)
                            prev_y = config.height - 50 - prev_height
                            svg_parts.append(
                                f'<line x1="{x - bar_width}" y1="{prev_y}" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2"/>'
                            )
                        svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)


class DataVisualizer:
    """数据可视化器"""

    def __init__(self):
        self._charts: Dict[str, Chart] = {}
        self._lock = threading.RLock()
        self._mapper = DataMapper()
        self._renderer = ChartRenderer()
        self._counter = 0
        self._logger = get_logger("viz.visualizer")

    def _generate_id(self) -> str:
        """生成ID"""
        with self._lock:
            self._counter += 1
            return f"CHART_{int(time.time())}_{self._counter}"

    def create_chart(self, config: ChartConfig, data: ChartData) -> Chart:
        """创建图表"""
        with self._lock:
            chart = Chart(
                chart_id=config.chart_id,
                config=config,
                data=data,
                rendered_at=time.time()
            )
            self._charts[config.chart_id] = chart
            return chart

    def create_chart_from_config(self, chart_id: str, title: str,
                               chart_type: ChartType,
                               data: ChartData,
                               **kwargs) -> Chart:
        """从配置创建图表"""
        config = ChartConfig(
            chart_id=chart_id,
            title=title,
            chart_type=chart_type,
            **kwargs
        )
        return self.create_chart(config, data)

    def get_chart(self, chart_id: str) -> Optional[Chart]:
        """获取图表"""
        with self._lock:
            return self._charts.get(chart_id)

    def update_chart(self, chart_id: str, data: ChartData) -> bool:
        """更新图表数据"""
        with self._lock:
            chart = self._charts.get(chart_id)
            if not chart:
                return False
            chart.data = data
            chart.rendered_at = time.time()
            return True

    def delete_chart(self, chart_id: str) -> bool:
        """删除图表"""
        with self._lock:
            if chart_id in self._charts:
                del self._charts[chart_id]
                return True
            return False

    def render_chart(self, chart_id: str) -> Optional[str]:
        """渲染图表"""
        with self._lock:
            chart = self._charts.get(chart_id)
            if not chart:
                return None
            return self._renderer.render(chart)

    def list_charts(self) -> List[Chart]:
        """列出图表"""
        with self._lock:
            return list(self._charts.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            by_type = {}
            for chart in self._charts.values():
                ct = chart.config.chart_type.value
                by_type[ct] = by_type.get(ct, 0) + 1
            return {
                "total_charts": len(self._charts),
                "by_type": by_type
            }


# 全局实例
_visualizer: Optional[DataVisualizer] = None


def get_visualizer() -> DataVisualizer:
    """获取全局可视化器"""
    global _visualizer
    if _visualizer is None:
        _visualizer = DataVisualizer()
    return _visualizer
