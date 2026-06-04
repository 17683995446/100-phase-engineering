# Phase 35 - 分布式追踪与OpenTelemetry集成

## 概述

本阶段实现了完整的分布式追踪系统，基于OpenTelemetry标准，为整个系统提供了可观测性能力。

## 实现内容

### 1. 核心追踪模块 (`src/utils/telemetry.py`)

实现了完整的分布式追踪系统，包括：
- **Span**: 追踪基本单元，支持属性、事件、链接
- **Tracer**: Span创建和管理
- **SpanContext**: 追踪上下文，支持W3C Trace Context和B3格式
- **SpanExporter**: Span导出器基类，包含日志导出器、内存导出器、批量导出器
- **TracerProvider**: 全局Tracer管理
- **装饰器**: `@trace`装饰器，方便为函数添加追踪
- **上下文传播**: `extract_context()`和`inject_context()`函数

### 2. API层集成 (`src/api_layer/core.py`)

- **TracingMiddleware**: 分布式追踪中间件
- 自动为每个API请求创建Span
- 从请求头提取追踪上下文
- 将追踪上下文注入响应头
- 记录请求信息、状态码、响应时间

### 3. 任务调度层集成 (`src/scheduling_layer/task_queue.py`)

- **QueuedTask**: 添加trace_context字段保存追踪上下文
- **AsyncTaskQueue**: 自动保存和恢复追踪上下文
- 入队时保存当前追踪上下文
- 执行任务时恢复追踪上下文并创建任务Span
- 记录任务ID、优先级、重试次数、执行时间等

## 功能特性

### 分布式追踪
- 跨服务追踪上下文传播
- 支持W3C Trace Context和B3格式
- 嵌套Span支持，父子关系明确
- Span属性、事件、链接支持

### 多种导出方式
- 日志导出器：将Span导出到日志
- 内存导出器：用于测试
- 批量导出器：定期批量导出Span

### 易用的API
- `with tracer.span()`上下文管理器
- `@trace()`装饰器
- 全局`get_tracer()`便捷函数

## 测试结果

所有测试通过！✓

### 测试覆盖
- Span创建和导出
- 嵌套Span
- `@trace`装饰器
- 上下文传播
- API层追踪
- 任务队列追踪
- 错误追踪

## 使用示例

### 基础使用

```python
from src.utils.telemetry import get_tracer

tracer = get_tracer("my.service")

with tracer.span("my.operation") as span:
    span.set_attribute("key", "value")
    span.add_event("my.event", {"data": "test"})
    # 执行操作
```

### 使用装饰器

```python
from src.utils.telemetry import trace

@trace(name="my.function")
def my_function(x, y):
    return x + y

result = my_function(1, 2)
```

### 上下文传播

```python
from src.utils.telemetry import extract_context, inject_context

# 服务端：从请求头提取
context = extract_context(request.headers)
with tracer.span("server.operation", context=context):
    # 处理请求
    pass

# 客户端：注入到请求头
headers = {}
inject_context(headers)
response = requests.get(url, headers=headers)
```

## 未来改进方向

1. **导出器扩展**: 支持Jaeger、Zipkin等主流追踪系统
2. **采样策略**: 实现更灵活的采样策略
3. **性能优化**: 高并发下的性能优化
4. **可视化**: 集成追踪数据可视化界面

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/utils/telemetry.py` | 新增 | 分布式追踪核心模块 |
| `src/api_layer/core.py` | 修改 | 添加TracingMiddleware |
| `src/scheduling_layer/task_queue.py` | 修改 | 任务队列集成追踪 |
| `test_phase35_tracing.py` | 新增 | Phase 35测试文件 |

## 阶段成果

Phase 35成功完成，系统现在具有完整的分布式追踪能力，为可观测性奠定了坚实基础。
