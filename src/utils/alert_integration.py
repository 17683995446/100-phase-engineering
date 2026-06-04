"""
告警与健康检查集成
将健康检查状态与告警系统集成
"""

import threading
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

from src.utils.alerts import (
    AlertManager,
    AlertRule,
    ThresholdCondition,
    StatusCondition,
    AlertSeverity,
    LogNotificationChannel,
    MemoryNotificationChannel,
    get_alert_manager
)
from src.utils.health import (
    HealthMonitor,
    HealthStatus,
    get_health_monitor
)
from src.utils.logger import logger
from src.utils.structured_logging import get_logger


@dataclass
class HealthAlertConfig:
    """健康告警配置"""
    # 内存告警阈值
    memory_warning_threshold: float = 85.0
    memory_error_threshold: float = 95.0
    
    # 线程告警阈值
    thread_warning_threshold: int = 150
    thread_error_threshold: int = 200
    
    # 检查间隔
    check_interval_seconds: int = 30
    
    # 告警冷却
    alert_cooldown_seconds: int = 300


class HealthAlertIntegrator:
    """健康告警集成器"""
    
    def __init__(
        self,
        health_monitor: Optional[HealthMonitor] = None,
        alert_manager: Optional[AlertManager] = None,
        config: Optional[HealthAlertConfig] = None
    ):
        self.health_monitor = health_monitor or get_health_monitor()
        self.alert_manager = alert_manager or get_alert_manager()
        self.config = config or HealthAlertConfig()
        self.logger = get_logger("health.alert.integrator")
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._previous_health_status: Dict[str, HealthStatus] = {}
        self._lock = threading.Lock()
    
    def setup_default_rules(self) -> None:
        """设置默认告警规则"""
        # 内存使用告警
        memory_warning_rule = AlertRule(
            rule_id="health_memory_warning",
            name="High Memory Usage",
            condition=ThresholdCondition(
                metric_name="memory_percent",
                threshold=self.config.memory_warning_threshold,
                operator="gt"
            ),
            severity=AlertSeverity.WARNING,
            cooldown_seconds=self.config.alert_cooldown_seconds,
            description="Memory usage is high",
            tags=["health", "memory", "warning"]
        )
        self.alert_manager.add_rule(memory_warning_rule)
        
        memory_error_rule = AlertRule(
            rule_id="health_memory_error",
            name="Critical Memory Usage",
            condition=ThresholdCondition(
                metric_name="memory_percent",
                threshold=self.config.memory_error_threshold,
                operator="gt"
            ),
            severity=AlertSeverity.CRITICAL,
            cooldown_seconds=self.config.alert_cooldown_seconds,
            description="Memory usage is critically high",
            tags=["health", "memory", "critical"]
        )
        self.alert_manager.add_rule(memory_error_rule)
        
        # 线程数量告警
        thread_warning_rule = AlertRule(
            rule_id="health_thread_warning",
            name="High Thread Count",
            condition=ThresholdCondition(
                metric_name="thread_count",
                threshold=float(self.config.thread_warning_threshold),
                operator="gt"
            ),
            severity=AlertSeverity.WARNING,
            cooldown_seconds=self.config.alert_cooldown_seconds,
            description="Thread count is high",
            tags=["health", "threads", "warning"]
        )
        self.alert_manager.add_rule(thread_warning_rule)
        
        thread_error_rule = AlertRule(
            rule_id="health_thread_error",
            name="Critical Thread Count",
            condition=ThresholdCondition(
                metric_name="thread_count",
                threshold=float(self.config.thread_error_threshold),
                operator="gt"
            ),
            severity=AlertSeverity.CRITICAL,
            cooldown_seconds=self.config.alert_cooldown_seconds,
            description="Thread count is critically high",
            tags=["health", "threads", "critical"]
        )
        self.alert_manager.add_rule(thread_error_rule)
        
        # 组件状态告警
        component_error_rule = AlertRule(
            rule_id="health_component_error",
            name="Component Health Issue",
            condition=StatusCondition(
                source="component",
                expected_status="HEALTHY"
            ),
            severity=AlertSeverity.ERROR,
            cooldown_seconds=self.config.alert_cooldown_seconds,
            description="A component is not healthy",
            tags=["health", "component", "error"]
        )
        self.alert_manager.add_rule(component_error_rule)
        
        # 添加默认通知渠道
        log_channel = LogNotificationChannel()
        self.alert_manager.add_channel(log_channel)
        
        self.logger.info("Default health alert rules setup")
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """收集健康指标"""
        metrics = {}
        
        # 收集健康检查结果
        health_status = self.health_monitor.run_all_checks()
        
        for component_name, component_result in health_status.components.items():
            metrics[f"{component_name}_status"] = component_result.status.name
            if component_result.status == HealthStatus.UNHEALTHY:
                metrics["component_status"] = "UNHEALTHY"
            elif component_result.status == HealthStatus.DEGRADED:
                if metrics.get("component_status") != "UNHEALTHY":
                    metrics["component_status"] = "DEGRADED"
        
        metrics["overall_status"] = health_status.overall_status.name
        
        # 尝试收集系统指标
        try:
            import psutil
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["thread_count"] = float(threading.active_count())
        except ImportError:
            pass
        
        return metrics
    
    def _check_health_and_alert(self) -> None:
        """检查健康并触发告警"""
        context = self._collect_metrics()
        self.alert_manager.evaluate_rules(context)
    
    def start(self) -> None:
        """启动集成器"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info("Health alert integrator started")
    
    def stop(self) -> None:
        """停止集成器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.logger.info("Health alert integrator stopped")
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                self._check_health_and_alert()
            except Exception as e:
                self.logger.error(f"Health check error: {e}", exc_info=True)
            
            # 等待下一次检查
            for _ in range(self.config.check_interval_seconds):
                if not self._running:
                    break
                time.sleep(1)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        return self.alert_manager.get_alert_summary()
    
    def get_active_alerts(self):
        """获取活跃告警"""
        return self.alert_manager.get_active_alerts()


# 全局实例
_default_integrator: Optional[HealthAlertIntegrator] = None


def get_health_alert_integrator() -> HealthAlertIntegrator:
    """获取全局健康告警集成器"""
    global _default_integrator
    if _default_integrator is None:
        _default_integrator = HealthAlertIntegrator()
    return _default_integrator


def set_health_alert_integrator(integrator: HealthAlertIntegrator) -> None:
    """设置全局健康告警集成器"""
    global _default_integrator
    _default_integrator = integrator


def initialize_health_alerts() -> HealthAlertIntegrator:
    """初始化健康告警系统"""
    integrator = get_health_alert_integrator()
    integrator.setup_default_rules()
    integrator.start()
    return integrator
