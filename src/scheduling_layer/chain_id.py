"""
全局可追溯链路ID机制
第一性原理：端到端全链路可追溯，信息最小熵
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from src.utils.logger import logger


class SpanType(Enum):
    """Span类型"""
    TASK = auto()
    AGENT = auto()
    EXECUTION = auto()
    VALIDATION = auto()
    MESSAGE = auto()
    STATE_CHANGE = auto()


class SpanStatus(Enum):
    """Span状态"""
    STARTED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class ChainID:
    """链路ID"""
    chain_id: str
    task_id: str
    created_at: datetime
    version: int = 1

    def to_string(self) -> str:
        """转换为字符串"""
        return self.chain_id

    @classmethod
    def generate(cls, task_id: str) -> 'ChainID':
        """生成链路ID"""
        chain_id = f"CH-{task_id}-{uuid.uuid4().hex[:16].upper()}"
        return cls(
            chain_id=chain_id,
            task_id=task_id,
            created_at=datetime.now()
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "chain_id": self.chain_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "version": self.version
        }


@dataclass
class SpanID:
    """Span ID"""
    span_id: str
    chain_id: str
    parent_span_id: str | None
    span_type: SpanType

    @classmethod
    def generate(cls, chain_id: str, span_type: SpanType, parent_span_id: str | None = None) -> 'SpanID':
        """生成Span ID"""
        span_id = f"SP-{uuid.uuid4().hex[:12].upper()}"
        return cls(
            span_id=span_id,
            chain_id=chain_id,
            parent_span_id=parent_span_id,
            span_type=span_type
        )


@dataclass
class Span:
    """Span - 链路中的单个操作单元"""
    span_id: str
    chain_id: str
    span_type: SpanType
    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.STARTED
    parent_span_id: str | None = None
    layer: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    duration_ms: float | None = None

    def complete(self, status: SpanStatus = SpanStatus.COMPLETED, metadata: dict[str, Any] | None = None):
        """完成Span"""
        self.end_time = datetime.now()
        self.status = status
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

        if metadata:
            self.metadata.update(metadata)

        if status == SpanStatus.FAILED and self.error:
            self.tags["error"] = "true"

    def add_tag(self, key: str, value: str):
        """添加标签"""
        self.tags[key] = value

    def add_log(self, message: str, metadata: dict[str, Any] | None = None):
        """添加日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        if metadata:
            log_entry["metadata"] = metadata
        self.logs.append(log_entry)

    def fail(self, error: str):
        """标记为失败"""
        self.error = error
        self.complete(status=SpanStatus.FAILED)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "span_id": self.span_id,
            "chain_id": self.chain_id,
            "span_type": self.span_type.name,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.name,
            "parent_span_id": self.parent_span_id,
            "layer": self.layer,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "tags": self.tags,
            "logs": self.logs,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


