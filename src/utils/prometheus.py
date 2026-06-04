"""
Prometheus 指标收集系统
可观测性公理: 系统状态完全可观测，无隐藏状态，提供 Prometheus 标准格式
"""

import time
import threading
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum, auto
from collections import defaultdict
from datetime import datetime
from src.utils.logger import logger


class PromMetricType(Enum):
    """Prometheus 指标类型"""
    COUNTER = auto()      # 计数器
    GAUGE = auto()        # 仪表盘
    HISTOGRAM = auto()    # 直方图
    SUMMARY = auto()      # 摘要


@dataclass
class LabelPair:
    """标签对"""
    name: str
    value: str


@dataclass
class HistogramBucket:
    """直方图桶"""
    upper_bound: float
    count: int = 0


@dataclass
class SummaryQuantile:
    """摘要分位数"""
    quantile: float
    value: float


class MetricFamily:
    """指标族（一组具有相同名称和标签集的指标）"""
    
    def __init__(
        self,
        name: str,
        metric_type: PromMetricType,
        help_text: str = ""
    ):
        self.name = name
        self.type = metric_type
        self.help = help_text
        self.samples: Dict[str, Any] = {}  # 标签字符串 -> 指标数据
        self._lock = threading.RLock()
    
    def get_labels_key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """将标签字典转换为字符串键"""
        if not labels:
            return ""
        # 排序以确保一致性
        sorted_pairs = sorted(labels.items())
        return ",".join(f"{k}={v}" for k, v in sorted_pairs)


class Counter:
    """Prometheus 计数器（只增不减）"""
    
    def __init__(self, family: MetricFamily, labels: Optional[Dict[str, str]] = None):
        self.family = family
        self.labels = labels or {}
        self.value: float = 0.0
        self.created_at: float = time.time()
    
    def inc(self, value: float = 1.0):
        """递增计数器"""
        if value < 0:
            raise ValueError("Counter cannot decrease")
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.value += value
            self.family.samples[key] = self
    
    def get(self) -> float:
        """获取当前值"""
        return self.value


class Gauge:
    """Prometheus 仪表盘（可增可减）"""
    
    def __init__(self, family: MetricFamily, labels: Optional[Dict[str, str]] = None):
        self.family = family
        self.labels = labels or {}
        self.value: float = 0.0
    
    def set(self, value: float):
        """设置值"""
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.value = value
            self.family.samples[key] = self
    
    def inc(self, value: float = 1.0):
        """递增"""
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.value += value
            self.family.samples[key] = self
    
    def dec(self, value: float = 1.0):
        """递减"""
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.value -= value
            self.family.samples[key] = self
    
    def get(self) -> float:
        """获取当前值"""
        return self.value


class Histogram:
    """Prometheus 直方图"""
    
    def __init__(
        self,
        family: MetricFamily,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None
    ):
        self.family = family
        self.labels = labels or {}
        self.buckets: List[HistogramBucket] = []
        self.count: int = 0
        self.sum: float = 0.0
        
        if buckets:
            for upper_bound in buckets:
                self.buckets.append(HistogramBucket(upper_bound=upper_bound))
        else:
            # 默认桶
            default_buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
            for upper_bound in default_buckets:
                self.buckets.append(HistogramBucket(upper_bound=upper_bound))
        # 添加 +Inf 桶
        self.buckets.append(HistogramBucket(upper_bound=float('inf')))
    
    def observe(self, value: float):
        """记录观测值"""
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.count += 1
            self.sum += value
            for bucket in self.buckets:
                if value <= bucket.upper_bound or bucket.upper_bound == float('inf'):
                    bucket.count += 1
            self.family.samples[key] = self


