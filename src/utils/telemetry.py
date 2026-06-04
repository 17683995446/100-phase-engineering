"""
OpenTelemetry 分布式追踪系统
遵循可观测性公理：系统状态完全可观测，提供分布式追踪、度量和日志
"""

import time
import uuid
import threading
import random
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from collections import deque

from src.utils.logger import logger
from src.utils.structured_logging import get_logger, LogContext


class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = auto()    # 内部操作
    SERVER = auto()      # 服务端处理
    CLIENT = auto()      # 客户端调用
    PRODUCER = auto()    # 生产者
    CONSUMER = auto()    # 消费者


class SpanStatus(Enum):
    """Span 状态"""
    UNSET = auto()       # 未设置
    OK = auto()          # 成功
    ERROR = auto()       # 错误


class PropagationFormat(Enum):
    """上下文传播格式"""
    W3C_TRACEPARENT = auto()   # W3C Trace Context
    B3 = auto()                # B3 Multi Header
    B3_SINGLE = auto()         # B3 Single Header


@dataclass
class SpanContext:
    """Span 上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # 0x01 = sampled
    is_remote: bool = False
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_w3c_traceparent(self) -> str:
        """转换为 W3C Traceparent 格式"""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"

    def to_b3_headers(self) -> Dict[str, str]:
        """转换为 B3 头部格式"""
        headers = {
            "X-B3-TraceId": self.trace_id,
            "X-B3-SpanId": self.span_id,
            "X-B3-Sampled": str(self.trace_flags & 0x01),
        }
        if self.parent_span_id:
            headers["X-B3-ParentSpanId"] = self.parent_span_id
        return headers

    @classmethod
    def from_w3c_traceparent(cls, traceparent: str) -> Optional['SpanContext']:
        """从 W3C Traceparent 解析"""
        try:
            parts = traceparent.strip().split("-")
            if len(parts) != 4:
                return None
            version = parts[0]
            if version != "00":
                return None
            trace_id = parts[1]
            span_id = parts[2]
            trace_flags = int(parts[3], 16)
            return cls(
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=trace_flags
            )
        except Exception:
            return None

    @classmethod
    def from_b3_headers(cls, headers: Dict[str, str]) -> Optional['SpanContext']:
        """从 B3 头部解析"""
        trace_id = headers.get("X-B3-TraceId")
        span_id = headers.get("X-B3-SpanId")
        if not trace_id or not span_id:
            # 尝试单一头部格式
            b3 = headers.get("B3")
            if b3:
                parts = b3.split("-")
                if len(parts) >= 2:
                    trace_id = parts[0]
                    span_id = parts[1]
        if trace_id and span_id:
            sampled = headers.get("X-B3-Sampled", "1")
            parent_span_id = headers.get("X-B3-ParentSpanId")
            return cls(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                trace_flags=int(sampled)
            )
        return None

    @classmethod
    def generate_new(cls) -> 'SpanContext':
        """生成新的 SpanContext"""
        return cls(
            trace_id=format(random.getrandbits(128), "032x"),
            span_id=format(random.getrandbits(64), "016x"),
            trace_flags=1
        )


@dataclass
class SpanEvent:
    """Span 事件"""
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Span 链接"""
    context: SpanContext
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Span - 分布式追踪的基本单元"""
    name: str
    kind: SpanKind
    context: SpanContext
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    status_description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后设置资源属性"""
        self.resource_attributes.update({
            "service.name": "maes-system",
            "service.version": "1.0.0",
        })

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> 'Span':
        """添加事件"""
        self.events.append(SpanEvent(
            name=name,
            attributes=attributes or {}
        ))
        return self

    def add_link(self, context: SpanContext, attributes: Optional[Dict[str, Any]] = None) -> 'Span':
        """添加链接"""
        self.links.append(SpanLink(
            context=context,
            attributes=attributes or {}
        ))
        return self

    def set_attributes(self, attributes: Dict[str, Any]) -> 'Span':
        """设置属性"""
        self.attributes.update(attributes)
        return self

    def set_attribute(self, key: str, value: Any) -> 'Span':
        """设置单个属性"""
        self.attributes[key] = value
        return self

    def set_status(self, status: SpanStatus, description: str = "") -> 'Span':
        """设置状态"""
        self.status = status
        self.status_description = description
        return self

    def end(self) -> 'Span':
        """结束 Span"""
        if self.end_time is None:
            self.end_time = time.time()
        return self

    @property
    def duration_ms(self) -> float:
        """获取持续时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于导出）"""
        return {
            "name": self.name,
            "kind": self.kind.name,
            "traceId": self.context.trace_id,
            "spanId": self.context.span_id,
            "parentSpanId": self.context.parent_span_id,
            "startTimeUnixNano": int(self.start_time * 1e9),
            "endTimeUnixNano": int(self.end_time * 1e9) if self.end_time else None,
            "status": {
                "code": self.status.name,
                "message": self.status_description
            },
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timeUnixNano": int(e.timestamp * 1e9),
                    "attributes": e.attributes
                }
                for e in self.events
            ],
            "links": [
                {
                    "traceId": l.context.trace_id,
                    "spanId": l.context.span_id,
                    "attributes": l.attributes
                }
                for l in self.links
            ],
            "resource": self.resource_attributes,
            "durationMs": self.duration_ms
        }