@dataclass
class Chain:
    """链路 - 整个生命周期的追踪"""
    chain_id: str
    task_id: str
    created_at: datetime
    root_span_id: str | None = None
    completed_at: datetime | None = None
    status: SpanStatus = SpanStatus.STARTED
    spans: list[Span] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    task_type: str | None = None
    priority: int | None = None
    source: str | None = None

    def add_span(self, span: Span):
        """添加Span"""
        if self.root_span_id is None:
            self.root_span_id = span.span_id
        self.spans.append(span)

    def complete(self, status: SpanStatus = SpanStatus.COMPLETED):
        """完成链路"""
        self.completed_at = datetime.now()
        self.status = status

    def get_span(self, span_id: str) -> Span | None:
        """获取Span"""
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def get_spans_by_type(self, span_type: SpanType) -> list[Span]:
        """获取指定类型的Spans"""
        return [s for s in self.spans if s.span_type == span_type]

    def get_duration_ms(self) -> float | None:
        """获取链路总时长"""
        if not self.spans:
            return None

        start_time = min(s.start_time for s in self.spans)
        end_time = max(s.end_time for s in self.spans if s.end_time)

        if end_time:
            return (end_time - start_time).total_seconds() * 1000
        return None

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_spans": len(self.spans),
            "completed_spans": len([s for s in self.spans if s.status == SpanStatus.COMPLETED]),
            "failed_spans": len([s for s in self.spans if s.status == SpanStatus.FAILED]),
            "spans_by_type": {},
            "spans_by_layer": {},
            "total_duration_ms": self.get_duration_ms()
        }

        for span in self.spans:
            span_type_name = span.span_type.name
            stats["spans_by_type"][span_type_name] = stats["spans_by_type"].get(span_type_name, 0) + 1

            if span.layer:
                stats["spans_by_layer"][span.layer] = stats["spans_by_layer"].get(span.layer, 0) + 1

        return stats

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "chain_id": self.chain_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.name,
            "root_span_id": self.root_span_id,
            "metadata": self.metadata,
            "task_type": self.task_type,
            "priority": self.priority,
            "source": self.source,
            "statistics": self.get_statistics(),
            "spans": [s.to_dict() for s in self.spans]
        }


class ChainTracker:
    """链路追踪器"""

    def __init__(self):
        self.chains: dict[str, Chain] = {}
        self.active_chains: dict[str, Chain] = {}
        self._current_span_context: dict[str, str] = {}

        logger.info("链路追踪器初始化完成")

    def create_chain(self, task_id: str, task_type: str | None = None,
                    priority: int | None = None, source: str | None = None,
                    metadata: dict[str, Any] | None = None) -> Chain:
        """创建新链路"""
        chain_id = ChainID.generate(task_id)

        chain = Chain(
            chain_id=chain_id.chain_id,
            task_id=task_id,
            created_at=chain_id.created_at,
            task_type=task_type,
            priority=priority,
            source=source,
            metadata=metadata or {}
        )

        self.chains[chain_id.chain_id] = chain
        self.active_chains[chain_id.chain_id] = chain

        logger.info(f"创建链路: {chain_id.chain_id} (task_id={task_id})")

        return chain

    def start_span(self, chain_id: str, span_type: SpanType, operation_name: str,
                  layer: str | None = None, agent_id: str | None = None,
                  parent_span_id: str | None = None, metadata: dict[str, Any] | None = None) -> Span | None:
        """开始一个Span"""
        if chain_id not in self.chains:
            logger.warning(f"链路不存在: {chain_id}")
            return None

        if parent_span_id is None:
            parent_span_id = self._current_span_context.get(chain_id)

        span_id = SpanID.generate(chain_id, span_type, parent_span_id)

        span = Span(
            span_id=span_id.span_id,
            chain_id=chain_id,
            span_type=span_type,
            operation_name=operation_name,
            start_time=datetime.now(),
            parent_span_id=parent_span_id,
            layer=layer,
            agent_id=agent_id,
            metadata=metadata or {}
        )

        chain = self.chains[chain_id]
        chain.add_span(span)

        self._current_span_context[chain_id] = span_id.span_id

        logger.debug(f"开始Span: {span_id.span_id} in chain {chain_id} (operation={operation_name})")

        return span

    def end_span(self, span_id: str, status: SpanStatus = SpanStatus.COMPLETED,
                error: str | None = None, metadata: dict[str, Any] | None = None):
        """结束一个Span"""
        for chain in self.chains.values():
            span = chain.get_span(span_id)
            if span:
                if error:
                    span.fail(error)
                else:
                    span.complete(status, metadata)

                if span.parent_span_id:
                    self._current_span_context[chain.chain_id] = span.parent_span_id
                elif self._current_span_context.get(chain.chain_id) == span_id:
                    self._current_span_context.pop(chain.chain_id, None)

                logger.debug(f"结束Span: {span_id} (status={span.status.name}, duration={span.duration_ms}ms)")
                return

        logger.warning(f"Span不存在: {span_id}")

    def complete_chain(self, chain_id: str, status: SpanStatus = SpanStatus.COMPLETED):
        """完成链路"""
        if chain_id not in self.chains:
            logger.warning(f"链路不存在: {chain_id}")
            return

        chain = self.chains[chain_id]
        chain.complete(status)

        if chain_id in self.active_chains:
            del self.active_chains[chain_id]

        logger.info(f"完成链路: {chain_id} (status={status.name}, duration={chain.get_duration_ms()}ms)")

    def get_chain(self, chain_id: str) -> Chain | None:
        """获取链路"""
        return self.chains.get(chain_id)

    def get_chain_by_task(self, task_id: str) -> Chain | None:
        """根据任务ID获取链路"""
        for chain in self.chains.values():
            if chain.task_id == task_id:
                return chain
        return None

    def get_active_chains(self) -> list[Chain]:
        """获取活跃链路"""
        return list(self.active_chains.values())

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total_chains = len(self.chains)
        active_chains = len(self.active_chains)

        total_spans = 0
        completed_spans = 0
        failed_spans = 0

        for chain in self.chains.values():
            total_spans += len(chain.spans)
            completed_spans += len([s for s in chain.spans if s.status == SpanStatus.COMPLETED])
            failed_spans += len([s for s in chain.spans if s.status == SpanStatus.FAILED])

        return {
            "total_chains": total_chains,
            "active_chains": active_chains,
            "completed_chains": total_chains - active_chains,
            "total_spans": total_spans,
            "completed_spans": completed_spans,
            "failed_spans": failed_spans,
            "success_rate": (completed_spans / total_spans * 100) if total_spans > 0 else 0
        }

    def export_chain(self, chain_id: str) -> dict[str, Any] | None:
        """导出链路"""
        chain = self.get_chain(chain_id)
        return chain.to_dict() if chain else None

    def verify_traceability(self) -> dict[str, Any]:
        """验证可追溯性"""
        result = {
            "valid": True,
            "issues": [],
            "metrics": {}
        }

        for chain in self.chains.values():
            if not chain.spans:
                result["valid"] = False
                result["issues"].append(f"链路 {chain.chain_id} 没有Span记录")

            for span in chain.spans:
                if span.status == SpanStatus.FAILED and not span.error:
                    result["valid"] = False
                    result["issues"].append(f"Span {span.span_id} 失败但未记录错误信息")

        result["metrics"] = self.get_statistics()

        return result


