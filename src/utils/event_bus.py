"""
消息队列与事件驱动系统
提供事件总线、消息队列和发布订阅功能
"""
import threading
import queue
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class EventPriority(Enum):
    """事件优先级"""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class Event:
    """事件对象"""
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.name,
            "source": self.source,
            "correlation_id": self.correlation_id
        }


class EventBus:
    """事件总线"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._subscribers: Dict[str, List[Callable]] = {}
        self._all_subscribers: List[Callable] = []
        self._lock = threading.RLock()
        self._logger = get_logger(f"event.bus.{name}")
        self._history: List[Event] = []
        self._max_history = 1000
        self._running = False
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._worker_thread: Optional[threading.Thread] = None
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """订阅特定类型事件"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            self._logger.debug(f"Subscribed to {event_type}")
    
    def subscribe_all(self, handler: Callable[[Event], None]) -> None:
        """订阅所有事件"""
        with self._lock:
            self._all_subscribers.append(handler)
            self._logger.debug("Subscribed to all events")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """取消订阅"""
        with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                return True
            return False
    
    def publish(self, event: Event) -> None:
        """发布事件"""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        
        # 放入队列（异步处理）
        priority_value = {
            EventPriority.LOW: 3,
            EventPriority.NORMAL: 2,
            EventPriority.HIGH: 1,
            EventPriority.CRITICAL: 0
        }[event.priority]
        
        self._event_queue.put((priority_value, event))
        self._logger.debug(f"Published event: {event.event_type}")
    
    def publish_sync(self, event: Event) -> None:
        """同步发布事件（立即处理）"""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        self._process_event(event)
    
    def _process_event(self, event: Event) -> None:
        """处理事件"""
        # 通知特定订阅者
        with self._lock:
            handlers = list(self._subscribers.get(event.event_type, []))
            all_handlers = list(self._all_subscribers)
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self._logger.error(f"Error in event handler: {e}", exc_info=True)
        
        for handler in all_handlers:
            try:
                handler(event)
            except Exception as e:
                self._logger.error(f"Error in global event handler: {e}", exc_info=True)
    
    def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self._logger.info("Event bus started")
    
    def stop(self) -> None:
        """停止事件总线"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self._logger.info("Event bus stopped")
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                _, event = self._event_queue.get(timeout=1)
                self._process_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                self._logger.error(f"Event processing error: {e}", exc_info=True)
    
    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """获取事件历史"""
        with self._lock:
            events = self._history[-limit:]
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return events
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "name": self.name,
                "subscribers": len(self._subscribers),
                "all_subscribers": len(self._all_subscribers),
                "queue_size": self._event_queue.qsize(),
                "history_size": len(self._history),
                "running": self._running
            }


class MessageQueue:
    """消息队列"""
    
    def __init__(self, name: str = "default", max_size: int = 1000):
        self.name = name
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._consumers: List[Callable] = []
        self._lock = threading.RLock()
        self._logger = get_logger(f"message.queue.{name}")
        self._running = False
        self._consumer_threads: List[threading.Thread] = []
        self._consumer_count = 1
    
    def produce(self, message: Dict[str, Any]) -> bool:
        """生产消息"""
        try:
            self._queue.put_nowait(message)
            self._logger.debug(f"Produced message: {message}")
            return True
        except queue.Full:
            self._logger.warning("Message queue is full")
            return False
    
    def consume(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """消费消息"""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def register_consumer(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """注册消费者"""
        with self._lock:
            self._consumers.append(handler)
    
    def start_consumers(self, count: int = 1) -> None:
        """启动消费者"""
        self._consumer_count = count
        self._running = True
        
        for i in range(count):
            thread = threading.Thread(
                target=self._consumer_loop,
                args=(i,),
                daemon=True
            )
            thread.start()
            self._consumer_threads.append(thread)
        
        self._logger.info(f"Started {count} consumers")
    
    def stop_consumers(self) -> None:
        """停止消费者"""
        self._running = False
        for thread in self._consumer_threads:
            thread.join(timeout=5)
        self._consumer_threads.clear()
        self._logger.info("Consumers stopped")
    
    def _consumer_loop(self, consumer_id: int) -> None:
        """消费者循环"""
        while self._running:
            try:
                message = self._queue.get(timeout=1)
                
                with self._lock:
                    handlers = list(self._consumers)
                
                for handler in handlers:
                    try:
                        handler(message)
                    except Exception as e:
                        self._logger.error(f"Consumer {consumer_id} error: {e}", exc_info=True)
                
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self._logger.error(f"Consumer {consumer_id} error: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "name": self.name,
            "queue_size": self._queue.qsize(),
            "max_size": self._queue.maxsize,
            "consumers": len(self._consumers),
            "consumer_threads": len(self._consumer_threads),
            "running": self._running
        }


# 全局实例
_event_bus: Optional[EventBus] = None
_message_queue: Optional[MessageQueue] = None


def get_event_bus(name: str = "default") -> EventBus:
    """获取事件总线"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(name)
    return _event_bus


def get_message_queue(name: str = "default") -> MessageQueue:
    """获取消息队列"""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue(name)
    return _message_queue
