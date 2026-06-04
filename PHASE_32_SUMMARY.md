# Phase 32: 任务队列系统

## 阶段概述

**阶段名称**: 任务队列系统
**完成状态**: ✅ 已完成
**测试结果**: 36 个测试用例全部通过
**系统总测试**: 293+ 个测试通过

## 核心设计原则

遵循 **异步解耦** 原则，提供完整的任务队列系统，支持异步任务调度、延迟执行、重试机制和优先级管理。

## 主要组件

### 1. 枚举类型

- **TaskStatus**: 任务状态（PENDING、QUEUED、RUNNING、COMPLETED、FAILED、RETRYING、CANCELLED）
- **TaskPriority**: 任务优先级（CRITICAL、HIGH、NORMAL、LOW、BACKGROUND）

### 2. 数据模型

- **TaskResult**: 任务结果（成功/失败、数据、错误信息、执行时间）
- **QueuedTask**: 队列任务（任务ID、函数、参数、优先级、状态、时间戳、重试次数、超时、依赖）
- **QueueStats**: 队列统计（任务总数、待处理、运行中、已完成、失败、重试）

### 3. 队列系统

- **AsyncTaskQueue**: 异步任务队列核心类
  - 入队/出队操作
  - 优先级队列管理
  - 多工作线程支持
  - 任务状态追踪
  - 失败重试机制
  - Prometheus 指标集成

### 4. 队列管理器

- **TaskQueueManager**: 任务队列管理器
  - 多队列管理
  - 统一的入队接口
  - 全局统计信息

### 5. 全局函数

- **get_task_queue_manager()**: 获取默认任务队列管理器
- **create_task_queue()**: 便捷创建队列函数
- **enqueue_task()**: 便捷入队函数

## 文件结构

```
src/scheduling_layer/
├── __init__.py           # 模块导出（包含任务队列组件）
├── state.py              # 状态管理
├── graph.py              # 工作流图
├── task_dispatcher.py    # 任务分发器
├── task_queue.py         # 任务队列系统 ✨
├── state_sync.py         # 状态同步
├── monitoring.py         # 监控告警
├── chain_id.py           # 链路追踪
├── event_tracker.py      # 事件追踪
└── dag_validator.py      # DAG 验证

test_task_queue.py        # 任务队列测试用例 ✨
```

## 与现有系统的集成

### 调度层集成

- 与 Phase 17 (TaskDispatcher) 协同工作
- 异步任务支持独立的队列处理
- 支持依赖任务链

### Prometheus 集成

- 任务入队/完成计数
- 运行中任务仪表盘
- 队列大小监控

### 结构化日志

- 任务入队、执行、完成、失败记录
- 包含任务ID、优先级、执行时间等上下文

## 使用示例

### 基本使用

```python
from src.scheduling_layer.task_queue import (
    AsyncTaskQueue,
    TaskPriority
)

# 创建队列
queue = AsyncTaskQueue(name="my-queue")

# 定义任务
def process_data(data):
    return f"Processed: {data}"

# 入队任务
task_id = queue.enqueue(
    process_data,
    "Hello",
    priority=TaskPriority.HIGH
)

# 启动队列处理
queue.start(num_workers=2)

# 获取任务状态
status = queue.get_task_status(task_id)
result = queue.get_task_result(task_id)

# 停止队列
queue.stop()
```

### 使用队列管理器

```python
from src.scheduling_layer.task_queue import (
    create_task_queue,
    enqueue_task,
    TaskPriority
)

# 创建队列
queue = create_task_queue("tasks", num_workers=4)

# 便捷入队
task_id = enqueue_task(
    "tasks",
    lambda: print("Hello!"),
    priority=TaskPriority.NORMAL
)
```

### 延迟任务

```python
from datetime import datetime, timedelta

queue = AsyncTaskQueue(name="delayed")

# 延迟 10 秒执行
future_time = datetime.now() + timedelta(seconds=10)
queue.enqueue(
    my_task,
    scheduled_at=future_time
)
```

### 失败重试

```python
queue = AsyncTaskQueue(name="retry-test")

def unreliable_task():
    # 可能失败的逻辑
    raise ValueError("Temporary failure")

# 最多重试 3 次
task_id = queue.enqueue(
    unreliable_task,
    max_retries=3
)
```

### 带超时的任务

```python
queue = AsyncTaskQueue(name="timeout-test")

def long_running_task():
    # 可能运行很久的任务
    import time
    time.sleep(100)

# 设置 5 秒超时
queue.enqueue(
    long_running_task,
    timeout=5.0
)
```

## 已完成阶段回顾 (Phase 13-32)

| 阶段 | 名称 | 状态 | 关键组件 |
|------|------|------|---------|
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
| Phase 28 | API 接口层 | ✅ | APIApp、Route、Middleware |
| Phase 29 | WebSocket 通信 | ✅ | WebSocketApp、Channel、Handler |
| Phase 30 | GraphQL 支持 | ✅ | GraphQLApp、Schema、Resolver |
| Phase 31 | API 文档系统 | ✅ | APIDocumentation、Builder、OpenAPI |
| **Phase 32** | **任务队列系统** | **✅** | **AsyncTaskQueue、QueueManager** |

## 下一步 (Phase 33+)

可选方向：
- 分布式追踪（OpenTelemetry）
- 数据库 ORM 集成
- 性能优化与基准测试
- 部署与容器化
- 安全与认证
- 任务调度（Cron/定时任务）
