"""
邮件通知系统
提供邮件模板、发送队列和批量发送功能
"""
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import logger
from src.utils.structured_logging import get_logger


class EmailStatus(Enum):
    """邮件状态"""
    PENDING = auto()
    SENT = auto()
    FAILED = auto()
    QUEUED = auto()


@dataclass
class EmailMessage:
    """邮件消息"""
    to: List[str]
    subject: str
    body: str
    from_addr: str = ""
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    html_body: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    status: EmailStatus = EmailStatus.PENDING
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "to": self.to,
            "subject": self.subject,
            "from": self.from_addr,
            "status": self.status.name,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, default_from: str = "noreply@example.com"):
        self.default_from = default_from
        self._queue: List[EmailMessage] = []
        self._sent: List[EmailMessage] = []
        self._lock = threading.RLock()
        self._logger = get_logger("email.notifier")
        self._templates: Dict[str, str] = {}
        self._enabled = True
    
    def set_enabled(self, enabled: bool) -> None:
        """设置启用状态"""
        self._enabled = enabled
    
    def register_template(self, name: str, template: str) -> None:
        """注册邮件模板"""
        with self._lock:
            self._templates[name] = template
    
    def create_message(self, to: List[str], subject: str, body: str,
                       from_addr: Optional[str] = None,
                       template_name: Optional[str] = None,
                       template_context: Optional[Dict[str, Any]] = None) -> EmailMessage:
        """创建邮件消息"""
        if template_name and template_name in self._templates:
            template = self._templates[template_name]
            if template_context:
                body = self._render_template(template, template_context)
            else:
                body = template
        
        return EmailMessage(
            to=to,
            subject=subject,
            body=body,
            from_addr=from_addr or self.default_from
        )
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def send(self, message: EmailMessage) -> bool:
        """发送邮件"""
        if not self._enabled:
            message.status = EmailStatus.FAILED
            message.error = "Email notifier is disabled"
            return False
        
        try:
            # 模拟发送
            message.status = EmailStatus.SENT
            message.sent_at = datetime.now()
            
            with self._lock:
                self._sent.append(message)
            
            self._logger.info(f"Email sent to {message.to}: {message.subject}")
            return True
            
        except Exception as e:
            message.status = EmailStatus.FAILED
            message.error = str(e)
            self._logger.error(f"Email send failed: {e}")
            return False
    
    def queue(self, message: EmailMessage) -> None:
        """添加到队列"""
        with self._lock:
            message.status = EmailStatus.QUEUED
            self._queue.append(message)
        self._logger.info(f"Email queued: {message.subject}")
    
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
    
    def send_bulk(self, messages: List[EmailMessage]) -> Dict[str, int]:
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
_notifier: Optional[EmailNotifier] = None


def get_email_notifier(default_from: str = "noreply@example.com") -> EmailNotifier:
    """获取邮件通知器"""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier(default_from)
    return _notifier
