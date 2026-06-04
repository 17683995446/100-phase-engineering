"""
监控告警系统
提供指标收集、阈值监控、告警触发、通知渠道和告警历史功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

from src.utils.structured_logging import get_logger


class AlertSeverity(Enum):
    """告警级别"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """告警状态"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class ComparisonOperator(Enum):
    """比较操作符"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    metric_name: str
    operator: ComparisonOperator
    threshold: float
    duration: int = 0
    severity: AlertSeverity = AlertSeverity.MEDIUM
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "duration": self.duration,
            "severity": self.severity.value,
            "enabled": self.enabled
        }


@dataclass
class Alert:
    """告警实例"""
    alert_id: str
    rule_id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.FIRING
    value: float = 0.0
    threshold: float = 0.0
    fired_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    message: str = ""
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "fired_at": self.fired_at,
            "resolved_at": self.resolved_at,
            "acknowledged_by": self.acknowledged_by,
            "message": self.message
        }


class MonitoringAlertSystem:
    """监控告警系统"""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._logger = get_logger("monitoring.alert")
        self._notifiers: Dict[str, Callable[[Alert], None]] = {}
        self._alert_counter = 0

    def register_notifier(self, channel: str,
                          handler: Callable[[Alert], None]) -> None:
        """注册通知渠道"""
        with self._lock:
            self._notifiers[channel] = handler

    def create_rule(self, rule_id: str, name: str, metric_name: str,
                    operator: ComparisonOperator, threshold: float,
                    duration: int = 0,
                    severity: AlertSeverity = AlertSeverity.MEDIUM,
                    labels: Optional[Dict[str, str]] = None) -> AlertRule:
        """创建告警规则"""
        with self._lock:
            if rule_id in self._rules:
                raise ValueError(f"Rule already exists: {rule_id}")

            rule = AlertRule(
                rule_id=rule_id,
                name=name,
                metric_name=metric_name,
                operator=operator,
                threshold=threshold,
                duration=duration,
                severity=severity,
                labels=labels or {}
            )
            self._rules[rule_id] = rule
            self._logger.info(f"Alert rule created: {rule_id}")
            return rule

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取告警规则"""
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self) -> List[Dict[str, Any]]:
        """列出告警规则"""
        with self._lock:
            return [r.to_dict() for r in self._rules.values()]

    def delete_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._logger.info(f"Alert rule deleted: {rule_id}")
                return True
            return False

    def enable_rule(self, rule_id: str) -> bool:
        """启用告警规则"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = True
                return True
            return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用告警规则"""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = False
                return True
            return False

    def record_metric(self, metric_name: str, value: float,
                      labels: Optional[Dict[str, str]] = None) -> None:
        """记录指标"""
        with self._lock:
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            key = self._metric_key(metric_name, labels or {})
            self._metrics[key].append(point)
            self._evaluate_rules(metric_name, value, labels or {})

    def _metric_key(self, metric_name: str, labels: Dict[str, str]) -> str:
        """生成指标键"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}{{{label_str}}}"
        return metric_name

    def _evaluate_rules(self, metric_name: str, value: float,
                        labels: Dict[str, str]) -> None:
        """评估告警规则"""
        for rule in self._rules.values():
            if not rule.enabled or rule.metric_name != metric_name:
                continue

            # 检查标签匹配
            if rule.labels and not all(
                labels.get(k) == v for k, v in rule.labels.items()
            ):
                continue

            triggered = self._compare(value, rule.operator, rule.threshold)

            if triggered:
                self._trigger_alert(rule, value, labels)
            else:
                self._resolve_alert(rule, value)

    def _compare(self, value: float, operator: ComparisonOperator,
                 threshold: float) -> bool:
        """比较值"""
        if operator == ComparisonOperator.GREATER_THAN:
            return value > threshold
        elif operator == ComparisonOperator.LESS_THAN:
            return value < threshold
        elif operator == ComparisonOperator.EQUAL:
            return value == threshold
        elif operator == ComparisonOperator.NOT_EQUAL:
            return value != threshold
        elif operator == ComparisonOperator.GREATER_EQUAL:
            return value >= threshold
        elif operator == ComparisonOperator.LESS_EQUAL:
            return value <= threshold
        return False

    def _trigger_alert(self, rule: AlertRule, value: float,
                       labels: Dict[str, str]) -> None:
        """触发告警"""
        alert_key = f"{rule.rule_id}:{self._labels_key(labels)}"

        # 检查是否已有活跃告警
        for alert in self._alerts.values():
            if alert.rule_id == rule.rule_id and alert.status == AlertStatus.FIRING:
                if all(alert.labels.get(k) == v for k, v in labels.items()):
                    return

        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter}"
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            value=value,
            threshold=rule.threshold,
            message=f"{rule.name}: {value} {rule.operator.value} {rule.threshold}",
            labels=dict(labels)
        )
        self._alerts[alert_id] = alert
        self._history.append({
            "alert_id": alert_id,
            "action": "fired",
            "timestamp": time.time()
        })
        self._logger.warning(f"Alert fired: {alert_id} - {alert.message}")

        # 发送通知
        for handler in self._notifiers.values():
            try:
                handler(alert)
            except Exception as e:
                self._logger.error(f"Notifier error: {e}")

    def _resolve_alert(self, rule: AlertRule, value: float) -> None:
        """解决告警"""
        for alert in list(self._alerts.values()):
            if alert.rule_id == rule.rule_id and alert.status == AlertStatus.FIRING:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = time.time()
                alert.value = value
                self._history.append({
                    "alert_id": alert.alert_id,
                    "action": "resolved",
                    "timestamp": time.time()
                })
                self._logger.info(f"Alert resolved: {alert.alert_id}")

    def _labels_key(self, labels: Dict[str, str]) -> str:
        """生成标签键"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """确认告警"""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert or alert.status != AlertStatus.FIRING:
                return False
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            alert.acknowledged_by = user
            self._logger.info(f"Alert acknowledged: {alert_id} by {user}")
            return True

    def suppress_alert(self, alert_id: str) -> bool:
        """抑制告警"""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return False
            alert.status = AlertStatus.SUPPRESSED
            self._logger.info(f"Alert suppressed: {alert_id}")
            return True

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """获取告警"""
        with self._lock:
            return self._alerts.get(alert_id)

    def list_alerts(self, status: Optional[str] = None,
                    severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出告警"""
        with self._lock:
            alerts = self._alerts.values()
            if status:
                alerts = [a for a in alerts if a.status.value == status]
            if severity:
                alerts = [a for a in alerts if a.severity.value == severity]
            return [a.to_dict() for a in alerts]

    def get_metrics(self, metric_name: str,
                    labels: Optional[Dict[str, str]] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标数据"""
        with self._lock:
            key = self._metric_key(metric_name, labels or {})
            points = list(self._metrics.get(key, []))[-limit:]
            return [
                {"timestamp": p.timestamp, "value": p.value, "labels": p.labels}
                for p in points
            ]

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        with self._lock:
            return list(self._history)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            firing = sum(1 for a in self._alerts.values()
                         if a.status == AlertStatus.FIRING)
            resolved = sum(1 for a in self._alerts.values()
                           if a.status == AlertStatus.RESOLVED)
            acknowledged = sum(1 for a in self._alerts.values()
                               if a.status == AlertStatus.ACKNOWLEDGED)
            return {
                "total_rules": len(self._rules),
                "total_alerts": len(self._alerts),
                "firing": firing,
                "resolved": resolved,
                "acknowledged": acknowledged,
                "total_metrics": len(self._metrics)
            }


# 全局实例
_system: Optional[MonitoringAlertSystem] = None


def get_monitoring_alert_system() -> MonitoringAlertSystem:
    """获取全局监控告警系统"""
    global _system
    if _system is None:
        _system = MonitoringAlertSystem()
    return _system