_global_chain_tracker: ChainTracker | None = None


def get_chain_tracker() -> ChainTracker:
    """获取全局链路追踪器"""
    global _global_chain_tracker
    if _global_chain_tracker is None:
        _global_chain_tracker = ChainTracker()
    return _global_chain_tracker


def set_chain_tracker(tracker: ChainTracker):
    """设置全局链路追踪器"""
    global _global_chain_tracker
    _global_chain_tracker = tracker


class ChainContext:
    """链路上下文管理器"""

    def __init__(self, tracker: ChainTracker, chain_id: str, span_type: SpanType,
                 operation_name: str, layer: str | None = None, agent_id: str | None = None):
        self.tracker = tracker
        self.chain_id = chain_id
        self.span_type = span_type
        self.operation_name = operation_name
        self.layer = layer
        self.agent_id = agent_id
        self.span: Span | None = None

    def __enter__(self):
        self.span = self.tracker.start_span(
            self.chain_id,
            self.span_type,
            self.operation_name,
            self.layer,
            self.agent_id
        )
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                error_msg = f"{exc_type.__name__}: {str(exc_val)}"
                self.tracker.end_span(self.span.span_id, status=SpanStatus.FAILED, error=error_msg)
            else:
                self.tracker.end_span(self.span.span_id, status=SpanStatus.COMPLETED)
        return False
