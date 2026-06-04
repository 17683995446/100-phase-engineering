"""
事件追踪系统
信息最小熵公理: 消灭隐式状态，所有信息显式化可追溯
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
import json
from copy import deepcopy

from src.utils.logger import logger


class EventType(Enum):
    """事件类型枚举"""
    TASK_CREATED = auto()
    TASK_STARTED = auto()
    TASK_UPDATED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    AGENT_MESSAGE_SENT = auto()
    AGENT_MESSAGE_RECEIVED = auto()
    CODE_CHANGED = auto()
    CODE_CHECKED = auto()
    TEST_RUN = auto()
    STATE_CHANGED = auto()
    DATA_FLOW_STARTED = auto()
    DATA_FLOW_COMPLETED = auto()
    ERROR_OCCURRED = auto()
    SYSTEM_EVENT = auto()


class EventSeverity(Enum):
    """事件严重程度"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class Event:
    """事件数据类"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    severity: EventSeverity = EventSeverity.INFO
    data: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    elapsed_ms: Optional[float] = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "timestamp": self.timestamp.isoformat(),
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "severity": self.severity.name,
            "data": self.data,
            "parent_event_id": self.parent_event_id,
            "elapsed_ms": self.elapsed_ms,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """从字典创建"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType[data["event_type"]],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_id=data.get("task_id"),
            agent_id=data.get("agent_id"),
            severity=EventSeverity[data["severity"]],
            data=data.get("data", {}),
            parent_event_id=data.get("parent_event_id"),
            elapsed_ms=data.get("elapsed_ms"),
            description=data.get("description", "")
        )


@dataclass
class DataFlowRecord:
    """数据流转记录"""
    flow_id: str
    task_id: str
    source_layer: str
    target_layer: str
    data_type: str
    data_summary: str
    timestamp: datetime
    is_valid: bool = True
    validation_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "task_id": self.task_id,
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "data_type": self.data_type,
            "data_summary": self.data_summary,
            "timestamp": self.timestamp.isoformat(),
            "is_valid": self.is_valid,
            "validation_result": self.validation_result
        }


