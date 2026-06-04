"""
可观测性仪表板与可视化系统
提供健康状态、告警、追踪的统一可视化接口
"""
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from src.utils.health import (
    get_health_monitor,
    HealthStatus,
    HealthCheckType
)
from src.utils.alerts import (
    get_alert_manager,
    AlertSeverity,
    AlertStatus
)
from src.utils.telemetry import (
    get_tracer,
    SpanContext
)
from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class DashboardStatus:
    """仪表板总状态"""
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    active_alerts_count: int = 0
    critical_alerts_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0


@dataclass
class HealthWidgetData:
    """健康检查组件数据"""
    component_name: str
    status: HealthStatus
    last_check_time: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertWidgetData:
    """告警组件数据"""
    alert_id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    created_time: datetime
    source: str


@dataclass
class TraceWidgetData:
    """追踪组件数据"""
    trace_id: str
    spans_count: int
    duration_ms: float
    start_time: datetime
    status: str
    service_name: str


class ObservabilityDashboard:
    """可观测性仪表板核心类"""
    
    def __init__(self):
        self.health_monitor = get_health_monitor()
        self.alert_manager = get_alert_manager()
        self.tracer = get_tracer("observability.dashboard")
        
        self.logger = get_logger("observability.dashboard")
        self._dashboard_start_time = time.time()
        
        # 缓存数据
        self._cached_status = DashboardStatus()
        self._cached_health_widgets: Dict[str, HealthWidgetData] = {}
        self._cached_alert_widgets: List[AlertWidgetData] = []
        self._cached_trace_widgets: List[TraceWidgetData] = []
        self._cache_lock = threading.Lock()
        
        # 更新配置
        self._auto_update_interval = 30  # 秒
        self._max_cached_items = 100
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
    
    def get_dashboard_overview(self) -> Dict[str, Any]:
        """获取仪表板总览"""
        with self._cache_lock:
            self._cached_status.uptime_seconds = time.time() - self._dashboard_start_time
        
        self._refresh_cached_status()
        
        with self._cache_lock:
            status = self._cached_status
            return {
                "overall_health": status.overall_health.name,
                "active_alerts_count": status.active_alerts_count,
                "critical_alerts_count": status.critical_alerts_count,
                "uptime_seconds": status.uptime_seconds,
                "last_updated": status.last_updated.isoformat()
            }
    
    def get_health_widgets(self) -> Dict[str, Any]:
        """获取健康状态组件"""
        self._refresh_health_widgets()
        
        with self._cache_lock:
            widgets_data = []
            for component_name, widget in self._cached_health_widgets.items():
                widgets_data.append({
                    "component_name": widget.component_name,
                    "status": widget.status.name,
                    "last_check_time": widget.last_check_time.isoformat(),
                    "response_time_ms": widget.response_time_ms,
                    "details": widget.details
                })
            
            summary = self._calculate_health_summary()
            
            return {
                "widgets": widgets_data,
                "summary": summary,
                "last_updated": datetime.now().isoformat()
            }
    
    def get_alert_widgets(self, limit: int = 50) -> Dict[str, Any]:
        """获取告警组件"""
        self._refresh_alert_widgets()
        
        with self._cache_lock:
            widgets_data = []
            for widget in self._cached_alert_widgets[:limit]:
                widgets_data.append({
                    "alert_id": widget.alert_id,
                    "name": widget.name,
                    "severity": widget.severity.name,
                    "status": widget.status.name,
                    "message": widget.message,
                    "created_time": widget.created_time.isoformat(),
                    "source": widget.source
                })
            
            summary = self._calculate_alert_summary()
            
            return {
                "widgets": widgets_data,
                "summary": summary,
                "last_updated": datetime.now().isoformat()
            }
    
    def get_trace_widgets(self, limit: int = 50) -> Dict[str, Any]:
        """获取追踪组件（模拟）"""
        self._refresh_trace_widgets()
        
        with self._cache_lock:
            widgets_data = []
            for widget in self._cached_trace_widgets[:limit]:
                widgets_data.append({
                    "trace_id": widget.trace_id,
                    "spans_count": widget.spans_count,
                    "duration_ms": widget.duration_ms,
                    "start_time": widget.start_time.isoformat(),
                    "status": widget.status,
                    "service_name": widget.service_name
                })
            
            summary = self._calculate_trace_summary()
            
            return {
                "widgets": widgets_data,
                "summary": summary,
                "last_updated": datetime.now().isoformat()
            }
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        result = self.alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        if result:
            self._refresh_alert_widgets()
        return result
    
    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_note: str = "") -> bool:
        """解决告警"""
        result = self.alert_manager.resolve_alert(alert_id, resolved_by, resolution_note)
        if result:
            self._refresh_alert_widgets()
        return result
    
    def close_alert(self, alert_id: str) -> bool:
        """关闭告警"""
        result = self.alert_manager.close_alert(alert_id)
        if result:
            self._refresh_alert_widgets()
        return result
    
    def run_health_checks(self) -> Dict[str, Any]:
        """立即运行健康检查"""
        result = self.health_monitor.run_all_checks()
        self._refresh_health_widgets()
        return result.to_dict()
    
    def _refresh_cached_status(self) -> None:
        """刷新总状态缓存"""
        # 获取健康状态
        health_result = self.health_monitor.run_all_checks()
        
        # 获取告警统计
        alert_summary = self.alert_manager.get_alert_summary()
        
        with self._cache_lock:
            self._cached_status = DashboardStatus(
                overall_health=health_result.overall_status,
                active_alerts_count=alert_summary["active"],
                critical_alerts_count=alert_summary["by_severity"].get("CRITICAL", 0),
                last_updated=datetime.now(),
                uptime_seconds=time.time() - self._dashboard_start_time
            )
    
    def _refresh_health_widgets(self) -> None:
        """刷新健康组件缓存"""
        health_result = self.health_monitor.run_all_checks()
        
        with self._cache_lock:
            self._cached_health_widgets.clear()
            
            for component_name, component_result in health_result.components.items():
                widget = HealthWidgetData(
                    component_name=component_name,
                    status=component_result.status,
                    last_check_time=datetime.now(),
                    response_time_ms=component_result.duration_ms,
                    details=component_result.details
                )
                self._cached_health_widgets[component_name] = widget
    
    def _refresh_alert_widgets(self) -> None:
        """刷新告警组件缓存"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        # 按创建时间排序（最新在前）
        sorted_alerts = sorted(
            active_alerts,
            key=lambda a: a.created_at,
            reverse=True
        )
        
        with self._cache_lock:
            self._cached_alert_widgets.clear()
            
            for alert in sorted_alerts:
                widget = AlertWidgetData(
                    alert_id=alert.alert_id,
                    name=alert.name,
                    severity=alert.severity,
                    status=alert.status,
                    message=alert.message,
                    created_time=alert.created_at,
                    source=alert.source
                )
                self._cached_alert_widgets.append(widget)
    
    def _refresh_trace_widgets(self) -> None:
        """刷新追踪组件缓存（模拟）"""
        # 这里模拟一些追踪数据
        import random
        
        sample_traces = [
            {
                "trace_id": f"trace_{random.randint(1000, 9999)}",
                "spans_count": random.randint(1, 10),
                "duration_ms": random.uniform(10, 500),
                "status": "OK" if random.random() > 0.1 else "ERROR",
                "service_name": "api.service"
            },
            {
                "trace_id": f"trace_{random.randint(1000, 9999)}",
                "spans_count": random.randint(1, 10),
                "duration_ms": random.uniform(10, 500),
                "status": "OK" if random.random() > 0.1 else "ERROR",
                "service_name": "scheduling.service"
            }
        ]
        
        with self._cache_lock:
            self._cached_trace_widgets.clear()
            
            for trace_data in sample_traces:
                widget = TraceWidgetData(
                    trace_id=trace_data["trace_id"],
                    spans_count=trace_data["spans_count"],
                    duration_ms=trace_data["duration_ms"],
                    start_time=datetime.now(),
                    status=trace_data["status"],
                    service_name=trace_data["service_name"]
                )
                self._cached_trace_widgets.append(widget)
    
    def _calculate_health_summary(self) -> Dict[str, Any]:
        """计算健康状态统计"""
        with self._cache_lock:
            widgets = list(self._cached_health_widgets.values())
            
            summary = {
                "total": len(widgets),
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "unknown": 0
            }
            
            for widget in widgets:
                status_name = widget.status.name
                summary[status_name.lower()] = summary.get(status_name.lower(), 0) + 1
            
            return summary
    
    def _calculate_alert_summary(self) -> Dict[str, Any]:
        """计算告警统计"""
        return self.alert_manager.get_alert_summary()
    
    def _calculate_trace_summary(self) -> Dict[str, Any]:
        """计算追踪统计"""
        with self._cache_lock:
            total = len(self._cached_trace_widgets)
            error_count = sum(1 for t in self._cached_trace_widgets if t.status == "ERROR")
            avg_duration = (
                sum(t.duration_ms for t in self._cached_trace_widgets) / total
                if total > 0 else 0
            )
            
            return {
                "total": total,
                "error_count": error_count,
                "avg_duration_ms": avg_duration
            }
    
    def start_auto_update(self, interval_seconds: int = 30) -> None:
        """启动自动更新"""
        if self._running:
            return
        
        self._running = True
        self._auto_update_interval = interval_seconds
        self._update_thread = threading.Thread(
            target=self._auto_update_loop,
            daemon=True
        )
        self._update_thread.start()
        self.logger.info(f"Dashboard auto-update started (interval: {interval_seconds}s)")
    
    def stop_auto_update(self) -> None:
        """停止自动更新"""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=5)
        self.logger.info("Dashboard auto-update stopped")
    
    def _auto_update_loop(self) -> None:
        """自动更新循环"""
        while self._running:
            try:
                self._refresh_cached_status()
                self._refresh_health_widgets()
                self._refresh_alert_widgets()
            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}", exc_info=True)
            
            time.sleep(self._auto_update_interval)


# 全局实例
_dashboard_instance: Optional[ObservabilityDashboard] = None


def get_observability_dashboard() -> ObservabilityDashboard:
    """获取全局可观测性仪表板实例"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = ObservabilityDashboard()
    return _dashboard_instance


def set_observability_dashboard(dashboard: ObservabilityDashboard) -> None:
    """设置全局可观测性仪表板实例"""
    global _dashboard_instance
    _dashboard_instance = dashboard
