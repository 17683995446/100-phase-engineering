"""
Prometheus 指标收集系统测试
可观测性公理: 验证 Prometheus 格式输出正确性
"""

import pytest
import time
import math
from datetime import datetime
from src.utils.prometheus import (
    PromMetricType,
    PrometheusRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    timer,
    get_default_registry,
    set_default_registry
)


class TestCounter:
    """计数器测试"""
    
    def test_create_counter(self):
        """测试创建计数器"""
        registry = PrometheusRegistry(namespace="test")
        counter = registry.create_counter("requests_total", help_text="Total requests")
        assert counter is not None
        assert counter.get() == 0.0
    
    def test_counter_inc(self):
        """测试计数器递增"""
        registry = PrometheusRegistry(namespace="test")
        counter = registry.create_counter("test_counter")
        counter.inc()
        assert counter.get() == 1.0
        counter.inc(5.0)
        assert counter.get() == 6.0
    
    def test_counter_negative_error(self):
        """测试负数值异常"""
        registry = PrometheusRegistry(namespace="test")
        counter = registry.create_counter("test_counter")
        with pytest.raises(ValueError):
            counter.inc(-1.0)
    
    def test_counter_labels(self):
        """测试带标签的计数器"""
        registry = PrometheusRegistry(namespace="test")
        counter = registry.create_counter("requests_total", labels={"method": "GET", "status": "200"})
        counter.inc()
        assert counter.get() == 1.0
        assert counter.labels["method"] == "GET"


class TestGauge:
    """仪表盘测试"""
    
    def test_create_gauge(self):
        """测试创建仪表盘"""
        registry = PrometheusRegistry(namespace="test")
        gauge = registry.create_gauge("active_workers", help_text="Active workers")
        assert gauge is not None
        assert gauge.get() == 0.0
    
    def test_gauge_set(self):
        """测试设置值"""
        registry = PrometheusRegistry(namespace="test")
        gauge = registry.create_gauge("test_gauge")
        gauge.set(42.0)
        assert gauge.get() == 42.0
    
    def test_gauge_inc_dec(self):
        """测试递增递减"""
        registry = PrometheusRegistry(namespace="test")
        gauge = registry.create_gauge("test_gauge")
        gauge.set(10.0)
        assert gauge.get() == 10.0
        gauge.inc(5.0)
        assert gauge.get() == 15.0
        gauge.dec(3.0)
        assert gauge.get() == 12.0


class TestHistogram:
    """直方图测试"""
    
    def test_create_histogram(self):
        """测试创建直方图"""
        registry = PrometheusRegistry(namespace="test")
        hist = registry.create_histogram("request_duration_seconds")
        assert hist is not None
    
    def test_histogram_observe(self):
        """测试直方图观测"""
        registry = PrometheusRegistry(namespace="test")
        hist = registry.create_histogram("test_histogram")
        hist.observe(0.1)
        hist.observe(0.5)
        hist.observe(1.5)
        assert hist.count == 3
        assert hist.sum == 2.1
    
    def test_histogram_buckets(self):
        """测试直方图桶"""
        registry = PrometheusRegistry(namespace="test")
        buckets = [0.1, 0.5, 1.0]
        hist = registry.create_histogram("test_histogram", buckets=buckets)
        hist.observe(0.05)
        hist.observe(0.3)
        hist.observe(0.7)
        hist.observe(2.0)
        
        # +Inf 桶应该有 4 个
        assert hist.buckets[-1].count == 4


class TestSummary:
    """摘要测试"""
    
    def test_create_summary(self):
        """测试创建摘要"""
        registry = PrometheusRegistry(namespace="test")
        summary = registry.create_summary("response_latency_seconds")
        assert summary is not None
    
    def test_summary_observe(self):
        """测试摘要观测"""
        registry = PrometheusRegistry(namespace="test")
        summary = registry.create_summary("test_summary")
        summary.observe(1.0)
        summary.observe(2.0)
        summary.observe(3.0)
        assert summary.count == 3
        assert summary.sum == 6.0
    
    def test_summary_quantiles(self):
        """测试摘要分位数"""
        registry = PrometheusRegistry(namespace="test")
        summary = registry.create_summary("test_summary", quantiles=[0.5, 0.9])
        
        # 观测一些值
        for i in range(1, 101):
            summary.observe(i * 0.1)
        
        # 检查分位数
        assert len(summary.quantiles) == 2


class TestRegistry:
    """注册表测试"""
    
    def test_create_mixed_metrics(self):
        """测试创建混合指标"""
        registry = PrometheusRegistry(namespace="test")
        
        counter = registry.create_counter("counter", help_text="Test counter")
        gauge = registry.create_gauge("gauge", help_text="Test gauge")
        histogram = registry.create_histogram("histogram", help_text="Test histogram")
        summary = registry.create_summary("summary", help_text="Test summary")
        
        counter.inc()
        gauge.set(42)
        histogram.observe(0.5)
        summary.observe(1.0)
        
        assert len(registry.families) == 4


class TestTextFormat:
    """文本格式测试"""
    
    def test_generate_text_format(self):
        """测试生成 Prometheus 文本格式"""
        registry = PrometheusRegistry(namespace="test")
        
        counter = registry.create_counter("requests_total", help_text="Total requests", labels={"service": "api"})
        counter.inc(42)
        
        text = registry.generate_text_format()
        
        assert "# HELP test_requests_total Total requests" in text
        assert "# TYPE test_requests_total counter" in text
        assert "test_requests_total{service=\"api\"} 42" in text
    
    def test_text_format_without_labels(self):
        """测试无标签格式"""
        registry = PrometheusRegistry(namespace="test")
        counter = registry.create_counter("test_counter")
        counter.inc()
        text = registry.generate_text_format()
        assert "test_counter 1" in text


