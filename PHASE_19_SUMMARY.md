# Phase 19: 监控与告警系统

## 阶段目标

实现完整的监控与告警系统，提供系统状态完全可观测性，遵循可观测性公理：系统状态完全可观测，无隐藏状态，提供实时监控与告警。

## 核心成果

### 1. 指标类型与值 (MetricType & MetricValue)

**文件**: `/workspace/src/scheduling_layer/monitoring.py`

```python
class MetricType(Enum):
    COUNTER = auto()    # 计数器: 只增不减
    GAUGE = auto()      # 仪表盘: 可增可减
    HISTOGRAM = auto()  # 直方图: 分布统计
    TIMER = auto()      # 计时器: 时间统计

@dataclass
class MetricValue:
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metadata: Dict[str, Any]
```

### 2. 告警类型与状态 (AlertSeverity & AlertStatus)

```python
class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

class AlertStatus(Enum):
    PENDING = auto()
    ACTIVE = auto()
    ACKNOWLEDGED = auto()
    RESOLVED = auto()
```

### 3. 指标注册表 (MetricsRegistry)

核心功能：
- `record(metric_name, value, labels)` - 记录指标值
- `increment(metric_name, by, labels)` - 递增计数器
- `decrement(metric_name, by, labels)` - 递减计数器
- `gauge(metric_name, value, labels)` - 设置仪表盘值
- `get_statistics(metric_name, window)` - 获取指标统计信息
- 支持标签和元数据，保留最近10000个值

### 4. 告警管理器 (AlertManager)

核心功能：
- `register_rule(rule)` - 注册告警规则
- `create_alert(rule_id, severity, message)` - 创建告警
- `acknowledge_alert(alert_id)` - 确认告警
- `resolve_alert(alert_id)` - 解决告警
- `evaluate_rules()` - 评估告警规则
- `start_rule_evaluation()` - 启动规则评估线程
- `get_statistics()` - 获取告警统计信息

### 5. 告警规则 (AlertRule)

```python
@dataclass
class AlertRule:
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    evaluation_interval: float = 60.0
    enabled: bool = True
    labels: Dict[str, str]
```

### 6. 监控系统 (MonitoringSystem)

核心功能：
- `start()` - 启动监控系统（指标收集 + 告警规则评估）
- `stop()` - 停止监控系统
- `get_status()` - 获取监控系统状态
- 内置默认指标收集器和告警规则
- 与 EventTracker 集成（可进一步扩展）

## 技术特性

### 1. 多类型指标支持

支持四种类型的指标，适应不同的监控场景：
- 计数器：只增不减（如请求数、任务数）
- 仪表盘：可增可减（如内存使用、CPU负载）
- 直方图：分布统计（如响应时间分布）
- 计时器：时间统计

### 2. 自动规则评估

告警规则支持条件函数，自动评估：
```python
def high_error_rate_condition(data: Dict[str, Any]) -> bool:
    error_rate_stats = data.get("metrics", {}).get("error_rate")
    if error_rate_stats and error_rate_stats.get("latest", 0) > 0.1:
        return True
    return False
```

### 3. 告警生命周期管理

告警完整的状态转换：
- PENDING → ACTIVE → ACKNOWLEDGED → RESOLVED
- 完整的历史记录和元数据

### 4. 统计与分析

每个指标都提供丰富的统计：
- 最小值、最大值、平均值
- 最新值、计数
- 时间窗口支持（默认最近60秒）

### 5. 线程安全

使用锁保证并发安全，支持多线程环境：
```python
self._lock = threading.RLock()
```

## 验证测试

**文件**: `/workspace/test_monitoring.py`

**测试覆盖**:
- 指标注册表功能（8个测试）
- 告警管理器功能（6个测试）
- 监控系统功能（3个测试）
- 全局实例与集成（3个测试）

**测试结果**: 20个测试全部通过 ✓

## 与现有系统集成

### 1. 与 EventTracker 集成

- 事件追踪器和监控系统互补
- 可将事件计数为指标（如错误事件数）
- 可在事件发生时创建告警

### 2. 与 StateManager 集成

- 可监控状态管理器的关键指标（如活跃任务数）
- 可在状态异常时触发告警

### 3. 与 TaskDispatcher 集成

- 可监控任务分发器的负载
- 可监控任务完成率和延迟

## 使用示例

### 1. 基本指标收集

```python
from src.scheduling_layer.monitoring import MetricsRegistry

registry = MetricsRegistry()

# 计数器
registry.increment("request_count", by=1)

# 仪表盘
registry.gauge("memory_usage", 75.5)

# 获取统计
stats = registry.get_statistics("memory_usage")
print(f"Min: {stats['min']}, Max: {stats['max']}, Avg: {stats['avg']}")
```

### 2. 告警规则

```python
from src.scheduling_layer.monitoring import AlertManager, AlertRule, AlertSeverity

manager = AlertManager()

# 创建总是触发的规则
def always_trigger(data: dict) -> bool:
    return True

rule = AlertRule(
    rule_id="test_rule",
    name="Test Rule",
    description="Always triggers",
    severity=AlertSeverity.WARNING,
    condition=always_trigger
)

manager.register_rule(rule)
```

### 3. 完整监控系统

```python
from src.scheduling_layer.monitoring import MonitoringSystem, get_monitoring_system

system = get_monitoring_system()

# 启动
system.start()

# 获取状态
status = system.get_status()
print(f"Running: {status['running']}")
print(f"Active Alerts: {status['alerts']['active_alerts']}")

# 停止
system.stop()
```

## 架构位置

**调度层 (scheduling_layer)** 核心组件：
- 位置: `src/scheduling_layer/monitoring.py`
- 导出: `src/scheduling_layer/__init__.py`
- 依赖: event_tracker.py, logger.py

## 设计原则

1. **可观测性**: 系统状态完全可观测，无隐藏状态
2. **实时监控**: 指标收集和告警评估实时进行
3. **灵活告警**: 自定义告警条件，支持多种严重程度
4. **完整生命周期**: 告警有完整的状态转换流程
5. **统计分析**: 提供丰富的统计分析能力

## 下一步

Phase 20 将实现系统的最后一个关键功能，完成 100 阶段计划的圆满结束。

## 统计

- **代码行数**: ~530行
- **测试用例**: 20个
- **测试通过率**: 100%
- **指标类型**: 4种
- **告警状态**: 4种
- **导出API**: 13个
