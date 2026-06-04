"""
系统告警与通知机制
提供告警管理、规则匹配、通知发送功能
"""

import time
import threading
import queue
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from abc import ABC, abstractmethod

from src.utils.logger import logger
from src.utils.structured_logging import get_logger
from src.utils.telemetry import get_tracer, SpanKind, SpanStatus


class AlertSeverity(Enum):
    """告警级别"""
    INFO = auto()      # 信息
    WARNING = auto()   # 警告
    ERROR = auto()     # 错误
    CRITICAL = auto()  # 严重


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = auto()     # 活跃
    ACKNOWLEDGED = auto()  # 已确认
    RESOLVED = auto()   # 已解决
    CLOSED = auto()     # 已关闭


@dataclass
class Alert:
    """告警对象"""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.name,
            "message": self.message,
            "source": self.source,
            "status": self.status.name,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags
        }


class AlertCondition(ABC):
    """告警条件基类"""
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件是否触发告警"""
        pass


class ThresholdCondition(AlertCondition):
    """阈值条件"""
    
    def __init__(
        self,
        metric_name: str,
        threshold: float,
        operator: str = "gt",  # gt, gte, lt, lte, eq
        window_seconds: Optional[int] = None
    ):
        self.metric_name = metric_name
        self.threshold = threshold
        self.operator = operator
        self.window_seconds = window_seconds
        self.value_history: deque = deque(maxlen=100)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估阈值条件"""
        value = context.get(self.metric_name)
        if value is None:
            return False
        
        self.value_history.append((time.time(), value))
        
        if self.window_seconds:
            # 窗口内的平均值
            now = time.time()
            recent_values = [
                v for ts, v in self.value_history
                if ts >= now - self.window_seconds
            ]
            if not recent_values:
                return False
            value = sum(recent_values) / len(recent_values)
        
        if self.operator == "gt":
            return value > self.threshold
        elif self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "lt":
            return value < self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        return False


class StatusCondition(AlertCondition):
    """状态条件"""
    
    def __init__(self, source: str, expected_status: str):
        self.source = source
        self.expected_status = expected_status
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估状态条件"""
        current_status = context.get(f"{self.source}_status")
        return current_status != self.expected_status


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    condition: AlertCondition
    severity: AlertSeverity
    cooldown_seconds: int = 300
    enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)
    last_triggered: Optional[float] = None
    _tracer: Any = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        self._tracer = get_tracer("alert.rule")
    
    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """判断是否应该触发告警"""
        if not self.enabled:
            return False
        
        # 检查冷却期
        now = time.time()
        if self.last_triggered and (now - self.last_triggered < self.cooldown_seconds):
            return False
        
        # 评估条件
        return self.condition.evaluate(context)
    
    def trigger(self, context: Dict[str, Any]) -> Alert:
        """触发告警"""
        self.last_triggered = time.time()
        
        alert = Alert(
            alert_id=f"alert_{self.rule_id}_{int(time.time())}",
            name=self.name,
            severity=self.severity,
            message=f"Rule '{self.name}' triggered",
            source=self.name,
            details=context.copy(),
            tags=self.tags
        )
        
        logger.warning(f"Alert triggered: {self.name} - {self.severity.name} - alert_id: {alert.alert_id}")
        
        return alert


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送通知"""
        pass


class LogNotificationChannel(NotificationChannel):
    """日志通知渠道"""
    
    def __init__(self):
        self.logger = get_logger("alert.notification.log")
    
    def send(self, alert: Alert) -> bool:
        """发送日志通知"""
        self.logger.error(
            f"[ALERT {alert.severity.name}] {alert.name}: {alert.message}",
            alert_id=alert.alert_id,
            source=alert.source,
            details=alert.details
        )
        return True