class TestTimerDecorator:
    """计时器装饰器测试"""
    
    def test_timer_decorator(self):
        """测试计时器装饰器"""
        registry = PrometheusRegistry(namespace="test")
        hist = registry.create_histogram("function_duration_seconds")
        
        @timer(hist)
        def slow_function():
            time.sleep(0.001)
        
        slow_function()
        slow_function()
        assert hist.count == 2
        assert hist.sum > 0
    
    def test_timer_with_labels(self):
        """测试带标签的计时器"""
        registry = PrometheusRegistry(namespace="test")
        summary = registry.create_summary("task_duration_seconds", labels={"type": "compute"})
        
        @timer(summary)
        def compute_task():
            return sum(range(10000))
        
        compute_task()
        assert summary.count == 1
        assert summary.sum > 0


class TestGlobalRegistry:
    """全局注册表测试"""
    
    def test_get_default_registry(self):
        """测试获取默认注册表"""
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        assert registry1 is registry2
    
    def test_set_default_registry(self):
        """测试设置默认注册表"""
        custom_registry = PrometheusRegistry(namespace="custom")
        set_default_registry(custom_registry)
        
        from src.utils.prometheus import _default_registry
        assert _default_registry is custom_registry
        
        # 恢复默认
        set_default_registry(PrometheusRegistry(namespace="maes"))


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_counter_function(self):
        """测试 counter 便捷函数"""
        from src.utils.prometheus import counter
        c = counter("convenience_counter")
        assert c is not None
        c.inc()
        assert c.get() == 1.0
    
    def test_gauge_function(self):
        """测试 gauge 便捷函数"""
        from src.utils.prometheus import gauge
        g = gauge("convenience_gauge")
        g.set(100.0)
        assert g.get() == 100.0


class TestMultipleLabels:
    """多标签测试"""
    
    def test_different_labels(self):
        """测试不同标签组合"""
        registry = PrometheusRegistry(namespace="test")
        
        counter1 = registry.create_counter("test_counter", labels={"app": "api", "status": "200"})
        counter2 = registry.create_counter("test_counter", labels={"app": "api", "status": "500"})
        
        counter1.inc(10)
        counter2.inc(20)
        
        assert counter1.get() == 10
        assert counter2.get() == 20
        
        # 应该有两个不同的样本
        assert len(registry.families["test_test_counter"].samples) == 2


class TestTextFormatDetails:
    """文本格式详细测试"""
    
    def test_histogram_format(self):
        """测试直方图格式"""
        registry = PrometheusRegistry(namespace="test")
        hist = registry.create_histogram("request_duration_seconds", buckets=[0.1, 0.5, 1.0])
        hist.observe(0.05)
        hist.observe(0.6)
        
        text = registry.generate_text_format()
        
        assert "test_request_duration_seconds_bucket" in text
        assert "test_request_duration_seconds_sum" in text
        assert "test_request_duration_seconds_count" in text
    
    def test_summary_format(self):
        """测试摘要格式"""
        registry = PrometheusRegistry(namespace="test")
        summary = registry.create_summary("response_latency_seconds")
        summary.observe(1.0)
        text = registry.generate_text_format()
        
        assert "test_response_latency_seconds_sum" in text
        assert "test_response_latency_seconds_count" in text


class TestMetricTypes:
    """指标类型测试"""
    
    def test_metric_types(self):
        """测试所有指标类型"""
        registry = PrometheusRegistry(namespace="test")
        
        # 计数器
        counter = registry.create_counter("test_counter")
        assert registry.families["test_test_counter"].type == PromMetricType.COUNTER
        
        # 仪表盘
        gauge = registry.create_gauge("test_gauge")
        assert registry.families["test_test_gauge"].type == PromMetricType.GAUGE
        
        # 直方图
        hist = registry.create_histogram("test_histogram")
        assert registry.families["test_test_histogram"].type == PromMetricType.HISTOGRAM
        
        # 摘要
        summary = registry.create_summary("test_summary")
        assert registry.families["test_test_summary"].type == PromMetricType.SUMMARY


class TestUnregister:
    """取消注册测试"""
    
    def test_unregister(self):
        """测试取消注册"""
        registry = PrometheusRegistry(namespace="test")
        registry.create_counter("test_counter")
        assert "test_test_counter" in registry.families
        
        registry.unregister("test_counter")
        assert "test_test_counter" not in registry.families


class TestLabelEscaping:
    """标签转义测试"""
    
    def test_label_escaping(self):
        """测试标签转义"""
        registry = PrometheusRegistry(namespace="test")
        
        counter = registry.create_counter("test_counter", labels={"special": 'val"ue', "newline": "line1\\nline2"})
        text = registry.generate_text_format()
        
        # 转义后的内容应该被包含
        assert "special" in text


def test_thread_safety():
    """测试线程安全"""
    import threading
    registry = PrometheusRegistry(namespace="test")
    counter = registry.create_counter("thread_safe_counter")
    
    def increment_counter():
        for _ in range(100):
            counter.inc()
    
    threads = []
    for _ in range(10):
        t = threading.Thread(target=increment_counter)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert counter.get() == 1000