class Tracer:
    """Tracer - 创建和管理 Span"""

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        exporter: Optional['SpanExporter'] = None
    ):
        self.name = name
        self.version = version
        self.exporter = exporter
        self.logger = get_logger(f"tracer.{name}")
        self._local = threading.local()

    @property
    def current_span(self) -> Optional[Span]:
        """获取当前线程的活动 Span"""
        return getattr(self._local, "current_span", None)

    @current_span.setter
    def current_span(self, span: Optional[Span]):
        """设置当前线程的活动 Span"""
        self._local.current_span = span

    @property
    def current_context(self) -> Optional[SpanContext]:
        """获取当前上下文"""
        if self.current_span:
            return self.current_span.context
        return None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """开始新的 Span"""
        if context is None:
            # 从当前 Span 创建子 Span
            if self.current_span:
                parent_context = self.current_span.context
                context = SpanContext(
                    trace_id=parent_context.trace_id,
                    span_id=format(random.getrandbits(64), "016x"),
                    parent_span_id=parent_context.span_id,
                    trace_flags=parent_context.trace_flags,
                    baggage=parent_context.baggage.copy()
                )
            else:
                # 创建新的根 Span
                context = SpanContext.generate_new()

        span = Span(
            name=name,
            kind=kind,
            context=context,
            attributes=attributes or {}
        )

        self.current_span = span
        self.logger.debug(f"Started span: {name} [trace={context.trace_id}, span={context.span_id}]")

        # 更新 LogContext
        LogContext.set_context(
            trace_id=context.trace_id,
            span_id=context.span_id,
            parent_span_id=context.parent_span_id
        )

        return span

    def end_current_span(self) -> Optional[Span]:
        """结束当前 Span"""
        span = self.current_span
        if span:
            span.end()
            self.logger.debug(f"Ended span: {span.name} [duration={span.duration_ms:.2f}ms]")
            
            if self.exporter:
                self.exporter.export(span)

            # 恢复父 Span
            if span.context.parent_span_id:
                # 在实际实现中，这里应该维护一个 Span 栈
                # 为简单起见，这里先不实现完整的栈管理
                pass
            else:
                self.current_span = None
                LogContext.clear_context()

        return span

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """上下文管理器，自动管理 Span 生命周期"""
        span = self.start_span(name, kind, attributes=attributes)
        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.add_event("exception", {
                "exception.type": type(e).__name__,
                "exception.message": str(e),
            })
            raise
        finally:
            self.end_current_span()


class SpanExporter:
    """Span 导出器基类"""

    def export(self, span: Span):
        """导出 Span"""
        raise NotImplementedError

    def export_batch(self, spans: List[Span]):
        """批量导出 Span"""
        for span in spans:
            self.export(span)

    def shutdown(self):
        """关闭导出器"""
        pass


class LogSpanExporter(SpanExporter):
    """日志导出器 - 将 Span 导出到日志"""

    def __init__(self):
        self.logger = get_logger("span.exporter.log")

    def export(self, span: Span):
        """导出 Span 到日志"""
        self.logger.info(
            f"Span completed: {span.name}",
            trace_id=span.context.trace_id,
            span_id=span.context.span_id,
            parent_span_id=span.context.parent_span_id,
            duration_ms=span.duration_ms,
            status=span.status.name,
            attributes=span.attributes
        )


class InMemorySpanExporter(SpanExporter):
    """内存导出器 - 保存 Span 到内存（用于测试）"""

    def __init__(self):
        self.spans: List[Span] = []
        self._lock = threading.Lock()

    def export(self, span: Span):
        """导出 Span 到内存"""
        with self._lock:
            self.spans.append(span)

    def get_spans(self) -> List[Span]:
        """获取所有导出的 Span"""
        with self._lock:
            return self.spans.copy()

    def get_spans_by_trace_id(self, trace_id: str) -> List[Span]:
        """根据 Trace ID 获取 Span"""
        with self._lock:
            return [s for s in self.spans if s.context.trace_id == trace_id]

    def clear(self):
        """清空导出的 Span"""
        with self._lock:
            self.spans.clear()