class Summary:
    """Prometheus 摘要"""
    
    def __init__(
        self,
        family: MetricFamily,
        labels: Optional[Dict[str, str]] = None,
        quantiles: Optional[List[float]] = None
    ):
        self.family = family
        self.labels = labels or {}
        self.quantiles: List[SummaryQuantile] = []
        self.count: int = 0
        self.sum: float = 0.0
        self._values: List[float] = []  # 保留最近的值用于计算分位数
        self._max_values: int = 1000
        
        if quantiles:
            for q in quantiles:
                self.quantiles.append(SummaryQuantile(quantile=q, value=0.0))
        else:
            # 默认分位数
            default_quantiles = [0.5, 0.9, 0.95, 0.99]
            for q in default_quantiles:
                self.quantiles.append(SummaryQuantile(quantile=q, value=0.0))
    
    def observe(self, value: float):
        """记录观测值"""
        with self.family._lock:
            key = self.family.get_labels_key(self.labels)
            self.count += 1
            self.sum += value
            self._values.append(value)
            
            if len(self._values) > self._max_values:
                self._values = self._values[-self._max_values:]
            
            # 重新计算分位数
            if len(self._values) > 0:
                sorted_values = sorted(self._values)
                for q in self.quantiles:
                    index = int(math.ceil(q.quantile * len(sorted_values))) - 1
                    index = max(0, min(index, len(sorted_values) - 1))
                    q.value = sorted_values[index]
            
            self.family.samples[key] = self


