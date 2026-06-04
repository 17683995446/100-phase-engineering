# Phase 27: Prometheus 指标收集系统

## 阶段概述

**阶段名称**: Prometheus 指标收集系统
**完成状态**: ✅ 已完成
**测试结果**: 29 个测试用例全部通过
**系统总测试**: 440+ 个测试通过

## 核心设计原则

遵循 **可观测性公理**: 系统状态完全可观测，无隐藏状态，提供 Prometheus 标准格式

## 核心架构

### 指标类型枚举

```python
class PromMetricType(Enum):
    COUNTER = auto()      # 计数器（只增不减）
    GAUGE = auto()        # 仪表盘（可增可减）
    HISTOGRAM = auto()    # 直方图（分布统计）
    SUMMARY = auto()      # 摘要（分位数统计）
```

## 主要组件

### Counter（计数器）
- 只增不减的指标
- 适用于：请求数、错误数、处理量等
- 提供 `inc()` 方法递增
- 支持标签和命名空间

### Gauge（仪表盘）
- 可增可减的指标
- 适用于：活跃任务数、CPU 使用率、内存使用量等
- 提供 `set()`、`inc()`、`dec()` 方法

### Histogram（直方图）
- 统计数值分布的指标
- 适用于：请求延迟、响应时间、处理耗时等
- 默认桶：[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0] +Inf
- 提供 `observe()` 方法记录观测值
- 输出包含：桶计数、总和、总数

### Summary（摘要）
- 统计分位数的指标
- 适用于：P50、P90、P95、P99 延迟
- 默认分位数：[0.5, 0.9, 0.95, 0.99]
- 提供 `observe()` 方法记录观测值
- 保留最近 1000 个值用于计算分位数

## PrometheusRegistry（注册表）

### 核心功能
- 指标注册和管理
- 命名空间隔离
- 线程安全
- 生成标准 Prometheus 文本格式

### 创建指标的方法
```python
registry = PrometheusRegistry(namespace="maes")

# 计数器
counter = registry.create_counter("requests_total", help_text="Total requests", labels={"service": "api"})

# 仪表盘
gauge = registry.create_gauge("active_workers", help_text="Active workers")

# 直方图
hist = registry.create_histogram("request_duration_seconds", help_text="Request duration", buckets=[0.1, 0.5, 1.0])

# 摘要
summary = registry.create_summary("response_latency_seconds", quantiles=[0.5, 0.9, 0.95])
```

## 便捷函数

### 使用默认注册表
```python
from src.utils.prometheus import counter, gauge, histogram, summary, timer

# 创建并获取计数器
c = counter("api_requests_total", help_text="API requests")
c.inc()

# 创建并获取仪表盘
g = gauge("active_tasks", help_text="Active tasks")
g.set(10)

# 计时器装饰器
hist = histogram("function_duration_seconds")
@timer(hist)
def expensive_function():
    pass
```

## 文本格式输出

### Prometheus 标准格式示例
```
# HELP maes_requests_total Total requests
# TYPE maes_requests_total counter
maes_requests_total{service="api",method="GET"} 42

# HELP maes_request_duration_seconds Request duration
# TYPE maes_request_duration_seconds histogram
maes_request_duration_seconds_bucket{le="0.1"} 10
maes_request_duration_seconds_bucket{le="0.5"} 25
maes_request_duration_seconds_bucket{le="+Inf"} 100
maes_request_duration_seconds_sum 50.5
maes_request_duration_seconds_count 100

# HELP maes_response_latency_seconds Response latency
# TYPE maes_response_latency_seconds summary
maes_response_latency_seconds{quantile="0.5"} 0.25
maes_response_latency_seconds{quantile="0.9"} 0.5
maes_response_latency_seconds_sum 100.0
maes_response_latency_seconds_count 200
```

## 使用示例

### 基础使用
```python
from src.utils.prometheus import PrometheusRegistry, timer

registry = PrometheusRegistry(namespace="maes")
request_count = registry.create_counter("requests_total", help_text="Total requests")
request_duration = registry.create_histogram("request_duration_seconds")

@timer(request_duration)
def handle_request():
    request_count.inc()
    # 处理请求
    pass

# 使用指标
metrics_text = registry.generate_text_format()
```

### 标签使用
```python
success_count = registry.create_counter("requests_success_total", labels={"method": "GET", "status": "200"})
error_count = registry.create_counter("requests_errors_total", labels={"method": "POST", "status": "500"})

success_count.inc()
error_count.inc()
```

### 性能测量
```python
duration_hist = registry.create_histogram("task_processing_seconds", buckets=[0.1, 1.0, 5.0, 10.0])

@timer(duration_hist)
def process_task(task_data):
    # 处理任务
    pass
```

## 与现有监控系统集成

### Phase 19 监控系统对比
- 原系统：自定义 MetricsRegistry（历史保留）
- 新增系统：Prometheus 标准格式（与外部监控集成）
- 两者可以同时使用，不冲突

## 文件清单

| 文件路径 | 描述 |
|---------|------|
| [src/utils/prometheus.py](file:///workspace/src/utils/prometheus.py) | Prometheus 指标收集核心 |
| [test_prometheus.py](file:///workspace/test_prometheus.py) | 29 个测试用例 |
| [src/utils/__init__.py](file:///workspace/src/utils/__init__.py) | 模块导出更新 |
| [PHASE_27_SUMMARY.md](file:///workspace/PHASE_27_SUMMARY.md) | 本阶段总结 |

## 已完成阶段回顾

| 阶段 | 名称 | 状态 | 关键组件 |
|-----|------|-----|--------|
| Phase 13 | 链路追踪 | ✅ | ChainID、Span |
| Phase 14 | Agent 角色 | ✅ | AgentRoles、Registry |
| Phase 15 | 工作流编排 | ✅ | WorkflowEngine |
| Phase 16 | 协作协议 | ✅ | MessageProtocol |
| Phase 17 | 任务分发与负载均衡 | ✅ | TaskDispatcher |
| Phase 18 | 状态同步 | ✅ | StateSync |
| Phase 19 | 监控与告警 | ✅ | MetricsRegistry、AlertManager |
| Phase 20 | 系统集成与协调 | ✅ | SystemCoordinator |
| Phase 21 | 输入层增强 | ✅ | TaskValidator |
| Phase 22 | 代码解析 | ✅ | EnhancedASTProcessor |
| Phase 23 | Agent 能力增强 | ✅ | AgentLearningEngine |
| Phase 24 | 配置与持久化 | ✅ | ConfigPersistence |
| Phase 25 | 缓存管理 | ✅ | CacheManager |
| Phase 26 | 日志系统增强 | ✅ | StructuredLogger |
| Phase 27 | Prometheus 指标 | ✅ | PrometheusRegistry |

## 下一步（Phase 28）

可选方向：
- **API 接口层**（REST/GraphQL）
- **WebSocket 通信**
- **任务队列**（Celery/RQ）
- **分布式追踪**（OpenTelemetry）
