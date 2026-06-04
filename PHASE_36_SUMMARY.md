# Phase 36 - 高级健康检查与系统状态监控

## 概述

本阶段实现了完整的健康检查与系统状态监控系统，提供了Kubernetes风格的存活探针、就绪探针和启动探针，为系统提供了全面的健康监控能力。

## 实现内容

### 1. 健康检查核心模块 (`src/utils/health.py`)

实现了灵活的健康检查框架：

#### 健康检查类型
- **ComponentHealthCheck**: 组件健康检查，支持自定义检查函数
- **ThresholdHealthCheck**: 阈值健康检查，基于指标阈值判断健康状态
- **DependencyHealthCheck**: 依赖健康检查，验证依赖服务可用性

#### 健康状态
- **HEALTHY**: 健康
- **DEGRADED**: 降级
- **UNHEALTHY**: 不健康
- **UNKNOWN**: 未知

#### 核心组件
- **HealthMonitor**: 健康监控器，管理所有健康检查
- **AggregatedHealthStatus**: 聚合健康状态
- **HealthCheckResult**: 单个检查结果

#### 特性
- 支持多种检查类型（存活、就绪、启动探针）
- 可配置的检查间隔和超时时间
- 完整的历史记录
- 集成分布式追踪

### 2. 系统健康检查 (`src/utils/system_health.py`)

预定义的系统级健康检查：

#### 检查项
- **system.memory**: 内存使用情况
- **system.gc**: 垃圾回收状态
- **system.threads**: 线程数量
- **cache.manager**: 缓存管理器状态
- **task.queue.manager**: 任务队列管理器状态

#### 功能
- 自动初始化系统健康检查
- 提供便捷的状态查询函数
- 支持Kubernetes探针模式

### 3. API层集成 (`src/api_layer/core.py`)

添加了4个健康检查端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 整体健康状态 |
| `/health/live` | GET | Kubernetes存活探针 |
| `/health/ready` | GET | Kubernetes就绪探针 |
| `/health/startup` | GET | Kubernetes启动探针 |

#### 响应格式
```json
{
  "status": "HEALTHY|DEGRADED|UNHEALTHY",
  "summary": {
    "total": 5,
    "healthy": 4,
    "degraded": 1,
    "unhealthy": 0,
    "unknown": 0
  },
  "components": {
    "component_name": {
      "status": "HEALTHY",
      "message": "Component is healthy",
      "details": {...},
      "duration_ms": 1.5
    }
  }
}
```

## 功能特性

### Kubernetes探针支持
- **Liveness Probe**: 检测应用是否存活
- **Readiness Probe**: 检测应用是否就绪
- **Startup Probe**: 检测应用是否启动完成

### 灵活的健康检查
- 自定义检查函数
- 阈值检查
- 依赖检查
- 历史记录

### 聚合状态
- 整体状态聚合
- 组件级别详情
- 统计信息

### 可观测性集成
- 分布式追踪
- 结构化日志
- Prometheus指标

## 测试结果

所有测试通过！✓

### 测试覆盖
- 组件健康检查
- 阈值健康检查
- 健康监控器
- 系统健康检查
- API健康端点

## 使用示例

### 1. 注册自定义健康检查

```python
from src.utils.health import (
    get_health_monitor,
    create_component_check,
    HealthCheckType
)

monitor = get_health_monitor()

def check_database():
    # 检查数据库连接
    return True

check = create_component_check(
    name="database",
    check_fn=check_database,
    check_type=HealthCheckType.READINESS,
    tags=["database", "infrastructure"]
)

monitor.register_check(check)
```

### 2. 使用阈值检查

```python
from src.utils.health import ThresholdHealthCheck

threshold_check = ThresholdHealthCheck(
    name="response_time",
    metric_fn=lambda: 0.95,  # 95th percentile
    healthy_threshold=200.0,  # < 200ms
    degraded_threshold=500.0,  # < 500ms
    higher_is_healthier=False
)
```

### 3. 查询健康状态

```python
from src.utils.system_health import get_liveness_status, setup_system_health_checks

# 初始化系统健康检查
setup_system_health_checks()

# 查询状态
liveness = get_liveness_status()
print(f"System is {liveness['status']}")
```

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/utils/health.py` | 新增 | 健康检查核心框架 |
| `src/utils/system_health.py` | 新增 | 系统健康检查实现 |
| `src/api_layer/core.py` | 修改 | 添加健康检查端点 |
| `test_phase36_health.py` | 新增 | Phase 36测试文件 |

## 阶段成果

Phase 36成功完成！系统现在具有：

1. ✅ 灵活的健康检查框架
2. ✅ Kubernetes风格的探针支持
3. ✅ 完整的系统健康监控
4. ✅ RESTful健康检查API
5. ✅ 与可观测性系统集成

## 未来改进方向

1. **健康检查持久化**: 将健康历史存储到数据库
2. **告警集成**: 与告警系统集成
3. **健康报告**: 自动生成健康报告
4. **自愈机制**: 基于健康状态触发自愈操作
5. **健康评分**: 计算整体健康评分

## 与Phase 35的集成

Phase 36与Phase 35（分布式追踪）完美集成：
- 健康检查集成分布式追踪
- 每个检查创建Span
- 检查结果记录到追踪系统
- 健康端点支持traceparent头

这使得健康状态完全可观测，方便问题定位和性能分析。