class PrometheusRegistry:
    """Prometheus 指标注册表"""
    
    def __init__(self, namespace: str = "maes"):
        self.namespace = namespace
        self.families: Dict[str, MetricFamily] = {}
        self._lock = threading.RLock()
        logger.info(f"Prometheus 指标注册表初始化 (namespace={namespace})")
    
    def create_counter(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Counter:
        """创建计数器"""
        full_name = f"{self.namespace}_{name}" if self.namespace else name
        with self._lock:
            if full_name not in self.families:
                self.families[full_name] = MetricFamily(full_name, PromMetricType.COUNTER, help_text)
            
            family = self.families[full_name]
            counter = Counter(family, labels)
            key = family.get_labels_key(labels)
            family.samples[key] = counter
            return counter
    
    def create_gauge(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Gauge:
        """创建仪表盘"""
        full_name = f"{self.namespace}_{name}" if self.namespace else name
        with self._lock:
            if full_name not in self.families:
                self.families[full_name] = MetricFamily(full_name, PromMetricType.GAUGE, help_text)
            
            family = self.families[full_name]
            gauge = Gauge(family, labels)
            key = family.get_labels_key(labels)
            family.samples[key] = gauge
            return gauge
    
    def create_histogram(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """创建直方图"""
        full_name = f"{self.namespace}_{name}" if self.namespace else name
        with self._lock:
            if full_name not in self.families:
                self.families[full_name] = MetricFamily(full_name, PromMetricType.HISTOGRAM, help_text)
            
            family = self.families[full_name]
            histogram = Histogram(family, labels, buckets)
            key = family.get_labels_key(labels)
            family.samples[key] = histogram
            return histogram
    
    def create_summary(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Dict[str, str]] = None,
        quantiles: Optional[List[float]] = None
    ) -> Summary:
        """创建摘要"""
        full_name = f"{self.namespace}_{name}" if self.namespace else name
        with self._lock:
            if full_name not in self.families:
                self.families[full_name] = MetricFamily(full_name, PromMetricType.SUMMARY, help_text)
            
            family = self.families[full_name]
            summary = Summary(family, labels, quantiles)
            key = family.get_labels_key(labels)
            family.samples[key] = summary
            return summary
    
    def register_family(self, family: MetricFamily):
        """注册指标族"""
        with self._lock:
            self.families[family.name] = family
    
    def unregister(self, name: str):
        """取消注册指标"""
        with self._lock:
            full_name = f"{self.namespace}_{name}" if self.namespace else name
            if full_name in self.families:
                del self.families[full_name]
    
    def generate_text_format(self) -> str:
        """生成 Prometheus 文本格式输出"""
        lines = []
        with self._lock:
            for name, family in self.families.items():
                # 帮助信息
                if family.help:
                    lines.append(f"# HELP {name} {family.help}")
                # 类型信息
                type_str = family.type.name.lower()
                lines.append(f"# TYPE {name} {type_str}")
                
                # 样本数据
                for sample in family.samples.values():
                    if family.type == PromMetricType.COUNTER:
                        lines.extend(self._render_counter(name, sample))
                    elif family.type == PromMetricType.GAUGE:
                        lines.extend(self._render_gauge(name, sample))
                    elif family.type == PromMetricType.HISTOGRAM:
                        lines.extend(self._render_histogram(name, sample))
                    elif family.type == PromMetricType.SUMMARY:
                        lines.extend(self._render_summary(name, sample))
        
        return "\n".join(lines) + "\n"
    
    def _render_counter(self, name: str, counter: Counter) -> List[str]:
        """渲染计数器"""
        label_str = self._format_labels(counter.labels)
        line = f"{name}{label_str} {counter.value}"
        return [line]
    
    def _render_gauge(self, name: str, gauge: Gauge) -> List[str]:
        """渲染仪表盘"""
        label_str = self._format_labels(gauge.labels)
        line = f"{name}{label_str} {gauge.value}"
        return [line]
    
    def _render_histogram(self, name: str, histogram: Histogram) -> List[str]:
        """渲染直方图"""
        lines = []
        label_str = self._format_labels(histogram.labels)
        
        # 渲染桶
        for bucket in histogram.buckets:
            bucket_labels = histogram.labels.copy()
            if bucket.upper_bound == float('inf'):
                bucket_labels['le'] = '+Inf'
            else:
                bucket_labels['le'] = str(bucket.upper_bound)
            bucket_label_str = self._format_labels(bucket_labels)
            lines.append(f"{name}_bucket{bucket_label_str} {bucket.count}")
        
        # 渲染总数
        lines.append(f"{name}_sum{label_str} {histogram.sum}")
        lines.append(f"{name}_count{label_str} {histogram.count}")
        
        return lines
    
    def _render_summary(self, name: str, summary: Summary) -> List[str]:
        """渲染摘要"""
        lines = []
        label_str = self._format_labels(summary.labels)
        
        # 渲染分位数
        for q in summary.quantiles:
            quantile_labels = summary.labels.copy()
            quantile_labels['quantile'] = str(q.quantile)
            q_label_str = self._format_labels(quantile_labels)
            lines.append(f"{name}{q_label_str} {q.value}")
        
        # 渲染总数
        lines.append(f"{name}_sum{label_str} {summary.sum}")
        lines.append(f"{name}_count{label_str} {summary.count}")
        
        return lines
    
    def _format_labels(self, labels: Optional[Dict[str, str]] = None) -> str:
        """格式化标签字符串"""
        if not labels:
            return ""
        parts = []
        for key, value in sorted(labels.items()):
            # 转义特殊字符
            escaped_value = value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
            parts.append(f'{key}="{escaped_value}"')
        return "{" + ",".join(parts) + "}"


def timer(metric: Union[Histogram, Summary]) -> Callable:
    """计时器装饰器（用于测量函数执行时间）"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        return wrapper
    return decorator


# 全局默认注册表
_default_registry: Optional[PrometheusRegistry] = None


def get_default_registry() -> PrometheusRegistry:
    """获取默认注册表"""
    global _default_registry
    if _default_registry is None:
        _default_registry = PrometheusRegistry()
    return _default_registry


def set_default_registry(registry: PrometheusRegistry):
    """设置默认注册表"""
    global _default_registry
    _default_registry = registry


# 便捷函数
def counter(
    name: str,
    help_text: str = "",
    labels: Optional[Dict[str, str]] = None
) -> Counter:
    """创建并获取默认注册表中的计数器"""
    return get_default_registry().create_counter(name, help_text, labels)


def gauge(
    name: str,
    help_text: str = "",
    labels: Optional[Dict[str, str]] = None
) -> Gauge:
    """创建并获取默认注册表中的仪表盘"""
    return get_default_registry().create_gauge(name, help_text, labels)


def histogram(
    name: str,
    help_text: str = "",
    labels: Optional[Dict[str, str]] = None,
    buckets: Optional[List[float]] = None
) -> Histogram:
    """创建并获取默认注册表中的直方图"""
    return get_default_registry().create_histogram(name, help_text, labels, buckets)


def summary(
    name: str,
    help_text: str = "",
    labels: Optional[Dict[str, str]] = None,
    quantiles: Optional[List[float]] = None
) -> Summary:
    """创建并获取默认注册表中的摘要"""
    return get_default_registry().create_summary(name, help_text, labels, quantiles)