class BatchSpanExporter(SpanExporter):
    """批量导出器 - 定期批量导出 Span"""

    def __init__(
        self,
        exporter: SpanExporter,
        max_queue_size: int = 1024,
        schedule_delay_ms: float = 5000.0,
        max_export_batch_size: int = 512
    ):
        self.exporter = exporter
        self.max_queue_size = max_queue_size
        self.schedule_delay_ms = schedule_delay_ms
        self.max_export_batch_size = max_export_batch_size
        
        self.queue: deque = deque()
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._shutdown = threading.Event()
        self.logger = get_logger("span.exporter.batch")

    def start(self):
        """启动批量导出器"""
        if self._worker is None or not self._worker.is_alive():
            self._shutdown.clear()
            self._worker = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker.start()
            self.logger.info("Batch span exporter started")

    def export(self, span: Span):
        """添加 Span 到队列"""
        with self._lock:
            if len(self.queue) < self.max_queue_size:
                self.queue.append(span)
            else:
                self.logger.warning(f"Span queue full, dropping span: {span.name}")

    def _worker_loop(self):
        """工作线程循环"""
        while not self._shutdown.is_set():
            self._export_batch()
            time.sleep(self.schedule_delay_ms / 1000.0)
        
        # 关闭前导出剩余的 Span
        self._export_batch()

    def _export_batch(self):
        """导出一批 Span"""
        batch: List[Span] = []
        with self._lock:
            while self.queue and len(batch) < self.max_export_batch_size:
                batch.append(self.queue.popleft())
        
        if batch:
            try:
                self.exporter.export_batch(batch)
                self.logger.debug(f"Exported batch of {len(batch)} spans")
            except Exception as e:
                self.logger.error(f"Failed to export batch: {e}")

    def shutdown(self):
        """关闭批量导出器"""
        self._shutdown.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5.0)
        self.exporter.shutdown()
        self.logger.info("Batch span exporter shutdown")


class TracerProvider:
    """Tracer 提供者 - 全局 Tracer 管理"""

    _instance: Optional['TracerProvider'] = None
    _lock = threading.Lock()

    def __init__(self, exporter: Optional[SpanExporter] = None):
        self.tracers: Dict[str, Tracer] = {}
        self.exporter = exporter or LogSpanExporter()
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'TracerProvider':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: 'TracerProvider'):
        """设置全局实例"""
        with cls._lock:
            cls._instance = instance

    def get_tracer(self, name: str, version: str = "1.0.0") -> Tracer:
        """获取或创建 Tracer"""
        with self._lock:
            if name not in self.tracers:
                self.tracers[name] = Tracer(name, version, self.exporter)
            return self.tracers[name]

    def set_exporter(self, exporter: SpanExporter):
        """设置全局导出器"""
        with self._lock:
            self.exporter = exporter
            # 更新所有现有 Tracer 的导出器
            for tracer in self.tracers.values():
                tracer.exporter = exporter


# 全局便捷函数
def get_tracer(name: str, version: str = "1.0.0") -> Tracer:
    """获取 Tracer"""
    return TracerProvider.get_instance().get_tracer(name, version)


def trace(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """装饰器 - 为函数自动添加追踪"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer_name = func.__module__
            tracer = get_tracer(tracer_name)
            span_name = name or func.__qualname__
            
            with tracer.span(span_name, kind, attributes=attributes) as span:
                span.set_attributes({
                    "code.function": func.__name__,
                    "code.namespace": func.__module__,
                })
                return func(*args, **kwargs)
        return wrapper
    return decorator


def extract_context(headers: Dict[str, str]) -> Optional[SpanContext]:
    """从请求头中提取追踪上下文"""
    # 优先尝试 W3C Trace Context
    traceparent = headers.get("traceparent")
    if traceparent:
        context = SpanContext.from_w3c_traceparent(traceparent)
        if context:
            return context
    
    # 尝试 B3 格式
    context = SpanContext.from_b3_headers(headers)
    if context:
        return context
    
    return None


def inject_context(
    headers: Dict[str, str],
    context: Optional[SpanContext] = None,
    format: PropagationFormat = PropagationFormat.W3C_TRACEPARENT
) -> Dict[str, str]:
    """将追踪上下文注入到请求头中"""
    if context is None:
        tracer = get_tracer("default")
        context = tracer.current_context
    
    if context:
        if format == PropagationFormat.W3C_TRACEPARENT:
            headers["traceparent"] = context.to_w3c_traceparent()
        elif format in (PropagationFormat.B3, PropagationFormat.B3_SINGLE):
            b3_headers = context.to_b3_headers()
            headers.update(b3_headers)
    
    return headers


def with_context(
    context: Optional[SpanContext] = None,
    tracer: Optional[Tracer] = None
):
    """装饰器 - 在指定的追踪上下文中运行函数"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            actual_tracer = tracer or get_tracer(func.__module__)
            original_span = actual_tracer.current_span
            
            try:
                if context:
                    # 创建一个从给定上下文开始的 Span
                    with actual_tracer.span(
                        f"{func.__qualname__} (with context)",
                        context=context
                    ):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            finally:
                # 恢复原始 Span
                actual_tracer.current_span = original_span
        return wrapper
    return decorator
