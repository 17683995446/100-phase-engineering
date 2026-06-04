"""
消息队列高级功能
提供优先级队列、延迟队列和死信队列功能
"""
import time
import heapq
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class QueueMessage:
    """队列消息"""
    message_id: str
    payload: Any
    priority: MessagePriority = MessagePriority.NORMAL
    delay_until: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "priority": self.priority.name,
            "retry_count": self.retry_count,
            "created_at": self.created_at
        }
    
    def __lt__(self, other):
        """用于优先级队列比较"""
        return self.priority.value < other.priority.value


class PriorityQueue:
    """优先级队列"""
    
    def __init__(self):
        self._queue: List[QueueMessage] = []
        self._lock = threading.Lock()
        self._logger = get_logger("priority.queue")
    
    def enqueue(self, message: QueueMessage) -> None:
        """入队"""
        with self._lock:
            heapq.heappush(self._queue, message)
    
    def dequeue(self) -> Optional[QueueMessage]:
        """出队"""
        with self._lock:
            if self._queue:
                return heapq.heappop(self._queue)
            return None
    
    def peek(self) -> Optional[QueueMessage]:
        """查看队首"""
        with self._lock:
            return self._queue[0] if self._queue else None
    
    def size(self) -> int:
        """获取大小"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """是否为空"""
        return self.size() == 0


class DelayedQueue:
    """延迟队列"""
    
    def __init__(self):
        self._queue: List[QueueMessage] = []
        self._lock = threading.Lock()
        self._logger = get_logger("delayed.queue")
    
    def enqueue(self, message: QueueMessage, delay_seconds: float) -> None:
        """入队（带延迟）"""
        message.delay_until = time.time() + delay_seconds
        with self._lock:
            self._queue.append(message)
    
    def dequeue(self) -> Optional[QueueMessage]:
        """出队（只返回已到期的）"""
        now = time.time()
        with self._lock:
            ready = [
                msg for msg in self._queue
                if msg.delay_until is None or msg.delay_until <= now
            ]
            for msg in ready:
                self._queue.remove(msg)
            return ready[0] if ready else None
    
    def size(self) -> int:
        """获取大小"""
        with self._lock:
            return len(self._queue)
    
    def ready_count(self) -> int:
        """获取已到期消息数"""
        now = time.time()
        with self._lock:
            return sum(
                1 for msg in self._queue
                if msg.delay_until is None or msg.delay_until <= now
            )


class DeadLetterQueue:
    """死信队列"""

    def __init__(self, max_retries: int = 3):
        self._messages: List[QueueMessage] = []
        self._max_retries = max_retries
        self._lock = threading.Lock()
        self._logger = get_logger("dead.letter.queue")

    def add(self, message: QueueMessage, reason: str = "") -> None:
        """添加到死信队列（幂等：同一消息只添加一次）"""
        with self._lock:
            for msg in self._messages:
                if msg.message_id == message.message_id:
                    return
            self._messages.append(message)
        self._logger.warning(f"Message moved to DLQ: {message.message_id}, reason: {reason}")
    
    def get_messages(self) -> List[QueueMessage]:
        """获取所有死信"""
        with self._lock:
            return list(self._messages)
    
    def size(self) -> int:
        """获取大小"""
        with self._lock:
            return len(self._messages)
    
    def clear(self) -> None:
        """清空"""
        with self._lock:
            self._messages.clear()


class AdvancedMessageQueue:
    """高级消息队列"""
    
    def __init__(self):
        self._priority_queue = PriorityQueue()
        self._delayed_queue = DelayedQueue()
        self._dlq = DeadLetterQueue()
        self._consumers: List[Callable] = []
        self._lock = threading.RLock()
        self._logger = get_logger("advanced.mq")
        self._processed = 0
        self._failed = 0
    
    def publish(self, message: QueueMessage, delay_seconds: float = 0) -> bool:
        """发布消息"""
        if delay_seconds > 0:
            self._delayed_queue.enqueue(message, delay_seconds)
        else:
            self._priority_queue.enqueue(message)
        return True
    
    def consume(self) -> Optional[QueueMessage]:
        """消费消息"""
        # 先检查延迟队列
        delayed = self._delayed_queue.dequeue()
        if delayed:
            return delayed
        
        # 再检查优先级队列
        return self._priority_queue.dequeue()
    
    def process_message(self, message: QueueMessage,
                        handler: Callable[[Any], bool]) -> bool:
        """处理消息"""
        # 如果消息已经在死信队列中，直接返回失败
        for msg in self._dlq.get_messages():
            if msg.message_id == message.message_id:
                return False
        try:
            success = handler(message.payload)

            if success:
                self._processed += 1
                return True
            else:
                # 处理失败，重试
                message.retry_count += 1
                if message.retry_count >= message.max_retries:
                    self._dlq.add(message, "Max retries exceeded")
                    self._failed += 1
                else:
                    # 重新入队，带延迟
                    self._delayed_queue.enqueue(message, 5.0)
                return False

        except Exception as e:
            message.retry_count += 1
            if message.retry_count >= message.max_retries:
                self._dlq.add(message, f"Exception: {str(e)}")
                self._failed += 1
            else:
                self._delayed_queue.enqueue(message, 5.0)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "priority_queue_size": self._priority_queue.size(),
            "delayed_queue_size": self._delayed_queue.size(),
            "delayed_ready": self._delayed_queue.ready_count(),
            "dlq_size": self._dlq.size(),
            "processed": self._processed,
            "failed": self._failed
        }


# 全局实例
_queue: Optional[AdvancedMessageQueue] = None


def get_advanced_message_queue() -> AdvancedMessageQueue:
    """获取高级消息队列"""
    global _queue
    if _queue is None:
        _queue = AdvancedMessageQueue()
    return _queue
