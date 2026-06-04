"""
审计日志系统
提供操作记录、日志查询、合规性检查和审计报告功能
"""
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.utils.structured_logging import get_logger


class AuditLevel(Enum):
    """审计级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(Enum):
    """审计动作"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS = "access"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"


@dataclass
class AuditEntry:
    """审计条目"""
    entry_id: str
    timestamp: float
    user_id: str
    action: AuditAction
    resource: str
    resource_id: str
    level: AuditLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    result: str = "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "user_id": self.user_id,
            "action": self.action.value,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "result": self.result
        }


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._counter = 0
        self._logger = get_logger("audit.logger")

    def _generate_id(self) -> str:
        """生成条目ID"""
        with self._lock:
            self._counter += 1
            return f"AUDIT_{int(time.time())}_{self._counter}"

    def log(self, user_id: str, action: AuditAction, resource: str,
            resource_id: str, level: AuditLevel = AuditLevel.INFO,
            message: str = "", details: Optional[Dict[str, Any]] = None,
            ip_address: str = "", user_agent: str = "",
            result: str = "success") -> AuditEntry:
        """记录审计日志"""
        entry = AuditEntry(
            entry_id=self._generate_id(),
            timestamp=time.time(),
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            level=level,
            message=message,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            result=result
        )

        with self._lock:
            self._entries.append(entry)

        self._logger.info(f"Audit: {user_id} {action.value} {resource}/{resource_id}")
        return entry

    def query(self, user_id: Optional[str] = None,
              action: Optional[AuditAction] = None,
              resource: Optional[str] = None,
              start_time: Optional[float] = None,
              end_time: Optional[float] = None,
              level: Optional[AuditLevel] = None,
              result: Optional[str] = None) -> List[AuditEntry]:
        """查询审计日志"""
        with self._lock:
            results = self._entries.copy()

        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if resource:
            results = [e for e in results if e.resource == resource]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if level:
            results = [e for e in results if e.level == level]
        if result:
            results = [e for e in results if e.result == result]

        return results

    def get_entries_by_resource(self, resource: str,
                                resource_id: Optional[str] = None) -> List[AuditEntry]:
        """获取资源的审计条目"""
        with self._lock:
            entries = [e for e in self._entries if e.resource == resource]
            if resource_id:
                entries = [e for e in entries if e.resource_id == resource_id]
            return entries

    def get_entries_by_user(self, user_id: str) -> List[AuditEntry]:
        """获取用户的审计条目"""
        with self._lock:
            return [e for e in self._entries if e.user_id == user_id]

    def get_recent_entries(self, limit: int = 100) -> List[AuditEntry]:
        """获取最近的审计条目"""
        with self._lock:
            return sorted(self._entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        """清空日志"""
        with self._lock:
            self._entries.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self._entries)
            by_action = {}
            by_level = {}
            by_result = {}
            for entry in self._entries:
                action = entry.action.value
                level = entry.level.value
                result = entry.result
                by_action[action] = by_action.get(action, 0) + 1
                by_level[level] = by_level.get(level, 0) + 1
                by_result[result] = by_result.get(result, 0) + 1

            return {
                "total_entries": total,
                "by_action": by_action,
                "by_level": by_level,
                "by_result": by_result
            }


class AuditReport:
    """审计报告"""

    def __init__(self, audit_logger: AuditLogger):
        self._audit = audit_logger
        self._logger = get_logger("audit.report")

    def generate_report(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """生成审计报告"""
        entries = self._audit.query(start_time=start_time, end_time=end_time)

        user_activity = {}
        resource_activity = {}
        failed_actions = []

        for entry in entries:
            # 用户活动统计
            if entry.user_id not in user_activity:
                user_activity[entry.user_id] = 0
            user_activity[entry.user_id] += 1

            # 资源活动统计
            key = f"{entry.resource}/{entry.resource_id}"
            if key not in resource_activity:
                resource_activity[key] = 0
            resource_activity[key] += 1

            # 失败记录
            if entry.result != "success":
                failed_actions.append(entry.to_dict())

        return {
            "period": {
                "start": datetime.fromtimestamp(start_time).isoformat(),
                "end": datetime.fromtimestamp(end_time).isoformat()
            },
            "total_entries": len(entries),
            "user_activity": user_activity,
            "resource_activity": resource_activity,
            "failed_actions": failed_actions,
            "failure_rate": len(failed_actions) / max(len(entries), 1)
        }

    def check_compliance(self, rules: List[Callable[[AuditEntry], bool]]) -> List[Dict[str, Any]]:
        """合规性检查"""
        violations = []
        entries = self._audit.query()

        for entry in entries:
            for rule in rules:
                if not rule(entry):
                    violations.append({
                        "entry": entry.to_dict(),
                        "violation": "Rule check failed"
                    })

        return violations


# 全局实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
