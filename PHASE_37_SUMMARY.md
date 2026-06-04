# Phase 37 - 系统告警与通知机制

## 概述

本阶段实现了完整的系统告警与通知机制，为整个系统提供了基于规则的告警、告警管理和多渠道通知功能。该系统与Phase 36的健康检查系统完美集成，形成了完整的可观测性解决方案。

## 实现内容

### 1. 告警核心模块 ([src/utils/alerts.py](file:///workspace/src/utils/alerts.py))

#### 核心功能

- **AlertSeverity (告警级别)**: INFO, WARNING, ERROR, CRITICAL
- **AlertStatus (告警状态)**: ACTIVE, ACKNOWLEDGED, RESOLVED, CLOSED
- **Alert (告警对象)**: 包含告警ID、名称、级别、消息、状态、详情、时间戳、标签等
- **AlertRule (告警规则)**: 配置告警条件、级别、冷却期等

#### 告警条件类型

- **ThresholdCondition (阈值条件)**: 基于数值指标和阈值比较
  - 支持多种比较操作：gt, gte, lt, lte, eq
  - 支持时间窗口内平均值计算
- **StatusCondition (状态条件)**: 基于状态值比较

#### AlertManager (告警管理器)

核心功能：
- 规则管理：添加/删除告警规则
- 告警评估：定期或手动评估规则
- 告警管理：确认、解决、关闭告警
- 历史记录：维护告警历史
- 通知分发：通过多个渠道发送通知
- 工作线程：异步处理告警评估

#### 通知渠道

- **LogNotificationChannel**: 日志输出通知
- **MemoryNotificationChannel**: 内存存储通知（用于测试）
- **扩展接口**: 支持自定义通知渠道

### 2. 健康告警集成 ([src/utils/alert_integration.py](file:///workspace/src/utils/alert_integration.py))

#### HealthAlertConfig (健康告警配置)

- 内存告警阈值
- 线程告警阈值
- 检查间隔
- 告警冷却期

#### HealthAlertIntegrator (健康告警集成器)

- 自动收集健康指标
- 定期检查健康状态
- 预设默认告警规则
- 与健康检查系统无缝集成
- 后台工作线程循环检查

#### 预设告警规则

- 高内存使用告警 (WARNING)
- 严重内存使用告警 (CRITICAL)
- 高线程数告警 (WARNING)
- 严重线程数告警 (CRITICAL)
- 组件健康问题告警 (ERROR)

### 3. 系统集成

与Phase 35和36的完美集成：
- 与分布式追踪系统集成
- 与健康检查系统集成
- 与日志系统集成

## 功能特性

### 灵活的告警规则

```python
# 创建阈值告警
condition = ThresholdCondition(
    metric_name="cpu_usage",
    threshold=80.0,
    operator="gt",
    window_seconds=60  # 1分钟窗口平均
)
rule = AlertRule(
    rule_id="cpu_high",
    name="High CPU Usage",
    condition=condition,
    severity=AlertSeverity.WARNING,
    cooldown_seconds=300
)
```

### 告警生命周期管理

```python
# 确认告警
alert_manager.acknowledge_alert(alert_id, "operator")

# 解决告警
alert_manager.resolve_alert(alert_id, "admin", "Fixed issue")

# 关闭告警
alert_manager.close_alert(alert_id)
```

### 与健康检查集成

```python
from src.utils.alert_integration import initialize_health_alerts

# 初始化健康告警系统
integrator = initialize_health_alerts()

# 获取告警摘要
summary = integrator.get_alert_summary()

# 获取活跃告警
active_alerts = integrator.get_active_alerts()
```

## 使用示例

### 1. 基础告警规则

```python
from src.utils.alerts import (
    AlertManager,
    AlertRule,
    ThresholdCondition,
    AlertSeverity,
    LogNotificationChannel
)

# 创建告警管理器
alert_manager = AlertManager()

# 添加日志通知渠道
alert_manager.add_channel(LogNotificationChannel())

# 添加告警规则
condition = ThresholdCondition(
    metric_name="error_rate",
    threshold=5.0,
    operator="gt"
)
rule = AlertRule(
    rule_id="high_error_rate",
    name="High Error Rate",
    condition=condition,
    severity=AlertSeverity.ERROR
)
alert_manager.add_rule(rule)

# 评估规则
alerts = alert_manager.evaluate_rules({"error_rate": 10.0})
```

### 2. 健康告警配置

```python
from src.utils.alert_integration import (
    HealthAlertIntegrator,
    HealthAlertConfig
)

# 自定义配置
config = HealthAlertConfig(
    memory_warning_threshold=75.0,
    memory_error_threshold=90.0,
    thread_warning_threshold=200,
    thread_error_threshold=300,
    check_interval_seconds=10,
    alert_cooldown_seconds=600
)

integrator = HealthAlertIntegrator(config=config)
integrator.setup_default_rules()
integrator.start()
```

### 3. 自定义通知渠道

```python
from src.utils.alerts import NotificationChannel, Alert

class SlackNotificationChannel(NotificationChannel):
    def send(self, alert: Alert) -> bool:
        # 实现Slack通知发送逻辑
        message = f"[{alert.severity.name}] {alert.name}: {alert.message}"
        # slack_client.send(message)
        return True

alert_manager.add_channel(SlackNotificationChannel())
```

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| [src/utils/alerts.py](file:///workspace/src/utils/alerts.py) | 新增 | 告警核心模块 |
| [src/utils/alert_integration.py](file:///workspace/src/utils/alert_integration.py) | 新增 | 健康告警集成 |
| [test_phase37_alerts.py](file:///workspace/test_phase37_alerts.py) | 新增 | Phase 37测试文件 |

## 阶段成果

Phase 37成功完成！系统现在具有：

1. ✅ 完整的告警核心框架
2. ✅ 灵活的告警规则系统
3. ✅ 阈值和状态条件支持
4. ✅ 告警生命周期管理
5. ✅ 多渠道通知支持
6. ✅ 健康检查集成
7. ✅ 与分布式追踪集成

## 与前序阶段的集成

### Phase 35 - 分布式追踪
- 告警评估过程包含分布式追踪
- 每个告警操作都有对应的追踪Span

### Phase 36 - 健康检查
- 自动收集健康检查指标
- 基于健康状态触发告警
- 预设系统健康告警规则

## 未来改进方向

1. **更多通知渠道**: Slack、Email、PagerDuty、Webhook等
2. **告警聚合**: 相关告警聚合减少噪音
3. **告警抑制**: 基于时间或依赖关系抑制告警
4. **告警升级**: 自动升级严重级别
5. **告警模板**: 可配置的通知模板
6. **持久化存储**: 告警历史持久化
7. **可视化界面**: 告警查看和管理界面

## 测试覆盖

10个测试用例全部通过 ✓：
- 阈值条件测试
- 状态条件测试
- 告警规则测试
- 告警管理器基础功能
- 告警生命周期测试
- 告警摘要测试
- 冷却期测试
- 默认规则设置测试
- 指标收集测试
- 集成触发测试
