"""
实时数据处理
提供流数据接收、处理和窗口计算功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class StreamRecord:
    """流数据记录"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class WindowType(Enum):
    """窗口类型"""
    TUMBLING = auto()
    SLIDING = auto()
    SESSION = auto()


class StreamWindow:
    """流窗口"""
    
    def __init__(self, window_type: WindowType, size_seconds: float,
                 slide_seconds: Optional[float] = None):
        self.window_type = window_type
        self.size_seconds = size_seconds
        self.slide_seconds = slide_seconds or size_seconds
        self._records: deque = deque()
        self._lock = threading.Lock()
    
    def add(self, record: StreamRecord) -> None:
        """添加记录"""
        with self._lock:
            self._records.append(record)
            self._cleanup()
    
    def _cleanup(self) -> None:
        """清理过期记录"""
        now = time.time()
        cutoff = now - self.size_seconds
        
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()
    
    def get_records(self) -> List[StreamRecord]:
        """获取窗口内记录"""
        with self._lock:
            self._cleanup()
            return list(self._records)
    
    def count(self) -> int:
        """获取记录数"""
        with self._lock:
            self._cleanup()
            return len(self._records)
    
    def sum_values(self) -> float:
        """求和"""
        with self._lock:
            self._cleanup()
            total = 0.0
            for record in self._records:
                try:
                    total += float(record.value)
                except (TypeError, ValueError):
                    pass
            return total
    
    def average(self) -> float:
        """平均值"""
        with self._lock:
            self._cleanup()
            values = []
            for record in self._records:
                try:
                    values.append(float(record.value))
                except (TypeError, ValueError):
                    pass
            return sum(values) / len(values) if values else 0.0


class StreamProcessor:
    """流处理器"""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._windows: Dict[str, StreamWindow] = {}
        self._running = False
        self._lock = threading.RLock()
        self._logger = get_logger("stream.processor")
        self._processed_count = 0
        self._error_count = 0
    
    def add_handler(self, key: str, handler: Callable[[StreamRecord], None]) -> None:
        """添加处理器"""
        with self._lock:
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(handler)
    
    def create_window(self, key: str, window_type: WindowType,
                      size_seconds: float,
                      slide_seconds: Optional[float] = None) -> StreamWindow:
        """创建窗口"""
        with self._lock:
            window = StreamWindow(window_type, size_seconds, slide_seconds)
            self._windows[key] = window
            return window
    
    def process(self, record: StreamRecord) -> bool:
        """处理记录"""
        try:
            # 添加到窗口
            with self._lock:
                if record.key in self._windows:
                    self._windows[record.key].add(record)
            
            # 调用处理器
            handlers = self._handlers.get(record.key, [])
            for handler in handlers:
                try:
                    handler(record)
                except Exception as e:
                    self._logger.error(f"Handler error: {e}")
                    self._error_count += 1
            
            self._processed_count += 1
            return True
            
        except Exception as e:
            self._logger.error(f"Processing error: {e}")
            self._error_count += 1
            return False
    
    def get_window_stats(self, key: str) -> Dict[str, Any]:
        """获取窗口统计"""
        with self._lock:
            window = self._windows.get(key)
            if not window:
                return {}
            
            return {
                "count": window.count(),
                "sum": window.sum_values(),
                "average": window.average()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "processed": self._processed_count,
                "errors": self._error_count,
                "handlers": len(self._handlers),
                "windows": len(self._windows)
            }


class StreamAggregator:
    """流聚合器"""
    
    def __init__(self):
        self._aggregates: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._logger = get_logger("stream.aggregator")
    
    def aggregate(self, key: str, record: StreamRecord,
                  agg_func: str = "sum") -> Any:
        """聚合"""
        with self._lock:
            if key not in self._aggregates:
                self._aggregates[key] = {
                    "count": 0,
                    "sum": 0.0,
                    "min": float('inf'),
                    "max": float('-inf'),
                    "values": []
                }
            
            agg = self._aggregates[key]
            
            try:
                value = float(record.value)
            except (TypeError, ValueError):
                return None
            
            agg["count"] += 1
            agg["sum"] += value
            agg["min"] = min(agg["min"], value)
            agg["max"] = max(agg["max"], value)
            agg["values"].append(value)
            
            if agg_func == "sum":
                return agg["sum"]
            elif agg_func == "count":
                return agg["count"]
            elif agg_func == "avg":
                return agg["sum"] / agg["count"]
            elif agg_func == "min":
                return agg["min"]
            elif agg_func == "max":
                return agg["max"]
            
            return agg["sum"]
    
    def get_aggregate(self, key: str) -> Optional[Dict[str, Any]]:
        """获取聚合结果"""
        with self._lock:
            return self._aggregates.get(key)


# 全局实例
_processor: Optional[StreamProcessor] = None


def get_stream_processor() -> StreamProcessor:
    """获取流处理器"""
    global _processor
    if _processor is None:
        _processor = StreamProcessor()
    return _processor