class EventTracker:
    """事件追踪器"""
    
    def __init__(self, event_store_dir: Optional[Path] = None):
        self.event_store_dir = event_store_dir
        self.events: List[Event] = []
        self.data_flows: List[DataFlowRecord] = []
        self.event_stack: List[str] = []  # 用于追踪嵌套事件
        self._callbacks: List[Callable[[Event], None]] = []
        
        if event_store_dir:
            event_store_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("事件追踪器初始化完成")
    
    def emit_event(
        self,
        event_type: EventType,
        description: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        severity: EventSeverity = EventSeverity.INFO,
        data: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None
    ) -> Event:
        """
        发射一个事件
        
        Args:
            event_type: 事件类型
            description: 描述
            task_id: 任务ID
            agent_id: Agent ID
            severity: 严重程度
            data: 额外数据
            parent_event_id: 父事件ID
            
        Returns:
            创建的事件
        """
        import uuid
        
        event_id = str(uuid.uuid4())
        
        if parent_event_id is None and self.event_stack:
            parent_event_id = self.event_stack[-1]
        
        event = Event(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            task_id=task_id,
            agent_id=agent_id,
            severity=severity,
            data=deepcopy(data) if data else {},
            parent_event_id=parent_event_id,
            description=description
        )
        
        self.events.append(event)
        self._log_event(event)
        self._fire_callbacks(event)
        
        return event
    
    def _log_event(self, event: Event):
        """记录事件到日志"""
        prefix = f"[{event.event_type.name}]"
        if event.task_id:
            prefix += f" [Task:{event.task_id[:8]}]"
        if event.agent_id:
            prefix += f" [Agent:{event.agent_id}]"
        
        message = f"{prefix} {event.description}"
        
        if event.severity == EventSeverity.ERROR:
            logger.error(message)
        elif event.severity == EventSeverity.WARNING:
            logger.warning(message)
        elif event.severity == EventSeverity.CRITICAL:
            logger.error(f"CRITICAL: {message}")
        else:
            logger.info(message)
    
    def start_event_context(self, event_id: str):
        """开始事件上下文 - 用于嵌套事件"""
        self.event_stack.append(event_id)
    
    def end_event_context(self):
        """结束事件上下文"""
        if self.event_stack:
            self.event_stack.pop()
    
    def track_data_flow(
        self,
        task_id: str,
        source_layer: str,
        target_layer: str,
        data_type: str,
        data_summary: str,
        is_valid: bool = True,
        validation_result: Optional[str] = None
    ) -> DataFlowRecord:
        """
        追踪数据流转
        
        Args:
            task_id: 任务ID
            source_layer: 源层
            target_layer: 目标层
            data_type: 数据类型
            data_summary: 数据摘要
            is_valid: 是否有效
            validation_result: 验证结果
            
        Returns:
            数据流转记录
        """
        import uuid
        
        record = DataFlowRecord(
            flow_id=str(uuid.uuid4()),
            task_id=task_id,
            source_layer=source_layer,
            target_layer=target_layer,
            data_type=data_type,
            data_summary=data_summary,
            timestamp=datetime.now(),
            is_valid=is_valid,
            validation_result=validation_result
        )
        
        self.data_flows.append(record)
        logger.info(f"[DATA_FLOW] {source_layer} → {target_layer} | {data_type}: {data_summary}")
        
        return record
    
    def add_callback(self, callback: Callable[[Event], None]):
        """添加事件回调"""
        self._callbacks.append(callback)
    
    def _fire_callbacks(self, event: Event):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调失败: {e}")
    
    def get_events_by_task(self, task_id: str) -> List[Event]:
        """获取指定任务的所有事件"""
        return [e for e in self.events if e.task_id == task_id]
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """获取指定类型的事件"""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_data_flows_by_task(self, task_id: str) -> List[DataFlowRecord]:
        """获取指定任务的数据流转记录"""
        return [f for f in self.data_flows if f.task_id == task_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_events": len(self.events),
            "total_data_flows": len(self.data_flows),
            "events_by_type": {},
            "events_by_severity": {},
            "active_tasks": set()
        }
        
        for event in self.events:
            event_type = event.event_type.name
            severity = event.severity.name
            
            stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1
            stats["events_by_severity"][severity] = stats["events_by_severity"].get(severity, 0) + 1
            
            if event.task_id:
                stats["active_tasks"].add(event.task_id)
        
        stats["active_tasks"] = len(stats["active_tasks"])
        
        return stats
    
    def export_events(self, file_path: Path):
        """导出事件到文件"""
        export_data = [event.to_dict() for event in self.events]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"导出 {len(self.events)} 个事件到 {file_path}")
    
    def export_data_flows(self, file_path: Path):
        """导出数据流转记录到文件"""
        export_data = [flow.to_dict() for flow in self.data_flows]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"导出 {len(self.data_flows)} 个数据流转记录到 {file_path}")
    
    def clear_old_events(self, keep_last_n: int = 1000):
        """清理旧事件"""
        if len(self.events) > keep_last_n:
            self.events = self.events[-keep_last_n:]
            logger.info(f"保留最近 {keep_last_n} 个事件")
    
    def verify_no_implicit_state(self) -> Dict[str, Any]:
        """
        验证是否存在隐式状态
        
        Returns:
            验证结果
        """
        result = {
            "valid": True,
            "issues": [],
            "implicit_state_candidates": []
        }
        
        # 检查事件记录是否覆盖所有关键操作
        required_types = {
            EventType.TASK_CREATED,
            EventType.TASK_STARTED,
            EventType.STATE_CHANGED,
            EventType.DATA_FLOW_STARTED,
            EventType.DATA_FLOW_COMPLETED
        }
        
        missing_types = required_types - {e.event_type for e in self.events}
        if missing_types:
            result["valid"] = False
            result["issues"].append(f"缺少关键事件类型: {[t.name for t in missing_types]}")
        
        # 检查数据流转完整性
        if self.events:
            tasks_without_flows = set(e.task_id for e in self.events if e.task_id)
            tasks_with_flows = set(f.task_id for f in self.data_flows)
            missing_flows = tasks_without_flows - tasks_with_flows
            
            if missing_flows:
                result["valid"] = False
                result["implicit_state_candidates"].extend(list(missing_flows))
                result["issues"].append(f"{len(missing_flows)} 个任务缺少数据流转记录")
        
        return result


# 全局事件追踪器
_global_event_tracker: Optional[EventTracker] = None


def get_event_tracker() -> EventTracker:
    """获取全局事件追踪器"""
    global _global_event_tracker
    if _global_event_tracker is None:
        _global_event_tracker = EventTracker()
    return _global_event_tracker


def set_event_tracker(tracker: EventTracker):
    """设置全局事件追踪器"""
    global _global_event_tracker
    _global_event_tracker = tracker
