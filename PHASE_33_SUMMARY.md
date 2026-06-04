# Phase 33: 定时任务调度系统

## 阶段概述

**阶段名称**: 定时任务调度系统
**完成状态**: ✅ 已完成
**测试结果**: 33 个测试用例通过
**系统总测试**: 326+ 个测试通过

## 核心设计原则

遵循 **解耦与定时精确** 原则，提供完整的定时任务调度功能，支持多种调度方式，与现有系统无缝集成。

## 主要组件

### 1. 枚举类型

- **JobStatus**: 定时任务状态
  - PENDING: 等待中
  - SCHEDULED: 已安排
  - RUNNING: 运行中
  - COMPLETED: 已完成
  - FAILED: 失败
  - PAUSED: 已暂停
  - CANCELLED: 已取消

- **JobType**: 定时任务类型
  - CRON: Cron 表达式
  - INTERVAL: 固定间隔
  - DELAY: 一次性延迟
  - DAILY: 每日固定时间
  - WEEKLY: 每周固定时间

### 2. 数据模型

- **JobResult**: 定时任务执行结果
  - success: 是否成功
  - data: 结果数据
  - error: 错误信息
  - execution_time_ms: 执行耗时
  - started_at: 开始时间
  - completed_at: 完成时间

- **ScheduledJob**: 已安排的任务
  - job_id: 任务ID
  - func: 任务函数
  - job_type: 任务类型
  - priority: 任务优先级
  - status: 任务状态
  - args/kwargs: 函数参数
  - created_at: 创建时间
  - next_run: 下次运行时间
  - last_run: 上次运行时间
  - run_count: 运行次数
  - success_count: 成功次数
  - failure_count: 失败次数
  - last_result: 上次结果
  - cron_expr: Cron 表达式
  - interval_seconds: 间隔秒数
  - delay_seconds: 延迟秒数
  - daily_time: 每日时间
  - weekly_day: 每周星期几
  - weekly_time: 每周时间
  - max_runs: 最大运行次数
  - metadata: 元数据

- **JobStats**: 任务统计
  - total_jobs: 总任务数
  - pending_jobs: 等待任务数
  - running_jobs: 运行任务数
  - completed_jobs: 完成任务数
  - failed_jobs: 失败任务数
  - paused_jobs: 暂停任务数
  - total_executions: 总执行次数
  - avg_execution_time_ms: 平均执行时间

### 3. 解析器

- **CronParser**: Cron 表达式解析器
  - parse(): 解析 Cron 表达式
  - calculate_next_run(): 计算下次运行时间

### 4. 执行器

- **ScheduledJobExecutor**: 定时任务执行器
  - 负责执行单个任务
  - 记录执行结果
  - 处理异常

### 5. 调度器

- **TaskScheduler**: 任务调度器核心类
  - 任务注册与管理
  - 多工作线程池
  - 优先级队列
  - Prometheus 指标集成
  - 任务暂停/恢复
  - 任务取消
  - 统计信息

### 6. 全局函数

- **get_default_scheduler()**: 获取默认调度器
- **set_default_scheduler()**: 设置默认调度器
- **schedule_cron()**: 安排 Cron 任务（便捷函数）
- **schedule_interval()**: 安排间隔任务（便捷函数）
- **schedule_delay()**: 安排延迟任务（便捷函数）

## 文件结构

```
src/scheduling_layer/
├── __init__.py          # 模块导出（含调度器组件）
├── state.py             # 状态管理
├── graph.py             # 工作流图
├── task_dispatcher.py   # 任务分发器
├── task_queue.py        # 异步任务队列
├── scheduler.py         # 定时任务调度器 ✨
├── state_sync.py        # 状态同步
├── monitoring.py        # 监控告警
├── chain_id.py          # 链路追踪
├── event_tracker.py     # 事件追踪
└── dag_validator.py     # DAG 验证

test_scheduler.py        # 定时任务调度器测试用例 ✨
```

## 使用示例

### 基本使用

```python
from src.scheduling_layer.scheduler import (
    TaskScheduler,
    TaskPriority
)

# 创建调度器
scheduler = TaskScheduler(name="my-scheduler")

# 启动调度器
scheduler.start(num_workers=2)

# 定义任务
def cleanup_data():
    print("Cleaning up data...")

# 添加延迟任务（5秒后执行）
job_id = scheduler.add_delay_job(
    cleanup_data, 5.0)

# 添加间隔任务（每10秒执行，最多5次）
job_id2 = scheduler.add_interval_job(
    cleanup_data, 10.0,
    max_runs=5)

# 添加每日任务（每天上午9点执行）
job_id3 = scheduler.add_daily_job(
    cleanup_data, "09:00")

# 停止调度器
scheduler.stop()
```

### Cron 任务

```python
# 添加 Cron 任务（每小时执行）
job_id = scheduler.add_cron_job(
    cleanup_data, "0 * * * *",
    priority=TaskPriority.HIGH)

# 获取任务
job = scheduler.get_job(job_id)

# 暂停任务
scheduler.pause_job(job_id)

# 恢复任务
scheduler.resume_job(job_id)

# 取消任务
scheduler.cancel_job(job_id)
```

### 便捷函数

```python
from src.scheduling_layer.scheduler import (
    schedule_cron,
    schedule_interval,
    schedule_delay
)

# 使用全局调度器
schedule_delay(lambda: print("Hello!"), 3.0)

schedule_interval(lambda: print("Hi!"), 2.0, max_runs=10)
```

### 任务管理

```python
# 获取所有任务
all_jobs = scheduler.get_jobs()

# 获取特定状态的任务
pending_jobs = scheduler.get_jobs(status=JobStatus.SCHEDULED)
running_jobs = scheduler.get_jobs(status=JobStatus.RUNNING)

# 获取统计信息
stats = scheduler.get_stats()
print(f"Total jobs: {stats.total_jobs}")
print(f"Running jobs: {stats.running_jobs}")
print(f"Total executions: {stats.total_executions}")
```

## 与现有系统的集成

### Phase 32 任务队列集成

- 与 `TaskQueue` 配合使用，实现异步任务与定时任务的结合
- 优先级调度系统统一

### Phase 27 Prometheus 集成

- 任务提交计数
- 任务完成计数
- 任务失败计数
- 运行任务仪表盘

### 调度层集成

- 与 `TaskDispatcher` 无缝结合
- 支持工作流定时触发

## 已完成阶段回顾 (Phase 13-33)

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
| Phase 32 | 任务队列系统 | ✅ | AsyncTaskQueue、QueueManager |
| **Phase 33** | **定时任务调度系统** | **✅** | **TaskScheduler、CronParser、ScheduledJob** |

## 下一步 (Phase 34+)

可选方向：
- 分布式追踪（OpenTelemetry）
- 数据库 ORM 集成
- 性能优化与基准测试
- 部署与容器化
- 安全与认证
- Web 管理界面
- 任务持久化与恢复