class MemoryNotificationChannel(NotificationChannel):
    """内存通知渠道（用于测试）"""
    
    def __init__(self):
        self.notifications: List[Alert] = []
        self._lock = threading.Lock()
    
    def send(self, alert: Alert) -> bool:
        """存储通知到内存"""
        with self._lock:
            self.notifications.append(alert)
        return True
    
    def get_notifications(self, limit: int = 100) -> List[Alert]:
        """获取通知记录"""
        with self._lock:
            return self.notifications[-limit:]
    
    def clear(self):
        """清空通知"""
        with self._lock:
            self.notifications.clear()


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
        self.channels: List[NotificationChannel] = []
        self._lock = threading.Lock()
        self._history: deque = deque(maxlen=1000)
        self._tracer = get_tracer("alert.manager")
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._event_queue: queue.Queue = queue.Queue()
        self.logger = get_logger("alert.manager")
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self.rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则"""
        with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                self.logger.info(f"Removed alert rule: {rule_id}")
                return True
        return False
    
    def add_channel(self, channel: NotificationChannel) -> None:
        """添加通知渠道"""
        with self._lock:
            self.channels.append(channel)
        self.logger.info("Added notification channel")
    
    def evaluate_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """评估所有规则"""
        triggered_alerts: List[Alert] = []
        
        with self._lock:
            rules_to_check = list(self.rules.values())
        
        for rule in rules_to_check:
            if rule.should_trigger(context):
                alert = rule.trigger(context)
                with self._lock:
                    self.alerts[alert.alert_id] = alert
                    self._history.append(alert)
                self._send_notifications(alert)
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def _send_notifications(self, alert: Alert) -> None:
        """发送通知"""
        with self._lock:
            channels = list(self.channels)
        
        for channel in channels:
            try:
                channel.send(alert)
            except Exception as e:
                self.logger.error(f"Failed to send notification: {e}", alert_id=alert.alert_id)
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """获取告警"""
        with self._lock:
            return self.alerts.get(alert_id)
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            alerts = [
                alert for alert in self.alerts.values()
                if alert.status == AlertStatus.ACTIVE
            ]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now()
                self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_note: str = "") -> bool:
        """解决告警"""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_by = resolved_by
                alert.resolution_note = resolution_note
                alert.updated_at = datetime.now()
                self.logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
                return True
        return False
    
    def close_alert(self, alert_id: str) -> bool:
        """关闭告警"""
        with self._lock:
            alert = self.alerts.get(alert_id)
            if alert:
                alert.status = AlertStatus.CLOSED
                alert.updated_at = datetime.now()
                self.logger.info(f"Alert closed: {alert_id}")
                return True
        return False
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        with self._lock:
            return list(self._history)[-limit:]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        with self._lock:
            active = sum(1 for a in self.alerts.values() if a.status == AlertStatus.ACTIVE)
            acknowledged = sum(1 for a in self.alerts.values() if a.status == AlertStatus.ACKNOWLEDGED)
            resolved = sum(1 for a in self.alerts.values() if a.status == AlertStatus.RESOLVED)
            
            severity_counts = {
                severity.name: sum(1 for a in self.alerts.values() if a.severity == severity)
                for severity in AlertSeverity
            }
            
            return {
                "total_alerts": len(self.alerts),
                "active": active,
                "acknowledged": acknowledged,
                "resolved": resolved,
                "by_severity": severity_counts,
                "rules_count": len(self.rules)
            }
    
    def start(self) -> None:
        """启动告警管理器"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info("Alert manager started")
    
    def stop(self) -> None:
        """停止告警管理器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.logger.info("Alert manager stopped")
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                context = self._event_queue.get(timeout=1)
                self.evaluate_rules(context)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Alert worker error: {e}", exc_info=True)
    
    def submit_context(self, context: Dict[str, Any]) -> None:
        """提交上下文进行评估"""
        self._event_queue.put(context.copy())


# 全局实例
_default_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = AlertManager()
    return _default_manager


def set_alert_manager(manager: AlertManager) -> None:
    """设置全局告警管理器"""
    global _default_manager
    _default_manager = manager
