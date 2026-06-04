"""
短信通知系统
提供短信模板、发送队列和批量发送功能
"""
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class SMSStatus(Enum):
    """短信状态"""
    PENDING = auto()
    SENT = auto()
    FAILED = auto()
    QUEUED = auto()


@dataclass
class SMSMessage:
    """短信消息"""
    to: str
    content: str
    from_number: str = ""
    status: SMSStatus = SMSStatus.PENDING
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "to": self.to,
            "content": self.content[:20] + "..." if len(self.content) > 20 else self.content,
            "from": self.from_number,
            "status": self.status.name,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }


class SMSNotifier:
    """短信通知器"""
    
    def __init__(self, default_from: str = "1234567890"):
        self.default_from = default_from
        self._queue: List[SMSMessage] = []
        self._sent: List[SMSMessage] = []
        self._lock = threading.RLock()
        self._logger = get_logger("sms.notifier")
        self._templates: Dict[str, str] = {}
        self._enabled = True
    
    def set_enabled(self, enabled: bool) -> None:
        """设置启用状态"""
        self._enabled = enabled
    
    def register_template(self, name: str, template: str) -> None:
        """注册短信模板"""
        with self._lock:
            self._templates[name] = template
    
    def create_message(self, to: str, content: str,
                       from_number: Optional[str] = None,
                       template_name: Optional[str] = None,
                       template_context: Optional[Dict[str, Any]] = None) -> SMSMessage:
        """创建短信消息"""
        if template_name and template_name in self._templates:
            template = self._templates[template_name]
            if template_context:
                content = self._render_template(template, template_context)
            else:
                content = template
        
        return SMSMessage(
            to=to,
            content=content,
            from_number=from_number or self.default_from
        )
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def send(self, message: SMSMessage) -> bool:
        """发送短信"""
        if not self._enabled:
            message.status = SMSStatus.FAILED
            message.error = "SMS notifier is disabled"
            return False
        
        try:
            # 模拟发送
            message.status = SMSStatus.SENT
            message.sent_at = datetime.now()
            
            with self._lock:
                self._sent.append(message)
            
            self._logger.info(f"SMS sent to {message.to}: {message.content[:30]}...")
            return True
            
        except Exception as e:
            message.status = SMSStatus.FAILED
            message.error = str(e)
            self._logger.error(f"SMS send failed: {e}")
            return False
    
    def queue(self, message: SMSMessage) -> None:
        """添加到队列"""
        with self._lock:
            message.status = SMSStatus.QUEUED
            self._queue.append(message)
        self._logger.info(f"SMS queued: {message.to}")
    
    def process_queue(self, batch_size: int = 10) -> Dict[str, int]:
        """处理队列"""
        with self._lock:
            batch = self._queue[:batch_size]
            self._queue = self._queue[batch_size:]
        
        sent = 0
        failed = 0
        
        for message in batch:
            if self.send(message):
                sent += 1
            else:
                failed += 1
        
        return {"sent": sent, "failed": failed}
    
    def send_bulk(self, messages: List[SMSMessage]) -> Dict[str, int]:
        """批量发送"""
        sent = 0
        failed = 0
        
        for message in messages:
            if self.send(message):
                sent += 1
            else:
                failed += 1
        
        return {"sent": sent, "failed": failed}
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)
    
    def get_sent_count(self) -> int:
        """获取已发送数量"""
        with self._lock:
            return len(self._sent)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "queue_size": len(self._queue),
                "sent": len(self._sent),
                "templates": len(self._templates),
                "enabled": self._enabled
            }
    
    def clear_queue(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()
    
    def clear_sent(self) -> None:
        """清空已发送记录"""
        with self._lock:
            self._sent.clear()


# 全局实例
_notifier: Optional[SMSNotifier] = None


def get_sms_notifier(default_from: str = "1234567890") -> SMSNotifier:
    """获取短信通知器"""
    global _notifier
    if _notifier is None:
        _notifier = SMSNotifier(default_from)
    return _notifier
